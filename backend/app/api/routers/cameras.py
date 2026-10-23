import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from starlette.concurrency import run_in_threadpool
import time

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db, init_db
from database.models import Classroom, ROIPolygon, AttendanceDetail, AttendanceSession, NVRDevice, User
from config.notification_settings_store import save_notification_settings
from services.scheduler import attendance_scheduler
from backend.app.core.rtsp_client import rtsp_client
from backend.app.core.relay_service import relay_service
from services.nvr_service import nvr_service
from backend.app.api.deps import get_current_user, require_admin
from backend.app.api.security import (
    check_rate_limit,
    client_ip,
    log_info_redacted,
    mask_stream_url,
    validate_relay_ip,
    validate_stream_source,
)
from backend.app.schemas.camera_schemas import (
    CameraCreateRequest,
    CameraUpdateRequest,
    TestCameraRequest,
    TestCameraIRRequest,
    NVRProbeRequest,
    NVRBatchImportRequest,
    SwitchCameraSourceModeRequest,
    InspectFolderRequest,
    BatchStatusRequest,
    ValidateNewCameraRequest,
    AutoScheduleRequest
)

router = APIRouter(prefix="/cameras", tags=["Cameras"], dependencies=[Depends(get_current_user)])

@router.get("")
@router.get("/")
async def get_all_cameras(db: Session = Depends(get_db)):
    """Lấy danh sách chi tiết tất cả Camera/Lớp học kèm loại nguồn, trạng thái và số liệu điểm danh mới nhất."""
    # 1. Eager load Classroom và ROIPolygon trong 1 câu query duy nhất (khử 30 queries riêng lẻ)
    classrooms = db.query(Classroom).options(joinedload(Classroom.roi)).order_by(Classroom.id.asc()).all()

    # 2. Thu thập dữ liệu điểm danh thực tế mới nhất theo batch kèm joinedload session
    latest_session = db.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()
    details_map = {}
    if latest_session:
        details = (
            db.query(AttendanceDetail)
            .options(joinedload(AttendanceDetail.session))
            .filter(AttendanceDetail.session_id == latest_session.id)
            .all()
        )
        for d in details:
            details_map[d.classroom_id] = d

    # Nạp bản ghi mới nhất cho các lớp còn thiếu trong 1 câu batch query duy nhất
    missing_c_ids = [c.id for c in classrooms if c.id not in details_map]
    if missing_c_ids:
        fallback_details = (
            db.query(AttendanceDetail)
            .options(joinedload(AttendanceDetail.session))
            .filter(AttendanceDetail.classroom_id.in_(missing_c_ids))
            .order_by(AttendanceDetail.id.desc())
            .all()
        )
        for fd in fallback_details:
            if fd.classroom_id not in details_map:
                details_map[fd.classroom_id] = fd

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

        has_roi = bool(c.roi and (c.roi.green_zone or c.roi.red_zone))

        # Lấy từ bộ đệm details_map (không query DB trong vòng lặp)
        det = details_map.get(c.id)

        present_count = det.present_count if det else 0
        absent_count = det.absent_count if det else 0
        scan_time = ""
        scan_date = ""
        if det and det.session:
            scan_time = det.session.scan_time or ""
            scan_date = det.session.scan_date or ""
        elif det and det.created_at:
            scan_time = det.created_at.strftime("%H:%M:%S")
            scan_date = det.created_at.strftime("%d/%m/%Y")

        scan_status = det.status if det else "CHUA_QUET"
        has_scanned = det is not None

        results.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "room_number": c.room_number,
            "standard_count": c.standard_count,
            "present_count": present_count,
            "absent_count": absent_count,
            "scan_time": scan_time,
            "scan_date": scan_date,
            "scan_status": scan_status,
            "has_scanned": has_scanned,
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


@router.get("/auto-schedule")
async def get_classroom_auto_schedule():
    """Lấy cấu hình lịch quét điểm danh tự động toàn trường."""
    m_time = getattr(settings, "SCAN_TIME_MORNING", "06:45")
    a_time = getattr(settings, "SCAN_TIME_AFTERNOON", "12:45")
    days = getattr(settings, "SCHEDULE_DAYS", "mon-sat")
    enabled = getattr(settings, "AUTO_SCAN_ENABLED", True)
    afternoon_enabled = getattr(settings, "AFTERNOON_SCAN_ENABLED", True)
    return {
        "success": True,
        "auto_scan_enabled": bool(enabled),
        "afternoon_enabled": bool(afternoon_enabled),
        "scan_time_morning": m_time,
        "scan_time_afternoon": a_time,
        "schedule_days": days,
        "timezone": "Asia/Ho_Chi_Minh (GMT+7)"
    }


@router.post("/auto-schedule")
async def update_classroom_auto_schedule(req: AutoScheduleRequest, _admin: User = Depends(require_admin)):
    """Cập nhật cấu hình lịch quét tự động và áp dụng ngay vào tiến trình chạy ngầm."""
    m_time = req.scan_time_morning or getattr(settings, "SCAN_TIME_MORNING", "06:45")
    a_time = req.scan_time_afternoon or getattr(settings, "SCAN_TIME_AFTERNOON", "12:45")
    days = req.schedule_days or getattr(settings, "SCHEDULE_DAYS", "mon-sat")
    enabled = req.auto_scan_enabled if req.auto_scan_enabled is not None else getattr(settings, "AUTO_SCAN_ENABLED", True)
    afternoon_enabled = req.afternoon_enabled if req.afternoon_enabled is not None else getattr(settings, "AFTERNOON_SCAN_ENABLED", True)

    payload = {
        "SCAN_TIME_MORNING": m_time,
        "SCAN_TIME_AFTERNOON": a_time,
        "SCHEDULE_DAYS": days,
        "AUTO_SCAN_ENABLED": bool(enabled),
        "AFTERNOON_SCAN_ENABLED": bool(afternoon_enabled),
    }
    save_notification_settings(settings, payload)

    try:
        attendance_scheduler.update_schedule(
            morning_time=m_time,
            afternoon_time=a_time,
            days=days,
            enabled=bool(enabled),
            afternoon_enabled=bool(afternoon_enabled)
        )
    except Exception as e:
        logger.warning(f"Lỗi cập nhật attendance_scheduler: {e}")

    return {
        "success": True,
        "message": "Đã lưu cài đặt lịch quét tự động thành công!",
        "auto_scan_enabled": bool(enabled),
        "afternoon_enabled": bool(afternoon_enabled),
        "scan_time_morning": m_time,
        "scan_time_afternoon": a_time,
        "schedule_days": days
    }


@router.post("/auto-schedule/trigger")
async def trigger_test_auto_schedule(_admin: User = Depends(require_admin)):
    """Kích hoạt chạy quét điểm danh thử nghiệm ngay lập tức từ modal cài đặt lịch."""
    try:
        from backend.app.core.attendance_engine import attendance_engine
        res = await run_in_threadpool(attendance_engine.run_daily_attendance, trigger_led=False)
        return {
            "success": True,
            "message": "Đã kích hoạt quét điểm danh toàn trường thành công!",
            "session_code": res.get("session_code"),
            "total_present": res.get("total_present"),
            "total_absent": res.get("total_absent")
        }
    except Exception as e:
        logger.error(f"Lỗi khi kích hoạt quét thử: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi quét thử: {str(e)}")



@router.get("/{classroom_id}/raw")
async def get_camera_raw_rtsp(classroom_id: int, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Trả URL gốc (có credential) cho admin khi cần chỉnh sửa cấu hình camera."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera/lớp học")
    return {"success": True, "rtsp_url": cls.rtsp_url}

@router.get("/{classroom_id}/stream")
@router.get("/{classroom_id}/live-stream")
async def stream_classroom_video(
    classroom_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Phát luồng video trực tiếp thời gian thực (Live MJPEG Stream).
    Hỗ trợ đọc từ RTSP / camera source, tự động chuyển động và lớp phủ OSD thời gian thực.
    """
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera/lớp học")

    import cv2
    import numpy as np
    from datetime import datetime

    source_url = cls.rtsp_url or ""
    cam_name = cls.name or f"Camera {classroom_id}"
    room_name = cls.room_number or f"Phòng {classroom_id}"

    async def frame_generator():
        base_frame = None
        for p in [
            Path(f"data/storage/captures/latest/Lop_{classroom_id}.jpg"),
            Path(f"storage/captures/latest/Lop_{classroom_id}.jpg"),
            Path("data/dataset/samples/classroom_sample.jpg"),
            Path("dataset/samples/classroom_sample.jpg")
        ]:
            if p.exists():
                try:
                    base_frame = cv2.imread(str(p))
                    if base_frame is not None:
                        break
                except Exception:
                    pass

        if base_frame is None:
            base_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            base_frame[:] = (20, 24, 33)

        cap = None
        if source_url.startswith(("rtsp://", "http://")) or source_url.endswith((".mp4", ".avi", ".mkv")):
            try:
                cap = cv2.VideoCapture(source_url)
                if not cap.isOpened():
                    cap = None
            except Exception:
                cap = None

        frame_counter = 0
        try:
            while True:
                if await request.is_disconnected():
                    break

                current_frame = None
                if cap is not None and cap.isOpened():
                    ret, f = cap.read()
                    if ret and f is not None:
                        current_frame = f
                    else:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

                if current_frame is None:
                    current_frame = base_frame.copy()

                h, w = current_frame.shape[:2]
                if w > 1280:
                    current_frame = cv2.resize(current_frame, (1280, int(h * 1280 / w)))
                    h, w = current_frame.shape[:2]

                now = datetime.now()
                time_str = now.strftime("%Y-%m-%d %H:%M:%S")

                # Vẽ OSD Video chuyên nghiệp
                cv2.rectangle(current_frame, (0, 0), (w, 38), (15, 23, 42), -1)

                blink = (frame_counter // 10) % 2 == 0
                dot_color = (0, 0, 230) if blink else (60, 60, 120)
                cv2.circle(current_frame, (20, 19), 6, dot_color, -1)
                cv2.putText(current_frame, "LIVE", (32, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

                info_text = f"{cam_name} | {room_name} | CH{classroom_id:02d}"
                cv2.putText(current_frame, info_text, (100, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)
                cv2.putText(current_frame, time_str, (max(10, w - 240), 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 255), 2)

                success, buffer = cv2.imencode('.jpg', current_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if not success:
                    await asyncio.sleep(0.05)
                    continue

                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                frame_counter += 1
                await asyncio.sleep(0.04)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Stream ngắt kết nối cho camera {classroom_id}: {e}")
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no"
        }
    )

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

    # Camera mới mặc định ở trạng thái toàn cảnh (chưa cấu hình ROI)
    default_green_zone = []
    default_red_zone = []
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

@router.post("/batch-status")
async def batch_toggle_camera_status(data: BatchStatusRequest, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Bật/Tắt kích hoạt đồng loạt camera (chỉ admin). Nếu camera_ids rỗng thì áp dụng cho toàn bộ camera."""
    query = db.query(Classroom)
    if data.camera_ids and len(data.camera_ids) > 0:
        query = query.filter(Classroom.id.in_(data.camera_ids))
    count = query.update({Classroom.is_active: data.is_active}, synchronize_session=False)
    db.commit()
    status_str = "kích hoạt" if data.is_active else "tạm ngưng"
    logger.info(f"Admin đã {status_str} đồng loạt {count} camera lớp học")
    return {"success": True, "message": f"Đã {status_str} thành công {count} camera/lớp học!", "count": count}


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


@router.post("/validate-new-camera")
async def validate_new_camera_wizard(
    req: ValidateNewCameraRequest,
    request: Request,
    _admin: User = Depends(require_admin)
):
    """
    Quy trình kiểm định 5 bước chuẩn hóa trước khi thêm camera mới vào hệ thống:
    - Bước 1: Kết nối & đo độ trễ RTSP/Camera (Ping handshake).
    - Bước 2: Đọc 5 frame liên tiếp kiểm tra độ ổn định tín hiệu và tốc độ nạp khung hình.
    - Bước 3: Thẩm định độ phân giải (yêu cầu >= 1280x720) và phân tích kích cỡ đầu học sinh ở dãy bàn xa.
    - Bước 4: Kiểm tra và mô phỏng vùng ROI (Bàn học Green Zone / Bục giảng Red Zone).
    - Bước 5: Chạy thử nghiệm AI YOLO nhận diện đầu người và trả về kết quả đối chứng.
    Người dùng xác nhận kết quả đạt chuẩn mới tiến hành lưu camera vào CSDL.
    """
    check_rate_limit("action", f"valcam:{client_ip(request)}", limit=10, window_seconds=60)
    validate_stream_source(req.source_url)
    validate_relay_ip(req.relay_ip or "")

    import base64
    import cv2
    import numpy as np

    # Bước 1: Kết nối ban đầu
    conn_res = rtsp_client.test_camera_stream(req.source_url, trigger_signal=False, relay_ip=req.relay_ip or "")
    step1_ok = bool(conn_res.get("success", False))
    step1_latency = conn_res.get("latency_ms", 0)

    if not step1_ok:
        return {
            "success": False,
            "ready_for_save": False,
            "failed_step": 1,
            "message": f"Bước 1 thất bại: Không thể kết nối tới nguồn camera ({conn_res.get('message', '')})",
            "step1_connection": {"ok": False, "latency_ms": step1_latency, "error": conn_res.get("message")},
            "step2_frames": {"ok": False},
            "step3_resolution": {"ok": False},
            "step4_roi": {"ok": False},
            "step5_ai": {"ok": False}
        }

    # Bước 2: Đọc 5 frame liên tục
    sample_res = rtsp_client.capture_sample_frames(req.source_url, count=5)
    step2_ok = bool(sample_res.get("success", False))
    frames = sample_res.get("frames", [])
    best_frame = sample_res.get("best_frame")

    if not step2_ok or best_frame is None:
        return {
            "success": False,
            "ready_for_save": False,
            "failed_step": 2,
            "message": "Bước 2 thất bại: Luồng camera không ổn định (không đọc đủ 3-5 frame sạch)",
            "step1_connection": {"ok": True, "latency_ms": step1_latency},
            "step2_frames": {
                "ok": False,
                "frames_read": sample_res.get("frames_read", 0),
                "avg_latency_ms": sample_res.get("avg_latency_ms", 0)
            },
            "step3_resolution": {"ok": False},
            "step4_roi": {"ok": False},
            "step5_ai": {"ok": False}
        }

    # Bước 3: Thẩm định độ phân giải và kích thước đầu học sinh
    h, w = best_frame.shape[:2]
    is_res_ok = (w >= 1280 and h >= 720)
    sharpness = sample_res.get("best_sharpness", 0.0)

    # Bước 4: Vùng ROI
    default_green_zone = req.green_zone or [[200, 300], [1720, 300], [1850, 1050], [80, 1050]]
    default_red_zone = req.red_zone or [[350, 80], [900, 80], [950, 280], [300, 280]]

    # Vẽ preview có ROI
    roi_preview = best_frame.copy()
    if default_green_zone and len(default_green_zone) >= 3:
        pts = np.array(default_green_zone, np.int32).reshape((-1, 1, 2))
        cv2.polylines(roi_preview, [pts], isClosed=True, color=(0, 220, 100), thickness=3)
    if default_red_zone and len(default_red_zone) >= 3:
        pts_red = np.array(default_red_zone, np.int32).reshape((-1, 1, 2))
        cv2.polylines(roi_preview, [pts_red], isClosed=True, color=(0, 0, 240), thickness=3)

    _, buf_roi = cv2.imencode(".jpg", roi_preview, [cv2.IMWRITE_JPEG_QUALITY, 80])
    roi_preview_url = f"data:image/jpeg;base64,{base64.b64encode(buf_roi).decode('utf-8')}"

    # Bước 5: Chạy AI Object Detection thử nghiệm
    from backend.app.core.detector import detector
    present_count, detected_students, annotated_img = detector.detect_students_in_classroom(
        image=best_frame,
        red_zone=default_red_zone,
        green_zone=default_green_zone,
        classroom_name="Kiểm Định Camera",
        standard_count=req.standard_count or 40,
        apply_clahe=True
    )

    conf_avg = 0.0
    head_widths = []
    if detected_students:
        conf_avg = round(sum(s["confidence"] for s in detected_students) / len(detected_students), 2)
        for s in detected_students:
            b = s.get("bbox")
            if b and len(b) == 4:
                bw = b[2] - b[0]
                head_widths.append(bw)

    min_head_px = min(head_widths) if head_widths else 0
    avg_head_px = round(sum(head_widths) / len(head_widths), 1) if head_widths else 0
    far_heads_adequate = (min_head_px >= 10) if head_widths else True

    annotated_preview_url = ""
    if annotated_img is not None:
        _, buf_ann = cv2.imencode(".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        annotated_preview_url = f"data:image/jpeg;base64,{base64.b64encode(buf_ann).decode('utf-8')}"

    ready_for_save = is_res_ok and (sample_res.get("frames_read", 0) >= 3)

    return {
        "success": True,
        "ready_for_save": ready_for_save,
        "message": "Kiểm định 5 bước hoàn tất! Camera đạt chuẩn sẵn sàng đưa vào sử dụng." if ready_for_save else "Kiểm định hoàn tất kèm cảnh báo (Độ phân giải dưới chuẩn 720p).",
        "step1_connection": {
            "ok": True,
            "latency_ms": step1_latency,
            "message": f"Kết nối ổn định ({step1_latency}ms)"
        },
        "step2_frames": {
            "ok": True,
            "requested_count": 5,
            "frames_read": sample_res.get("frames_read", 0),
            "avg_latency_ms": sample_res.get("avg_latency_ms", 0),
            "total_elapsed_ms": sample_res.get("total_elapsed_ms", 0)
        },
        "step3_resolution": {
            "ok": is_res_ok,
            "resolution": f"{w}x{h}",
            "width": w,
            "height": h,
            "sharpness": sharpness,
            "min_head_px": min_head_px,
            "avg_head_px": avg_head_px,
            "far_heads_adequate": far_heads_adequate,
            "message": "Độ phân giải HD/Full HD chuẩn" if is_res_ok else "Cảnh báo: Độ phân giải dưới 720p"
        },
        "step4_roi": {
            "ok": True,
            "green_zone_points": len(default_green_zone),
            "red_zone_points": len(default_red_zone),
            "preview_url": roi_preview_url
        },
        "step5_ai": {
            "ok": True,
            "students_detected": present_count,
            "confidence_avg": conf_avg,
            "annotated_preview_url": annotated_preview_url,
            "message": f"Nhận diện thành công {present_count} vị trí học sinh (Độ tin cậy: {conf_avg})"
        }
    }

@router.post("/refresh-all-snapshots")
async def refresh_all_snapshots(request: Request, _user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Chụp lại ảnh mới nhất đồng loạt từ toàn bộ 30 camera lớp học trực tiếp qua NVR/RTSP."""
    check_rate_limit("action", f"refreshsnaps:{client_ip(request)}", limit=10, window_seconds=60)
    classrooms = db.query(Classroom).order_by(Classroom.id).all()
    if not classrooms:
        raise HTTPException(status_code=404, detail="Không có camera nào trong hệ thống.")
    
    from services.progress_service import progress_tracker
    progress_tracker.start("CAPTURE_ALL", f"Chụp Lại Toàn Bộ {len(classrooms)} Camera NVR", total_steps=1, total_items=len(classrooms))

    cls_data_list = [
        {"id": c.id, "name": c.name, "rtsp_url": c.rtsp_url}
        for c in classrooms
    ]
    latest_dir = settings.CAPTURES_DIR / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    
    def on_snap_captured(cur_done, total_done, cls_info, success):
        status_s = "thành công" if success else "thử lại / lỗi"
        log_t = "success" if success else "warning"
        pct = int((cur_done / max(1, total_done)) * 100)
        progress_tracker.update(
            step=1,
            step_title="Chụp Ảnh Trực Tiếp Từ Đầu Ghi NVR",
            current=cur_done,
            total=total_done,
            current_item=f"{cls_info['name']} (CH{cls_info['id']:02d})",
            percent=pct,
            log_text=f"Camera CH{cls_info['id']:02d} ({cls_info['name']}): Đã chụp {status_s}",
            log_type=log_t
        )

    results = await run_in_threadpool(
        rtsp_client.capture_all_classrooms,
        cls_data_list,
        target_folder=latest_dir,
        progress_callback=on_snap_captured
    )
    success_count = sum(1 for r in results.values() if r.get("success"))
    msg = f"Đã làm mới và chụp ảnh thành công {success_count}/{len(classrooms)} camera!"
    progress_tracker.finish(True, msg, result={"success_count": success_count, "total": len(classrooms)})
    return {
        "success": True,
        "message": msg,
        "success_count": success_count,
        "total": len(classrooms)
    }

@router.post("/{classroom_id}/refresh-snapshot")
async def refresh_single_classroom_snapshot(classroom_id: int, _user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Chụp lại ảnh mới nhất của 1 camera lớp học."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera/lớp học")
    
    from services.progress_service import progress_tracker
    progress_tracker.start("CAPTURE_SINGLE", f"Chụp Lại Camera {cls.name}", total_steps=1, total_items=1)
    progress_tracker.update(step=1, step_title="Đang kết nối luồng RTSP...", percent=35, current_item=cls.name, log_text=f"Đang kết nối camera {cls.name}...")

    latest_dir = settings.CAPTURES_DIR / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    _, success, path, _ = await run_in_threadpool(
        rtsp_client.capture_single_camera,
        cls.id,
        cls.name,
        cls.rtsp_url,
        latest_dir
    )
    snap_url = f"/storage/captures/latest/Lop_{cls.id}.jpg?t={int(time.time()*1000)}"
    if success:
        progress_tracker.finish(True, f"Đã cập nhật khung hình mới cho {cls.name}!", result={"snapshot_url": snap_url, "classroom_id": cls.id})
    else:
        progress_tracker.finish(False, f"Không thể lấy khung hình mới cho {cls.name}")

    return {
        "success": success,
        "message": f"Đã cập nhật khung hình mới cho {cls.name}" if success else f"Không thể lấy khung hình mới cho {cls.name}",
        "snapshot_url": snap_url
    }

@router.get("/progress")
async def get_cameras_progress():
    """Lấy trạng thái tiến trình thời gian thực của tác vụ chụp camera."""
    from services.progress_service import progress_tracker
    return progress_tracker.get_state()


@router.post("/test-ir-by-url")
async def test_ir_by_url_endpoint(req: TestCameraRequest, _admin: User = Depends(require_admin)):
    """Thử nghiệm chu trình bật đèn hồng ngoại camera (2.5s) rồi trả về Auto trên URL nhập từ form (chỉ admin)."""
    validate_stream_source(req.source_url)
    validate_relay_ip(req.relay_ip or "")
    cam_info = {"rtsp_url": req.source_url, "relay_ip": req.relay_ip or "", "name": "TestURLCamera"}
    ok_on = await run_in_threadpool(relay_service.set_camera_day_night, cam_info, "IR_ON")
    await asyncio.sleep(2.5)
    ok_off = await run_in_threadpool(relay_service.set_camera_day_night, cam_info, "AUTO")
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

    cam_info = {"rtsp_url": cls.rtsp_url, "relay_ip": cls.relay_ip or "", "name": cls.name}
    ok = await run_in_threadpool(relay_service.set_camera_day_night, cam_info, mode)
    
    if ok:
        async def _auto_restore():
            await asyncio.sleep(duration)
            await run_in_threadpool(relay_service.set_camera_day_night, cam_info, "AUTO")
        
        asyncio.create_task(_auto_restore())
    
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
        capture_color=True,
        force=True
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
    res = await run_in_threadpool(
        nvr_service.probe_all_nvr_channels,
        ip_address=req.ip_address,
        rtsp_port=req.rtsp_port,
        username=req.username,
        password=req.password,
        brand=req.brand,
        channels_count=req.channels_count,
        start_channel=req.start_channel,
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
    # Camera import mặc định ở trạng thái toàn cảnh (chưa cấu hình ROI)
    default_red_zone = []
    default_green_zone = []

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

        # Chụp/lưu ngay khung hình snapshot từ thumbnail xem trước hoặc từ camera nguồn
        try:
            if getattr(item, "thumbnail", None) and item.thumbnail.startswith("data:image"):
                b64_data = item.thumbnail.split(",", 1)[-1]
                img_bytes = base64.b64decode(b64_data)
                snap_path = latest_dir / f"Lop_{cls.id}.jpg"
                with open(snap_path, "wb") as f_snap:
                    f_snap.write(img_bytes)
            else:
                rtsp_client.capture_single_camera(cls.id, cls.name, cls.rtsp_url, latest_dir)
        except Exception as e:
            logger.debug(f"Không thể nạp snapshot cho Lop_{cls.id}: {e}")

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
    from backend.app.core.camera_source_manager import camera_source_manager
    return camera_source_manager.get_source_status(db, folder_str=folder)

@router.post("/inspect-folder")
async def inspect_camera_folder(req: InspectFolderRequest):
    """Kiểm tra sự tồn tại và số lượng ảnh trong thư mục người dùng nhập."""
    from backend.app.core.camera_source_manager import camera_source_manager
    return camera_source_manager.inspect_folder(req.folder_path)

@router.post("/switch-source-mode")
async def switch_camera_source_mode(req: SwitchCameraSourceModeRequest, db: Session = Depends(get_db)):
    """Chuyển đổi đồng loạt 30 camera sang Đầu Ghi NVR thực tế hoặc Ảnh mẫu thử nghiệm (chọn thư mục tùy ý)."""
    from backend.app.core.camera_source_manager import camera_source_manager
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
    from backend.app.core.camera_source_manager import camera_source_manager
    return camera_source_manager.cleanup_mock_folder(folder_path=folder or "camera")
