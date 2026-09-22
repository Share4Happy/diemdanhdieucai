"""
Kiểm tra tài khoản admin trong database
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 70)
print("KIỂM TRA TÀI KHOẢN ADMIN")
print("=" * 70)

# 1. Kiểm tra .env
print("\n1. Kiểm tra file .env:")
try:
    from config.settings import settings
    print(f"   ADMIN_EMAIL: {settings.ADMIN_EMAIL}")
    print(f"   ADMIN_PASSWORD: {'Đã đặt' if settings.ADMIN_PASSWORD else 'CHƯA ĐẶT!'}")
    print(f"   JWT_SECRET: {settings.JWT_SECRET[:20]}...")
except Exception as e:
    print(f"   ✗ Lỗi: {e}")
    sys.exit(1)

# 2. Kiểm tra database
print("\n2. Kiểm tra database:")
try:
    from database.db_session import SessionLocal
    from database.models import User
    
    db = SessionLocal()
    
    # Đếm user
    total_users = db.query(User).count()
    print(f"   Tổng số user trong DB: {total_users}")
    
    if total_users == 0:
        print("   ⚠️ CẢNH BÁO: Chưa có user nào!")
        print("   → Cần chạy init_db() để tạo admin")
        
        # Thử tạo admin
        print("\n3. Thử tạo admin tự động:")
        from services.auth_service import seed_admin_if_empty
        seed_admin_if_empty(db)
        db.commit()
        
        total_users = db.query(User).count()
        print(f"   Số user sau khi seed: {total_users}")
    
    # Liệt kê user
    print("\n4. Danh sách user:")
    users = db.query(User).all()
    for u in users:
        print(f"   - ID: {u.id}")
        print(f"     Email: {u.email}")
        print(f"     Full name: {u.full_name}")
        print(f"     Role: {u.role}")
        print(f"     Active: {u.is_active}")
        print(f"     Password hash: {u.password_hash[:30]}...")
    
    # Test password
    print("\n5. Test đăng nhập:")
    admin_email = settings.ADMIN_EMAIL.strip().lower()
    admin = db.query(User).filter(User.email == admin_email).first()
    
    if not admin:
        print(f"   ✗ Không tìm thấy user với email: {admin_email}")
        print(f"   → Kiểm tra lại ADMIN_EMAIL trong .env")
    else:
        print(f"   ✓ Tìm thấy user: {admin.email}")
        
        # Test password
        from services.auth_service import verify_password
        password = settings.ADMIN_PASSWORD
        
        if verify_password(password, admin.password_hash):
            print(f"   ✓ Password ĐÚNG!")
            print(f"   ✓ Email: {admin_email}")
            print(f"   ✓ Password: {password}")
            print(f"   ✓ Có thể đăng nhập!")
        else:
            print(f"   ✗ Password SAI!")
            print(f"   → Password trong .env: {password}")
            print(f"   → Password hash trong DB: {admin.password_hash[:50]}...")
            print(f"\n   Đề xuất: Đặt lại password")
            print(f"   1. Xóa file database/attendance.db")
            print(f"   2. Chạy lại server để tạo admin mới")
    
    db.close()
    
except Exception as e:
    print(f"   ✗ Lỗi: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("HOÀN TẤT KIỂM TRA")
print("=" * 70)
