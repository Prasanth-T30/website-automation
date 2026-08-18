"""UserRepository against the real Firestore emulator."""

from __future__ import annotations

import uuid

import pytest

from app.models.user import UserRole
from app.repositories.users import EmailAlreadyExists, UserRepository
from tests.conftest import requires_emulator


@pytest.fixture
def repo(firestore_client):
    return UserRepository(firestore_client)


def _email(prefix: str) -> str:
    """Unique address per run.

    Writes are isolated per project, but anything the emulator loaded via
    `--import` is readable from every project — so a fixed address like
    `admin@dvein.in` collides with the seeded dev account and the create fails.
    """
    return f"{prefix}-{uuid.uuid4().hex[:8]}@dvein.in"


@requires_emulator
def test_create_and_get_roundtrip(repo: UserRepository):
    address = _email("Admin")
    user = repo.create(
        email=address.upper(),  # mixed case, on purpose
        full_name="Admin Person",
        password_hash="hashed",
        role=UserRole.admin,
        phone=None,
        must_change_password=True,
    )
    assert user.id
    assert user.email == address.lower()  # normalized
    assert user.token_version == 0

    fetched = repo.get(user.id)
    assert fetched is not None
    assert fetched.full_name == "Admin Person"


@requires_emulator
def test_get_by_email_uses_the_index(repo: UserRepository):
    address = _email("hr1")
    created = repo.create(
        email=address,
        full_name="HR One",
        password_hash="hashed",
        role=UserRole.hr,
        phone=None,
        must_change_password=False,
    )
    found = repo.get_by_email(address.upper())  # case-insensitive lookup
    assert found is not None
    assert found.id == created.id


@requires_emulator
def test_duplicate_email_is_rejected(repo: UserRepository):
    repo.create(
        email="dup@dvein.in",
        full_name="First",
        password_hash="hashed",
        role=UserRole.hr,
        phone=None,
        must_change_password=False,
    )
    with pytest.raises(EmailAlreadyExists):
        repo.create(
            email="dup@dvein.in",
            full_name="Second",
            password_hash="hashed",
            role=UserRole.hr,
            phone=None,
            must_change_password=False,
        )


@requires_emulator
def test_get_unknown_id_returns_none(repo: UserRepository):
    assert repo.get("does-not-exist") is None


@requires_emulator
def test_get_by_unknown_email_returns_none(repo: UserRepository):
    assert repo.get_by_email("nobody@dvein.in") is None


@requires_emulator
def test_bump_token_version_is_atomic_increment(repo: UserRepository):
    user = repo.create(
        email="tok@dvein.in",
        full_name="Token Test",
        password_hash="hashed",
        role=UserRole.hr,
        phone=None,
        must_change_password=False,
    )
    repo.bump_token_version(user.id)
    repo.bump_token_version(user.id)
    assert repo.get(user.id).token_version == 2


@requires_emulator
def test_list_all_sorted_by_role_then_name(repo: UserRepository):
    repo.create(
        email="z@dvein.in", full_name="Zeta HR", password_hash="h", role=UserRole.hr,
        phone=None, must_change_password=False,
    )
    repo.create(
        email="a@dvein.in", full_name="Alpha Admin", password_hash="h", role=UserRole.admin,
        phone=None, must_change_password=False,
    )
    repo.create(
        email="a2@dvein.in", full_name="Alpha HR", password_hash="h", role=UserRole.hr,
        phone=None, must_change_password=False,
    )
    # Scoped to this test's own rows. Imported dev data is readable from every
    # project, so asserting over the whole collection would fail for reasons
    # that have nothing to do with sort order.
    mine = {"Alpha Admin", "Alpha HR", "Zeta HR"}
    ordered = [(u.role.value, u.full_name) for u in repo.list_all() if u.full_name in mine]
    assert ordered == [
        ("admin", "Alpha Admin"),
        ("hr", "Alpha HR"),
        ("hr", "Zeta HR"),
    ]


@requires_emulator
def test_update_email_moves_the_index(repo: UserRepository):
    user = repo.create(
        email="old@dvein.in", full_name="Email Mover", password_hash="h", role=UserRole.hr,
        phone=None, must_change_password=False,
    )
    repo.update_email(user.id, "New@Dvein.In")

    assert repo.get(user.id).email == "new@dvein.in"
    assert repo.get_by_email("new@dvein.in") is not None
    assert repo.get_by_email("old@dvein.in") is None  # old index entry is gone


@requires_emulator
def test_update_email_to_an_existing_address_is_rejected(repo: UserRepository):
    repo.create(
        email="taken@dvein.in", full_name="First", password_hash="h", role=UserRole.hr,
        phone=None, must_change_password=False,
    )
    mover = repo.create(
        email="mover@dvein.in", full_name="Second", password_hash="h", role=UserRole.hr,
        phone=None, must_change_password=False,
    )
    with pytest.raises(EmailAlreadyExists):
        repo.update_email(mover.id, "taken@dvein.in")
    # Rejected attempt must not have moved the index halfway.
    assert repo.get_by_email("mover@dvein.in") is not None


@requires_emulator
def test_delete_removes_the_user_and_the_email_index(repo: UserRepository):
    user = repo.create(
        email="gone@dvein.in", full_name="To Delete", password_hash="h", role=UserRole.hr,
        phone=None, must_change_password=False,
    )
    repo.delete(user.id)

    assert repo.get(user.id) is None
    assert repo.get_by_email("gone@dvein.in") is None


@requires_emulator
def test_delete_frees_the_email_for_reuse(repo: UserRepository):
    first = repo.create(
        email="reuse@dvein.in", full_name="First", password_hash="h", role=UserRole.hr,
        phone=None, must_change_password=False,
    )
    repo.delete(first.id)

    # Would previously have raised EmailAlreadyExists against the stale index.
    second = repo.create(
        email="reuse@dvein.in", full_name="Second", password_hash="h", role=UserRole.hr,
        phone=None, must_change_password=False,
    )
    assert second.id != first.id
    assert repo.get_by_email("reuse@dvein.in").id == second.id


@requires_emulator
def test_delete_unknown_id_is_a_no_op(repo: UserRepository):
    repo.delete("does-not-exist")  # must not raise


@requires_emulator
def test_count_active_admins_excludes_inactive_and_hr(repo: UserRepository):
    # Any imported dev accounts are visible here too, so this asserts on the
    # delta this test causes rather than on an absolute count.
    baseline = repo.count_active_admins()

    a1 = repo.create(
        email=_email("a1"), full_name="Admin One", password_hash="h", role=UserRole.admin,
        phone=None, must_change_password=False,
    )
    repo.create(
        email=_email("a2"), full_name="Admin Two", password_hash="h", role=UserRole.admin,
        phone=None, must_change_password=False,
    )
    # An HR must not be counted at all.
    repo.create(
        email=_email("h1"), full_name="HR One", password_hash="h", role=UserRole.hr,
        phone=None, must_change_password=False,
    )
    assert repo.count_active_admins() == baseline + 2
    assert repo.count_active_admins(excluding=a1.id) == baseline + 1

    repo.update_fields(a1.id, {"is_active": False})
    assert repo.count_active_admins() == baseline + 1
