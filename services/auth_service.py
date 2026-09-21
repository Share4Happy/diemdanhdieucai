"""Bam mat khau, JWT va seed admin lan dau."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session

from config.logging_config import logger
from config.settings import settings
from database.models import User

AUTH_COOKIE_NAME = "access_token"
RESET_TOKEN_HOURS = 1


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def seed_admin_if_empty(db: Session) -> None:
    """Tao admin dau tien khi bang users trong va ADMIN_EMAIL/PASSWORD da cau hinh."""
    if db.query(User).first() is not None:
        return
    email = (settings.ADMIN_EMAIL or "").strip().lower()
    password = settings.ADMIN_PASSWORD or ""
    if not email or not password:
        logger.warning(
            "Chưa có tài khoản nào. Đặt ADMIN_EMAIL và ADMIN_PASSWORD rồi khởi động lại để tạo admin."
        )
        return
    admin = User(
        email=email,
        full_name=settings.ADMIN_FULL_NAME or "Quản trị hệ thống",
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.info(f"Đã tạo tài khoản admin khởi tạo: {email}")
