from fastapi import APIRouter
from config.settings import settings

router = APIRouter(tags=["System"])

@router.get("/database/info")
async def get_database_info():
    """Lấy thông tin cấu hình Cơ Sở Dữ Liệu hiện tại (PostgreSQL / MySQL / SQLite)."""
    db_type = "SQLite"
    if "postgres" in settings.DATABASE_URL:
        db_type = "PostgreSQL"
    elif "mysql" in settings.DATABASE_URL:
        db_type = "MySQL"

    return {
        "database_url": settings.DATABASE_URL,
        "db_type": db_type,
        "status": "Kết nối thành công (Active)",
        "supported_drivers": ["sqlite3", "psycopg2 (PostgreSQL)", "pymysql (MySQL)"]
    }

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "architecture": "Decoupled Backend (FastAPI REST API)"
    }
