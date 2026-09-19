import os
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db, init_db, SessionLocal
from database.models import Classroom, ROIPolygon, AttendanceSession, AttendanceDetail
from services.scheduler import attendance_scheduler
from core.attendance_engine import attendance_engine
from core.rtsp_client import rtsp_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động CSDL & Lập lịch
    logger.info("=== ĐANG KHỞI ĐỘNG HỆ THỐNG ĐIỂM DANH AI ĐIỀU CẢI ===")
    init_db()
    attendance_scheduler.start()
    yield
    # Dừng hệ thống an toàn
    attendance_scheduler.shutdown()
    logger.info("=== HỆ THỐNG ĐÃ DỪNG AN TOÀN ===")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Cấu hình thư mục tĩnh & templates
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "web" / "templates"))

app.mount("/static", StaticFiles(directory=str(settings.BASE_DIR / "web" / "static")), name="static")
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")
app.mount("/dataset", StaticFiles(directory=str(settings.BASE_DIR / "dataset")), name="dataset")

# Models cho Request body
class ROISaveRequest(BaseModel):
    red_zone: List[List[int]]
    green_zone: Optional[List[List[int]]] = []
    image_width: int = 1920
    image_height: int = 1080

# --- Web UI Routes ---

@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Trang chủ Dashboard theo dõi điểm danh 30 lớp học."""
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"app_name": settings.APP_NAME}
    )

@app.get("/roi-config", response_class=HTMLResponse)
async def roi_config_page(request: Request):
    """Trang công cụ thiết lập không gian ROI (Red/Green Zone) cho từng lớp."""
    return templates.TemplateResponse(
        request=request,
        name="roi_config.html",
        context={"app_name": settings.APP_NAME}
    )

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Trang Quản Lý Dữ Liệu & Báo Cáo Điểm Danh (Giai đoạn 4)."""
    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={"app_name": settings.APP_NAME}
    )

@app.get("/cameras", response_class=HTMLResponse)
@app.get("/cameras/", response_class=HTMLResponse)
@app.get("/camera", response_class=HTMLResponse)
@app.get("/camera/", response_class=HTMLResponse)
async def cameras_page(request: Request):
    """Trang Quản Lý Camera & Lớp Học (Thêm, Sửa, Xóa, Test kết nối)."""
    return templates.TemplateResponse(
        request=request,
        name="cameras.html",
        context={"app_name": settings.APP_NAME}
    )


# --- REST API Endpoints ---

@app.get("/api/classrooms")
async def list_classrooms(db: Session = Depends(get_db)):
    """Lấy danh sách 30 lớp học và trạng thái cấu hình."""
    classrooms = db.query(Classroom).order_by(Classroom.id).all()
    results = []
    for c in classrooms:
        has_roi = bool(c.roi and c.roi.red_zone)
        results.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "room_number": c.room_number,
            "standard_count": c.standard_count,
            "rtsp_url": c.rtsp_url,
            "has_roi": has_roi
        })
    return results

@app.get("/api/roi/{classroom_id}")
async def get_classroom_roi(classroom_id: int, refresh: bool = False, db: Session = Depends(get_db)):
    """Lấy tọa độ Red Zone & Green Zone của lớp học và tự động chụp ảnh thực tế từ Camera."""
    import time
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    roi = cls.roi
    red_zone = roi.red_zone if roi else []
    green_zone = roi.green_zone if roi else []

    # Kiểm tra hoặc chụp ảnh mới nhất từ Camera thực tế
    latest_dir = settings.CAPTURES_DIR / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    live_path = latest_dir / f"Lop_{classroom_id}.jpg"

    # Kiểm tra xem ảnh hiện tại có quá cũ (> 2 phút) hoặc được yêu cầu làm mới hay không
    is_stale = False
    if live_path.exists():
        try:
            file_age = time.time() - live_path.stat().st_mtime
            if file_age > 120:  # Quá 2 phút coi như cũ
                is_stale = True
        except Exception:
            is_stale = True

    if refresh or not live_path.exists() or is_stale:
        rtsp_client.capture_single_camera(
            cls.id,
            cls.name,
            cls.rtsp_url,
            latest_dir
        )

    if live_path.exists():
        snapshot_url = f"/storage/captures/latest/Lop_{classroom_id}.jpg?t={int(time.time() * 1000)}"
    else:
        extracted_imgs = list((settings.BASE_DIR / "dataset" / "extracted_frames").glob("*.jpg"))
        if extracted_imgs:
            sample_file = extracted_imgs[(classroom_id - 1) % len(extracted_imgs)]
            snapshot_url = f"/dataset/extracted_frames/{sample_file.name}"
        else:
            snapshot_url = f"/dataset/samples/classroom_sample_1.jpg"

    return {
        "classroom_id": cls.id,
        "name": cls.name,
        "standard_count": cls.standard_count,
        "red_zone": red_zone,
        "green_zone": green_zone,
        "snapshot_url": snapshot_url
    }

@app.post("/api/roi/{classroom_id}/refresh-snapshot")
async def refresh_classroom_snapshot(classroom_id: int, db: Session = Depends(get_db)):
    """Chụp ngay khung hình trực tiếp mới nhất từ Camera đang kết nối và trả về URL ảnh cập nhật."""
    import time
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    latest_dir = settings.CAPTURES_DIR / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)

    cid, ok, filepath, frame = rtsp_client.capture_single_camera(
        cls.id,
        cls.name,
        cls.rtsp_url,
        latest_dir
    )

    snapshot_url = f"/storage/captures/latest/Lop_{classroom_id}.jpg?t={int(time.time() * 1000)}"
    h, w = (frame.shape[:2]) if (ok and frame is not None) else (1080, 1920)

    logger.info(f"Đã chụp khung hình mới cho lớp {cls.name} từ nguồn '{cls.rtsp_url}': {ok} ({w}x{h})")
    return {
        "success": ok,
        "message": f"Đã chụp khung hình mới từ camera {cls.name} ({w}x{h})" if ok else f"Đã kết nối nhưng dùng ảnh đối chứng cho camera {cls.name}",
        "snapshot_url": snapshot_url,
        "width": w,
        "height": h
    }

@app.post("/api/roi/{classroom_id}")
async def save_classroom_roi(classroom_id: int, data: ROISaveRequest, db: Session = Depends(get_db)):
    """Lưu tọa độ Red Zone (bàn học) và Green Zone (bục giảng) cho lớp học."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    roi = cls.roi
    if not roi:
        roi = ROIPolygon(classroom_id=classroom_id)
        db.add(roi)

    roi.red_zone = data.red_zone
    roi.green_zone = data.green_zone
    roi.image_width = data.image_width
    roi.image_height = data.image_height

    db.commit()
    logger.info(f"Đã lưu tọa độ ROI cho lớp {cls.name}: Red ({len(data.red_zone)} pts), Green ({len(data.green_zone)} pts)")
    return {"success": True, "message": f"Đã lưu thành công ROI cho {cls.name}"}

@app.post("/api/attendance/trigger")
async def trigger_attendance_scan():
    """Kích hoạt quét điểm danh đồng loạt 30 lớp ngay lập tức."""
    result = attendance_engine.run_daily_attendance(trigger_led=True)
    return result

@app.get("/api/attendance/latest")
async def get_latest_attendance(db: Session = Depends(get_db)):
    """Lấy kết quả của phiên điểm danh gần nhất."""
    session = db.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()
    if not session:
        return {"session": None, "details": []}

    details = (
        db.query(AttendanceDetail)
        .filter(AttendanceDetail.session_id == session.id)
        .order_by(AttendanceDetail.classroom_id)
        .all()
    )

    details_data = []
    for d in details:
        cname = d.classroom.name if d.classroom else f"Lớp {d.classroom_id}"
        room = d.classroom.room_number if d.classroom else ""

        # Chuẩn hóa link ảnh cho web
        raw_url = ""
        if d.raw_image_path:
            p = Path(d.raw_image_path)
            raw_url = f"/storage/captures/{p.parent.name}/{p.name}"

        annotated_url = ""
        if d.annotated_image_path:
            p = Path(d.annotated_image_path)
            annotated_url = f"/storage/annotated/{p.parent.name}/{p.name}"

        details_data.append({
            "classroom_id": d.classroom_id,
            "class_name": cname,
            "room_number": room,
            "standard_count": d.standard_count,
            "present_count": d.present_count,
            "absent_count": d.absent_count,
            "raw_image_path": raw_url,
            "annotated_image_path": annotated_url,
            "confidence_avg": d.confidence_avg,
            "notes": d.notes
        })

    return {
        "session": {
            "id": session.id,
            "session_code": session.session_code,
            "scan_date": session.scan_date,
            "scan_time": session.scan_time,
            "total_classes": session.total_classes,
            "total_standard": session.total_standard,
            "total_present": session.total_present,
            "total_absent": session.total_absent,
            "status": session.status,
            "excel_report_path": session.excel_report_path
        },
        "details": details_data
    }

@app.get("/api/attendance/download-excel")
async def download_excel(db: Session = Depends(get_db)):
    """Tải file báo cáo Excel của phiên điểm danh gần nhất."""
    session = db.query(AttendanceSession).filter(AttendanceSession.excel_report_path != "").order_by(AttendanceSession.id.desc()).first()
    if not session or not session.excel_report_path or not os.path.exists(session.excel_report_path):
        raise HTTPException(status_code=404, detail="Chưa có file báo cáo Excel nào được xuất.")

    file_path = session.excel_report_path
    filename = Path(file_path).name
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- Các API chuyên biệt cho Giai Đoạn 4 (Quản Lý Dữ Liệu & Báo Cáo) ---

@app.get("/api/reports/list")
async def list_reports():
    """Lấy danh sách tất cả các file Excel đã xuất trong hệ thống."""
    from services.excel_exporter import excel_exporter
    reports = excel_exporter.list_all_reports()
    return {"reports": reports}

@app.post("/api/reports/export-now")
async def export_excel_now(db: Session = Depends(get_db)):
    """Xuất file Excel tổng hợp 30 lớp học ngay lập tức bằng pandas & openpyxl."""
    from services.excel_exporter import excel_exporter
    session = db.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()
    if not session:
        # Nếu chưa có phiên nào, tự động tạo một phiên điểm danh mẫu từ CSDL
        result = attendance_engine.run_daily_attendance(trigger_led=False)
        session_id = result.get("session_id")
    else:
        session_id = session.id

    path = excel_exporter.generate_daily_report(session_id)
    if not path or not os.path.exists(str(path)):
        raise HTTPException(status_code=500, detail="Không thể tạo file Excel báo cáo.")

    rel_path = path.relative_to(settings.REPORTS_DIR)
    download_url = f"/storage/reports/{str(rel_path).replace('\\', '/')}"
    return {
        "success": True,
        "filename": path.name,
        "download_url": download_url
    }

@app.get("/api/attendance/history")
async def get_attendance_history(limit: int = 150, db: Session = Depends(get_db)):
    """Lấy toàn bộ lịch sử điểm danh từ CSDL (PostgreSQL/MySQL/SQLite) kèm đường dẫn ảnh đối chứng."""
    details = (
        db.query(AttendanceDetail)
        .join(AttendanceSession)
        .join(Classroom)
        .order_by(AttendanceSession.id.desc(), Classroom.id.asc())
        .limit(limit)
        .all()
    )

    records = []
    for d in details:
        s = d.session
        c = d.classroom

        raw_url = ""
        if d.raw_image_path and os.path.exists(d.raw_image_path):
            p = Path(d.raw_image_path)
            raw_url = f"/storage/captures/{p.parent.name}/{p.name}"

        annotated_url = ""
        if d.annotated_image_path and os.path.exists(d.annotated_image_path):
            p = Path(d.annotated_image_path)
            annotated_url = f"/storage/annotated/{p.parent.name}/{p.name}"

        records.append({
            "id": d.id,
            "session_code": s.session_code if s else "",
            "scan_date": s.scan_date if s else "",
            "scan_time": s.scan_time if s else "",
            "class_name": c.name if c else f"Lớp {d.classroom_id}",
            "room_number": c.room_number if c else "",
            "standard_count": d.standard_count,
            "present_count": d.present_count,
            "absent_count": d.absent_count,
            "raw_image_path": raw_url,
            "annotated_image_path": annotated_url,
            "confidence_avg": d.confidence_avg,
            "notes": d.notes
        })

    return {"records": records}

class SendEmailRequest(BaseModel):
    email: Optional[str] = None

@app.post("/api/reports/send-email")
async def send_report_email(req: SendEmailRequest):
    """Gửi email báo cáo điểm danh trực tiếp tới Hiệu trưởng."""
    from services.notification import notification_service
    res = notification_service.send_test_email(req.email)
    return res

@app.get("/api/reports/distribution-status")
async def get_distribution_status():
    """Lấy thông tin trạng thái phân phối báo cáo nội bộ và email."""
    from services.notification import notification_service
    return notification_service.get_status()

@app.get("/api/database/info")
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

# --- Models & API Quản Lý Camera & Nguồn Test ---

class CameraCreateRequest(BaseModel):
    code: str
    name: str
    room_number: Optional[str] = ""
    standard_count: int = 40
    rtsp_url: str
    relay_ip: Optional[str] = ""
    is_active: bool = True

class CameraUpdateRequest(BaseModel):
    name: Optional[str] = None
    room_number: Optional[str] = None
    standard_count: Optional[int] = None
    rtsp_url: Optional[str] = None
    relay_ip: Optional[str] = None
    is_active: Optional[bool] = None

class TestCameraRequest(BaseModel):
    source_url: str

class ZaloTestRequest(BaseModel):
    target_type: Optional[str] = "WEBHOOK"
    webhook_url: Optional[str] = None
    access_token: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[int] = None

class ZaloConfigSaveRequest(BaseModel):
    enabled: bool
    notification_type: str
    webhook_url: Optional[str] = ""
    access_token: Optional[str] = ""
    recipient_user_id: Optional[str] = ""

@app.get("/api/cameras")
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

@app.post("/api/cameras")
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

@app.put("/api/cameras/{classroom_id}")
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

@app.delete("/api/cameras/{classroom_id}")
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

@app.get("/api/cameras/available-webcams")
async def get_available_webcams_endpoint(refresh: bool = False):
    """Quét và trả về danh sách tất cả Webcam vật lý và ảo đang kết nối trên máy tính kèm preview thumbnail."""
    webcams = rtsp_client.get_available_webcams(refresh=refresh)
    return {
        "success": True,
        "count": len(webcams),
        "webcams": webcams
    }

@app.post("/api/cameras/test-connection")
async def test_camera_connection(req: TestCameraRequest):
    """Kiểm tra trực tiếp kết nối tới nguồn camera (RTSP, Webcam, File) và trả về snapshot preview."""
    res = rtsp_client.test_camera_stream(req.source_url)
    return res

@app.post("/api/cameras/reset-defaults")
async def reset_default_cameras(db: Session = Depends(get_db)):
    """Khôi phục lại danh sách 30 lớp học chuẩn của trường THPT Điều Cải."""
    from database.db_session import init_db
    # Xóa các lớp hiện tại
    db.query(ROIPolygon).delete()
    db.query(AttendanceDetail).delete()
    db.query(Classroom).delete()
    db.commit()
    # Khởi tạo lại
    init_db()
    return {"success": True, "message": "Đã khôi phục thành công danh sách 30 lớp học chuẩn của trường Điều Cải!"}

# --- API Phân Phối Thông Báo ZALO ---

@app.post("/api/reports/send-zalo")
async def send_zalo_report(req: ZaloTestRequest):
    """Gửi tin nhắn báo cáo điểm danh hoặc tin thử nghiệm qua Zalo."""
    from services.zalo_service import zalo_service
    if req.session_id:
        res = zalo_service.send_attendance_summary(req.session_id)
    else:
        res = zalo_service.send_test_message(
            target_type=req.target_type or "WEBHOOK",
            webhook_url=req.webhook_url,
            access_token=req.access_token,
            user_id=req.user_id
        )
    return res

@app.get("/api/reports/zalo-status")
async def get_zalo_status():
    """Lấy trạng thái cấu hình dịch vụ Zalo."""
    from services.zalo_service import zalo_service
    return zalo_service.get_status()

@app.post("/api/reports/save-zalo-config")
async def save_zalo_config(req: ZaloConfigSaveRequest):
    """Lưu cấu hình Zalo vào bộ nhớ hệ thống."""
    settings.ENABLE_ZALO_NOTIFICATION = req.enabled
    settings.ZALO_NOTIFICATION_TYPE = req.notification_type
    if req.webhook_url is not None:
        settings.ZALO_WEBHOOK_URL = req.webhook_url.strip()
    if req.access_token is not None:
        settings.ZALO_OA_ACCESS_TOKEN = req.access_token.strip()
    if req.recipient_user_id is not None:
        settings.ZALO_RECIPIENT_USER_ID = req.recipient_user_id.strip()
    return {"success": True, "message": "Đã cập nhật cấu hình Zalo thành công!"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=True)

