"""
Quick test để kiểm tra server có chạy được không
"""
import sys
print("Python version:", sys.version)
print("Python executable:", sys.executable)

try:
    import fastapi
    print("✅ FastAPI installed:", fastapi.__version__)
except ImportError as e:
    print("❌ FastAPI not installed:", e)
    sys.exit(1)

try:
    import uvicorn
    print("✅ Uvicorn installed:", uvicorn.__version__)
except ImportError as e:
    print("❌ Uvicorn not installed:", e)
    sys.exit(1)

try:
    from config.settings import settings
    print("✅ Config loaded successfully")
    print("   App Name:", settings.APP_NAME)
    print("   Host:", settings.HOST)
    print("   Port:", settings.PORT)
except Exception as e:
    print("❌ Config error:", e)
    sys.exit(1)

print("\n" + "="*50)
print("Tất cả dependencies OK! Server có thể chạy được.")
print("="*50)
print("\nĐể chạy server:")
print("  python app.py")
print("hoặc:")
print("  uvicorn app:app --reload")
