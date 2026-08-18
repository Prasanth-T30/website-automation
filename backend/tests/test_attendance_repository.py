"""AttendanceRepository against the real Firestore emulator."""

from __future__ import annotations

import pytest

from app.repositories.attendance import AttendanceRepository
from tests.conftest import requires_emulator


@pytest.fixture
def repo(firestore_client):
    return AttendanceRepository(firestore_client)


def _mark(repo, student_id, date_iso, status, *, batch_id=None, notes=None):
    return repo.mark(
        student_id=student_id, batch_id=batch_id, date_iso=date_iso, status=status, notes=notes
    )


@requires_emulator
def test_mark_creates_a_record(repo: AttendanceRepository):
    rec = _mark(repo, "student-1", "2026-09-01", "present", batch_id="batch-1")
    assert rec.status == "present"
    assert rec.id == "student-1__2026-09-01"


@requires_emulator
def test_marking_the_same_student_and_date_twice_overwrites_not_duplicates(
    repo: AttendanceRepository,
):
    _mark(repo, "student-2", "2026-09-01", "present", batch_id="batch-1")
    _mark(repo, "student-2", "2026-09-01", "absent", batch_id="batch-1", notes="sick")

    rows = repo.list_all(student_id="student-2")
    assert len(rows) == 1
    assert rows[0].status == "absent"
    assert rows[0].notes == "sick"


@requires_emulator
def test_created_at_is_preserved_across_an_overwrite(repo: AttendanceRepository):
    first = _mark(repo, "student-3", "2026-09-01", "present")
    second = _mark(repo, "student-3", "2026-09-01", "late")
    assert second.created_at == first.created_at
    assert second.updated_at != first.created_at or second.status != first.status


@requires_emulator
def test_list_all_filters_by_batch_and_date(repo: AttendanceRepository):
    _mark(repo, "s-a", "2026-09-01", "present", batch_id="batch-x")
    _mark(repo, "s-b", "2026-09-01", "present", batch_id="batch-y")
    _mark(repo, "s-a", "2026-09-02", "absent", batch_id="batch-x")

    by_batch = repo.list_all(batch_id="batch-x")
    assert {r.student_id for r in by_batch} == {"s-a"}
    assert len(by_batch) == 2

    by_date = repo.list_all(batch_id="batch-x", date_filter="2026-09-01")
    assert len(by_date) == 1
    assert by_date[0].student_id == "s-a"
