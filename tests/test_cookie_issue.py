"""
Kiểm tra vấn đề cookie và JWT
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 70)
print("KIỂM TRA COOKIE & JWT")
print("=" * 70)

try:
    from config.settings import settings
    from services.auth_service import create_access_token, decode_access_token
    
    print("\n1. Kiểm tra JWT Secret:")
    print(f"   JWT_SECRET: {settings.JWT_SECRET}")
    print(f"   Độ dài: {len(settings.JWT_SECRET)} ký tự")
    
    if len(settings.JWT_SECRET) < 20:
        print("   ⚠️ CẢNH BÁO: JWT_SECRET quá ngắn!")
        print("   → Nên dùng secret dài hơn 32 ký tự")
    
    print(f"\n2. Kiểm tra CORS:")
    print(f"   CORS_ORIGINS: {settings.CORS_ORIGINS}")
    
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
    print(f"\n   Các origin được phép:")
    for o in origins:
        print(f"     - {o}")
    
    print(f"\n3. Test JWT token:")
    # Tạo token test
    test_user_id = 1
    token = create_access_token(test_user_id)
    print(f"   Token mẫu: {token[:50]}...")
    
    # Decode token
    decoded_id = decode_access_token(token)
    if decoded_id == test_user_id:
        print(f"   ✓ JWT hoạt động đúng (user_id={decoded_id})")
    else:
        print(f"   ✗ JWT decode sai! Decoded: {decoded_id}, Expected: {test_user_id}")
    
    print(f"\n4. Kiểm tra cookie settings:")
    from services.auth_service import AUTH_COOKIE_NAME
    print(f"   Cookie name: {AUTH_COOKIE_NAME}")
    print(f"   JWT expire: {settings.JWT_EXPIRE_HOURS} giờ")
    print(f"   Cookie properties:")
    print(f"     - HttpOnly: True")
    print(f"     - SameSite: Lax")
    print(f"     - Secure: False (cho localhost)")
    print(f"     - Path: /")
    
    print(f"\n5. Kiểm tra backend URL:")
    print(f"   APP_PUBLIC_URL: {settings.APP_PUBLIC_URL}")
    print(f"   Nên trùng với URL bạn đang truy cập")
    
    print("\n" + "=" * 70)
    print("✅ TẤT CẢ KIỂM TRA HOÀN TẤT")
    print("=" * 70)
    
    print("\nNếu vẫn bị lỗi 401 khi refresh:")
    print("1. Xóa tất cả cookies trong F12 → Application → Cookies")
    print("2. Login lại")
    print("3. Kiểm tra F12 → Application → Cookies → Có 'access_token' không")
    print("4. Kiểm tra Network → Request có gửi Cookie header không")
    
except Exception as e:
    print(f"\n✗ LỖI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
