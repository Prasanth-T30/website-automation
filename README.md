# Dvein HRM

Multi-user HRM for Dvein Innovations. A public registration form feeds a shared
applicant pool; HR users claim applicants and drive them through enrolment,
batches, attendance and fees; an admin oversees all of it and sees each HR's
revenue.

Replaces the single-user PyInstaller desktop app in `../DveinHRM`, which had no
real authentication, no concept of a user, and no intake path.

---

## Stack

| Layer | Choice |
|---|---|
| API | FastAPI · Pydantic v2 · Firebase Admin SDK |
| Database | Cloud Firestore |
| File storage | Firebase Storage |
| Web | React 19 · JavaScript · Vite · Tailwind v4 · TanStack Query |
| Auth | JWT access + refresh in httpOnly cookies, double-submit CSRF, bcrypt |
| Documents | openpyxl (Excel) · fpdf2 (offer letters, receipts, certificates) |

Auth is deliberately **not** Firebase Authentication — the backend issues its
own JWTs so that role checks, forced-password-change and token revocation stay
entirely under the API's control. Firestore and Storage hold data and files only.

## Layout

Three deployable units. The registration form is separate from the console
because it is the only surface strangers reach, and it ships no console code.

```
backend/        FastAPI service
  app/
    core/          config, Firebase client, security (JWT/bcrypt), CSRF, constants
    models/        Firestore document shapes (plain dataclasses)
    repositories/  the only code that talks to Firestore directly
    schemas/       Pydantic request/response models
    api/v1/        routers
    services/      domain logic, PDFs, email, Storage wrapper

frontend/       React SPA — the staff console
  src/
    styles/      design tokens + globals
    components/  UI primitives
    features/    per-domain API clients and JSDoc typedefs
    routes/      page components
    lib/         api client, helpers

registration/   React SPA — the public form (no auth, no console code)
```

---

## Prerequisites

Node 20+, pnpm, Python 3.12, and **Java 21+** for the Firebase emulators
(`firebase-tools` no longer supports older JDKs). Check with `java --version`:

```bash
winget install --id EclipseAdoptium.Temurin.21.JDK -e
```

The Firebase CLI is pinned as a root devDependency, so `pnpm install` provides
it — no global install needed.

## Setup

```bash
pnpm install
cp .env.example .env
# Fill in JWT_SECRET_KEY:
#   python -c "import secrets; print(secrets.token_urlsafe(64))"
# Leave the *_EMULATOR_HOST lines as-is for local dev.
```

### Running natively (recommended for local dev)

```bash
# 1. Emulators — Firestore + Storage. Data persists across restarts.
pnpm emulators
```

```bash
# 2. API
cd backend && uv sync
uv run python -m app.cli seed          # admin + 3 HR accounts
uv run uvicorn app.main:app --reload --port 8000
```

```bash
# 3. Console (5173) and public form (5174)
pnpm console
pnpm registration
```

Emulator UI (inspect Firestore/Storage live): http://127.0.0.1:4000

`pnpm emulators` imports from and exports to `./emulator-data`, so local records
survive a restart. Use `pnpm emulators:fresh` to start empty.

Two things to know:

- **Export happens on a clean shutdown** (Ctrl+C in that terminal). A hard kill
  skips it and you lose everything since the last export. To dump on demand
  without stopping:

  ```bash
  curl -X POST http://127.0.0.1:4400/_admin/export -H "Content-Type: application/json" -d "{\"path\":\"<absolute-path>/emulator-data\"}"
  ```

- **Tests run against their own Firestore project**, not your dev data. Each
  `pytest` run gets a throwaway `test-run-<uuid>` namespace (see
  `tests/conftest.py`), so it can share a running emulator with the console
  without leaving fabricated students and payments behind. If you ever need to
  reset the dev namespace by hand:

  ```bash
  curl -X DELETE "http://localhost:8080/emulator/v1/projects/demo-dvein-hrm/databases/(default)/documents"
  ```

### Everything in Docker

The emulator isn't containerized (it needs a JDK, and running it natively is
simpler). Start it on the host first, then:

```bash
docker compose up --build
```

`api` reaches the host-run emulator via `host.docker.internal`.

## Deploying to Firebase

Three pieces, one Firebase project, one Firestore database. Both the console
and the public form are static sites on Hosting; the API is a container on
Cloud Run, reached through a Hosting rewrite at `/api/**` so the browser stays
same-origin and the auth cookies remain first-party.

**Do this once, in order.** The Firestore region is fixed at creation and
cannot be changed afterwards.

```bash
# 1. Point the repo at your real project (replaces the demo id).
firebase use --add            # pick the project, alias it "default"
```

```bash
# 2. Create the two Hosting sites and bind them to the targets in firebase.json.
firebase hosting:sites:create dvein-hrm-console
firebase hosting:sites:create dvein-hrm-apply
firebase target:apply hosting console dvein-hrm-console
firebase target:apply hosting registration dvein-hrm-apply
```

```bash
# 3. Deploy the API. Its service account needs Firestore + Storage access;
#    no key file is involved — Cloud Run supplies credentials ambiently.
pnpm deploy:api
```

```bash
# 4. Confirm the deployed service can actually reach the real project.
#    Does a write/read/delete round trip against Firestore and Storage, and
#    exits non-zero if either fails, so it can gate a release.
gcloud run services proxy dvein-hrm-api --region asia-south1 &
cd backend && uv run python -m app.cli check
```

```bash
# 5. Lock the database down, then publish both sites.
pnpm deploy
```

Set these on the Cloud Run service (not in the image): `JWT_SECRET_KEY`,
`CORS_ORIGINS`, `PUBLIC_BASE_URL`, `COOKIE_SECURE=true`, `APP_ENV=production`,
`FIREBASE_PROJECT_ID`, `FIREBASE_STORAGE_BUCKET`, `REPORTING_TIMEZONE`, and the
`SMTP_*` values. Leave `FIRESTORE_EMULATOR_HOST` and
`FIREBASE_STORAGE_EMULATOR_HOST` **unset** — with neither those nor a service
account path, the Admin SDK resolves credentials from the runtime, which is
what you want on Cloud Run. Keep `JWT_SECRET_KEY` and `SMTP_PASSWORD` in Secret
Manager and mount them as env vars.

Seed the staff accounts once against production with both seed passwords blank,
so each account is created with a generated password and must change it at
first sign-in.

### Pointing the existing Vercel form at this backend

The deployed registration site can keep running on Vercel — the API already
allows its origin and exposes the `/register` path that site posts to. Change
one environment variable there:

```
VITE_API_BASE_URL=https://<your-console-domain>/api/v1
```

No code change or rebuild of that app is needed. Moving it onto Hosting
instead (target `registration`) makes it same-origin and removes the CORS hop.

## Configuration

Every setting is documented in `.env.example`. Two worth calling out:

- **`REPORTING_TIMEZONE`** (default `Asia/Kolkata`) — timestamps are stored in
  UTC, but monthly revenue is bucketed on this clock. A UTC boundary would push
  payments taken in the opening hours of each month into the month before.
- **`SMTP_*`** — deliberately blank. Email sending switches on only when host,
  username and password are all set; until then the app logs a warning and
  carries on, so approving a student never depends on a mail server. Leave them
  unset in any environment holding restored production data, or approving a
  record there emails the real applicant.

## Data model

Firestore is schemaless, so there is no migration step — collections and their
shape are defined by the code that writes to them (`app/models/`,
`app/repositories/`). Conventions worth knowing:

- **`users`** are keyed by a Firestore auto-ID; **`user_emails/{email}`** is a
  manual unique index written in the same transaction as account creation,
  since Firestore has no native unique constraint.
- **Payments snapshot `owner_id`** from the student at the moment they are
  recorded, so per-HR revenue stays stable even if a student is later
  reassigned.
- Collections stay intentionally small (a handful of users, one institute), so
  list views sort and paginate client-side rather than needing composite indexes.

## Tests

Repository, Storage and full HTTP end-to-end tests run against the **real**
Firebase emulator rather than mocks. **153 passing.** Tests auto-skip if the
emulator isn't reachable, so a green run with everything skipped is not a pass —
check the count.

```bash
pnpm emulators:fresh
```

```bash
cd backend && uv run pytest
```

## Roles

| Role | Can |
|---|---|
| **admin** | Everything: manage HR accounts, reassign students, view every HR's performance and the activity log, edit institute settings |
| **hr** | Claim from the shared pool, own and drive their students, record payments, mark attendance, issue certificates, upload files. Sees all students but only acts on their own. |

Batches are the exception to ownership: every HR sees the whole timetable and
can create cohorts, but only the creator (or an admin) can edit or delete one.

Students do not log in. The schema carries the fields a future student portal
would need, so adding one later does not require a rework.

## Status

- [x] **0 · Foundations** — monorepo, tooling, design tokens, compose
- [x] **1 · Auth** — users, JWT cookies, CSRF, RBAC, seeded accounts
- [x] **2 · Intake** — public registration form, shared pool, claim/approve/reject
- [x] **3 · Core HRM** — students, batches, attendance, manual student entry
- [x] **4 · Money** — payments, receipts, per-HR revenue attribution
- [x] **5 · Files** — completion certificates, documents, derived notifications
- [x] **6 · Analytics** — dashboard, HR performance, settings
- [ ] **7 · Hardening** — production Firebase project, SMTP credentials,
      frontend test coverage, deploy

### Known gaps

- The completion certificate uses a house-style layout derived from the offer
  letter, not a supplied design. Swapping it touches only the drawing code in
  `services/pdf_certificate.py`.
- Email cannot send until `SMTP_*` is configured; `email_sent` reports `false`
  and the certificate is still generated and filed.
- The frontend has a vitest harness wired up but no test files yet.
