"""Admin authentication business logic."""
from fastapi import HTTPException, status

from app.core.security import verify_password
from app.database.mongodb import admins_collection
from app.utils.helper import serialize_document
from app.utils.jwt_handler import create_access_token


async def authenticate_admin(email: str, password: str) -> dict:
    admin = await admins_collection().find_one({"email": email})
    if not admin or not verify_password(password, admin["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    admin_out = serialize_document(admin)
    admin_out.pop("password_hash", None)

    token = create_access_token({"sub": admin_out["id"], "email": admin_out["email"], "role": admin_out.get("role", "admin")})
    return {"access_token": token, "token_type": "bearer", "admin": admin_out}
