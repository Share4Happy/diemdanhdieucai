import sys
import traceback
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=== Testing backend.main import ===")

try:
    # Import từng phần
    print("1. Import FastAPI...")
    from fastapi import FastAPI
    print("   ✓ OK")
    
    print("2. Import routers...")
    from backend.api.routers import attendance_router, cameras_router
    print("   ✓ OK")
    
    print("3. Import auth router...")
    from backend.api.routers.auth import router as auth_router
    print("   ✓ OK")
    
    print("4. Import full backend.main...")
    from backend import main
    print("   ✓ OK")
    
    print("5. Get app object...")
    app = main.app
    print("   ✓ OK")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    traceback.print_exc()

print("\n=== Complete ===")
