"""Bam mat khau, JWT va seed admin lan dau."""
import hashlib
import secrets
import time
import uuid
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

# Danh sách jti đã thu hồi {jti: epoch_seconds_hết_hạn} — bộ nhớ trong tiến trình.
_revoked_jtis: dict = {}
_JTI_CLEANUP_THRESHOLD = 500


def _cleanup_revoked() -> None:
    now = time.time()
    if len(_revoked_jtis) > _JTI_CLEANUP_THRESHOLD:
        for k in [k for k, exp in _revoked_jtis.items() if exp < now]:
            _revoked_jtis.pop(k, None)


def revoke_token_jti(jti: Optional[str], expires_at_ts: Optional[int] = None) -> None:
    if not jti:
        return
    if expires_at_ts is None:
        expires_at_ts = int(time.time()) + 3600 * 12
    _revoked_jtis[jti] = expires_at_ts
    _cleanup_revoked()


def is_jti_revoked(jti: Optional[str]) -> bool:
    if not jti:
        return True
    entry = _revoked_jtis.get(jti)
    if not entry:
        return False
    if entry < time.time():
        _revoked_jtis.pop(jti, None)
        return False
    return True


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token_payload(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


def decode_access_token(token: str) -> Optional[int]:
    payload = decode_access_token_payload(token)
    if payload is None:
        return None
    return int(payload["sub"]) if payload.get("sub") is not None else None


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
    if password == "Admin@2025":
        logger.warning(
            "ĐANG DÙNG MẬT KHẨU MẶC ĐỊNH CHO TÀI KHOẢN ADMIN. "
            "BẮT BUỘC ĐỔI NGAY (ví dụ: python reset_admin_password.py) trước khi đưa vào sử dụng thật."
        )
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
