"""Test server khởi động đơn giản"""
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_server_modules_and_app():
    """Kiểm tra các thư viện cốt lõi và khởi tạo ứng dụng FastAPI."""
    import fastapi
    import uvicorn
    import jwt
    import bcrypt

    assert fastapi is not None
    assert uvicorn is not None
    assert jwt is not None
    assert bcrypt is not None

    from config.settings import settings
    assert settings is not None

    from database.db_session import init_db
    init_db()

    from backend.main import app
    assert app is not None
    assert len(app.routes) > 0


if __name__ == "__main__":
    test_server_modules_and_app()
    print("✅ Tất cả kiểm tra server thành công!")
