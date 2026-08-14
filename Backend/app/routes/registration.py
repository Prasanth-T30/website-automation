"""
Registration endpoints:
  POST   /api/register
  GET    /api/registrations
  GET    /api/registrations/{id}
  PUT    /api/registrations/{id}/approve
  PUT    /api/registrations/{id}/reject
  DELETE /api/registrations/{id}
  GET    /api/registrations/{id}/offer-letter
  GET    /api/export/excel
  GET    /api/export/csv
"""
import io
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_admin
from app.schemas.registration_schema import ApproveRequest, RegistrationCreate, RejectRequest
from app.schemas.response_schema import PaginatedResponse, ResponseModel
from app.services.pdf_service import generate_offer_letter
from app.services.registration_service import (
    approve_registration,
    create_registration,
    delete_registration,
    export_to_csv,
    export_to_excel,
    get_registration_or_404,
    list_registrations,
    reject_registration,
)
from app.services.upload_service import handle_payment_upload
from app.utils.helper import serialize_document

router = APIRouter(prefix="/api", tags=["Registrations"])


@router.post("/register", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def register_student(
    title: str | None = Form(None),
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
    start_date: str = Form(...),
    end_date: str = Form(...),
    amount: float = Form(...),
    transaction_id: str = Form(...),
    declaration: bool = Form(...),
    payment_screenshot: UploadFile = File(...),
):
    try:
        payload = RegistrationCreate(
            title=title, name=name, email=email, phone=phone, college=college, place=place,
            department=department, year=year, applicant_type=applicant_type, category=category, domain=domain, duration=duration,
            start_date=start_date, end_date=end_date, amount=amount,
            transaction_id=transaction_id, declaration=declaration,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    try:
        filename = await handle_payment_upload(payment_screenshot)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    registration = await create_registration(payload, filename)
    return ResponseModel(success=True, message="Registration submitted successfully", data=registration)


@router.get("/registrations", response_model=PaginatedResponse)
async def get_registrations(
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    domain: str | None = Query(None),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: int = Query(-1),
    admin: dict = Depends(get_current_admin),
):
    items, total = await list_registrations(search, status_filter, domain, category, page, page_size, sort_by, sort_dir)
    total_pages = max((total + page_size - 1) // page_size, 1)
    return PaginatedResponse(data=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/registrations/{registration_id}", response_model=ResponseModel)
async def get_registration(registration_id: str, admin: dict = Depends(get_current_admin)):
    doc = await get_registration_or_404(registration_id)
    return ResponseModel(data=serialize_document(doc))


@router.put("/registrations/{registration_id}/approve", response_model=ResponseModel)
async def approve(registration_id: str, payload: ApproveRequest, admin: dict = Depends(get_current_admin)):
    updated = await approve_registration(registration_id, payload.subject, payload.body)
    message = "Registration approved and email sent" if updated.get("email_sent") else "Registration approved (no email sent for this category)"
    return ResponseModel(message=message, data=updated)


@router.put("/registrations/{registration_id}/reject", response_model=ResponseModel)
async def reject(registration_id: str, payload: RejectRequest, admin: dict = Depends(get_current_admin)):
    updated = await reject_registration(registration_id, payload.reason)
    return ResponseModel(message="Registration rejected and email sent", data=updated)


@router.delete("/registrations/{registration_id}", response_model=ResponseModel)
async def delete(registration_id: str, admin: dict = Depends(get_current_admin)):
    await delete_registration(registration_id)
    return ResponseModel(message="Registration deleted")


@router.get("/registrations/{registration_id}/offer-letter")
async def download_offer_letter(registration_id: str, admin: dict = Depends(get_current_admin)):
    doc = await get_registration_or_404(registration_id)
    pdf_bytes = generate_offer_letter(serialize_document(doc))
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Offer_Letter_{doc["registration_id"]}.pdf"'},
    )


@router.get("/export/excel")
async def export_excel(admin: dict = Depends(get_current_admin)):
    content = await export_to_excel()
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=registrations.xlsx"},
    )


@router.get("/export/csv")
async def export_csv(admin: dict = Depends(get_current_admin)):
    content = await export_to_csv()
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=registrations.csv"},
    )
