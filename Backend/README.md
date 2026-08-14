# Internship Registration & Approval Portal — Backend

FastAPI + MongoDB Atlas backend for the DVein Innovations internship registration and admin
approval system. Handles registration submissions, payment-screenshot uploads, admin auth,
approve/reject workflows (auto-emails a branded PDF offer letter), dashboard analytics, and
Excel/CSV export.

## Tech Stack

FastAPI, Pydantic, JWT (python-jose), bcrypt (passlib), MongoDB Atlas via Motor, SMTP,
ReportLab (PDF generation), Pandas/openpyxl (Excel/CSV export), Uvicorn.

## Project Structure

```
app/
  main.py                  FastAPI app, CORS, routers, startup/shutdown
  core/                    config.py, security.py, constants.py, deps.py (JWT dependency)
  database/                connection.py, mongodb.py
  models/                  registration_model.py, admin_model.py, settings_model.py
  schemas/                 pydantic request/response models
  services/                business logic incl. pdf_service.py (offer-letter generator)
  routes/                  auth, registration, dashboard, upload, settings
  utils/                   jwt_handler, password, validators, helper, file_upload
  assets/                  dvein_logo.png, signature.png (used by pdf_service.py)
uploads/
  payments/                stored payment screenshots
  templates/               admin-uploaded template files
seed_admin.py              creates the first admin user
requirements.txt
.env.example
```

## Getting Started

### 1. MongoDB Atlas

1. Create a free cluster at https://www.mongodb.com/cloud/atlas.
2. Create a database user and allow network access (or `0.0.0.0/0` for development).
3. Copy the connection string into `.env` as `MONGO_URI`.

### 2. Install & configure

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill in MONGO_URI, JWT_SECRET_KEY, SMTP_* values
python seed_admin.py      # creates the first admin (uses DEFAULT_ADMIN_EMAIL/PASSWORD from .env)
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/api/docs`.

### 3. SMTP (email delivery)

Works with any standard SMTP provider (Brevo, Gmail with an App Password, etc.). Set
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL` in `.env`.

- **Brevo:** `smtp-relay.brevo.com`, port `587`, SMTP login + SMTP key from **SMTP & API > SMTP**.
- **Gmail:** `smtp.gmail.com`, port `587`, your Gmail address + a 16-character **App Password**
  (requires 2-Step Verification enabled on the Google account).

## API Reference

| Method  | Endpoint                                | Description                           |
|---------|------------------------------------------|-----------------------------------------|
| POST    | `/api/auth/login`                       | Admin login, returns JWT                |
| POST    | `/api/register`                         | Submit a student registration           |
| GET     | `/api/registrations`                    | List/search/filter/paginate             |
| GET     | `/api/registrations/{id}`               | Get one registration                    |
| PUT     | `/api/registrations/{id}/approve`       | Approve + email offer-letter PDF        |
| PUT     | `/api/registrations/{id}/reject`        | Reject + email reason                   |
| DELETE  | `/api/registrations/{id}`               | Delete a registration                   |
| GET     | `/api/registrations/{id}/offer-letter`  | Download the generated PDF directly     |
| GET     | `/api/dashboard`                        | Summary cards                           |
| GET     | `/api/dashboard/analytics`              | Full analytics payload                  |
| POST    | `/api/template/upload`                  | Upload an admin template asset          |
| GET     | `/api/export/excel`                     | Export all registrations (.xlsx)        |
| GET     | `/api/export/csv`                       | Export all registrations (.csv)         |
| GET/PUT | `/api/settings`, `/api/settings/{key}`  | Portal settings (email templates, etc.) |

All admin-only endpoints require `Authorization: Bearer <token>`.

## Deployment

Deploy to Render or Railway. Set the same environment variables as `.env.example`, point
`CORS_ORIGINS` at your deployed frontend URL, and use a persistent disk (or migrate `uploads/`
to S3/Cloudinary) since Render/Railway's filesystem is ephemeral on redeploy.

## Future Enhancements

- Move payment screenshots and templates to S3/Cloudinary (`utils/file_upload.py` is structured
  so the storage backend can be swapped without touching route/service code).
- Add refresh tokens and role-based permissions (multiple admin roles).
- Add student-facing status lookup by Registration ID + email.
- Add automated tests (pytest + httpx).
