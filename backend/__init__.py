"""
Backend Package - Hệ thống điểm danh học sinh tự động bằng AI Camera THPT Điều Cải
"""
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
_APP_DIR = _BACKEND_DIR / "app"
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR), str(_APP_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Cung cấp module aliases để tương thích ngược 100% với mã cũ (backend.api, backend.core...)
try:
    from backend.app import api, core, schemas, services, database, config
    import backend.app.api.deps as _api_deps
    sys.modules['backend.api'] = api
    sys.modules['backend.api.deps'] = _api_deps
    sys.modules['backend.core'] = core
    sys.modules['backend.schemas'] = schemas
    sys.modules['backend.services'] = services
    sys.modules['backend.database'] = database
    sys.modules['backend.config'] = config
except Exception:
    pass
