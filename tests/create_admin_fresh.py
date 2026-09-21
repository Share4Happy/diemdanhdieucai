"""
Tạo hoặc cập nhật admin với password từ .env
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 70)
print("TẠO/CẬP NHẬT ADMIN")
print("=" * 70)

try:
    from config.settings import settings
    from database.db_session import SessionLocal, init_db
    from database.models import User
    from services.auth_service import hash_password, verify_password
    
    # Khởi tạo DB trước
    print("\n1. Khởi tạo database...")
    init_db()
    print("   ✓ Database OK")
    
    db = SessionLocal()
    
    admin_email = settings.ADMIN_EMAIL.strip().lower()
    admin_password = settings.ADMIN_PASSWORD
    
    if not admin_email or not admin_password:
        print("\n✗ LỖI: ADMIN_EMAIL hoặc ADMIN_PASSWORD chưa được đặt trong .env")
        print("\nVui lòng thêm vào file .env:")
        print("ADMIN_EMAIL=admin@truongdieucai.edu.vn")
        print("ADMIN_PASSWORD=Admin@2025")
        sys.exit(1)
    
    print(f"\n2. Thông tin admin từ .env:")
    print(f"   Email: {admin_email}")
    print(f"   Password: {admin_password}")
    
    # Tìm hoặc tạo admin
    admin = db.query(User).filter(User.email == admin_email).first()
    
    if admin:
        print(f"\n3. Tìm thấy user hiện có:")
        print(f"   ID: {admin.id}")
        print(f"   Email: {admin.email}")
        print(f"   Role: {admin.role}")
        
        # Cập nhật password
        print(f"\n4. Cập nhật password mới...")
        admin.password_hash = hash_password(admin_password)
        admin.is_active = True
        admin.role = "admin"
        db.commit()
        print(f"   ✓ Đã cập nhật!")
        
    else:
        print(f"\n3. Chưa có user, tạo mới...")
        admin = User(
            email=admin_email,
            full_name=settings.ADMIN_FULL_NAME or "Quản trị hệ thống",
            password_hash=hash_password(admin_password),
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"   ✓ Đã tạo admin mới (ID: {admin.id})")
    
    # Test password
    print(f"\n5. Test password...")
    if verify_password(admin_password, admin.password_hash):
        print(f"   ✓✓✓ PASSWORD ĐÚNG! ✓✓✓")
    else:
        print(f"   ✗✗✗ PASSWORD SAI! ✗✗✗")
        print(f"   → Có vấn đề với bcrypt hash")
    
    # Hiển thị thông tin đăng nhập
    print(f"\n" + "=" * 70)
    print(f"✅ THÀNH CÔNG!")
    print(f"=" * 70)
    print(f"\nThông tin đăng nhập:")
    print(f"  URL:      http://localhost:8000")
    print(f"  Email:    {admin_email}")
    print(f"  Password: {admin_password}")
    print(f"\n" + "=" * 70)
    
    # Liệt kê tất cả users
    print(f"\nDanh sách tất cả users trong hệ thống:")
    all_users = db.query(User).all()
    for u in all_users:
        print(f"  - ID={u.id}, Email={u.email}, Role={u.role}, Active={u.is_active}")
    
    db.close()
    
except Exception as e:
    print(f"\n✗ LỖI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("Bây giờ có thể đăng nhập!")
print("=" * 70)
