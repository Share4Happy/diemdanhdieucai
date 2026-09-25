import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db, init_db
from database.models import Classroom, ROIPolygon, AttendanceDetail, NVRDevice, User
from core.rtsp_client import rtsp_client
from core.relay_service import relay_service
from services.nvr_service import nvr_service
from backend.api.deps import get_current_user, require_admin
from backend.api.security import (
    check_rate_limit,
    client_ip,
    log_info_redacted,
    mask_stream_url,
    validate_relay_ip,
    validate_stream_source,
)
from backend.schemas.camera_schemas import (
    CameraCreateRequest,
    CameraUpdateRequest,
    TestCameraRequest,
    TestCameraIRRequest,
    NVRProbeRequest,
    NVRBatchImportRequest,
    SwitchCameraSourceModeRequest,
    InspectFolderRequest
)

router = APIRouter(prefix="/cameras", tags=["Cameras"], dependencies=[Depends(get_current_user)])

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
            # Che credential (user:pass) trong URL RTSP — chỉ admin mới lấy lại URL gốc.
            "rtsp_url": mask_stream_url(c.rtsp_url),
            "has_password": "@" in (c.rtsp_url or "").split("//", 1)[-1].split("/", 1)[0],
            "relay_ip": c.relay_ip,
            "is_active": c.is_active,
            "nvr_id": c.nvr_id,
            "channel_number": c.channel_number,
            "source_type": source_type,
            "has_roi": has_roi
        })
    return {"cameras": results}


@router.get("/{classroom_id}/raw")
async def get_camera_raw_rtsp(classroom_id: int, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Trả URL gốc (có credential) cho admin khi cần chỉnh sửa cấu hình camera."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera/lớp học")
    return {"success": True, "rtsp_url": cls.rtsp_url}

@router.post("")
@router.post("/")
async def create_camera(data: CameraCreateRequest, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Thêm mới một camera / lớp học vào hệ thống (chỉ admin)."""
    clean_code = data.code.strip().upper()
    validate_relay_ip(data.relay_ip or "")
    validate_stream_source(data.rtsp_url)
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
    default_green_zone = [[200, 300], [1720, 300], [1850, 1050], [80, 1050]]  # Phần LẤY (bàn học)
    default_red_zone = [[350, 80], [900, 80], [950, 280], [300, 280]]          # Phần BỎ ĐI (bục giảng)
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
async def update_camera(classroom_id: int, data: CameraUpdateRequest, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Cập nhật thông tin camera / lớp học (chỉ admin)."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera/lớp học")

    if data.relay_ip is not None:
        validate_relay_ip(data.relay_ip)
    if data.name is not None:
        cls.name = data.name.strip()
    if data.room_number is not None:
        cls.room_number = data.room_number.strip()
    if data.standard_count is not None:
        cls.standard_count = data.standard_count
    url_changed = False
    if data.rtsp_url is not None:
        new_url = data.rtsp_url.strip()
        # Nếu frontend gửi lại đúng giá trị đã che → giữ nguyên URL gốc cũ.
        if new_url == mask_stream_url(cls.rtsp_url or ""):
            new_url = (cls.rtsp_url or "").strip()
        elif new_url != (cls.rtsp_url or ""):
            validate_stream_source(new_url)
        if new_url != (cls.rtsp_url or ""):
            cls.rtsp_url = new_url
            url_changed = True
    if data.relay_ip is not None:
        cls.relay_ip = data.relay_ip.strip()
    if data.is_active is not None:
        cls.is_active = data.is_active
    if data.channel_number is not None:
        cls.channel_number = data.channel_number

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
async def delete_camera(classroom_id: int, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Xóa camera và các dữ liệu liên quan khỏi hệ thống (chỉ admin)."""
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
async def get_available_webcams_endpoint(refresh: bool = False, _admin: User = Depends(require_admin)):
    """Quét và trả về danh sách tất cả Webcam vật lý và ảo đang kết nối trên máy tính kèm preview thumbnail (chỉ admin)."""
    webcams = rtsp_client.get_available_webcams(refresh=refresh)
    return {
        "success": True,
        "count": len(webcams),
        "webcams": webcams
    }

@router.post("/test-connection")
async def test_camera_connection(req: TestCameraRequest, request: Request, _admin: User = Depends(require_admin)):
    """Kiểm tra trực tiếp kết nối tới nguồn camera (RTSP, Webcam, File) và trả về snapshot preview (chỉ admin)."""
    check_rate_limit("action", f"testconn:{client_ip(request)}", limit=10, window_seconds=60)
    validate_stream_source(req.source_url)
    validate_relay_ip(req.relay_ip or "")
    res = rtsp_client.test_camera_stream(
        source_url=req.source_url,
        trigger_signal=req.trigger_signal or False,
        relay_ip=req.relay_ip or ""
    )
    return res

@router.post("/test-ir-by-url")
async def test_ir_by_url_endpoint(req: TestCameraRequest, _admin: User = Depends(require_admin)):
    """Thử nghiệm chu trình bật đèn hồng ngoại camera (2.5s) rồi trả về Auto trên URL nhập từ form (chỉ admin)."""
    validate_stream_source(req.source_url)
    validate_relay_ip(req.relay_ip or "")
    cam_info = {"rtsp_url": req.source_url, "relay_ip": req.relay_ip or "", "name": "TestURLCamera"}
    ok_on = relay_service.set_camera_day_night(cam_info, "IR_ON")
    import time
    time.sleep(2.5)
    ok_off = relay_service.set_camera_day_night(cam_info, "AUTO")
    success = ok_on or ok_off
    return {
        "success": success,
        "message": "Đã kích hoạt đèn hồng ngoại camera thành công qua giao thức ONVIF (Đèn sáng đỏ 2.5s rồi tự động tắt)." if success else "Không thể kết nối hoặc camera không phản hồi giao thức ONVIF/CGI. Vui lòng kiểm tra lại IP/mật khẩu camera."
    }

@router.post("/{classroom_id}/test-ir")
async def test_classroom_camera_ir_endpoint(classroom_id: int, req: Optional[TestCameraIRRequest] = None, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Thử nghiệm bật đèn hồng ngoại trên camera lớp học trong X giây rồi tự động tắt (chỉ admin)."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera/lớp học")
    
    duration = req.duration_seconds if req and req.duration_seconds else 4
    mode = req.mode if req and req.mode else "IR_ON"

    ok = relay_service.set_camera_day_night(cls, mode)
    
    if ok:
        def _auto_restore():
            import time
            time.sleep(duration)
            relay_service.set_camera_day_night(cls, "AUTO")
        
        import threading
        threading.Thread(target=_auto_restore, daemon=True).start()
    
    mode_vn = "hồng ngoại" if mode == "IR_ON" else ("trợ sáng trắng" if mode == "WHITE_LIGHT_ON" else mode)
    return {
        "success": ok,
        "message": f"Đã kích hoạt đèn {mode_vn} cho {cls.name} (Tự động tắt sau {duration} giây)." if ok else f"Không thể gửi lệnh điều khiển đèn {mode_vn} tới camera {cls.name}. Vui lòng kiểm tra lại địa chỉ IP ({cls.relay_ip or 'chưa cấu hình'}) và kết nối mạng.",
        "classroom_id": classroom_id,
        "duration_seconds": duration
    }

@router.post("/test-all-ir")
async def test_all_cameras_ir_endpoint(req: Optional[TestCameraIRRequest] = None, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Thử nghiệm kích hoạt đèn hồng ngoại đồng loạt trên toàn bộ 30 camera lớp học (chỉ admin)."""
    classrooms = db.query(Classroom).filter(Classroom.is_active == True).order_by(Classroom.id).all()
    if not classrooms:
        raise HTTPException(status_code=404, detail="Chưa có camera lớp học nào đang kích hoạt trong hệ thống.")

    duration = req.duration_seconds if req and req.duration_seconds else 3
    logger.info(f"Kích hoạt thử nghiệm đèn hồng ngoại đồng loạt {len(classrooms)} camera ({duration}s)...")

    relay_service.signal_classrooms_before_capture(
        classrooms=classrooms,
        signal_seconds=duration,
        capture_color=True
    )
    relay_service.restore_classrooms_auto(classrooms)

    return {
        "success": True,
        "message": f"Đã phát tín hiệu đèn hồng ngoại đồng loạt trên {len(classrooms)} camera thành công ({duration}s báo hiệu đỏ -> chuyển ảnh màu -> tự động tắt)!",
        "count": len(classrooms),
        "duration_seconds": duration
    }


@router.post("/reset-defaults")
async def reset_default_cameras(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Khôi phục lại danh sách 30 lớp học chuẩn của trường THPT Điều Cải (chỉ admin)."""
    db.query(ROIPolygon).delete()
    db.query(AttendanceDetail).delete()
    db.query(Classroom).delete()
    db.commit()
    init_db(force_seed_classes=True)
    return {"success": True, "message": "Đã khôi phục thành công danh sách 30 lớp học chuẩn của trường Điều Cải!"}

# ==================== NVR / DVR SMART INTEGRATION ====================

@router.post("/nvr/probe")
async def probe_nvr_endpoint(req: NVRProbeRequest, request: Request, _admin: User = Depends(require_admin)):
    """Thăm dò đồng thời toàn bộ các kênh camera của đầu ghi NVR và trả về thumbnail live preview (chỉ admin)."""
    check_rate_limit("action", f"nvrprobe:{client_ip(request)}", limit=5, window_seconds=120)
    validate_relay_ip(req.ip_address)  # NVR phải nằm trong mạng nội bộ
    res = nvr_service.probe_all_nvr_channels(
        ip_address=req.ip_address,
        rtsp_port=req.rtsp_port,
        username=req.username,
        password=req.password,
        brand=req.brand,
        channels_count=req.channels_count,
        naming_mode=req.naming_mode,
        custom_pattern=req.custom_pattern or ""
    )
    return res

@router.post("/nvr/batch-import")
async def batch_import_nvr_endpoint(req: NVRBatchImportRequest, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """
    Nhập đồng loạt toàn bộ 30 camera từ Đầu Ghi NVR vào hệ thống (chỉ admin).
    Tự động khởi tạo cấu hình ROI chuẩn và lưu ảnh snapshot mới nhất.
    """
    import base64
    host = req.ip_address.strip()
    validate_relay_ip(host)
    
    # 1. Tìm hoặc tạo bản ghi NVRDevice
    nvr = db.query(NVRDevice).filter(NVRDevice.ip_address == host).first()
    if not nvr:
        nvr = NVRDevice(
            name=req.nvr_name.strip() if req.nvr_name else f"Đầu ghi NVR {host}",
            ip_address=host,
            rtsp_port=req.rtsp_port,
            http_port=req.http_port or 80,
            username=req.username,
            password=req.password,
            brand=req.brand,
            channels_count=req.channels_count,
            custom_url_pattern=req.custom_pattern or ""
        )
        db.add(nvr)
        db.flush()
    else:
        nvr.name = req.nvr_name.strip() if req.nvr_name else nvr.name
        nvr.rtsp_port = req.rtsp_port
        nvr.username = req.username
        nvr.password = req.password
        nvr.brand = req.brand
        nvr.channels_count = req.channels_count
        nvr.custom_url_pattern = req.custom_pattern or ""

    # 2. Xử lý ghi đè nếu được chọn
    if req.replace_existing:
        db.query(ROIPolygon).delete()
        db.query(AttendanceDetail).delete()
        db.query(Classroom).delete()
        db.commit()

    # Thư mục lưu snapshot mới nhất
    latest_dir = settings.CAPTURES_DIR / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)

    default_red_zone = [[200, 300], [1720, 300], [1850, 1050], [80, 1050]]
    default_green_zone = [[350, 80], [900, 80], [950, 280], [300, 280]]

    imported_count = 0
    for item in req.channels:
        if not item.is_selected:
            continue
        validate_stream_source(item.rtsp_url)
        clean_code = item.code.strip().upper()
        existing = db.query(Classroom).filter(Classroom.code == clean_code).first()
        if existing:
            existing.name = item.name.strip()
            existing.room_number = item.room_number.strip() if item.room_number else ""
            existing.standard_count = item.standard_count
            existing.rtsp_url = item.rtsp_url.strip()
            existing.relay_ip = host
            existing.nvr_id = nvr.id
            existing.channel_number = item.channel
            cls = existing
        else:
            cls = Classroom(
                code=clean_code,
                name=item.name.strip(),
                room_number=item.room_number.strip() if item.room_number else "",
                standard_count=item.standard_count,
                rtsp_url=item.rtsp_url.strip(),
                relay_ip=host,
                is_active=True,
                nvr_id=nvr.id,
                channel_number=item.channel
            )
            db.add(cls)
            db.flush()

            roi = ROIPolygon(
                classroom_id=cls.id,
                red_zone_json=json.dumps(default_red_zone),
                green_zone_json=json.dumps(default_green_zone),
                image_width=1920,
                image_height=1080
            )
            db.add(roi)

        # Chụp ngay khung hình Full HD 1080p sắc nét từ nguồn camera (hoặc nạp ảnh mẫu chuẩn 1080p nếu camera offline)
        try:
            rtsp_client.capture_single_camera(cls.id, cls.name, cls.rtsp_url, latest_dir)
        except Exception as e:
            logger.debug(f"Không thể nạp snapshot Full HD cho Lop_{cls.id}: {e}")

        imported_count += 1

    db.commit()
    logger.info(f"Đã nhập thành công {imported_count} camera từ NVR {host}")
    return {
        "success": True,
        "message": f"Đã nhập thành công {imported_count} camera từ đầu ghi {nvr.name}!",
        "imported_count": imported_count,
        "nvr_id": nvr.id
    }

@router.get("/nvr/list")
async def list_nvr_devices(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Lấy danh sách các Đầu Ghi NVR đã cấu hình (chỉ admin)."""
    nvrs = db.query(NVRDevice).order_by(NVRDevice.id.desc()).all()
    results = []
    for n in nvrs:
        cams_count = db.query(Classroom).filter(Classroom.nvr_id == n.id).count()
        results.append({
            "id": n.id,
            "name": n.name,
            "ip_address": n.ip_address,
            "rtsp_port": n.rtsp_port,
            "http_port": n.http_port,
            "username": n.username,
            "brand": n.brand,
            "channels_count": n.channels_count,
            "connected_cameras": cams_count,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S") if n.created_at else ""
        })
    return {"success": True, "nvrs": results}

@router.delete("/nvr/{nvr_id}")
async def delete_nvr_device(nvr_id: int, delete_cameras: bool = False, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Xóa đầu ghi NVR và tùy chọn xóa toàn bộ camera thuộc đầu ghi đó (chỉ admin)."""
    nvr = db.query(NVRDevice).filter(NVRDevice.id == nvr_id).first()
    if not nvr:
        raise HTTPException(status_code=404, detail="Không tìm thấy đầu ghi NVR")
    
    name = nvr.name
    if delete_cameras:
        classrooms = db.query(Classroom).filter(Classroom.nvr_id == nvr_id).all()
        for c in classrooms:
            db.query(ROIPolygon).filter(ROIPolygon.classroom_id == c.id).delete()
            db.query(AttendanceDetail).filter(AttendanceDetail.classroom_id == c.id).delete()
            db.delete(c)
    else:
        # Giữ lại camera, chỉ gỡ liên kết NVR
        db.query(Classroom).filter(Classroom.nvr_id == nvr_id).update({Classroom.nvr_id: None})

    db.delete(nvr)
    db.commit()
    logger.info(f"Đã xóa đầu ghi NVR {name}")
    return {"success": True, "message": f"Đã xóa đầu ghi {name} thành công"}

@router.get("/matrix-wall")
async def get_matrix_wall(db: Session = Depends(get_db)):
    """Lấy dữ liệu toàn bộ camera phục vụ màn hình Lưới Ma Trận TV Wall 30/32 ô."""
    classrooms = db.query(Classroom).order_by(Classroom.channel_number.asc(), Classroom.id.asc()).all()
    items = []
    for c in classrooms:
        snap_file = settings.CAPTURES_DIR / "latest" / f"Lop_{c.id}.jpg"
        has_snap = snap_file.exists()
        snap_url = f"/storage/captures/latest/Lop_{c.id}.jpg" if has_snap else ""
        
        items.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "room_number": c.room_number,
            "channel_number": c.channel_number or c.id,
            "standard_count": c.standard_count,
            "rtsp_url": mask_stream_url(c.rtsp_url),
            "is_active": c.is_active,
            "has_roi": bool(c.roi and c.roi.red_zone),
            "snapshot_url": snap_url,
            "relay_ip": c.relay_ip
        })
    return {
        "success": True,
        "total": len(items),
        "cameras": items
    }

@router.get("/source-status")
async def get_camera_source_status(folder: Optional[str] = None, db: Session = Depends(get_db)):
    """Kiểm tra trạng thái nguồn của 30 camera: Ảnh mẫu thử nghiệm (Test) hay Đầu ghi NVR (Production)."""
    from core.camera_source_manager import camera_source_manager
    return camera_source_manager.get_source_status(db, folder_str=folder)

@router.post("/inspect-folder")
async def inspect_camera_folder(req: InspectFolderRequest):
    """Kiểm tra sự tồn tại và số lượng ảnh trong thư mục người dùng nhập."""
    from core.camera_source_manager import camera_source_manager
    return camera_source_manager.inspect_folder(req.folder_path)

@router.post("/switch-source-mode")
async def switch_camera_source_mode(req: SwitchCameraSourceModeRequest, db: Session = Depends(get_db)):
    """Chuyển đổi đồng loạt 30 camera sang Đầu Ghi NVR thực tế hoặc Ảnh mẫu thử nghiệm (chọn thư mục tùy ý)."""
    from core.camera_source_manager import camera_source_manager
    if req.mode.upper() == "REAL_NVR":
        result = camera_source_manager.switch_to_real_nvr(
            db=db,
            nvr_ip=req.nvr_ip,
            nvr_port=req.nvr_port,
            nvr_user=req.nvr_user,
            nvr_pass=req.nvr_pass,
            nvr_brand=req.nvr_brand,
            channel_start=req.channel_start,
            cleanup_mock_images=req.cleanup_mock_images,
            mock_folder=req.mock_folder or "camera"
        )
    else:
        result = camera_source_manager.switch_to_mock_images(
            db=db,
            folder_path=req.mock_folder or "camera",
            channel_start=req.channel_start
        )
    return result

@router.post("/cleanup-test-images")
async def cleanup_test_images(folder: Optional[str] = "camera", _user=Depends(get_current_user)):
    """Xóa bỏ thư mục ảnh test giả lập sau khi đã bàn giao đầu ghi thực tế cho khách."""
    from core.camera_source_manager import camera_source_manager
    return camera_source_manager.cleanup_mock_folder(folder_path=folder or "camera")
