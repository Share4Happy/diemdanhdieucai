"""
Unit tests cho các tính năng nâng cấp:
1. Wizard kiểm định 5 bước thêm camera mới (validate_new_camera_wizard).
2. Phát hiện ảnh đóng băng (Frozen Frame Detection - chống camera/NVR treo hình).
3. Kiểm tra quá hạn TTL ảnh latest (is_image_stale).
4. Tăng cứng an ninh validate_stream_source.
5. Cảnh báo remap IP NVR trong rtsp_client.
"""
import pytest
import time
import uuid
import numpy as np
import cv2
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from config.settings import settings
from backend.main import app
from backend.api.security import validate_stream_source
from backend.core.rtsp_client import rtsp_client
from backend.core.attendance_engine import AttendanceEngine
from database.db_session import SessionLocal
from database.models import Classroom, AttendanceSession, AttendanceDetail, User

client = TestClient(app)


def get_admin_headers():
    db = SessionLocal()
    admin = db.query(User).filter(User.role == "admin").first()
    email = admin.email if admin else "admin@truongdieucai.edu.vn"
    db.close()
    res = client.post("/api/auth/login", json={"email": email, "password": "Admin@2025"})
    assert res.status_code == 200
    token = res.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


def test_validate_new_camera_wizard():
    """Kiểm tra Wizard 5 bước thêm camera mới: kết nối, 5 frame, độ phân giải, ROI, AI dry-run."""
    headers = get_admin_headers()

    # Tạo frame giả lập Full HD có kết cấu
    mock_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    for x in range(100, 1800, 150):
        cv2.circle(mock_frame, (x, 500), 25, (255, 200, 150), -1)

    mock_sample_res = {
        "success": True,
        "requested_count": 5,
        "frames_read": 5,
        "avg_latency_ms": 45.2,
        "total_elapsed_ms": 250.0,
        "resolution": "1920x1080",
        "width": 1920,
        "height": 1080,
        "best_sharpness": 35.8,
        "best_frame": mock_frame,
        "frames": [mock_frame] * 5
    }

    mock_conn_res = {
        "success": True,
        "latency_ms": 32,
        "message": "Kết nối thành công"
    }

    mock_detector_result = (
        12,  # 12 học sinh
        [{"confidence": 0.88, "bbox": [100, 480, 140, 520]}] * 12,
        mock_frame
    )

    with patch.object(rtsp_client, "test_camera_stream", return_value=mock_conn_res):
        with patch.object(rtsp_client, "capture_sample_frames", return_value=mock_sample_res):
            with patch("backend.core.detector.detector.detect_students_in_classroom", return_value=mock_detector_result):
                res = client.post(
                    "/api/cameras/validate-new-camera",
                    json={
                        "source_url": "rtsp://192.168.1.200:554/Streaming/Channels/101",
                        "relay_ip": "192.168.1.200",
                        "standard_count": 40
                    },
                    headers=headers
                )
                assert res.status_code == 200
                data = res.json()
                assert data["success"] is True
                assert data["ready_for_save"] is True
                assert data["step1_connection"]["ok"] is True
                assert data["step2_frames"]["ok"] is True
                assert data["step2_frames"]["frames_read"] == 5
                assert data["step3_resolution"]["ok"] is True
                assert data["step3_resolution"]["resolution"] == "1920x1080"
                assert data["step4_roi"]["ok"] is True
                assert "preview_url" in data["step4_roi"]
                assert data["step5_ai"]["ok"] is True
                assert data["step5_ai"]["students_detected"] == 12


def test_frozen_frame_detection():
    """Kiểm tra thuật toán phát hiện ảnh đóng băng (Frozen Frame Detection) qua MSE."""
    db = SessionLocal()
    # Tìm hoặc tạo lớp học test
    cls = db.query(Classroom).filter(Classroom.code == "LOP_FROZEN_TEST").first()
    if not cls:
        cls = Classroom(
            code="LOP_FROZEN_TEST",
            name="Lớp Test Đóng Băng",
            room_number="Phòng 999",
            standard_count=40,
            rtsp_url="rtsp://192.168.1.200:554/cam/test",
            is_active=True
        )
        db.add(cls)
        db.commit()
        db.refresh(cls)

    # Tạo ảnh mẫu giống hệt nhau
    temp_dir = settings.CAPTURES_DIR / "test_frozen"
    temp_dir.mkdir(parents=True, exist_ok=True)
    frozen_img_path = str(temp_dir / f"test_frozen_{uuid.uuid4().hex[:6]}.jpg")

    mock_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    cv2.circle(mock_img, (500, 500), 100, (255, 128, 64), -1)
    cv2.imwrite(frozen_img_path, mock_img)

    # Tạo phiên điểm danh cũ có lưu ảnh này
    old_sess = AttendanceSession(
        session_code=f"SESS_PREV_{uuid.uuid4().hex[:6]}",
        scan_date="2026-10-12",
        scan_time="06:45:00",
        total_classes=1,
        status="COMPLETED"
    )
    db.add(old_sess)
    db.commit()
    db.refresh(old_sess)

    cls_id = cls.id
    cls_name = cls.name

    old_detail = AttendanceDetail(
        session_id=old_sess.id,
        classroom_id=cls_id,
        standard_count=40,
        present_count=35,
        absent_count=5,
        raw_image_path=frozen_img_path,
        status="OK"
    )
    db.add(old_detail)
    db.commit()
    db.close()

    # Chạy AttendanceEngine với ảnh frame hiện tại giống hệt frame cũ
    engine = AttendanceEngine()

    mock_capture_results = {
        cls_id: {
            "classroom_id": cls_id,
            "classroom_name": cls_name,
            "success": True,
            "image_path": frozen_img_path,
            "frame": mock_img.copy()
        }
    }

    with patch.object(rtsp_client, "capture_all_classrooms", return_value=mock_capture_results):
        # Chạy daily attendance
        res = engine.run_daily_attendance(trigger_led=False)
        assert res["success"] is True

        # Kiểm tra trạng thái trong DB: phải là CAN_KIEM_TRA và ghi chú ảnh đóng băng
        db_chk = SessionLocal()
        sess_chk = db_chk.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()
        det_chk = db_chk.query(AttendanceDetail).filter(
            AttendanceDetail.session_id == sess_chk.id,
            AttendanceDetail.classroom_id == cls_id
        ).first()

        assert det_chk is not None
        assert det_chk.status == "CAN_KIEM_TRA"
        assert "đóng băng" in det_chk.notes.lower()
        db_chk.close()


def test_is_image_stale():
    """Kiểm tra cơ chế TTL (Time-To-Live) của file ảnh latest."""
    test_cls_id = 99999
    latest_img = settings.CAPTURES_DIR / "latest" / f"Lop_{test_cls_id}.jpg"
    latest_meta = settings.CAPTURES_DIR / "latest" / f"Lop_{test_cls_id}.meta.json"
    latest_img.parent.mkdir(parents=True, exist_ok=True)

    # Tạo ảnh và metadata vừa mới chụp
    dummy = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(latest_img), dummy)

    import json
    with open(latest_meta, "w", encoding="utf-8") as f:
        json.dump({"captured_at_ts": time.time(), "status": "OK"}, f)

    is_stale, age = rtsp_client.is_image_stale(test_cls_id, max_age_seconds=10.0)
    assert is_stale is False
    assert age < 5.0

    # Giả lập metadata cũ quá 2 giờ (7300s)
    with open(latest_meta, "w", encoding="utf-8") as f:
        json.dump({"captured_at_ts": time.time() - 7300.0, "status": "OK"}, f)

    is_stale_old, age_old = rtsp_client.is_image_stale(test_cls_id, max_age_seconds=7200.0)
    assert is_stale_old is True
    assert age_old >= 7200.0

    # Dọn dẹp file test
    try:
        latest_img.unlink(missing_ok=True)
        latest_meta.unlink(missing_ok=True)
    except Exception:
        pass


def test_validate_stream_source_security():
    """Kiểm tra tăng cứng an ninh của validate_stream_source chống LFI & SSRF."""
    # 1. file:// phải bị chặn
    with pytest.raises(HTTPException) as exc:
        validate_stream_source("file:///etc/passwd")
    assert exc.value.status_code == 400

    # 2. Loopback 127.0.0.1 bị chặn
    with pytest.raises(HTTPException) as exc:
        validate_stream_source("rtsp://admin:123@127.0.0.1:554/cam")
    assert exc.value.status_code == 400

    # 3. Link-local 169.254.169.254 bị chặn
    with pytest.raises(HTTPException) as exc:
        validate_stream_source("rtsp://169.254.169.254:554/live")
    assert exc.value.status_code == 400

    # 4. Khi DEBUG=False: chặn đường dẫn file media cục bộ và webcam 0
    with patch.object(settings, "DEBUG", False):
        with pytest.raises(HTTPException) as exc:
            validate_stream_source("0")
        assert exc.value.status_code == 400

        with pytest.raises(HTTPException) as exc:
            validate_stream_source("dataset/samples/sample.mp4")
        assert exc.value.status_code == 400

    # 5. IP LAN hợp lệ được thông qua
    validate_stream_source("rtsp://admin:pass@192.168.1.200:554/live")
    validate_stream_source("rtsp://10.0.0.15:554/Streaming/Channels/101")
