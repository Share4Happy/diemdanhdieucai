"""
Reset password của admin về giá trị trong .env
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 70)
print("RESET PASSWORD ADMIN")
print("=" * 70)

try:
    from config.settings import settings
    from database.db_session import SessionLocal
    from database.models import User
    from services.auth_service import hash_password
    
    db = SessionLocal()
    
    admin_email = settings.ADMIN_EMAIL.strip().lower()
    admin_password = settings.ADMIN_PASSWORD
    
    print(f"\nEmail: {admin_email}")
    print(f"Password mới: {admin_password}")
    
    # Tìm admin
    admin = db.query(User).filter(User.email == admin_email).first()
    
    if not admin:
        print(f"\n✗ Không tìm thấy user với email: {admin_email}")
        print("\nTạo admin mới...")
        
        admin = User(
            email=admin_email,
            full_name=settings.ADMIN_FULL_NAME or "Quản trị hệ thống",
            password_hash=hash_password(admin_password),
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        print(f"✓ Đã tạo admin mới: {admin_email}")
    else:
        print(f"\n✓ Tìm thấy user: {admin.email}")
        print(f"  Role: {admin.role}")
        print(f"  Active: {admin.is_active}")
        
        # Update password
        old_hash = admin.password_hash[:30]
        admin.password_hash = hash_password(admin_password)
        db.commit()
        new_hash = admin.password_hash[:30]
        
        print(f"\n✓ Đã cập nhật password!")
        print(f"  Old hash: {old_hash}...")
        print(f"  New hash: {new_hash}...")
    
    # Test login
    from services.auth_service import verify_password
    if verify_password(admin_password, admin.password_hash):
        print(f"\n✅ TEST THÀNH CÔNG!")
        print(f"\nThông tin đăng nhập:")
        print(f"  Email: {admin_email}")
        print(f"  Password: {admin_password}")
    else:
        print(f"\n✗ TEST THẤT BẠI! Password không khớp.")
    
    db.close()
    
except Exception as e:
    print(f"\n✗ Lỗi: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("HOÀN TẤT")
print("=" * 70)
print("\nBây giờ có thể đăng nhập tại: http://localhost:8000")
