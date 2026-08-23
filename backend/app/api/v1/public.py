"""Public, unauthenticated endpoints — the registration form's backend.

No auth dependency anywhere in this router by design: this is the only
surface strangers on the internet can write to, which is why it's rate
limited and why `applications` is a separate collection the rest of the
system never trusts blindly (conversion to a Student is an explicit,
authenticated action — see routers/applications.py).
"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status
from pydantic import ValidationError

from app.api.deps import ApplicationRepo, Storage
from app.core.config import settings
from app.core.constants import (
    CATEGORY_CHOICES,
    DOMAIN_CATALOG,
    DOMAIN_CHOICES,
    DURATION_CHOICES,
    TITLE_CHOICES,
    YEAR_CHOICES,
    passed_out_year_choices,
)
from app.core.ratelimit import limiter
from app.repositories.applications import DuplicateTransactionId
from app.schemas.application import ApplicationCreate, ApplicationOut, ChoicesOut, ProgrammeOut

router = APIRouter(prefix="/public", tags=["Public"])

ALLOWED_SCREENSHOT_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_SCREENSHOT_MB = 5


@router.get("/choices", response_model=ChoicesOut)
def get_choices() -> ChoicesOut:
    return ChoicesOut(
        titles=TITLE_CHOICES,
        categories=CATEGORY_CHOICES,
        domains=DOMAIN_CHOICES,
        durations=DURATION_CHOICES,
        years=YEAR_CHOICES,
        passed_out_years=passed_out_year_choices(),
        programmes=[
            ProgrammeOut(name=d.name, summary=d.summary, stack=list(d.stack))
            for d in DOMAIN_CATALOG
        ],
    )


@router.post("/applications", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.public_form_rate_limit)
async def submit_application(
    request: Request,  # noqa: ARG001 — required by the rate limiter
    response: Response,  # noqa: ARG001 — slowapi injects rate-limit headers here
    applications: ApplicationRepo,
    storage: Storage,
    title: str | None = Form(None),
    # The deployed form renamed this field to `salutation`. Accept either so a
    # running site keeps working through a redeploy in whichever order it lands.
    salutation: str | None = Form(None),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    college: str = Form(...),
    place: str = Form(...),
    department: str | None = Form(None),
    year: str | None = Form(None),
    applicant_type: str = Form("student"),
    category: str = Form(...),
    domain: str = Form(...),
    duration: str = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    amount: float = Form(...),
    transaction_id: str = Form(...),
    declaration: bool = Form(...),
    mode: str | None = Form(None),
    project_topic: str | None = Form(None),
    other: str | None = Form(None),
    native_place: str | None = Form(None),
    passed_out_year: str | None = Form(None),
    payment_screenshot: UploadFile = File(...),
) -> ApplicationOut:
    try:
        data = ApplicationCreate(
            title=title or salutation,
            name=name,
            email=email,
            phone=phone,
            college=college,
            place=place,
            department=department,
            year=year,
            applicant_type=applicant_type,
            category=category,
            domain=domain,
            duration=duration,
            start_date=start_date,
            end_date=end_date,
            amount=amount,
            transaction_id=transaction_id,
            declaration=declaration,
            mode=mode,
            project_topic=project_topic,
            other=other,
            native_place=native_place,
            passed_out_year=passed_out_year,
        )
    except ValidationError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()[0]["msg"]
        ) from exc

    suffix = Path(payment_screenshot.filename or "").suffix.lower()
    if suffix not in ALLOWED_SCREENSHOT_EXTENSIONS:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{suffix}' not allowed. Use JPG or PNG.",
        )

    content = await payment_screenshot.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Uploaded screenshot is empty.")
    if len(content) > MAX_SCREENSHOT_MB * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_SCREENSHOT_MB} MB limit.",
        )

    stored_filename = f"{uuid.uuid4().hex}{suffix}"
    storage.upload(
        stored_filename=stored_filename,
        content=content,
        content_type=payment_screenshot.content_type or "image/jpeg",
    )

    try:
        created = applications.create(
            **data.model_dump(),
            payment_screenshot=stored_filename,
        )
    except DuplicateTransactionId as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This transaction ID has already been used.",
        ) from exc

    return ApplicationOut.model_validate(created)


# ── Compatibility surface ───────────────────────────────────────────────────
# `<base>/register` is the path the previous standalone backend used, and the
# retired Vercel form posted to it. That form is no longer the published one
# and its origin has been removed from CORS, but the route stays: a bookmark,
# a cached page or a link in an old email would otherwise 404 silently, and a
# lost registration is worse than an extra route.
#
# It is the identical function, not a copy: same validation, same rate limit,
# same storage write, so the two paths cannot drift apart.
compat_router = APIRouter(tags=["Public"])
compat_router.add_api_route(
    "/register",
    submit_application,
    methods=["POST"],
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a registration (legacy path)",
)
