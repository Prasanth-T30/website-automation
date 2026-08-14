"""GET /api/dashboard — summary cards + full analytics for charts."""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_admin
from app.schemas.response_schema import ResponseModel
from app.services.dashboard_service import get_dashboard_summary, get_full_analytics

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/dashboard", response_model=ResponseModel)
async def dashboard(admin: dict = Depends(get_current_admin)):
    summary = await get_dashboard_summary()
    return ResponseModel(data=summary)


@router.get("/dashboard/analytics", response_model=ResponseModel)
async def analytics(admin: dict = Depends(get_current_admin)):
    data = await get_full_analytics()
    return ResponseModel(data=data)
