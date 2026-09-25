from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database.db_session import get_db
from database.models import User
from services.auth_service import (
    AUTH_COOKIE_NAME,
    decode_access_token_payload,
    is_jti_revoked,
)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    # Chỉ chấp nhận token từ cookie (nhất quán với kiến trúc cookie-only đã ghi trong README).
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa đăng nhập")
    payload = decode_access_token_payload(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không hợp lệ")
    if is_jti_revoked(payload.get("jti")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã bị thu hồi")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không hợp lệ")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không hợp lệ")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không còn hoạt động")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ quản trị viên mới được thực hiện thao tác này")
    return user
