# Dvein HRM — Console

Multi-user HRM for Dvein Innovations: a public application form feeds a shared
lead pool, three HR users claim applicants and drive them through an enrolment
pipeline, and an admin oversees all of it.

Replaces the single-user PyInstaller desktop app in `../DveinHRM`, which had no
real authentication, no concept of a user, and no intake path.

---

## Stack

| Layer | Choice |
|---|---|
| API | FastAPI · Pydantic v2 · Firebase Admin SDK |
| Database | Cloud Firestore |
| File storage | Firebase Storage |
| Web | React 19 · TypeScript · Vite · Tailwind v4 · TanStack Query |
| Auth | JWT access + refresh in httpOnly cookies, double-submit CSRF, bcrypt |
| Documents | openpyxl (Excel) · fpdf2 (PDF) |

Auth is deliberately **not** Firebase Authentication — the backend issues its
own JWTs so that role checks, forced-password-change and token revocation
stay entirely under the API's control. Firestore and Storage are used for
data and files only.

## Layout

```
backend/    FastAPI service
  app/
    core/          config, Firebase client, security (JWT/bcrypt), CSRF
    models/        Firestore document shapes (plain dataclasses)
    repositories/  the only code that talks to Firestore directly
    schemas/       Pydantic request/response models
    api/v1/        routers
    services/      domain logic, Firebase Storage wrapper

frontend/   React SPA
  src/
    styles/      design tokens + globals
    components/  UI primitives
    features/    feature modules
    routes/      page components
    lib/         api client, helpers
```

---

## Prerequisites

Node 20+, pnpm, Python 3.12, and the **Firebase CLI** (`npx firebase-tools`)
for local development — it runs the Firestore + Storage emulators, so no
cloud project or billing account is needed until you deploy.

The emulators need **Java 21+** (`firebase-tools` no longer supports older
JDKs). Check with `java --version`; install via:

```bash
winget install --id EclipseAdoptium.Temurin.21.JDK -e
```

## Setup

```bash
cp .env.example .env
# Fill in JWT_SECRET_KEY:
#   python -c "import secrets; print(secrets.token_urlsafe(64))"
# Leave the FIRESTORE_EMULATOR_HOST / FIREBASE_STORAGE_EMULATOR_HOST lines as-is for local dev.
```

### Running natively (recommended for local dev)

```bash
# 1. Firebase emulators — Firestore + Storage (leave running)
npx firebase-tools emulators:start --only firestore,storage

# 2. API
cd backend
uv sync
uv run python -m app.cli seed     # creates admin + 3 HR accounts
uv run uvicorn app.main:app --reload --port 8000

# 3. Web
cd frontend
pnpm install
pnpm dev
```

Emulator UI (inspect Firestore/Storage data live): http://127.0.0.1:4000

### Everything in Docker

The emulator itself isn't containerized (it needs a JDK, and running it
natively is simpler for local dev). Start it on the host first, then:

```bash
docker compose up --build
```

`api` reaches the host-run emulator via `host.docker.internal`. In
staging/production, set `FIREBASE_SERVICE_ACCOUNT_PATH` and remove the two
`*_EMULATOR_HOST` variables to point at a real Firebase project instead.

## Data model

Firestore is schemaless, so there is no migration step — collections and
their shape are defined by the code that writes to them (`app/models/`,
`app/repositories/`). Two conventions worth knowing:

- **`users`** are keyed by a Firestore auto-ID; **`user_emails/{email}`** is a
  manual unique index (`{"user_id": id}`) written in the same transaction as
  account creation, since Firestore has no native unique constraint.
- Collections stay intentionally small (a handful of users, one institute) so
  list views sort client-side rather than relying on Firestore composite
  indexes.

## Tests

Repository, Storage and full HTTP end-to-end tests run against the **real**
Firebase emulator rather than mocks — start it first, then:

```bash
cd backend
npx firebase-tools emulators:start --only firestore,storage &
uv run pytest                    # auto-skips DB-touching tests if the emulator isn't up

cd frontend
pnpm test        # unit
pnpm e2e          # Playwright
```

---

## Roles

| Role | Can |
|---|---|
| **admin** | Everything: manage the three HR accounts, reassign students, view every HR's performance and the activity log, edit institute settings |
| **hr** | Claim from the shared pool, own and drive their students, record payments, mark attendance, upload files. Sees all students but only acts on their own. |

Students do not log in. The schema carries the fields a future student portal
would need, so adding one later does not require a rework.

## Build phases

- [x] **0 · Foundations** — monorepo, tooling, design tokens, compose
- [x] **1 · Auth** — users, JWT cookies, CSRF, RBAC, seeded accounts, on
      Firestore + Firebase Storage. 48 tests passing against the real
      Firebase Local Emulator Suite (repository layer, Storage roundtrips,
      and full HTTP login/CSRF/RBAC/forced-password-change flows).
- [ ] **2 · Intake** — public form, shared pool, claim, pipeline board
- [ ] **3 · Core HRM** — students, batches, attendance
- [ ] **4 · Money** — payments, receipts, exports
- [ ] **5 · Files** — certificates, reports, notifications
- [ ] **6 · Analytics** — dashboards, HR performance, settings
- [ ] **7 · Hardening** — tests, seed data, deploy
