"""
=============================================================================
CÔNG CỤ ĐẶT LẠI MẬT KHẨU QUẢN TRỊ VIÊN (ADMIN) - THPT ĐIỀU CẢI
=============================================================================
Cách sử dụng:
    python scripts/reset_admin_password.py
    python scripts/reset_admin_password.py [mat_khau_moi]
"""
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
APP_DIR = BACKEND_DIR / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

def main():
    parser = argparse.ArgumentParser(description="Đặt lại mật khẩu admin hệ thống Điểm danh THPT Điều Cải")
    parser.add_argument("password", nargs="?", default=None, help="Mật khẩu mới (mặc định lấy từ .env ADMIN_PASSWORD)")
    args = parser.parse_args()

    try:
        from config.settings import settings
        from database.db_session import SessionLocal, init_db
        from database.models import User
        from services.auth_service import hash_password, verify_password
    except ImportError as e:
        print(f"[!] Lỗi nạp thư viện: {e}")
        print("    Vui lòng kích hoạt môi trường ảo (virtualenv) trước khi chạy script:")
        print("    Linux/Mac: source venv/bin/activate")
        print("    Windows:   call venv_cuda\\Scripts\\activate.bat")
        sys.exit(1)

    print("=" * 70)
    print(" ĐẶT LẠI MẬT KHẨU TÀI KHOẢN QUẢN TRỊ VIÊN (ADMIN)")
    print("=" * 70)

    init_db()
    db = SessionLocal()

    try:
        admin_email = (settings.ADMIN_EMAIL or "admin@truongdieucai.edu.vn").strip().lower()
        new_password = args.password or settings.ADMIN_PASSWORD or "Admin@2025"

        admin = db.query(User).filter(User.email == admin_email).first()

        if not admin:
            print(f"\n[*] Chưa tìm thấy tài khoản admin ({admin_email}). Đang tạo mới...")
            admin = User(
                email=admin_email,
                full_name=settings.ADMIN_FULL_NAME or "Quản trị hệ thống",
                password_hash=hash_password(new_password),
                role="admin",
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f" -> [THÀNH CÔNG] Đã tạo tài khoản Admin ID: {admin.id}")
        else:
            print(f"\n[*] Tìm thấy tài khoản Admin ID: {admin.id} ({admin.email})")
            admin.password_hash = hash_password(new_password)
            admin.is_active = True
            admin.role = "admin"
            db.commit()
            print(f" -> [THÀNH CÔNG] Đã cập nhật mật khẩu mới thành công!")

        # Kiểm tra tính toàn vẹn của mã băm
        if verify_password(new_password, admin.password_hash):
            print("\n" + "=" * 70)
            print(" XÁC THỰC MẬT KHẨU: HOÀN TOÀN CHÍNH XÁC")
            print(f" - URL đăng nhập: {settings.APP_PUBLIC_URL}/login")
            print(f" - Email:        {admin_email}")
            print(f" - Mật khẩu:     {new_password}")
            print("=" * 70)
        else:
            print("\n[LỖI] Kiểm tra băm mật khẩu không khớp!")

    except Exception as e:
        db.rollback()
        print(f"\n[LỖI]: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
