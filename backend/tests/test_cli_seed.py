"""Seeding the sign-in accounts.

The rule the deployment depends on: an account whose password this CLI
generated must be forced to change it at first login. An operator who chose
one in .env is trusted to have meant it.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.firebase import get_firestore
from app.repositories.users import UserRepository
from tests.conftest import requires_emulator

pytestmark = requires_emulator


@pytest.fixture
def seeded(monkeypatch):
    """Run `seed` against throwaway addresses and hand back what it made."""
    from app import cli
    from app.core.config import settings

    tag = uuid.uuid4().hex[:8]
    admin = f"seed-admin-{tag}@dvein.in"
    hrs = [(f"seed-hr{i}-{tag}@dvein.in", f"HR {i}") for i in (1, 2, 3)]
    monkeypatch.setattr(cli, "HR_SEEDS", hrs)
    monkeypatch.setattr(settings, "seed_admin_email", admin)

    created: list[str] = []

    def run() -> dict[str, dict]:
        assert cli.seed() == 0
        repo = UserRepository(get_firestore())
        out = {}
        for addr in [admin, *[e for e, _ in hrs]]:
            user = repo.get_by_email(addr)
            assert user is not None, addr
            created.append(user.id)
            out[addr] = user
        return out

    yield run

    db = get_firestore()
    for uid in created:
        db.collection("users").document(uid).delete()
    for addr in [admin, *[e for e, _ in hrs]]:
        db.collection("user_emails").document(addr).delete()


def test_a_generated_password_must_be_changed(seeded, monkeypatch):
    """The whole point of a temporary password."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "seed_admin_password", None)
    monkeypatch.setattr(settings, "seed_hr_password", None)

    for addr, user in seeded().items():
        assert user.must_change_password is True, addr


def test_a_blank_env_value_still_counts_as_generated(seeded, monkeypatch):
    """`SEED_ADMIN_PASSWORD=` is what .env.example ships.

    pydantic-settings hands that back as "", not None. Reading it as an
    operator's deliberate choice left every seeded account ungated, which is
    the one thing seeding must never do.
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "seed_admin_password", "")
    monkeypatch.setattr(settings, "seed_hr_password", "")

    for addr, user in seeded().items():
        assert user.must_change_password is True, addr


def test_an_operator_chosen_password_is_left_alone(seeded, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "seed_admin_password", "chosen-on-purpose-1")
    monkeypatch.setattr(settings, "seed_hr_password", "chosen-on-purpose-2")

    for addr, user in seeded().items():
        assert user.must_change_password is False, addr
