"""POST /api/auth/login"""
from fastapi import APIRouter

from app.schemas.login_schema import LoginRequest, TokenResponse
from app.schemas.response_schema import ResponseModel
from app.services.auth_service import authenticate_admin

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=ResponseModel)
async def login(payload: LoginRequest):
    result = await authenticate_admin(payload.email, payload.password)
    return ResponseModel(success=True, message="Login successful", data=result)
