from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db
from database.models import User
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_active_user,
    get_optional_current_user,
    require_admin
)
from backend.schemas.auth_schemas import (
    LoginRequest,
    TokenResponse,
    UserResponse,
    UserCreate,
    UserUpdate,
    ChangePasswordRequest
)

router = APIRouter(prefix="/auth", tags=["Xác thực & Tài khoản (Authentication)"])

@router.post("/login", response_model=TokenResponse, summary="Đăng nhập hệ thống (JSON)")
async def login(
    req: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Xác thực tên đăng nhập & mật khẩu.
    Trả về JWT Bearer Token có hiệu lực 24 giờ cùng thông tin người dùng.
    """
    user = db.query(User).filter(User.username == req.username.strip()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn đã bị vô hiệu hóa hoặc khóa"
        )

    # Cập nhật thời gian đăng nhập gần nhất
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    expires_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(data={
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "full_name": user.full_name
    })

    logger.info(f"Người dùng '{user.username}' ({user.role}) đã đăng nhập thành công!")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_seconds,
        user=UserResponse.model_validate(user)
    )

@router.post("/token", summary="OAuth2 Password Token Endpoint (Dành cho Swagger UI /docs)")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Endpoint chuẩn OAuth2 Password Bearer tương thích nút 'Authorize' trên Swagger UI.
    """
    user = db.query(User).filter(User.username == form_data.username.strip()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa"
        )

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(data={
        "sub": user.username,
        "user_id": user.id,
        "role": user.role
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse, summary="Lấy thông tin tài khoản hiện tại")
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Trả về thông tin hồ sơ và vai trò của người dùng đang đăng nhập dựa trên JWT token.
    """
    return UserResponse.model_validate(current_user)

@router.post("/change-password", summary="Đổi mật khẩu người dùng hiện tại")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cho phép người dùng đang đăng nhập đổi mật khẩu tài khoản cá nhân.
    """
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu cũ không chính xác"
        )
    
    if len(req.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải có tối thiểu 6 ký tự"
        )

    current_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    logger.info(f"Người dùng '{current_user.username}' đã đổi mật khẩu thành công.")
    return {"success": True, "message": "Đổi mật khẩu thành công"}

@router.post("/logout", summary="Đăng xuất khỏi hệ thống")
async def logout(
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Đăng xuất người dùng. Client cần xóa token ở localStorage / sessionStorage.
    """
    if current_user:
        logger.info(f"Người dùng '{current_user.username}' đã gửi yêu cầu đăng xuất.")
    return {"success": True, "message": "Đăng xuất thành công"}

# ==========================================
# QUẢN LÝ TÀI KHOẢN NGƯỜI DÙNG (DÀNH CHO ADMIN)
# ==========================================

@router.get("/users", response_model=List[UserResponse], summary="Danh sách tài khoản (Chỉ Admin)")
async def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Lấy toàn bộ danh sách tài khoản trong hệ thống. Chỉ dành cho quyền Quản trị viên (Admin).
    """
    users = db.query(User).order_by(User.id.asc()).all()
    return [UserResponse.model_validate(u) for u in users]

@router.post("/users", response_model=UserResponse, summary="Tạo tài khoản mới (Chỉ Admin)")
async def create_user(
    req: UserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Tạo tài khoản mới cho giáo viên hoặc quản trị viên.
    """
    clean_username = req.username.strip().lower()
    if len(clean_username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên đăng nhập phải có ít nhất 3 ký tự"
        )

    existing = db.query(User).filter(User.username == clean_username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tên đăng nhập '{clean_username}' đã tồn tại"
        )
    
    if len(req.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu phải có tối thiểu 6 ký tự"
        )

    new_user = User(
        username=clean_username,
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name or clean_username,
        role=req.role or "teacher",
        email=req.email,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"Admin '{admin.username}' vừa tạo tài khoản mới: '{new_user.username}' ({new_user.role})")
    return UserResponse.model_validate(new_user)

@router.put("/users/{user_id}", response_model=UserResponse, summary="Chỉnh sửa tài khoản (Chỉ Admin)")
async def update_user(
    user_id: int,
    req: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Cập nhật thông tin, trạng thái kích hoạt, vai trò hoặc đặt lại mật khẩu cho tài khoản.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người dùng có ID {user_id}"
        )

    if req.full_name is not None:
        target_user.full_name = req.full_name
    if req.role is not None:
        target_user.role = req.role
    if req.email is not None:
        target_user.email = req.email
    if req.is_active is not None:
        if target_user.id == admin.id and not req.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tự khóa tài khoản của chính mình"
            )
        target_user.is_active = req.is_active
    if req.password:
        if len(req.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu mới phải có tối thiểu 6 ký tự"
            )
        target_user.hashed_password = get_password_hash(req.password)

    db.commit()
    db.refresh(target_user)
    logger.info(f"Admin '{admin.username}' vừa cập nhật tài khoản ID {user_id} ('{target_user.username}')")
    return UserResponse.model_validate(target_user)

@router.delete("/users/{user_id}", summary="Xóa tài khoản (Chỉ Admin)")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Xóa tài khoản người dùng khỏi hệ thống. Không thể tự xóa chính mình.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người dùng có ID {user_id}"
        )

    if target_user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn không thể xóa tài khoản của chính mình"
        )

    del_username = target_user.username
    db.delete(target_user)
    db.commit()
    logger.info(f"Admin '{admin.username}' vừa xóa tài khoản '{del_username}' (ID {user_id})")
    return {"success": True, "message": f"Đã xóa tài khoản '{del_username}' thành công"}
