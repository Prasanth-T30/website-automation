# Registration Site — public form

The public-facing app: a student lands here, registers for a programme, and uploads
payment proof. It has **no admin routes and no console code at all** — this is the only
surface strangers on the internet can reach, so it ships nothing they shouldn't have.

A submission posts to the HRM API's `POST /public/applications`, which validates it,
stores the screenshot, and creates an application in the claim queue for an HR to pick
up in the console (`../console`). There is no separate database behind this app.

## Routes

```
/           Registration form
/success    Confirmation, showing the registration ID
```

## Getting started

From the repo root (this is a pnpm workspace, not a standalone npm project):

```bash
pnpm install --filter internship-portal-registration-site
```

```bash
pnpm --dir frontend/registration dev
```

Runs at **http://localhost:5174**. Needs the API up at `http://localhost:8000` — the dev
server proxies `/api` there, see `vite.config.js`. Start it with:

```bash
cd backend && uv run uvicorn app.main:app --port 8000 --reload
```

## Configuration

One variable, `VITE_API_BASE_URL` (see `.env.example`). Vite inlines it at **build time**,
so it must be set before `pnpm build` — setting it at container start has no effect.

Leave it relative (`/api/v1`) wherever the form and the API sit behind one host: the
bundled `nginx.conf` proxies `/api` through, which keeps the browser same-origin and
avoids a CORS preflight on every submission. Use an absolute origin only when the two are
on separate domains, and add that origin to the API's `CORS_ORIGINS` if you do.

## Build & deploy

```bash
pnpm --dir frontend/registration build
```

Deploy `dist/` as its own static site on its own URL, independent of the console. The
included `Dockerfile` does this end to end (build → nginx); `docker compose up
registration` from the repo root brings it up on port 5174 alongside the API.
