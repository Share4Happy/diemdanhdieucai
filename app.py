"""
===================================================================
HỆ THỐNG ĐIỂM DANH HỌC SINH TỰ ĐỘNG BẰNG AI CAMERA - THPT ĐIỀU CẢI
===================================================================
Tệp tương thích ngược (Backward Compatibility Entry Point).
Toàn bộ mã nguồn máy chủ đã được tái cấu trúc độc lập sang `backend/main.py`.
"""
import sys
from pathlib import Path

# Đảm bảo đường dẫn dự án
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app

if __name__ == "__main__":
    import uvicorn
    from config.settings import settings
    reload_dirs = [str(PROJECT_ROOT / "backend"), str(PROJECT_ROOT / "core"), str(PROJECT_ROOT / "config")]
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        reload_dirs=reload_dirs,
    )
