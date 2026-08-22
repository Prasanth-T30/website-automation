"""A forced password change has to actually stop you working.

The point of a one-time password is that its useful life ends at first
sign-in. That only holds if the rest of the API refuses to serve the holder
until it is replaced — otherwise the flag is decorative and the temporary
credential is just a working password, written down or sent over chat as
those things are.

The route audit below is the part that matters long-term: swapping every
endpoint by hand fixes today, but nothing stops the next one being written
against CurrentUser out of habit. This fails the build when that happens.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.users import UserRepository
from tests.conftest import requires_emulator


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ── The audit ────────────────────────────────────────────────────────────
#
# This reads the source rather than the running route table. An earlier
# version walked FastAPI's dependency tree, which looked more rigorous and was
# in fact useless: this version keeps included routers unflattened and builds
# their dependants lazily, so an endpoint switched back to CurrentUser simply
# vanished from the walk instead of being reported. A guard that cannot fail is
# worse than none, because it is trusted.
#
# The annotation is what we control and what a future edit will touch, so that
# is what gets checked.

ROUTERS = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"

# Only these may take CurrentUser — they have to keep working *during* a
# forced change, or the user is trapped: unable to work, unable to fix it.
MAY_SKIP_THE_GATE = {"auth.py"}

# No auth of any kind: the public form and the plumbing.
NOT_AUTHENTICATED = {"public.py", "router.py", "__init__.py"}


def _routers_using(annotation: str) -> dict[str, int]:
    found = {}
    for f in sorted(ROUTERS.glob("*.py")):
        if f.name in NOT_AUTHENTICATED:
            continue
        n = f.read_text(encoding="utf-8").count(f": {annotation}")
        if n:
            found[f.name] = n
    return found


def test_no_router_outside_auth_takes_an_ungated_user():
    offenders = {
        name: n for name, n in _routers_using("CurrentUser").items()
        if name not in MAY_SKIP_THE_GATE
    }
    assert not offenders, (
        "these routers accept a user who has not replaced their temporary "
        f"password: {offenders}"
    )


def test_the_gate_is_actually_applied_somewhere():
    """Guards against the check above passing because everything was renamed
    or moved — an empty codebase satisfies 'no offenders' perfectly."""
    gated = _routers_using("ActiveUser")
    assert len(gated) >= 8, f"only {len(gated)} routers use the gate: {gated}"
    assert sum(gated.values()) >= 25, f"only {sum(gated.values())} gated endpoints"


def test_auth_keeps_its_ungated_endpoints():
    """/auth/me and /auth/change-password must stay reachable mid-change."""
    assert _routers_using("CurrentUser").get("auth.py", 0) >= 2


def test_admin_privileges_sit_behind_the_gate():
    """AdminUser must derive from ActiveUser, not CurrentUser — creating
    accounts and resetting passwords are the last things that should work
    while your own credential is pending replacement."""
    deps = (ROUTERS.parent / "deps.py").read_text(encoding="utf-8")
    assert "def require_admin(user: ActiveUser)" in deps


# ── The behaviour, end to end ────────────────────────────────────────────

pytestmark_emulator = requires_emulator


@pytest.fixture
def client():
    from app.main import app

    app.state.limiter.reset()
    return TestClient(app)


@pytest.fixture
def user_repo():
    from app.core.firebase import get_firestore

    return UserRepository(get_firestore())


def _pending_user(client: TestClient, user_repo: UserRepository, *, role: UserRole) -> str:
    """Signed in, holding a password they have been told to replace."""
    email = f"{_unique('e2e-pending')}@dvein.in"
    user_repo.create(
        email=email, full_name="Pending Change", role=role,
        password_hash=hash_password("temporary-one-time-1"), phone=None,
        must_change_password=True,
    )
    res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "temporary-one-time-1"}
    )
    assert res.status_code == 200
    assert res.json()["user"]["must_change_password"] is True
    return client.cookies["dvein_csrf"]


@requires_emulator
def test_an_hr_cannot_read_or_write_until_they_change_it(client: TestClient, user_repo):
    _pending_user(client, user_repo, role=UserRole.hr)

    for path in ("/api/v1/students", "/api/v1/payments", "/api/v1/applications",
                 "/api/v1/reports", "/api/v1/batches", "/api/v1/notifications"):
        assert client.get(path).status_code == 403, f"{path} was reachable"


@requires_emulator
def test_an_admin_cannot_manage_accounts_until_they_change_it(client: TestClient, user_repo):
    """Creating accounts and resetting other people's passwords are the last
    things that should work while your own credential is pending replacement."""
    csrf = _pending_user(client, user_repo, role=UserRole.admin)

    assert client.get("/api/v1/admin/users").status_code == 403
    assert client.get("/api/v1/admin/hr-performance").status_code == 403
    created = client.post(
        "/api/v1/admin/users",
        json={"email": "sneak@dvein.in", "full_name": "Sneak", "role": "hr"},
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 403


@requires_emulator
def test_they_can_still_see_who_they_are_and_change_it(client: TestClient, user_repo):
    csrf = _pending_user(client, user_repo, role=UserRole.hr)

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True

    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "temporary-one-time-1", "new_password": "a-chosen-password-9"},
        headers={"X-CSRF-Token": csrf},
    )
    assert changed.status_code == 200, changed.text


@requires_emulator
def test_everything_opens_up_once_they_have(client: TestClient, user_repo):
    csrf = _pending_user(client, user_repo, role=UserRole.hr)
    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "temporary-one-time-1", "new_password": "a-chosen-password-9"},
        headers={"X-CSRF-Token": csrf},
    )
    assert changed.status_code == 200

    for path in ("/api/v1/students", "/api/v1/payments", "/api/v1/applications",
                 "/api/v1/reports", "/api/v1/batches", "/api/v1/notifications"):
        assert client.get(path).status_code == 200, f"{path} still blocked after the change"
