"""
Kiểm tra xem file .env có được load vào settings không
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_settings_loads_properly():
    from config.settings import settings
    assert settings.ADMIN_EMAIL is not None
    assert settings.JWT_SECRET is not None

def main():
    print("=" * 70)
    print("KIỂM TRA LOAD FILE .ENV")
    print("=" * 70)

    # Kiểm tra file .env có tồn tại không
    env_file = PROJECT_ROOT / ".env"
    print(f"\n1. Kiểm tra file .env:")
    print(f"   Path: {env_file}")
    print(f"   Tồn tại: {'✓ CÓ' if env_file.exists() else '✗ KHÔNG'}")

    if env_file.exists():
        print(f"   Kích thước: {env_file.stat().st_size} bytes")
        
        # Đọc một vài dòng đầu
        print(f"\n2. Nội dung file .env (10 dòng đầu):")
        with open(env_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 10:
                    break
                if line.strip() and not line.strip().startswith('#'):
                    # Ẩn giá trị nhạy cảm
                    if '=' in line:
                        key = line.split('=')[0].strip()
                        print(f"     {key}=...")
    else:
        print("\n✗ LỖI: File .env không tồn tại!")
        print("→ Chạy: copy .env.example .env")
        sys.exit(1)

    # Test load dotenv
    print(f"\n3. Test load dotenv:")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print(f"   ✓ python-dotenv đã cài và hoạt động")
    except ImportError:
        print(f"   ✗ python-dotenv CHƯA cài!")
        print(f"   → Chạy: pip install python-dotenv")
        sys.exit(1)

    # Kiểm tra các biến môi trường
    print(f"\n4. Kiểm tra biến môi trường từ .env:")

    env_vars = {
        'JWT_SECRET': os.getenv('JWT_SECRET'),
        'ADMIN_EMAIL': os.getenv('ADMIN_EMAIL'),
        'ADMIN_PASSWORD': os.getenv('ADMIN_PASSWORD'),
        'CORS_ORIGINS': os.getenv('CORS_ORIGINS'),
        'APP_PUBLIC_URL': os.getenv('APP_PUBLIC_URL'),
    }

    all_ok = True
    for key, value in env_vars.items():
        if value:
            # Ẩn giá trị password và secret
            if 'PASSWORD' in key or 'SECRET' in key:
                display = f"{'*' * 8} (độ dài: {len(value)})"
            else:
                display = value[:50] + ('...' if len(value) > 50 else '')
            print(f"   ✓ {key}: {display}")
        else:
            print(f"   ✗ {key}: CHƯA ĐẶT!")
            all_ok = False

    # Load settings
    print(f"\n5. Load settings.py:")
    try:
        from config.settings import settings
        print(f"   ✓ Settings loaded")
        
        print(f"\n6. Kiểm tra giá trị trong settings:")
        print(f"   JWT_SECRET: {'*' * 8} (độ dài: {len(settings.JWT_SECRET)})")
        print(f"   ADMIN_EMAIL: {settings.ADMIN_EMAIL}")
        print(f"   ADMIN_PASSWORD: {'ĐÃ ĐẶT' if settings.ADMIN_PASSWORD else 'CHƯA ĐẶT'}")
        print(f"   CORS_ORIGINS: {settings.CORS_ORIGINS[:80]}...")
        print(f"   JWT_EXPIRE_HOURS: {settings.JWT_EXPIRE_HOURS}")
        
        # So sánh với os.getenv
        print(f"\n7. So sánh settings vs os.getenv:")
        
        if settings.JWT_SECRET == env_vars['JWT_SECRET']:
            print(f"   ✓ JWT_SECRET khớp")
        else:
            print(f"   ✗ JWT_SECRET KHÔNG khớp!")
            print(f"     os.getenv: {env_vars['JWT_SECRET'][:20]}...")
            print(f"     settings:  {settings.JWT_SECRET[:20]}...")
        
        if settings.ADMIN_EMAIL == env_vars['ADMIN_EMAIL']:
            print(f"   ✓ ADMIN_EMAIL khớp")
        else:
            print(f"   ✗ ADMIN_EMAIL KHÔNG khớp!")
            print(f"     os.getenv: {env_vars['ADMIN_EMAIL']}")
            print(f"     settings:  {settings.ADMIN_EMAIL}")
        
        if settings.ADMIN_PASSWORD == env_vars['ADMIN_PASSWORD']:
            print(f"   ✓ ADMIN_PASSWORD khớp")
        else:
            print(f"   ✗ ADMIN_PASSWORD KHÔNG khớp!")
        
    except Exception as e:
        print(f"   ✗ LỖI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 70)
    if all_ok:
        print("✅ TẤT CẢ ĐỀU OK! File .env đã được load đúng cách")
    else:
        print("⚠️  MỘT SỐ BIẾN MÔI TRƯỜNG CHƯA ĐƯỢC ĐẶT")
        print("    → Kiểm tra lại file .env")
    print("=" * 70)

if __name__ == "__main__":
    main()

