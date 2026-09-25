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
                elif media_type == "camera":
                    ch_num = c.channel_number or 1
                    target_cam = settings.BASE_DIR / "camera" / f"{ch_num}.JPG"
                    if target_cam.exists():
                        c.rtsp_url = f"camera/{ch_num}.JPG"
                        updated_count += 1
                        continue
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


@router.post("/system/reset-to-camera-photos")
async def reset_to_camera_photos(_user=Depends(get_current_user)):
    """Khởi tạo sạch 30 camera từ 1 đến 30 tương ứng 30 ảnh trong thư mục camera/."""
    import json
    import shutil
    from database.db_session import SessionLocal
    from database.models import Classroom, ROIPolygon, AttendanceDetail

    db = SessionLocal()
    try:
        db.query(AttendanceDetail).delete()
        db.query(ROIPolygon).delete()
        db.query(Classroom).delete()
        db.commit()

        standard_counts = [
            42, 40, 41, 43, 39, 42, 40, 41, 40, 42,
            44, 43, 42, 40, 41, 42, 39, 41, 40, 43,
            45, 44, 42, 43, 41, 40, 42, 41, 40, 42
        ]

        latest_dir = settings.CAPTURES_DIR / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)
        default_green_zone = [[100, 200], [1820, 200], [1870, 1060], [50, 1060]]
        default_red_zone = []

        for i in range(1, 31):
            cls = Classroom(
                code=f"CAM_{i:02d}",
                name=f"Camera {i}",
                room_number=f"Phòng {100 + i}",
                standard_count=standard_counts[i - 1],
                rtsp_url=f"camera/{i}.JPG",
                relay_ip="192.168.10.200",
                is_active=True,
                channel_number=i
            )
            db.add(cls)
            db.flush()

            roi = ROIPolygon(
                classroom_id=cls.id,
                red_zone_json=json.dumps(default_red_zone),
                green_zone_json=json.dumps(default_green_zone),
                image_width=1920,
                image_height=1088
            )
            db.add(roi)

            src_img = settings.BASE_DIR / "camera" / f"{i}.JPG"
            dst_img = latest_dir / f"Lop_{cls.id}.jpg"
            if src_img.exists():
                shutil.copy2(src_img, dst_img)

        db.commit()
        return {"success": True, "message": "Đã thiết lập thành công 30 camera tương ứng 30 ảnh trong thư mục camera!"}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Lỗi: {str(e)}"}
    finally:
        db.close()

