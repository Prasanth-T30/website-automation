"""Small operational CLI.

    python -m app.cli check    verify this process can reach Firebase
    python -m app.cli smtp-check  verify SMTP TLS and authentication (sends nothing)
    python -m app.cli smtp-test   verify SMTP and send one labelled message to the sender
    python -m app.cli seed     create the admin + three HR accounts (idempotent)
    python -m app.cli whoami   list existing accounts
    python -m app.cli wipe <project-id>   delete every document and stored file
    python -m app.cli set-password <email> [password]   reset a locked-out account
    python -m app.cli demo <project-id>   load sample data to walk through the console
    python -m app.cli automation [--send]   what the scheduled run would send (dry by default)
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
from app.schemas.user import validate_password

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
            #
            # Keyed on "was one supplied", not "is it None": a bare
            # `SEED_ADMIN_PASSWORD=` line — which is exactly what .env.example
            # ships — arrives as "", so the old `password is None` test made
            # every generated password count as deliberate and left the seeded
            # accounts ungated.
            must_change_password=not password,
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


def set_password() -> int:
    """Set an account's password from the server.

    The way back in when an admin is locked out. There is no self-service
    reset by design, and the in-app one at /admin/users/{id}/reset-password
    needs an admin who can already sign in — which is circular when the admin
    is the one who forgot. Run on the server, where shell access is itself
    the proof of authority.

    Omit the password to have one generated and the account forced to change
    it at next login; supply one and it is taken as deliberate.
    """
    email = sys.argv[2].lower().strip() if len(sys.argv) > 2 else None
    supplied = sys.argv[3] if len(sys.argv) > 3 else None
    if not email:
        print("  Usage: python -m app.cli set-password <email> [password]")
        print("         Omit the password to generate a temporary one.")
        return 1

    users = UserRepository(get_firestore())
    user = users.get_by_email(email)
    if user is None:
        print(f"  No account with the address {email}.")
        print("  Run `python -m app.cli whoami` to list them.")
        return 1

    secret = supplied or generate_password()
    try:
        validate_password(secret)
    except ValueError as exc:
        print(f"  {exc}")
        return 1

    users.update_fields(
        user.id,
        {"password_hash": hash_password(secret), "must_change_password": supplied is None},
    )
    # Anyone holding a session for this account is signed out: a password
    # reset is exactly the moment old sessions should stop working.
    users.bump_token_version(user.id)

    ActivityRepository(get_firestore()).record(
        action="user.password_reset",
        entity_type="user",
        entity_id=user.id,
        summary=f"Password reset from the CLI for {email}",
    )

    print(f"  Password updated for {email} ({user.role.value}).")
    print(f"    {secret}")
    if supplied is None:
        print("\n  Generated, so it must be changed at next login.")
    else:
        print("\n  Set as given; no change will be forced at login.")
    print("  Any existing session for this account has been signed out.")
    return 0


def demo() -> int:
    """Load a realistic sample dataset on top of the seeded accounts.

    Guarded the same way as `wipe`: naming the project is the confirmation,
    so this cannot be run against production by muscle memory. Sends no mail
    of any kind — it writes through the repositories, never the endpoints
    that email an applicant.
    """
    expected = settings.firebase_project_id
    if (sys.argv[2] if len(sys.argv) > 2 else None) != expected:
        print("  Refusing to load demo data without confirmation.")
        print(f"    Configured project: {expected}")
        print(f"    Run:  python -m app.cli demo {expected}")
        return 1

    # Sample students carry @example.com addresses, which accept no mail. With
    # scheduled sending live, loading them arms a run that mails every one and
    # bounces the lot back into the sending mailbox.
    if settings.automation_enabled and "--i-know" not in sys.argv[3:]:
        print("  Refusing: AUTOMATION_ENABLED is true.")
        print("  The sample students would be emailed automatically, and every")
        print("  address is @example.com, so each send would bounce.")
        print()
        print("  Turn automation off first, or re-run with --i-know to override.")
        return 1

    from app.demo_data import build

    db = get_firestore()
    if sum(1 for _ in db.collection("students").limit(1).stream()):
        print("  There are already students in this project.")
        print(f"  Clear it first:  python -m app.cli wipe {expected} && python -m app.cli seed")
        return 1

    try:
        made = build(db)
    except RuntimeError as exc:
        print(f"  {exc}")
        return 1

    print(f"  Loaded demo data into {expected}:")
    print()
    for label, count in made.items():
        print(f"    {label:<16} {count}")
    print()
    print("  No email was sent. Sign in and try Documents > Offer Letters / Certificates.")
    return 0


def automation_run() -> int:
    """Show what the scheduled run would send, or actually send it.

    Dry by default. `--send` is the only way to make anything leave, and even
    then AUTOMATION_ENABLED still has to be on.
    """
    from app.api.deps import get_storage_service
    from app.repositories.applications import ApplicationRepository
    from app.repositories.batches import BatchRepository
    from app.repositories.payments import PaymentRepository
    from app.repositories.reports import ReportRepository
    from app.repositories.students import StudentRepository
    from app.services import automation
    from app.services.documents import offer_letter_fields

    live = "--send" in sys.argv[2:]
    db = get_firestore()
    result = automation.run(
        students=StudentRepository(db),
        payments=PaymentRepository(db),
        reports=ReportRepository(db),
        batches=BatchRepository(db),
        applications=ApplicationRepository(db),
        storage=get_storage_service(),
        activity_repo=ActivityRepository(db),
        offer_letter_fields=offer_letter_fields,
        dry_run=not live,
    )

    print(f"  automation enabled : {settings.automation_enabled}")
    print(f"  mode               : {'SEND' if live else 'dry run'}")
    print(f"  cap per run        : {settings.automation_max_per_run}")
    print()
    print(f"  due now: {len(result.planned)}")
    for item in result.planned:
        print(f"    {item.kind:<13} {item.name:<24} {item.email:<32} {item.reason}")

    if result.sent:
        print()
        print(f"  sent: {len(result.sent)}")
        for row in result.sent:
            state = "emailed" if row["email_sent"] else "filed, email FAILED"
            print(f"    {row['kind']:<13} {row['name']:<24} {state}")
    if result.failed:
        print()
        print(f"  failed: {len(result.failed)}")
        for row in result.failed:
            print(f"    {row['kind']:<13} {row['name']:<24} {row['error']}")
    if result.skipped_over_cap:
        print()
        print(f"  {result.skipped_over_cap} left for the next run (cap reached)")

    print()
    if not live and result.planned:
        print("  Nothing was sent. Add --send to actually send these.")
    if live and not settings.automation_enabled:
        print("  Nothing was sent: AUTOMATION_ENABLED is false.")
    return 0


def wipe() -> int:
    """Delete every Firestore document and every stored file.

    Takes the project id as an argument and refuses unless it matches the one
    configured. There is no undo and no confirmation prompt that a script
    could answer by accident — naming the target is the confirmation.
    """
    expected = settings.firebase_project_id
    given = sys.argv[2] if len(sys.argv) > 2 else None
    if given != expected:
        print("  Refusing to wipe without confirmation.")
        print(f"    Configured project: {expected}")
        print(f"    Run:  python -m app.cli wipe {expected}")
        return 1

    db = get_firestore()
    print(f"  Wiping Firestore project {expected} ...")
    total = 0
    for collection in db.collections():
        removed = 0
        # Streamed and deleted in batches: a collection can outgrow memory,
        # and Firestore has no "delete collection" operation.
        while True:
            docs = list(collection.limit(400).stream())
            if not docs:
                break
            batch = db.batch()
            for doc in docs:
                batch.delete(doc.reference)
            batch.commit()
            removed += len(docs)
        total += removed
        print(f"    — {collection.id:<20} {removed} documents")

    print()
    print("  Wiping Storage ...")
    bucket = get_bucket()
    files = 0
    for blob in bucket.list_blobs():
        blob.delete()
        files += 1
    print(f"    — {files} files")

    print()
    print(f"  Done. {total} documents and {files} files removed.")
    print("  Run `python -m app.cli seed` to recreate the sign-in accounts.")
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


def smtp_check() -> int:
    """Verify SMTP connectivity and credentials without sending an email."""
    from app.services.email import verify_smtp_connection

    print(f"  host           : {settings.smtp_host or '<not configured>'}")
    print(f"  port           : {settings.smtp_port}")
    print(f"  security       : {settings.smtp_security}")
    print(f"  username       : {settings.smtp_username or '<not configured>'}")
    print(f"  sender         : {settings.smtp_from_email}")
    print()

    ok, detail = verify_smtp_connection()
    print(f"  SMTP           : {'OK' if ok else 'FAILED'} - {detail}")
    return 0 if ok else 1


def smtp_test() -> int:
    """Authenticate and send one clearly labelled verification message to self."""
    from app.services.email import render_smtp_test_body, send_email, verify_smtp_connection

    ok, detail = verify_smtp_connection()
    if not ok:
        print(f"  SMTP           : FAILED - {detail}")
        return 1

    recipient = settings.smtp_username or settings.smtp_from_email
    sent = send_email(
        to_email=recipient,
        subject="[DVein HRM] SMTP verification",
        body_html=render_smtp_test_body(),
    )
    print(f"  Delivery       : {'SENT' if sent else 'FAILED'} - {recipient}")
    return 0 if sent else 1


COMMANDS = {
    "check": check,
    "smtp-check": smtp_check,
    "smtp-test": smtp_test,
    "seed": seed,
    "whoami": whoami,
    "wipe": wipe,
    "set-password": set_password,
    "demo": demo,
    "automation": automation_run,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return 1
    return COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main())
