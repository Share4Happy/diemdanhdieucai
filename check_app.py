"""
Kiểm tra app.py có import được không
"""
import sys

try:
    print("Đang import app.py...")
    from app import app
    print("✅ Import app.py thành công!")
    print("✅ FastAPI app object:", app)
    print("✅ App title:", app.title)
    
    # Kiểm tra routes
    print("\n📋 Danh sách routes:")
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"  - {route.path}")
    
    print("\n" + "="*50)
    print("✅ app.py KHÔNG CÓ LỖI SYNTAX")
    print("="*50)
    print("\nServer có thể chạy được. Hãy thử:")
    print("  python app.py")
    
except SyntaxError as e:
    print("❌ SYNTAX ERROR trong app.py:")
    print(f"   File: {e.filename}")
    print(f"   Line {e.lineno}: {e.text}")
    print(f"   Error: {e.msg}")
    sys.exit(1)
    
except ImportError as e:
    print("❌ IMPORT ERROR:")
    print(f"   {e}")
    print("\nKiểm tra:")
    print("  - Có thiếu dependencies không?")
    print("  - Có module nào không tồn tại không?")
    sys.exit(1)
    
except Exception as e:
    print("❌ LỖI KHÁC:")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
