"""
Backend App Package - THPT Điều Cải AI Camera Attendance System
Kiến trúc phân tầng chuẩn hóa: API, Core AI, Services, Database, Schemas, Config
"""
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _APP_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_APP_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

__version__ = "1.0.0"
