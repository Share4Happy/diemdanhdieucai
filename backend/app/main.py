import os
import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

# Đảm bảo root directory và backend/app có trong sys.path
CURRENT_DIR = Path(__file__).resolve().parent          # backend/app
BACKEND_DIR = CURRENT_DIR.parent                      # backend
PROJECT_ROOT = CURRENT_DIR.parent.parent              # diemdanhdieucai
for p in [str(PROJECT_ROOT), str(BACKEND_DIR), str(CURRENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config.settings import settings
from config.logging_config import logger
from database.db_session import init_db
from services.scheduler import attendance_scheduler

from backend.app.api.routers import (
    attendance_router,
    cameras_router,
    roi_router,
    reports_router,
    system_router,
    auth_router,
    backup_router,
    predict_router,
    # stream_mock_router,
    # stream_mock_background_loop,
    classrooms_router,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== ĐANG KHỞI ĐỘNG HỆ THỐNG ĐIỂM DANH AI ĐIỀU CẢI (BACKEND REST API) ===")
    init_db()
    attendance_scheduler.start()
    # stream_mock_task = asyncio.create_task(stream_mock_background_loop())
    yield
    # stream_mock_task.cancel()
    attendance_scheduler.shutdown()
    logger.info("=== HỆ THỐNG BACKEND ĐÃ DỪNG AN TOÀN ===")

app = FastAPI(
    title=f"{settings.APP_NAME} - REST API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    # Chỉ mở /docs, /redoc khi DEBUG=True (môi trường development).
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Cấu hình CORS cho cookie đăng nhập (tự động tích hợp APP_PUBLIC_URL từ biến môi trường)
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if settings.APP_PUBLIC_URL:
    pub_url = settings.APP_PUBLIC_URL.strip().rstrip("/")
    if pub_url and pub_url not in cors_origins:
        cors_origins.append(pub_url)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Đăng ký các APIRouters chuẩn hóa
app.include_router(auth_router, prefix="/api")
app.include_router(attendance_router, prefix="/api")
app.include_router(cameras_router, prefix="/api")
app.include_router(roi_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(backup_router, prefix="/api")
app.include_router(predict_router, prefix="/api")
app.include_router(predict_router)
# app.include_router(stream_mock_router, prefix="/api")
app.include_router(classrooms_router, prefix="/api")


def is_authenticated_request(request: Request) -> bool:
    """Kiểm tra token cookie hợp lệ nhanh chóng ngay tại Server."""
    from services.auth_service import (
        AUTH_COOKIE_NAME,
        decode_access_token_payload,
        is_jti_revoked,
    )
    token = request.cookies.get(AUTH_COOKIE_NAME) or ""
    if not token:
        return False
    payload = decode_access_token_payload(token)
    if payload is None or is_jti_revoked(payload.get("jti")):
        return False
    return True


class CORSStaticFiles(StaticFiles):
    """Phục vụ file tĩnh kèm tiêu đề CORS mở cho Frontend, chặn truy cập trái phép trực tiếp vào file HTML."""
    async def get_response(self, path: str, scope):
        clean_path = path.lower()
        if clean_path.endswith(".html"):
            public_pages = ("login.html", "forgot-password.html", "reset-password.html")
            if not any(clean_path.endswith(p) for p in public_pages):
                req = Request(scope)
                if not is_authenticated_request(req):
                    return RedirectResponse(
                        url=f"/login?redirect={path}",
                        status_code=status.HTTP_302_FOUND,
                        headers={"Cache-Control": "no-store"}
                    )
        response = await super().get_response(path, scope)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        if any(path.endswith(ext) for ext in [".js", ".html", ".css"]):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

class AuthStaticFiles(StaticFiles):
    """
    Mount yêu cầu đăng nhập (cookie access_token) — chống lộ dữ liệu nhạy cảm
    trong storage/ (ảnh học sinh, báo cáo Excel, backup CSDL, file cấu hình secret).
    """
    async def get_response(self, path: str, scope):
        from services.auth_service import (
            AUTH_COOKIE_NAME,
            decode_access_token_payload,
            is_jti_revoked,
        )

        request = Request(scope)
        token = request.cookies.get(AUTH_COOKIE_NAME) or ""
        payload = decode_access_token_payload(token) if token else None
        if payload is None or is_jti_revoked(payload.get("jti")):
            # Trả 401 JSON để trình duyệt không nhầm thành redirect (đặc biệt với <img>).
            return Response(
                content='{"detail":"Chưa đăng nhập"}',
                status_code=401,
                media_type="application/json",
                headers={"Cache-Control": "no-store"},
            )
        response = await super().get_response(path, scope)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Cache-Control"] = "private, no-store"
        return response


# Mount dữ liệu tĩnh (Lưu trữ ảnh và frame mẫu) — BẮT BUỘC đăng nhập
app.mount("/storage", AuthStaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")
dataset_path = getattr(settings, "DATASET_DIR", getattr(settings, "BASE_DIR", Path(".")) / "data" / "dataset")
if dataset_path and dataset_path.exists():
    app.mount("/dataset", AuthStaticFiles(directory=str(dataset_path)), name="dataset")
camera_dir = getattr(settings, "BASE_DIR", Path(".")) / "camera"
if camera_dir.exists():
    app.mount("/camera", AuthStaticFiles(directory=str(camera_dir)), name="camera")

# Hỗ trợ phục vụ Frontend tĩnh trực tiếp (Định tuyến bảo vệ Server-side Guard chống FOUC / lộ trang chủ)
frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    def _guard_page(request: Request, filename: str):
        if not is_authenticated_request(request):
            return RedirectResponse(url=f"/login?redirect={filename}", status_code=status.HTTP_302_FOUND)
        return FileResponse(frontend_dir / filename)

    @app.get("/", include_in_schema=False)
    @app.get("/index.html", include_in_schema=False)
    async def get_root_page(request: Request):
        if is_authenticated_request(request):
            return FileResponse(frontend_dir / "index.html")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    @app.get("/login", include_in_schema=False)
    @app.get("/login.html", include_in_schema=False)
    async def get_login_page(request: Request):
        if is_authenticated_request(request):
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        return FileResponse(frontend_dir / "login.html")

    @app.get("/forgot-password", include_in_schema=False)
    @app.get("/forgot-password.html", include_in_schema=False)
    async def get_forgot_password_page(request: Request):
        if is_authenticated_request(request):
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        return FileResponse(frontend_dir / "forgot-password.html")

    @app.get("/reset-password", include_in_schema=False)
    @app.get("/reset-password.html", include_in_schema=False)
    async def get_reset_password_page():
        return FileResponse(frontend_dir / "reset-password.html")

    @app.get("/settings", include_in_schema=False)
    @app.get("/settings.html", include_in_schema=False)
    async def get_settings_page(request: Request):
        return _guard_page(request, "settings.html")

    @app.get("/users", include_in_schema=False)
    @app.get("/users.html", include_in_schema=False)
    async def get_users_page(request: Request):
        return RedirectResponse(url="/settings.html", status_code=status.HTTP_301_MOVED_PERMANENTLY)

    @app.get("/cameras", include_in_schema=False)
    @app.get("/cameras.html", include_in_schema=False)
    async def get_cameras_page(request: Request):
        return _guard_page(request, "cameras.html")

    @app.get("/classrooms", include_in_schema=False)
    @app.get("/classrooms.html", include_in_schema=False)
    async def get_classrooms_page(request: Request):
        return _guard_page(request, "classrooms.html")

    @app.get("/roi-config", include_in_schema=False)
    @app.get("/roi-config.html", include_in_schema=False)
    async def get_roi_page(request: Request):
        return RedirectResponse(url="/classrooms", status_code=status.HTTP_302_FOUND)

    @app.get("/reports", include_in_schema=False)
    @app.get("/reports.html", include_in_schema=False)
    async def get_reports_page(request: Request):
        return _guard_page(request, "reports.html")

    @app.get("/notifications", include_in_schema=False)
    @app.get("/notifications.html", include_in_schema=False)
    async def get_notifications_page(request: Request):
        return _guard_page(request, "notifications.html")

    # [ĐÃ GOM VÀO mock_and_experiments]
    # @app.get("/stream-config", include_in_schema=False)
    # @app.get("/stream-config.html", include_in_schema=False)
    # async def get_stream_config_page(request: Request):
    #     return _guard_page(request, "stream-config.html")

    # @app.get("/ai-test", include_in_schema=False)
    # @app.get("/ai-test.html", include_in_schema=False)
    # async def get_ai_test_page(request: Request):
    #     return _guard_page(request, "ai-test.html")

    # html=False để không tự động phục vụ index.html nếu không qua guard
    app.mount("/", CORSStaticFiles(directory=str(frontend_dir), html=False), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
