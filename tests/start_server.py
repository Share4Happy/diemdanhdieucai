"""
Khởi động server không dùng reload mode (ổn định hơn)
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    import uvicorn
    from config.settings import settings
    
    print("=" * 70)
    print("  HỆ THỐNG ĐIỂM DANH AI - THPT ĐIỀU CẢI")
    print("=" * 70)
    print(f"  Server: http://{settings.HOST}:{settings.PORT}")
    print(f"  Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 70)
    print("\n⏳ Đang khởi động server...\n")
    
    # Chạy không dùng reload (ổn định hơn khi có nhiều dependencies)
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,  # Tắt reload để tránh treo
        log_level="info"
    )
