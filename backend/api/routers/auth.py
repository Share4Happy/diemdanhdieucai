from datetime import datetime, timedelta, timezone
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, require_admin
from backend.api.security import check_rate_limit, client_ip
from backend.schemas.auth_schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    UserCreateRequest,
    UserPublic,
    UserStatusRequest,
    UserUpdateRequest,
)
from config.logging_config import logger
from config.settings import settings
from database.db_session import get_db
from database.models import PasswordResetToken, User
from services.auth_service import (
    AUTH_COOKIE_NAME,
    RESET_TOKEN_HOURS,
    create_access_token,
    decode_access_token_payload,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    revoke_token_jti,
    verify_password,
)
from services.notification import notification_service

router = APIRouter(prefix="/auth", tags=["Auth"])

_FORGOT_COOLDOWN = timedelta(minutes=5)
_forgot_last_sent: Dict[str, datetime] = {}

FORGOT_OK_MESSAGE = "Nếu email tồn tại trong hệ thống, hướng dẫn đặt lại mật khẩu đã được gửi."


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=int(settings.JWT_EXPIRE_HOURS * 3600),
        path="/",
    )


def _prune_forgot_tracking() -> None:
    """Không để dict _forgot_last_sent phình bộ nhớ."""
    now = datetime.now(timezone.utc)
    for k in [k for k, t in _forgot_last_sent.items() if now - t > timedelta(hours=1)]:
        _forgot_last_sent.pop(k, None) if k in _forgot_last_sent else None


def _user_public(user: User) -> dict:
    return UserPublic.model_validate(user).model_dump()


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = client_ip(request)
    # Rate-limit chống brute-force: 10 lần/IP trong 5 phút, 15 lần/email+IP trong 15 phút
    check_rate_limit("login", f"ip:{ip}", limit=10, window_seconds=300)
    email = _normalize_email(req.email)
    check_rate_limit("login", f"email:{email}:{ip}", limit=15, window_seconds=900)
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng")
    token = create_access_token(user.id)
    _set_auth_cookie(response, token)
    return {"success": True, "user": _user_public(user)}


@router.post("/logout")
async def logout(request: Request, response: Response, _user: User = Depends(get_current_user)):
    token = request.cookies.get(AUTH_COOKIE_NAME) or ""
    payload = decode_access_token_payload(token) if token else None
    if payload:
        revoke_token_jti(payload.get("jti"), int(payload.get("exp", 0)))
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return {"success": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return _user_public(user)


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    email = _normalize_email(req.email)
    ip = client_ip(request)
    # Rate-limit chống spam email đặt lại mật khẩu
    check_rate_limit("forgot", f"ip:{ip}", limit=8, window_seconds=900)
    check_rate_limit("forgot", f"email:{email}:{ip}", limit=3, window_seconds=900)
    _prune_forgot_tracking()
    now = datetime.now(timezone.utc)
    last = _forgot_last_sent.get(email)
    if last and now - last < _FORGOT_COOLDOWN:
        return {"success": True, "message": FORGOT_OK_MESSAGE}

    _forgot_last_sent[email] = now
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user:
        return {"success": True, "message": FORGOT_OK_MESSAGE}

    raw_token = generate_reset_token()
    token_row = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(hours=RESET_TOKEN_HOURS),
    )
    db.add(token_row)
    db.commit()

    reset_url = f"{settings.APP_PUBLIC_URL.rstrip('/')}/reset-password.html?token={raw_token}"
    sent = notification_service.send_plain_email(
        to_email=user.email,
        subject="Đặt lại mật khẩu - Hệ thống điểm danh THPT Điều Cải",
        body=(
            f"Xin chào {user.full_name or user.email},\n\n"
            "Bạn (hoặc quản trị viên) đã yêu cầu đặt lại mật khẩu đăng nhập hệ thống điểm danh.\n"
            f"Mở liên kết sau trong vòng {RESET_TOKEN_HOURS} giờ để tạo mật khẩu mới:\n\n"
            f"{reset_url}\n\n"
            "Nếu bạn không yêu cầu, hãy bỏ qua email này.\n\n"
            "Trân trọng,\nHệ Thống Điểm Danh Tự Động AI"
        ),
    )
    if not sent:
        logger.warning("Không gửi được email đặt lại mật khẩu (SMTP chưa cấu hình hoặc lỗi gửi).")
    return {"success": True, "message": FORGOT_OK_MESSAGE}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit("forgot", f"ip:{client_ip(request)}", limit=10, window_seconds=600)
    token_hash = hash_reset_token((req.token or "").strip())
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )
    now = datetime.utcnow()
    if not row or row.used_at is not None or row.expires_at < now:
        raise HTTPException(status_code=400, detail="Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn")
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn")
    user.password_hash = hash_password(req.password)
    row.used_at = now
    db.commit()
    return {"success": True, "message": "Đã cập nhật mật khẩu. Bạn có thể đăng nhập lại."}


@router.get("/users")
async def list_users(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.asc()).all()
    return {"users": [_user_public(u) for u in users]}


@router.post("/users", status_code=201)
async def create_user(req: UserCreateRequest, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    role = (req.role or "staff").strip().lower()
    if role not in ("admin", "staff"):
        raise HTTPException(status_code=400, detail="Vai trò phải là admin hoặc staff")
    email = _normalize_email(req.email)
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Email không hợp lệ")
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")
    user = User(
        email=email,
        full_name=(req.full_name or "").strip(),
        password_hash=hash_password(req.password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"success": True, "user": _user_public(user)}


def _parse_role(role: str) -> str:
    value = (role or "").strip().lower()
    if value not in ("admin", "staff"):
        raise HTTPException(status_code=400, detail="Vai trò phải là admin hoặc staff")
    return value


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    return user


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    req: UserUpdateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, user_id)

    if req.full_name is not None:
        user.full_name = req.full_name.strip()

    if req.email is not None:
        email = _normalize_email(req.email)
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="Email không hợp lệ")
        existing = db.query(User).filter(User.email == email, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email đã được sử dụng")
        user.email = email

    if req.role is not None:
        new_role = _parse_role(req.role)
        if user.role == "admin" and new_role != "admin" and user.is_active:
            if _active_admin_count(db) <= 1:
                raise HTTPException(status_code=400, detail="Phải còn ít nhất một quản trị viên đang hoạt động")
        user.role = new_role

    if req.password:
        if len(req.password) < 8:
            raise HTTPException(status_code=400, detail="Mật khẩu tối thiểu 8 ký tự")
        user.password_hash = hash_password(req.password)

    db.commit()
    db.refresh(user)
    return {"success": True, "user": _user_public(user)}


@router.patch("/users/{user_id}/status")
async def set_user_status(
    user_id: int,
    req: UserStatusRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, user_id)
    if user.id == admin.id and not req.is_active:
        raise HTTPException(status_code=400, detail="Không thể tắt tài khoản đang đăng nhập")
    if user.role == "admin" and user.is_active and not req.is_active:
        if _active_admin_count(db) <= 1:
            raise HTTPException(status_code=400, detail="Không thể tắt quản trị viên hoạt động cuối cùng")
    user.is_active = req.is_active
    db.commit()
    db.refresh(user)
    return {"success": True, "user": _user_public(user)}
