# Internship Registration Portal — Registration Site

This is the **public-facing** app: students land here, register for an internship, and
upload payment proof. It has **no admin routes at all** — the Admin experience is a
completely separate app (see `../Admin-Site`). Both apps talk to the same shared `../Backend`.

## Routes

```
/           Home
/register   Registration form
/success    Confirmation after submitting
```

## Getting Started

```bash
npm install
cp .env.example .env
npm run dev
```

Runs at **http://localhost:5174**. Requires `../Backend` running at `http://localhost:8000`
(the dev server proxies `/api` and `/uploads` there — see `vite.config.js`).

`VITE_ADMIN_SITE_URL` (default `http://localhost:5175`) is only used for the "Admin Login"
link in the navbar, which is a plain link to the separate Admin app — not a client-side route.

## Build & Deploy

```bash
npm run build
```

Deploy `dist/` as its own static site, on its own URL/subdomain, independent of the Admin app.
Set `VITE_API_BASE_URL` and `VITE_ADMIN_SITE_URL` in the hosting provider's env vars.
