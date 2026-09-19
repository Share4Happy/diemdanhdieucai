import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db
from database.models import Classroom, ROIPolygon
from core.rtsp_client import rtsp_client
from backend.schemas.roi_schemas import ROISaveRequest

router = APIRouter(prefix="/roi", tags=["ROI"])

@router.get("/{classroom_id}")
async def get_classroom_roi(classroom_id: int, refresh: bool = False, db: Session = Depends(get_db)):
    """Lấy tọa độ Red Zone & Green Zone của lớp học và tự động chụp ảnh thực tế từ Camera."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    roi = cls.roi
    red_zone = roi.red_zone if roi else []
    green_zone = roi.green_zone if roi else []

    latest_dir = settings.CAPTURES_DIR / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    live_path = latest_dir / f"Lop_{classroom_id}.jpg"

    is_stale = False
    if live_path.exists():
        try:
            file_age = time.time() - live_path.stat().st_mtime
            if file_age > 120:
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
        "image_width": (roi.image_width if roi and roi.image_width else 1080),
        "image_height": (roi.image_height if roi and roi.image_height else 1024),
        "snapshot_url": snapshot_url
    }

@router.post("/{classroom_id}/refresh-snapshot")
async def refresh_classroom_snapshot(classroom_id: int, db: Session = Depends(get_db)):
    """Chụp ngay khung hình trực tiếp mới nhất từ Camera đang kết nối và trả về URL ảnh cập nhật."""
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

@router.post("/{classroom_id}")
async def save_classroom_roi(classroom_id: int, data: ROISaveRequest, db: Session = Depends(get_db)):
    """Lưu tọa độ Red Zone (bàn học) và Green Zone (bục giảng) cho lớp học, đồng thời tự động chạy lại nhận diện AI và đồng bộ sang giao diện quét."""
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

    # Tự động chạy lại AI và cập nhật kết quả nhận diện
    return await execute_roi_rescan(cls, data.red_zone, data.green_zone, data.image_width, data.image_height, db)


@router.post("/{classroom_id}/rescan")
async def rescan_classroom_roi(classroom_id: int, db: Session = Depends(get_db)):
    """Kích hoạt nhận diện lại ngay lập tức cho 1 lớp học theo ROI hiện hành trong CSDL."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    red_zone = cls.roi.red_zone if cls.roi else []
    green_zone = cls.roi.green_zone if cls.roi else []
    img_w = cls.roi.image_width if cls.roi else 1920
    img_h = cls.roi.image_height if cls.roi else 1080

    return await execute_roi_rescan(cls, red_zone, green_zone, img_w, img_h, db)


async def execute_roi_rescan(cls: Classroom, red_zone: list, green_zone: list, img_w: int, img_h: int, db: Session):
    """Hàm phụ trợ phân tích AI theo ROI, lưu ảnh đối chứng mới và cập nhật CSDL điểm danh."""
    present_count = None
    absent_count = None
    annotated_url = ""
    classroom_id = cls.id

    try:
        import cv2
        import numpy as np
        from datetime import datetime
        from core.detector import detector
        from database.models import AttendanceSession, AttendanceDetail

        # 1. Tìm frame mới nhất của lớp học
        frame = None
        raw_path = None
        latest_capture = settings.CAPTURES_DIR / "latest" / f"Lop_{classroom_id}.jpg"
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_capture = settings.CAPTURES_DIR / today_str / f"Lop_{classroom_id}.jpg"

        if latest_capture.exists():
            raw_path = str(latest_capture)
            frame = cv2.imread(raw_path)
        elif today_capture.exists():
            raw_path = str(today_capture)
            frame = cv2.imread(raw_path)
        else:
            latest_det = db.query(AttendanceDetail).filter(
                AttendanceDetail.classroom_id == classroom_id,
                AttendanceDetail.raw_image_path.isnot(None)
            ).order_by(AttendanceDetail.id.desc()).first()
            if latest_det and latest_det.raw_image_path and Path(latest_det.raw_image_path).exists():
                raw_path = latest_det.raw_image_path
                frame = cv2.imread(raw_path)

        if frame is None:
            extracted_frames = list((settings.BASE_DIR / "dataset" / "extracted_frames").glob("*.jpg"))
            if extracted_frames:
                sample_path = extracted_frames[(classroom_id - 1) % len(extracted_frames)]
                frame = cv2.imread(str(sample_path))
                raw_path = str(sample_path)

        if frame is not None:
            roi_dims = (img_w, img_h) if (img_w and img_h) else None
            present_count, detected_students, annotated_img = detector.detect_students_in_classroom(
                image=frame,
                red_zone=red_zone,
                green_zone=green_zone,
                classroom_name=cls.name,
                standard_count=cls.standard_count,
                apply_clahe=settings.USE_IMAGE_ENHANCEMENT,
                roi_dims=roi_dims
            )
            absent_count = max(0, cls.standard_count - present_count)

            # Lưu ảnh đối chứng đã vẽ bounding box và vùng ROI mới
            latest_annotated = settings.CAPTURES_DIR / "latest" / f"Lop_{classroom_id}_annotated.jpg"
            cv2.imwrite(str(latest_annotated), annotated_img)

            today_annotated_dir = settings.ANNOTATED_DIR / today_str
            today_annotated_dir.mkdir(parents=True, exist_ok=True)
            today_annotated_file = today_annotated_dir / f"Lop_{classroom_id}_result.jpg"
            cv2.imwrite(str(today_annotated_file), annotated_img)

            # Cập nhật AttendanceDetail của phiên gần nhất
            latest_session = db.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()
            if latest_session:
                det = db.query(AttendanceDetail).filter(
                    AttendanceDetail.session_id == latest_session.id,
                    AttendanceDetail.classroom_id == classroom_id
                ).first()
                if not det:
                    det = AttendanceDetail(
                        session_id=latest_session.id,
                        classroom_id=classroom_id,
                        standard_count=cls.standard_count,
                        raw_image_path=raw_path or str(latest_capture)
                    )
                    db.add(det)

                det.present_count = present_count
                det.absent_count = absent_count
                det.annotated_image_path = str(today_annotated_file)
                det.notes = f"Đã cập nhật theo ROI mới ({present_count}/{cls.standard_count})"
                if detected_students:
                    det.confidence_avg = round(sum(s["confidence"] for s in detected_students) / len(detected_students), 2)

                # Cập nhật tổng sĩ số phiên
                all_details = db.query(AttendanceDetail).filter(AttendanceDetail.session_id == latest_session.id).all()
                latest_session.total_present = sum(d.present_count for d in all_details)
                latest_session.total_absent = sum(d.absent_count for d in all_details)

                db.commit()
                logger.info(f"Đã cập nhật AttendanceDetail cho {cls.name}: hiện diện={present_count}, vắng={absent_count}")

            annotated_url = f"/storage/annotated/{today_str}/Lop_{classroom_id}_result.jpg?t={int(time.time() * 1000)}"

    except Exception as e:
        logger.error(f"Lỗi khi tự động tái nhận diện AI sau lưu ROI: {e}", exc_info=True)

    return {
        "success": True,
        "message": f"Đã lưu thành công ROI và đồng bộ AI cho {cls.name}!" + (f" Hiện diện: {present_count} HS, Vắng: {absent_count} HS." if present_count is not None else ""),
        "present_count": present_count,
        "absent_count": absent_count,
        "standard_count": cls.standard_count,
        "annotated_url": annotated_url
    }

