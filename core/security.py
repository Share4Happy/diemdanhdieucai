import os
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db
from database.models import User

# OAuth2 Scheme trỏ tới endpoint chuẩn token của Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

HASH_ALGORITHM = "sha256"
HASH_ITERATIONS = 100000

def get_password_hash(password: str) -> str:
    """
    Băm mật khẩu bằng PBKDF2-HMAC-SHA256 với 100.000 vòng lặp và muối ngẫu nhiên 16 bytes.
    Định dạng lưu trữ: pbkdf2_sha256$iterations$salt$hash_hex
    """
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS
    )
    return f"pbkdf2_sha256${HASH_ITERATIONS}${salt}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Xác minh mật khẩu sử dụng so sánh thời gian hằng số hmac.compare_digest.
    """
    if not hashed_password or not plain_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            iterations = int(parts[1])
            salt = parts[2]
            expected_hash = parts[3]
            key = hashlib.pbkdf2_hmac(
                HASH_ALGORITHM,
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations
            )
            return hmac.compare_digest(key.hex(), expected_hash)
        
        # Hỗ trợ tương thích nếu chuỗi hash dạng salt$hash thông thường
        if len(parts) == 2:
            salt, expected_hash = parts[0], parts[1]
            key = hashlib.pbkdf2_hmac(
                HASH_ALGORITHM,
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                HASH_ITERATIONS
            )
            return hmac.compare_digest(key.hex(), expected_hash)
            
        return False
    except Exception as e:
        logger.error(f"Lỗi khi xác minh mật khẩu: {e}")
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Tạo JSON Web Token (JWT) có hạn sử dụng.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": now
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    Giải mã và kiểm tra tính hợp lệ của token JWT.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token JWT đã hết hạn!")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token JWT không hợp lệ: {e}")
        return None

async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Lấy thông tin người dùng nếu có token hợp lệ, không chặn nếu không có token.
    """
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    username = payload.get("sub")
    if not username:
        return None
    user = db.query(User).filter(User.username == username).first()
    return user

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency bắt buộc người dùng phải đăng nhập và gửi kèm token hợp lệ.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Thông tin xác thực không hợp lệ hoặc phiên đăng nhập đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if not username:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency kiểm tra người dùng có đang hoạt động hay bị khóa tài khoản.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn đã bị vô hiệu hóa hoặc tạm khóa"
        )
    return current_user

async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency bắt buộc người dùng có quyền Admin (Quản trị viên).
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền quản trị viên (Admin) để thực hiện thao tác này"
        )
    return current_user

def require_roles(allowed_roles: List[str]):
    """
    Helper dependency kiểm tra quyền linh hoạt theo danh sách vai trò cho phép.
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Thao tác yêu cầu một trong các quyền: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker
