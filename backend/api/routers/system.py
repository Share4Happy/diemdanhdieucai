from fastapi import APIRouter, Depends
from config.settings import settings
from backend.api.deps import get_current_user

router = APIRouter(tags=["System"])

@router.get("/database/info")
async def get_database_info(_user=Depends(get_current_user)):
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
        "architecture": "Decoupled Backend (FastAPI REST API)",
        "ai_model": {
            "family": getattr(settings, "YOLO_FAMILY", "YOLO26"),
            "variant": getattr(settings, "YOLO_VARIANT", "26m"),
            "model_name": settings.YOLO_MODEL_NAME,
            "imgsz": settings.YOLO_IMGSZ,
            "confidence_threshold": settings.AI_CONFIDENCE_THRESHOLD
        }
    }

@router.get("/ai/info")
@router.get("/system/ai/info")
async def get_ai_info():
    """Lấy thông tin chi tiết mô hình AI (YOLO26m), thiết bị tính toán (GPU/CPU) và tham số nhận diện."""
    from core.detector import detector
    return {
        "success": True,
        "data": detector.get_model_info()
    }

@router.get("/system/classrooms-media")
async def get_classrooms_media(_user=Depends(get_current_user)):
    """Lấy danh mục dữ liệu 5 ảnh và 1 video 15s của 30 lớp học kèm thông tin sĩ số."""
    import json
    json_path = settings.CLASSROOMS_MEDIA_DIR / "danh_sach_si_so_toan_truong.json"
    if not json_path.exists():
        return {"success": False, "message": "Chưa khởi tạo bộ dữ liệu classrooms_media", "classes": []}

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"success": True, "data": data}

@router.post("/system/bind-sample-media")
async def bind_sample_media(media_type: str = "video", _user=Depends(get_current_user)):
    """
    Tùy chọn tự động gán nguồn rtsp_url của 30 lớp trong CSDL trỏ tới file video 15s hoặc ảnh mẫu
    để người dùng có thể chạy thử nghiệm tính năng điểm danh toàn diện ngay mà không cần camera vật lý.
    media_type: 'video' (mặc định video 15s) hoặc 'image' (ảnh 1)
    """
    from database.db_session import SessionLocal
    from database.models import Classroom
    db = SessionLocal()
    try:
        classrooms = db.query(Classroom).all()
        updated_count = 0
        for c in classrooms:
            clean_code = c.code.replace("LOP_", "")
            class_folder = settings.CLASSROOMS_MEDIA_DIR / f"Lop_{clean_code}"
            if class_folder.exists():
                if media_type == "image":
                    target_file = class_folder / "image_1.jpg"
                else:
                    target_file = class_folder / "video_15s.mp4"
                
                if target_file.exists():
                    rel_path = f"dataset/classrooms_media/Lop_{clean_code}/{target_file.name}"
                    c.rtsp_url = rel_path
                    updated_count += 1
        db.commit()
        return {
            "success": True, 
            "message": f"Đã liên kết thành công nguồn dữ liệu mẫu {media_type} cho {updated_count} lớp học!",
            "updated_count": updated_count
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Lỗi khi liên kết nguồn: {str(e)}"}
    finally:
        db.close()

