"""Attendance marking — idempotent per (student, date), owner-gated."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AttendanceRepo, CurrentUser, StudentRepo
from app.models.user import UserRole
from app.schemas.attendance import AttendanceMark, AttendanceOut

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("", response_model=list[AttendanceOut])
def list_attendance(
    attendance: AttendanceRepo,
    students: StudentRepo,
    user: CurrentUser,
    student_id: str | None = Query(None),
    batch_id: str | None = Query(None),
    date_filter: str | None = Query(None, alias="date"),
) -> list[AttendanceOut]:
    rows = attendance.list_all(student_id=student_id, batch_id=batch_id, date_filter=date_filter)
    if user.role is not UserRole.admin:
        # Batches are shared, but the roster inside one is not: an HR sees
        # attendance for their own students only, matching the students list.
        own = {s.id for s in students.list_all(owner_id=user.id)}
        rows = [a for a in rows if a.student_id in own]
    return [AttendanceOut.model_validate(a) for a in rows]


@router.post("", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def mark_attendance(
    data: AttendanceMark, attendance: AttendanceRepo, students: StudentRepo, user: CurrentUser
) -> AttendanceOut:
    student = students.get(data.student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found.")
    if user.role is not UserRole.admin and student.owner_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only this student's owner can mark attendance."
        )

    record = attendance.mark(
        student_id=data.student_id,
        batch_id=data.batch_id or student.batch_id,
        date_iso=data.date.isoformat(),
        status=data.status,
        notes=data.notes,
    )
    return AttendanceOut.model_validate(record)
