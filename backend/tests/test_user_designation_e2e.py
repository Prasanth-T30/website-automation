"""Job titles on user accounts.

A designation says what someone *is* — Executive Head, Managing Director.
`role` says what the software lets them *do* — admin or hr. They are separate
fields on purpose: every permission check in this codebase branches on `role`,
so folding job titles into it would mean either inventing an access level per
title or having most of them quietly mean "hr".

The tests worth having are the ones that pin that separation down, and that
a title the API would reject can never be stored.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import DESIGNATION_LABELS, DESIGNATIONS
from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.users import UserRepository
from tests.conftest import requires_emulator

pytestmark = requires_emulator


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def client():
    from app.main import app

    app.state.limiter.reset()
    return TestClient(app)


@pytest.fixture
def db():
    from app.core.firebase import get_firestore

    return get_firestore()


def _admin(client: TestClient, db) -> str:
    email = f"{_unique('desig')}@dvein.in"
    UserRepository(db).create(
        email=email, full_name="Designation Admin", role=UserRole.admin,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"}
    )
    assert res.status_code == 200, res.text
    return client.cookies["dvein_csrf"]


def _new_user(client: TestClient, csrf: str, **overrides):
    body = {
        "email": f"{_unique('staff')}@dvein.in",
        "full_name": "Staff Member",
        "password": "a-real-password-1",
        "role": "hr",
    }
    body.update(overrides)
    return client.post("/api/v1/admin/users", json=body, headers={"X-CSRF-Token": csrf})


# ── the list itself ──────────────────────────────────────────────────────


def test_every_requested_title_is_offered():
    assert list(DESIGNATION_LABELS.values()) == [
        "Executive HR",
        "Business Development Executive",
        "HR",
        "Technical Lead",
        "Executive Head",
        "Managing Director",
        "Director",
    ]


def test_the_console_is_told_what_the_api_will_accept(client, db):
    """Served rather than hard-coded twice, so a title in the dropdown that
    the API would refuse cannot exist."""
    _admin(client, db)
    offered = client.get("/api/v1/admin/users/designations").json()
    assert offered == DESIGNATION_LABELS
    assert set(offered) == set(DESIGNATIONS)


def test_only_an_admin_can_read_the_list(client, db):
    assert client.get("/api/v1/admin/users/designations").status_code == 401


# ── recording one ────────────────────────────────────────────────────────


@pytest.mark.parametrize("designation", DESIGNATIONS)
def test_every_title_can_be_given_to_a_user(client, db, designation):
    csrf = _admin(client, db)
    res = _new_user(client, csrf, designation=designation)
    assert res.status_code == 201, res.text
    assert res.json()["designation"] == designation


def test_an_invented_title_is_refused(client, db):
    csrf = _admin(client, db)
    assert _new_user(client, csrf, designation="chief_wizard").status_code == 422


def test_a_user_may_have_no_title_at_all(client, db):
    """Accounts created before designations existed have none, and reading
    one back must not fail."""
    csrf = _admin(client, db)
    for missing in ({}, {"designation": None}, {"designation": ""}):
        res = _new_user(client, csrf, **missing)
        assert res.status_code == 201, res.text
        assert res.json()["designation"] is None


def test_a_title_can_be_changed_later(client, db):
    csrf = _admin(client, db)
    uid = _new_user(client, csrf, designation="hr").json()["id"]

    res = client.patch(f"/api/v1/admin/users/{uid}",
                       json={"designation": "executive_head"},
                       headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200, res.text
    assert res.json()["designation"] == "executive_head"


def test_changing_a_title_leaves_their_access_alone(client, db):
    """The whole point of the split: a promotion on paper is not a promotion
    in the software."""
    csrf = _admin(client, db)
    uid = _new_user(client, csrf, role="hr", designation="hr").json()["id"]

    res = client.patch(f"/api/v1/admin/users/{uid}",
                       json={"designation": "managing_director"},
                       headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200, res.text
    assert res.json()["designation"] == "managing_director"
    assert res.json()["role"] == "hr"


# ── the two ideas stay independent ───────────────────────────────────────


def test_a_managing_director_can_hold_ordinary_access(client, db):
    csrf = _admin(client, db)
    res = _new_user(client, csrf, role="hr", designation="managing_director")
    assert res.status_code == 201, res.text
    assert (res.json()["role"], res.json()["designation"]) == ("hr", "managing_director")


def test_an_hr_by_title_can_hold_administrator_access(client, db):
    csrf = _admin(client, db)
    res = _new_user(client, csrf, role="admin", designation="hr")
    assert res.status_code == 201, res.text
    assert (res.json()["role"], res.json()["designation"]) == ("admin", "hr")


def test_a_title_grants_nothing_on_its_own(client, db):
    """An Executive Head with hr access must still be refused admin-only
    surfaces — otherwise the title would be a privilege escalation."""
    csrf = _admin(client, db)
    email = f"{_unique('head')}@dvein.in"
    created = _new_user(client, csrf, email=email, role="hr",
                        designation="executive_head", password="a-real-password-1")
    assert created.status_code == 201, created.text
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})

    client.post("/api/v1/auth/login",
                json={"email": email, "password": "a-real-password-1"})
    assert client.get("/api/v1/admin/users").status_code == 403
    assert client.get("/api/v1/admin/hr-performance").status_code == 403
