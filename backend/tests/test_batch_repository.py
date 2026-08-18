"""BatchRepository against the real Firestore emulator."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.repositories.batches import BatchRepository, DuplicateBatchCode
from tests.conftest import requires_emulator


@pytest.fixture
def repo(firestore_client):
    return BatchRepository(firestore_client)


@requires_emulator
def test_create_and_get(repo: BatchRepository):
    b = repo.create(
        code="JAVA-01", domain="Full Stack Java", start_date="2026-09-01", end_date="2026-10-01",
        capacity=20, notes=None, created_by_id="admin-1",
    )
    assert b.status == "upcoming"
    assert repo.get(b.id) is not None


@requires_emulator
def test_duplicate_code_is_rejected(repo: BatchRepository):
    repo.create(
        code="PY-01", domain="Full Stack Python", start_date="2026-09-01", end_date="2026-10-01",
        capacity=20, notes=None, created_by_id="admin-1",
    )
    with pytest.raises(DuplicateBatchCode):
        repo.create(
            code="PY-01", domain="Full Stack Python", start_date="2026-09-01", end_date="2026-10-01",
            capacity=20, notes=None, created_by_id="admin-1",
        )


@requires_emulator
def test_sync_lifecycle_flips_active_past_end_date_to_completed(repo: BatchRepository):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    b = repo.create(
        code="EXP-01", domain="Software Testing", start_date="2026-01-01", end_date=yesterday,
        capacity=10, notes=None, created_by_id="admin-1",
    )
    repo.update_fields(b.id, {"status": "active"})

    changed = repo.sync_lifecycle()
    assert any(e.id == b.id for e in changed)
    assert repo.get(b.id).status == "completed"


@requires_emulator
def test_sync_lifecycle_leaves_future_active_batches_alone(repo: BatchRepository):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    b = repo.create(
        code="FUT-01", domain="Software Testing", start_date="2026-01-01", end_date=tomorrow,
        capacity=10, notes=None, created_by_id="admin-1",
    )
    repo.update_fields(b.id, {"status": "active"})

    repo.sync_lifecycle()
    assert repo.get(b.id).status == "active"


@requires_emulator
def test_sync_lifecycle_activates_upcoming_batch_once_started(repo: BatchRepository):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    b = repo.create(
        code="START-01", domain="Software Testing", start_date=yesterday, end_date=tomorrow,
        capacity=10, notes=None, created_by_id="admin-1",
    )
    assert b.status == "upcoming"

    changed = repo.sync_lifecycle()
    assert any(e.id == b.id for e in changed)
    assert repo.get(b.id).status == "active"


@requires_emulator
def test_sync_lifecycle_leaves_future_upcoming_batches_alone(repo: BatchRepository):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    later = (date.today() + timedelta(days=30)).isoformat()
    b = repo.create(
        code="LATER-01", domain="Software Testing", start_date=tomorrow, end_date=later,
        capacity=10, notes=None, created_by_id="admin-1",
    )

    repo.sync_lifecycle()
    assert repo.get(b.id).status == "upcoming"


@requires_emulator
def test_delete_removes_the_code_index(repo: BatchRepository):
    b = repo.create(
        code="DEL-01", domain="Software Testing", start_date="2026-09-01", end_date="2026-10-01",
        capacity=10, notes=None, created_by_id="admin-1",
    )
    repo.delete(b.id)
    assert repo.get(b.id) is None

    # Code must be free for reuse — proves the batch_codes index was cleaned up.
    reused = repo.create(
        code="DEL-01", domain="Software Testing", start_date="2026-09-01", end_date="2026-10-01",
        capacity=10, notes=None, created_by_id="admin-1",
    )
    assert reused.id != b.id
