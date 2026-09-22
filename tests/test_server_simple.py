"""Test server khởi động đơn giản"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("KIỂM TRA KHỞI ĐỘNG SERVER")
print("=" * 60)

# Kiểm tra modules cần thiết
print("\n1. Kiểm tra modules...")
try:
    import fastapi
    print(f"   ✓ FastAPI {fastapi.__version__}")
except ImportError as e:
    print(f"   ✗ FastAPI chưa cài: {e}")
    print("   → Chạy: pip install fastapi")
    sys.exit(1)

try:
    import uvicorn
    print(f"   ✓ Uvicorn OK")
except ImportError as e:
    print(f"   ✗ Uvicorn chưa cài: {e}")
    print("   → Chạy: pip install uvicorn")
    sys.exit(1)

try:
    import jwt
    print(f"   ✓ PyJWT OK")
except ImportError as e:
    print(f"   ✗ PyJWT chưa cài: {e}")
    print("   → Chạy: pip install PyJWT")
    sys.exit(1)

try:
    import bcrypt
    print(f"   ✓ Bcrypt OK")
except ImportError as e:
    print(f"   ✗ Bcrypt chưa cài: {e}")
    print("   → Chạy: pip install bcrypt")
    sys.exit(1)

# Kiểm tra config
print("\n2. Kiểm tra config...")
try:
    from config.settings import settings
    print(f"   ✓ Settings loaded")
    print(f"     - Port: {settings.PORT}")
    print(f"     - JWT_SECRET: {'...' + settings.JWT_SECRET[-10:] if len(settings.JWT_SECRET) > 10 else 'TOO SHORT!'}")
    print(f"     - ADMIN_EMAIL: {settings.ADMIN_EMAIL}")
    print(f"     - ADMIN_PASSWORD: {'Đã đặt' if settings.ADMIN_PASSWORD else 'CHƯA ĐẶT!'}")
except Exception as e:
    print(f"   ✗ Lỗi config: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Kiểm tra database
print("\n3. Kiểm tra database...")
try:
    from database.db_session import init_db
    print(f"   ✓ DB session module OK")
    print("   → Khởi tạo database...")
    init_db()
    print(f"   ✓ Database initialized")
except Exception as e:
    print(f"   ✗ Lỗi database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Kiểm tra backend
print("\n4. Kiểm tra backend...")
try:
    from backend.main import app
    print(f"   ✓ Backend app loaded")
    print(f"   ✓ App routes: {len(app.routes)} routes")
except Exception as e:
    print(f"   ✗ Lỗi backend: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ TẤT CẢ KIỂM TRA THÀNH CÔNG!")
print("=" * 60)
print(f"\nServer sẽ chạy tại: http://{settings.HOST}:{settings.PORT}")
print("\nĐể khởi động server:")
print("  python app.py")
print("\nHoặc thủ công:")
print(f"  uvicorn backend.main:app --host {settings.HOST} --port {settings.PORT} --reload")
print("\n")
