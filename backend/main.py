import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Đảm bảo root directory có trong sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config.settings import settings
from config.logging_config import logger
from database.db_session import init_db
from services.scheduler import attendance_scheduler

from backend.api.routers import (
    attendance_router,
    cameras_router,
    roi_router,
    reports_router,
    system_router,
    auth_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== ĐANG KHỞI ĐỘNG HỆ THỐNG ĐIỂM DANH AI ĐIỀU CẢI (BACKEND REST API) ===")
    init_db()
    attendance_scheduler.start()
    yield
    attendance_scheduler.shutdown()
    logger.info("=== HỆ THỐNG BACKEND ĐÃ DỪNG AN TOÀN ===")

app = FastAPI(
    title=f"{settings.APP_NAME} - REST API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Cấu hình CORS cho cookie đăng nhập (không dùng allow_origins="*")
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các APIRouters chuẩn hóa
app.include_router(auth_router, prefix="/api")
app.include_router(attendance_router, prefix="/api")
app.include_router(cameras_router, prefix="/api")
app.include_router(roi_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(system_router, prefix="/api")

class CORSStaticFiles(StaticFiles):
    """Phục vụ file tĩnh kèm tiêu đề CORS mở cho phép Frontend port 3000 tải ảnh an toàn."""
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

# Mount dữ liệu tĩnh (Lưu trữ ảnh và frame mẫu)
app.mount("/storage", CORSStaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")
app.mount("/dataset", CORSStaticFiles(directory=str(settings.BASE_DIR / "dataset")), name="dataset")

# Hỗ trợ phục vụ Frontend tĩnh trực tiếp (cho kịch bản 1-click hoặc sản xuất)
frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    from fastapi.responses import FileResponse
    
    @app.get("/login", include_in_schema=False)
    async def get_login_page():
        return FileResponse(frontend_dir / "login.html")

    @app.get("/forgot-password", include_in_schema=False)
    async def get_forgot_password_page():
        return FileResponse(frontend_dir / "forgot-password.html")

    @app.get("/reset-password", include_in_schema=False)
    async def get_reset_password_page():
        return FileResponse(frontend_dir / "reset-password.html")

    @app.get("/users", include_in_schema=False)
    async def get_users_page():
        return FileResponse(frontend_dir / "users.html")

    @app.get("/cameras", include_in_schema=False)
    async def get_cameras_page():
        return FileResponse(frontend_dir / "cameras.html")

    @app.get("/roi-config", include_in_schema=False)
    async def get_roi_page():
        return FileResponse(frontend_dir / "roi-config.html")

    @app.get("/reports", include_in_schema=False)
    async def get_reports_page():
        return FileResponse(frontend_dir / "reports.html")

    @app.get("/notifications", include_in_schema=False)
    async def get_notifications_page():
        return FileResponse(frontend_dir / "notifications.html")

    app.mount("/", CORSStaticFiles(directory=str(frontend_dir), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
