"""Small operational CLI.

    python -m app.cli check    verify this process can reach Firebase
    python -m app.cli seed     create the admin + three HR accounts (idempotent)
    python -m app.cli whoami   list existing accounts
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

from app.core.config import settings
from app.core.firebase import get_bucket, get_firestore
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


def check() -> int:
    """Prove this process can actually reach Firebase, and say which one.

    Deploying against a real project is when configuration mistakes surface —
    the wrong project id, a bucket that doesn't exist, or an emulator host
    left set so the service quietly talks to nothing. This does a real round
    trip rather than reading settings back, so a pass means it genuinely works.
    """
    emulating = bool(settings.firestore_emulator_host or settings.firebase_storage_emulator_host)
    if emulating:
        credentials = "EMULATOR"
    elif settings.firebase_service_account_path:
        credentials = "service-account file"
    else:
        credentials = "runtime identity (Cloud Run / ADC)"

    print(f"  environment    : {settings.app_env}")
    print(f"  project        : {settings.firebase_project_id}")
    print(f"  storage bucket : {settings.firebase_storage_bucket}")
    print(f"  credentials    : {credentials}")
    if emulating:
        print(f"  firestore host : {settings.firestore_emulator_host}")
        print(f"  storage host   : {settings.firebase_storage_emulator_host}")
    print()

    ok = True

    # Write, read back, delete. A read alone would pass against a project this
    # identity can only read from, which is not enough to run the app.
    try:
        ref = get_firestore().collection("_healthcheck").document("cli")
        ref.set({"at": datetime.now(UTC).isoformat()})
        found = ref.get().exists
        ref.delete()
        print("  Firestore      : OK (write, read, delete)" if found
              else "  Firestore      : FAILED — wrote a document but read nothing back")
        ok = ok and found
    except Exception as exc:  # noqa: BLE001 — the real cause is the useful part
        print(f"  Firestore      : FAILED — {type(exc).__name__}: {exc}")
        ok = False

    try:
        bucket = get_bucket()
        blob = bucket.blob("_healthcheck/cli.txt")
        blob.upload_from_string("ok", content_type="text/plain")
        blob.delete()
        print(f"  Storage        : OK ({bucket.name})")
    except Exception as exc:  # noqa: BLE001
        print(f"  Storage        : FAILED — {type(exc).__name__}: {exc}")
        ok = False

    print()
    if not ok:
        print("  Not ready. Check FIREBASE_PROJECT_ID and FIREBASE_STORAGE_BUCKET, and that")
        print("  this runtime has Firestore/Storage access (or a valid service-account file).")
        return 1

    # Settings that are fine locally and wrong in production.
    warnings = []
    if settings.app_env == "production":
        if emulating:
            warnings.append("emulator hosts are set — production must reach the real project")
        if not settings.cookie_secure:
            warnings.append("COOKIE_SECURE is false — session cookies would go over plain HTTP")
        if not settings.smtp_configured:
            warnings.append("SMTP_HOST is unset — certificates generate and file but never send")
        if any("localhost" in o for o in settings.cors_origins):
            warnings.append("CORS_ORIGINS still lists localhost")

    if warnings:
        print("  Reachable, but check these before going live:")
        for w in warnings:
            print(f"    - {w}")
    else:
        print("  Ready.")
    return 0


COMMANDS = {"check": check, "seed": seed, "whoami": whoami}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return 1
    return COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main())
