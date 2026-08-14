"""
Central application configuration, loaded from environment variables (.env).
"""
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # App
    APP_NAME: str = "Internship Registration & Approval Portal"
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    API_PREFIX: str = "/api"

    # Security / JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-this-secret-key-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24h

    # CORS
    # Two separate frontend apps share this one backend:
    #   Registration-Site (public registration form) — default http://localhost:5174
    #   Admin-Site        (admin login + dashboard)   — default http://localhost:5175
    # 5173/3000 are kept for backward compatibility with the original combined Frontend app.
    CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5174,http://localhost:5175,http://localhost:5173,http://localhost:3000",
        ).split(",")
        if origin.strip()
    ]

    # MongoDB Atlas
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "internship_portal")

    # SMTP (Brevo)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp-relay.brevo.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "info@dveininnovation.com")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "DVein Innovations")

    # File Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
    PAYMENTS_DIR: str = os.path.join(UPLOAD_DIR, "payments")
    TEMPLATES_DIR: str = os.path.join(UPLOAD_DIR, "templates")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))
    ALLOWED_IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png"}

    # Default admin (seed script)
    DEFAULT_ADMIN_EMAIL: str = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@dveininnovation.com")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@12345")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
