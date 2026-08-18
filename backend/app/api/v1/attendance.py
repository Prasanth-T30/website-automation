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
    _: CurrentUser,
    student_id: str | None = Query(None),
    batch_id: str | None = Query(None),
    date_filter: str | None = Query(None, alias="date"),
) -> list[AttendanceOut]:
    rows = attendance.list_all(student_id=student_id, batch_id=batch_id, date_filter=date_filter)
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
