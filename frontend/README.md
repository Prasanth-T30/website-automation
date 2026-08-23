# Frontend applications

Both browser-facing applications live in this directory and remain independent
build and deployment targets:

- `console/` — authenticated HR and admin console, served on port 5173 in development.
- `registration/` — public internship registration form, served on port 5174.

Run commands from the repository root:

```bash
pnpm install
pnpm console
pnpm registration
pnpm build
```

Each application owns its source, assets, Vite configuration, container image,
and environment template. Shared project orchestration stays at the repository
root, while the FastAPI service remains isolated in `backend/`.
