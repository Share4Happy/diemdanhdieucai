import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db, init_db
from database.models import Classroom, ROIPolygon, AttendanceDetail
from core.rtsp_client import rtsp_client
from backend.schemas.camera_schemas import CameraCreateRequest, CameraUpdateRequest, TestCameraRequest

router = APIRouter(prefix="/cameras", tags=["Cameras"])

@router.get("")
@router.get("/")
async def get_all_cameras(db: Session = Depends(get_db)):
    """Lấy danh sách chi tiết tất cả Camera/Lớp học kèm loại nguồn và trạng thái."""
    classrooms = db.query(Classroom).order_by(Classroom.id.asc()).all()
    results = []
    for c in classrooms:
        source_type = "UNKNOWN"
        url = (c.rtsp_url or "").strip()
        if url.isdigit():
            source_type = "WEBCAM"
        elif any(url.lower().endswith(ext) for ext in [".mp4", ".avi", ".mkv", ".jpg", ".png"]):
            source_type = "FILE"
        elif url.startswith("rtsp://"):
            source_type = "RTSP"
        elif url.startswith("http://") or url.startswith("https://"):
            source_type = "HTTP"

        has_roi = bool(c.roi and c.roi.red_zone)
        results.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "room_number": c.room_number,
            "standard_count": c.standard_count,
            "rtsp_url": c.rtsp_url,
            "relay_ip": c.relay_ip,
            "is_active": c.is_active,
            "source_type": source_type,
            "has_roi": has_roi
        })
    return {"cameras": results}

@router.post("")
@router.post("/")
async def create_camera(data: CameraCreateRequest, db: Session = Depends(get_db)):
    """Thêm mới một camera / lớp học vào hệ thống."""
    clean_code = data.code.strip().upper()
    existing = db.query(Classroom).filter(Classroom.code == clean_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Mã camera/lớp '{clean_code}' đã tồn tại!")

    cls = Classroom(
        code=clean_code,
        name=data.name.strip(),
        room_number=data.room_number.strip() if data.room_number else "",
        standard_count=data.standard_count,
        rtsp_url=data.rtsp_url.strip(),
        relay_ip=data.relay_ip.strip() if data.relay_ip else "",
        is_active=data.is_active
    )
    db.add(cls)
    db.flush()

    # Tạo vùng ROI mặc định cho camera mới (1920x1080)
    default_red_zone = [[200, 300], [1720, 300], [1850, 1050], [80, 1050]]
    default_green_zone = [[350, 80], [900, 80], [950, 280], [300, 280]]
    roi = ROIPolygon(
        classroom_id=cls.id,
        red_zone_json=json.dumps(default_red_zone),
        green_zone_json=json.dumps(default_green_zone),
        image_width=1920,
        image_height=1080
    )
    db.add(roi)
    db.commit()
    db.refresh(cls)

    logger.info(f"Đã thêm camera mới: {cls.name} (Mã: {cls.code}, Nguồn: {cls.rtsp_url})")
    return {"success": True, "message": f"Đã thêm thành công camera {cls.name}", "camera_id": cls.id}

@router.put("/{classroom_id}")
async def update_camera(classroom_id: int, data: CameraUpdateRequest, db: Session = Depends(get_db)):
    """Cập nhật thông tin camera / lớp học."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera/lớp học")

    if data.name is not None:
        cls.name = data.name.strip()
    if data.room_number is not None:
        cls.room_number = data.room_number.strip()
    if data.standard_count is not None:
        cls.standard_count = data.standard_count
    url_changed = False
    if data.rtsp_url is not None:
        new_url = data.rtsp_url.strip()
        if new_url != cls.rtsp_url:
            cls.rtsp_url = new_url
            url_changed = True
    if data.relay_ip is not None:
        cls.relay_ip = data.relay_ip.strip()
    if data.is_active is not None:
        cls.is_active = data.is_active

    db.commit()
    logger.info(f"Đã cập nhật camera ID {classroom_id} ({cls.name})")

    # Nếu đổi nguồn camera, chụp ngay ảnh mới nhất cho lớp học
    if url_changed:
        latest_dir = settings.CAPTURES_DIR / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)
        try:
            rtsp_client.capture_single_camera(cls.id, cls.name, cls.rtsp_url, latest_dir)
        except Exception as e:
            logger.debug(f"Lỗi chụp snapshot mới khi đổi nguồn camera: {e}")

    return {"success": True, "message": f"Cập nhật camera {cls.name} thành công"}

@router.delete("/{classroom_id}")
async def delete_camera(classroom_id: int, db: Session = Depends(get_db)):
    """Xóa camera và các dữ liệu liên quan khỏi hệ thống."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera/lớp học")

    # Xóa ROI
    db.query(ROIPolygon).filter(ROIPolygon.classroom_id == classroom_id).delete()
    # Xóa các chi tiết điểm danh liên quan
    db.query(AttendanceDetail).filter(AttendanceDetail.classroom_id == classroom_id).delete()
    cname = cls.name
    db.delete(cls)
    db.commit()
    logger.info(f"Đã xóa camera {cname} (ID {classroom_id})")
    return {"success": True, "message": f"Đã xóa camera {cname} thành công"}

@router.get("/available-webcams")
async def get_available_webcams_endpoint(refresh: bool = False):
    """Quét và trả về danh sách tất cả Webcam vật lý và ảo đang kết nối trên máy tính kèm preview thumbnail."""
    webcams = rtsp_client.get_available_webcams(refresh=refresh)
    return {
        "success": True,
        "count": len(webcams),
        "webcams": webcams
    }

@router.post("/test-connection")
async def test_camera_connection(req: TestCameraRequest):
    """Kiểm tra trực tiếp kết nối tới nguồn camera (RTSP, Webcam, File) và trả về snapshot preview."""
    res = rtsp_client.test_camera_stream(req.source_url)
    return res

@router.post("/reset-defaults")
async def reset_default_cameras(db: Session = Depends(get_db)):
    """Khôi phục lại danh sách 30 lớp học chuẩn của trường THPT Điều Cải."""
    db.query(ROIPolygon).delete()
    db.query(AttendanceDetail).delete()
    db.query(Classroom).delete()
    db.commit()
    init_db()
    return {"success": True, "message": "Đã khôi phục thành công danh sách 30 lớp học chuẩn của trường Điều Cải!"}
