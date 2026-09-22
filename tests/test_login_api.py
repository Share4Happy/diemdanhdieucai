"""
Test API login trực tiếp
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("=" * 70)
    print("TEST API LOGIN")
    print("=" * 70)

    try:
        from config.settings import settings
        from database.db_session import SessionLocal
        from database.models import User
        from services.auth_service import verify_password, create_access_token
        
        db = SessionLocal()
        
        # Lấy thông tin từ .env
        email = settings.ADMIN_EMAIL.strip().lower()
        password = settings.ADMIN_PASSWORD
        
        print(f"\n1. Thông tin đăng nhập:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        
        # Tìm user
        print(f"\n2. Tìm user trong database:")
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"   ✗ Không tìm thấy user với email: {email}")
            print(f"\n   → Chạy: python reset_admin_password.py")
            sys.exit(1)
        
        print(f"   ✓ Tìm thấy user: {user.email}")
        print(f"     ID: {user.id}")
        print(f"     Full name: {user.full_name}")
        print(f"     Role: {user.role}")
        print(f"     Active: {user.is_active}")
        
        # Kiểm tra active
        if not user.is_active:
            print(f"\n   ✗ User không active!")
            print(f"   → Set active = True")
            user.is_active = True
            db.commit()
            print(f"   ✓ Đã bật active")
        
        # Kiểm tra password
        print(f"\n3. Kiểm tra password:")
        if verify_password(password, user.password_hash):
            print(f"   ✓ Password ĐÚNG!")
        else:
            print(f"   ✗ Password SAI!")
            print(f"   → Chạy: python reset_admin_password.py")
            sys.exit(1)
        
        # Tạo JWT token
        print(f"\n4. Tạo JWT token:")
        token = create_access_token(user.id)
        print(f"   ✓ Token: {token[:50]}...")
        
        # Test decode
        from services.auth_service import decode_access_token
        decoded_user_id = decode_access_token(token)
        if decoded_user_id == user.id:
            print(f"   ✓ Token decode thành công: user_id={decoded_user_id}")
        else:
            print(f"   ✗ Token decode thất bại")
        
        print(f"\n5. Kết luận:")
        print(f"   ✅ API login sẽ hoạt động!")
        print(f"\n   Thông tin đăng nhập:")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"   Email:    {email}")
        print(f"   Password: {password}")
        print(f"   URL:      http://localhost:8000")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        db.close()
        
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()

