"""Admin-only user management.

Both deactivate and delete are available. Deactivate is reversible and is the
right call once a user owns live records (students, batches, payments —
Phase 3+); delete is permanent and mainly useful for accounts created in
error or, today, for clearing out test data. Both are blocked against
self-service and against removing the last active administrator.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import ActivityRepo, AdminUser, StudentRepo, UserRepo
from app.core.security import generate_password, hash_password
from app.models.user import User, UserRole
from app.repositories.users import EmailAlreadyExists
from app.schemas.user import PasswordResetOut, UserCreate, UserOut, UserUpdate
from app.services import activity

router = APIRouter(prefix="/admin/users", tags=["Admin · Users"])


def _get_user_or_404(users: UserRepo, user_id: str) -> User:
    user = users.get(user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.get("", response_model=list[UserOut])
def list_users(users: UserRepo, _: AdminUser) -> list[UserOut]:
    return [UserOut.model_validate(u) for u in users.list_all()]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate, users: UserRepo, activity_repo: ActivityRepo, admin: AdminUser
) -> UserOut:
    try:
        user = users.create(
            email=data.email,
            full_name=data.full_name.strip(),
            password_hash=hash_password(data.password),
            role=data.role,
            phone=data.phone,
            must_change_password=data.must_change_password,
        )
    except EmailAlreadyExists as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail=f"An account already exists for {exc}."
        ) from exc

    activity.record(
        activity_repo,
        action="user.created",
        actor_id=admin.id,
        entity_type="user",
        entity_id=user.id,
        summary=f"Created {user.role.value} account for {user.full_name}",
    )
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str, data: UserUpdate, users: UserRepo, activity_repo: ActivityRepo, admin: AdminUser
) -> UserOut:
    user = _get_user_or_404(users, user_id)
    changes = data.model_dump(exclude_unset=True)

    # Guard against an admin locking themselves — or everyone — out.
    if user.id == admin.id:
        if changes.get("is_active") is False:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account."
            )
        if "role" in changes and changes["role"] is not UserRole.admin:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="You cannot remove your own admin role."
            )

    losing_admin = (changes.get("is_active") is False and user.role is UserRole.admin) or (
        "role" in changes and user.role is UserRole.admin and changes["role"] is not UserRole.admin
    )
    if losing_admin and users.count_active_admins(excluding=user.id) == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="At least one active administrator must remain.",
        )

    write_fields = {k: (v.value if isinstance(v, UserRole) else v) for k, v in changes.items()}
    users.update_fields(user.id, write_fields)

    # Deactivating must take effect immediately, not when the access token expires.
    if changes.get("is_active") is False:
        users.bump_token_version(user.id)

    activity.record(
        activity_repo,
        action="user.updated",
        actor_id=admin.id,
        entity_type="user",
        entity_id=user.id,
        summary=f"Updated {user.full_name}",
        meta=write_fields,
    )

    updated = users.get(user.id)
    assert updated is not None
    return UserOut.model_validate(updated)


@router.post("/{user_id}/reset-password", response_model=PasswordResetOut)
def reset_password(
    user_id: str, users: UserRepo, activity_repo: ActivityRepo, admin: AdminUser
) -> PasswordResetOut:
    """Issue a temporary password. Shown once — it is never recoverable later."""
    user = _get_user_or_404(users, user_id)

    temporary = generate_password()
    users.update_fields(
        user.id, {"password_hash": hash_password(temporary), "must_change_password": True}
    )
    users.bump_token_version(user.id)  # kicks the user out of any live session

    activity.record(
        activity_repo,
        action="user.password_reset",
        actor_id=admin.id,
        entity_type="user",
        entity_id=user.id,
        summary=f"Reset password for {user.full_name}",
    )
    return PasswordResetOut(user_id=user.id, temporary_password=temporary)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    users: UserRepo,
    students: StudentRepo,
    activity_repo: ActivityRepo,
    admin: AdminUser,
) -> None:
    user = _get_user_or_404(users, user_id)

    if user.id == admin.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account."
        )

    if user.role is UserRole.admin and users.count_active_admins(excluding=user.id) == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="At least one active administrator must remain.",
        )

    # Deleting an HR who still holds students strands them: the records keep
    # an owner_id pointing at an account that no longer exists, so they drop
    # out of every per-HR view while their payments stay in the institute
    # ledger. The admin's own revenue breakdown then quietly stops adding up
    # to the total, with nothing on screen to say why.
    #
    # Refused rather than silently reassigned — moving someone else's students
    # to an arbitrary owner is not a decision this endpoint should make on the
    # admin's behalf. /students/{id}/reassign already moves a student together
    # with their payment history and originating application.
    owned = students.list_all(owner_id=user.id)
    if owned:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                f"{user.full_name} still owns {len(owned)} student"
                f"{'s' if len(owned) != 1 else ''}. Reassign them to another HR "
                f"first, or deactivate this account instead of deleting it."
            ),
        )

    users.delete(user.id)

    activity.record(
        activity_repo,
        action="user.deleted",
        actor_id=admin.id,
        entity_type="user",
        entity_id=user.id,
        summary=f"Deleted account for {user.full_name} ({user.email})",
    )
