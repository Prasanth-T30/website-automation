"""Shared FastAPI dependencies: Firestore repositories, current user, role guards."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.cookies import ACCESS_COOKIE
from app.core.firebase import get_bucket, get_firestore
from app.core.security import TokenError, decode_token
from app.models.user import User, UserRole
from app.repositories.activity import ActivityRepository
from app.repositories.applications import ApplicationRepository
from app.repositories.attendance import AttendanceRepository
from app.repositories.batches import BatchRepository
from app.repositories.payments import PaymentRepository
from app.repositories.reports import ReportRepository
from app.repositories.settings import SettingsRepository
from app.repositories.students import StudentRepository
from app.repositories.users import UserRepository
from app.services.storage import StorageService


def get_user_repo() -> UserRepository:
    return UserRepository(get_firestore())


def get_activity_repo() -> ActivityRepository:
    return ActivityRepository(get_firestore())


def get_application_repo() -> ApplicationRepository:
    return ApplicationRepository(get_firestore())


def get_student_repo() -> StudentRepository:
    return StudentRepository(get_firestore())


def get_batch_repo() -> BatchRepository:
    return BatchRepository(get_firestore())


def get_attendance_repo() -> AttendanceRepository:
    return AttendanceRepository(get_firestore())


def get_payment_repo() -> PaymentRepository:
    return PaymentRepository(get_firestore())


def get_report_repo() -> ReportRepository:
    return ReportRepository(get_firestore())


def get_settings_repo() -> SettingsRepository:
    return SettingsRepository(get_firestore())


def get_storage_service() -> StorageService:
    return StorageService(get_bucket())


UserRepo = Annotated[UserRepository, Depends(get_user_repo)]
ActivityRepo = Annotated[ActivityRepository, Depends(get_activity_repo)]
ApplicationRepo = Annotated[ApplicationRepository, Depends(get_application_repo)]
StudentRepo = Annotated[StudentRepository, Depends(get_student_repo)]
BatchRepo = Annotated[BatchRepository, Depends(get_batch_repo)]
AttendanceRepo = Annotated[AttendanceRepository, Depends(get_attendance_repo)]
PaymentRepo = Annotated[PaymentRepository, Depends(get_payment_repo)]
ReportRepo = Annotated[ReportRepository, Depends(get_report_repo)]
SettingsRepo = Annotated[SettingsRepository, Depends(get_settings_repo)]
Storage = Annotated[StorageService, Depends(get_storage_service)]

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated."
)


def get_current_user(request: Request, users: UserRepo) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise _UNAUTHENTICATED

    try:
        payload = decode_token(token, expected_type="access")
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise _UNAUTHENTICATED

    user = users.get(user_id)
    if user is None or not user.is_active:
        raise _UNAUTHENTICATED

    # A bumped token_version means the password changed or the account was
    # deactivated — every token issued before that moment is dead.
    if user.token_version != payload.get("tv"):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please sign in again."
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role is not UserRole.admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="This action requires an administrator account."
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_password_current(user: CurrentUser) -> User:
    """Block normal API use while a forced password change is outstanding."""
    if user.must_change_password:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You must change your password before continuing.",
        )
    return user


ActiveUser = Annotated[User, Depends(require_password_current)]
