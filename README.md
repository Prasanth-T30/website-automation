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

## Running in production

Live at:

| Piece | Where |
|---|---|
| Console | https://dvein-hrm-console.web.app |
| Public form | https://dvein-registration.web.app |
| API | `dvein-hrm-api` on Cloud Run, `asia-south1` |
| Database | Firestore `(default)`, `asia-south1` |
| Files | `dvein-hrm.firebasestorage.app` |
| Project | `dvein-hrm` |

### How the browser reaches the API

**Both sites call Cloud Run directly.** `VITE_API_URL` is baked into each
build at compile time and points at the service URL.

They do *not* go through a Firebase Hosting rewrite, and that is deliberate:
Hosting strips every cookie except one named `__session` before forwarding a
request. Sign-in appeared to succeed and every subsequent request arrived
unauthenticated. The `/api/**` rewrite still exists in `firebase.json` — it is
harmless and useful as a fallback — but nothing relies on it.

Because the API is a different origin, three things must stay in step:

- `CORS_ORIGINS` lists exactly the two site URLs
- `COOKIE_SAMESITE=none` with `COOKIE_SECURE=true` — a browser silently
  discards that combination if Secure is missing, and a startup validator
  refuses to boot rather than let it happen quietly
- The CSRF token is returned in the login response body as well as a cookie,
  because JavaScript cannot read another origin's cookies

### Redeploying

Configuration lives **on the Cloud Run service**, not in the repository. A
deploy that omits `--set-env-vars` preserves what is already set, so the
everyday command is short:

```bash
pnpm deploy:api          # API only
pnpm deploy:web          # both sites (rebuilds first)
pnpm deploy:rules        # Firestore + Storage rules
```

The frontends need `VITE_API_URL` at build time. It lives in
`frontend/.env.production` and `registration/.env.production` — both
gitignored, both containing the Cloud Run URL. **A machine that clones this
repo will not have them**, and the resulting build silently falls back to
same-origin, which reintroduces the cookie bug. Recreate them before building:

```bash
echo "VITE_API_URL=https://dvein-hrm-api-931951603198.asia-south1.run.app" > frontend/.env.production
echo "VITE_API_URL=https://dvein-hrm-api-931951603198.asia-south1.run.app" > registration/.env.production
```

To change an environment variable, edit it on the service rather than
redeploying from a file:

```bash
gcloud run services update dvein-hrm-api --region asia-south1 \
  --update-env-vars CORS_ORIGINS=https://a.web.app,https://b.web.app
```

### Verifying a deploy

```bash
curl https://dvein-hrm-api-931951603198.asia-south1.run.app/health
# {"status":"ok","version":"1.0.0","env":"production"}
```

`env` must read `production`. If it says `development`, the service is running
without its environment and is probably pointed at nothing.

---

## Operations

### Adding an HR

From the console: **Admin → Users → Add**. The account is created with a
generated password and `must_change_password` set, so the person must replace
it at first sign-in. Until they do, every endpoint outside `/auth/me` and
`/auth/change-password` returns 403 — a temporary password is deliberately
useless for anything but replacing itself.

### Rotating the SMTP password

The password is in Secret Manager, not in any file or image layer.

```bash
printf %s 'NEW_APP_PASSWORD' | gcloud secrets versions add smtp-password \
  --data-file=- --project dvein-hrm
gcloud run services update dvein-hrm-api --region asia-south1 \
  --update-secrets SMTP_PASSWORD=smtp-password:latest
```

The service reads `:latest`, so the new version takes effect on the next
revision. Update `.env` locally too if you send mail from a laptop.

### Rotating the JWT secret

```bash
python -c "import secrets; print(secrets.token_hex(32))"
gcloud run services update dvein-hrm-api --region asia-south1 \
  --update-env-vars JWT_SECRET_KEY=<new value>
```

Every signed-in session dies immediately. That is the point — do it if a
secret leaks, not routinely.

### Backing up

Firestore has no automatic backup on this project.

```bash
gcloud firestore export gs://dvein-hrm.firebasestorage.app/backups/$(date +%F) \
  --project dvein-hrm
```

Worth scheduling before real data accumulates.

### Reading logs

```bash
gcloud logging read \
  'resource.type=cloud_run_revision AND resource.labels.service_name=dvein-hrm-api' \
  --limit 50 --project dvein-hrm --format="value(textPayload)"
```

---

## Known limitations

Real, and worth knowing before they surprise someone.

**Email lands in spam.** Sent from a personal Gmail (`info.dveininnovation@gmail.com`)
with no domain sending reputation. The messages themselves are correct — proper
`Date` and `Message-ID`, base64-encoded body, plain-text alternative, inline
logo, PDF attached — and none of that outweighs the sender. The fix is a
mailbox on `dveininnovation.com`, which already runs GoDaddy Professional Email
with SPF configured. Four values in `.env` and a redeploy once someone with the
GoDaddy account provides one.

**The letterhead and the sender disagree.** PDFs print
`info@dveininnovation.com`; mail arrives from the Gmail address. A student
replying to the email and one writing to the address on their offer letter
reach different inboxes.

**Lists load in full.** Every list endpoint reads its whole collection and
filters in Python. Cursor pagination exists (`?limit=&cursor=`, with an
`X-Next-Cursor` header) but is opt-in, because the console derives its
dashboard and Finance totals from complete lists — serving one page by default
would make those figures wrong rather than merely slow. Moving the totals to
server-side aggregates is the prerequisite for turning it on by default.

**Rate limiting counts per instance.** In-memory storage, so the real limit is
the configured one times the number of live Cloud Run instances. Set
`RATE_LIMIT_STORAGE_URI` to a shared Redis before the numbers need to mean
anything.

**No frontend linting.** `pnpm lint` names a package that was never installed.
Frontend tests exist but cover only the Finance arithmetic; the rest of the UI
rests on the build compiling.

**Attendance is a fixed trailing week.** No date navigation, no monthly report.

**"Overdue" is inferred.** There is no due-date field; a balance counts as
overdue once its batch is marked completed.

## Configuration

Every setting is documented in `.env.example`. Two worth calling out:

- **`REPORTING_TIMEZONE`** (default `Asia/Kolkata`) — timestamps are stored in
  UTC, but monthly revenue is bucketed on this clock. A UTC boundary would push
  payments taken in the opening hours of each month into the month before.
- **`SMTP_*`** — deliberately blank. Sending switches on when `SMTP_HOST` is
  set; credentials are separate, so a local mail catcher needs none. Until
  then the app logs a warning and
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
Firebase emulator rather than mocks. **295 backend, 20 frontend.**

Backend tests auto-skip if the emulator is unreachable, so a green run with
everything skipped is not a pass — check the count, not the colour.

```bash
pnpm emulators:fresh
```

```bash
cd backend && uv run pytest
```

```bash
cd frontend && pnpm test
```

`conftest.py` overwrites the SMTP settings rather than defaulting them: the
developer `.env` holds working credentials, so without that every run would
post real messages through the institute's mailbox and spend its daily quota.

## Roles

| Role | Can |
|---|---|
| **admin** | Everything: manage HR accounts, reassign students, view every HR's performance and the activity log, edit institute settings |
| **hr** | Claim from the shared pool, own and drive their students, record payments, mark attendance, issue certificates, upload files. **Sees only their own students, revenue and documents.** |

Isolation is enforced in the API, not the console. An HR reading `/students`
or `/payments` gets their own records whatever the request asks for; only an
admin can widen the view. This matters because the console reads those lists
from a dozen screens, and one forgetting a filter would leak a colleague's
book.

Batches are the deliberate exception. Every HR sees the whole timetable and
the people in each cohort — that is how you tell a viable batch from an empty
one — but the fee figures come back null for a colleague's student, so the
amounts never reach the browser at all. Only the creator or an admin can edit
a batch or change who is in it, with one carve-out: a batch created by an
admin is an institute cohort that any HR may fill, because otherwise an
institute that sets its batches up centrally leaves every HR unable to place
a single student.

Students do not log in. The schema carries the fields a future student portal
would need, so adding one later does not require a rework.

## Status

Deployed and in use. Every phase below is live on `dvein-hrm`.

- [x] **0 · Foundations** — monorepo, tooling, design tokens, compose
- [x] **1 · Auth** — users, JWT cookies, CSRF, RBAC, forced password change
- [x] **2 · Intake** — public registration form, shared pool, claim/approve/reject
- [x] **3 · Core HRM** — students, batches, attendance, manual student entry
- [x] **4 · Money** — payments, receipts, per-HR revenue attribution, exports
- [x] **5 · Files** — offer letters, certificates, documents, notifications
- [x] **6 · Analytics** — dashboard, HR performance, announcements, settings
- [x] **7 · Hardening** — production project, SMTP, cross-origin sessions,
      pagination, isolation audit, frontend tests

Both documents render onto Dvein's own supplied artwork: the body text is
stripped from each template and recomposed, so the logo, watermark, seal,
signature and footer are the originals. Only the name, programme and dates are
drawn on top.

See **Known limitations** above for what is genuinely outstanding.
