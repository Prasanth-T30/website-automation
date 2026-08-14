"""Small operational CLI.

    python -m app.cli seed     create the admin + three HR accounts (idempotent)
    python -m app.cli whoami   list existing accounts
"""

from __future__ import annotations

import sys

from app.core.config import settings
from app.core.firebase import get_firestore
from app.core.security import generate_password, hash_password
from app.models.user import UserRole
from app.repositories.activity import ActivityRepository
from app.repositories.users import UserRepository

# Deliberately generic placeholders — the admin renames these to the real
# people from the Users screen after first sign-in.
HR_SEEDS = [
    ("hr1@dvein.in", "HR Executive One"),
    ("hr2@dvein.in", "HR Executive Two"),
    ("hr3@dvein.in", "HR Executive Three"),
]


def seed() -> int:
    """Create the four accounts if they do not already exist."""
    users = UserRepository(get_firestore())
    activity_repo = ActivityRepository(get_firestore())
    created: list[tuple[str, str, str]] = []

    def ensure(email: str, full_name: str, role: UserRole, password: str | None) -> None:
        email = email.lower().strip()
        if users.get_by_email(email):
            print(f"  = {email:<24} already exists, left untouched")
            return

        secret = password or generate_password()
        user = users.create(
            email=email,
            full_name=full_name,
            password_hash=hash_password(secret),
            role=role,
            phone=None,
            # A generated password must be replaced; an operator-chosen one
            # from .env is assumed intentional.
            must_change_password=password is None,
        )
        activity_repo.record(
            action="user.seeded",
            entity_type="user",
            entity_id=user.id,
            summary=f"Seeded {role.value} account {email}",
        )
        created.append((email, secret, role.value))
        print(f"  + {email:<24} created ({role.value})")

    ensure(settings.seed_admin_email, "Administrator", UserRole.admin, settings.seed_admin_password)
    for email, name in HR_SEEDS:
        ensure(email, name, UserRole.hr, settings.seed_hr_password)

    if created:
        print("\n  Save these now — passwords are hashed and cannot be recovered:\n")
        for email, secret, role in created:
            print(f"    {role:<6} {email:<24} {secret}")
        print("\n  Accounts created with a generated password must change it at first login.")
    else:
        print("\n  Nothing to do — all four accounts already exist.")
    return 0


def whoami() -> int:
    users = UserRepository(get_firestore()).list_all()
    if not users:
        print("  No accounts yet. Run:  python -m app.cli seed")
        return 0
    print(f"  {'ROLE':<6} {'EMAIL':<24} {'NAME':<22} ACTIVE")
    for u in users:
        print(f"  {u.role.value:<6} {u.email:<24} {u.full_name:<22} {u.is_active}")
    return 0


COMMANDS = {"seed": seed, "whoami": whoami}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return 1
    return COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main())
