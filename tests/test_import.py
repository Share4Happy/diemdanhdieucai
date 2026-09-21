import sys
import traceback

print("=== Testing imports ===")

try:
    print("1. Import config.settings...")
    from config.settings import settings
    print(f"   ✓ Settings OK - Port: {settings.PORT}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()

try:
    print("2. Import database models...")
    from database.models import User, PasswordResetToken
    print(f"   ✓ Models OK")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()

try:
    print("3. Import services.auth_service...")
    from services.auth_service import hash_password
    print(f"   ✓ Auth service OK")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()

try:
    print("4. Import database.db_session...")
    from database.db_session import init_db
    print(f"   ✓ DB session OK")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()

try:
    print("5. Import backend.main...")
    from backend.main import app
    print(f"   ✓ Backend main OK")
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()

print("\n=== All imports complete ===")
