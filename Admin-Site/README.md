# DVein Admin Panel — Admin Site

This is the **admin-only** app: login, then the dashboard (registrations, analytics,
settings, profile). It has **no public registration routes at all** — the registration
flow is a completely separate app (see `../Registration-Site`). Both apps talk to the
same shared `../Backend`.

## Routes

```
/                    redirects to /login
/login               Admin login
/dashboard           (protected) overview cards
/registrations       (protected) list + search + filter
/registrations/:id   (protected) detail, approve/reject
/analytics           (protected) charts
/settings            (protected)
/profile             (protected)
```

All `/dashboard`, `/registrations`, `/analytics`, `/settings`, `/profile` routes require
being logged in — unauthenticated visits redirect to `/login`.

## Getting Started

```bash
npm install
cp .env.example .env
npm run dev
```

Runs at **http://localhost:5175**. Requires `../Backend` running at `http://localhost:8000`
(the dev server proxies `/api` and `/uploads` there — see `vite.config.js`). Admin
credentials come from the backend's `seed_admin.py` script.

`VITE_REGISTRATION_SITE_URL` (default `http://localhost:5174`) is only used for linking
back to the public site if needed — not a client-side route.

## Build & Deploy

```bash
npm run build
```

Deploy `dist/` as its own static site, on its own URL/subdomain (ideally not
publicly linked/indexed, since this is the admin surface). Set `VITE_API_BASE_URL` and
`VITE_REGISTRATION_SITE_URL` in the hosting provider's env vars.
