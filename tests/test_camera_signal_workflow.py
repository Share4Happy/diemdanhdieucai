import pytest
import time
from fastapi.testclient import TestClient
from backend.main import app
from database.db_session import init_db, SessionLocal
from database.models import Classroom, AttendanceSession, AttendanceDetail, User
from core.relay_service import relay_service
from core.attendance_engine import attendance_engine

from backend.api.deps import get_current_user

app.dependency_overrides[get_current_user] = lambda: User(id=1, email="admin@truongdieucai.edu.vn", role="admin")

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    yield

def test_parse_camera_info():
    # 1. Dahua RTSP URL
    dahua_url = "rtsp://admin:L288AF23@192.168.100.194:554/cam/realmonitor?channel=2&subtype=0"
    info = relay_service.parse_camera_info({"rtsp_url": dahua_url, "name": "Lớp 12A1"})
    assert info["host"] == "192.168.100.194"
    assert info["username"] == "admin"
    assert info["password"] == "L288AF23"
    assert info["channel"] == 2
    assert info["brand"] == "DAHUA"
    assert info["is_network_camera"] is True

    # 2. Hikvision RTSP URL
    hik_url = "rtsp://admin:pass123@192.168.1.105:554/Streaming/Channels/101"
    info_hik = relay_service.parse_camera_info({"rtsp_url": hik_url, "name": "Lớp 10A1"})
    assert info_hik["host"] == "192.168.1.105"
    assert info_hik["brand"] == "HIKVISION"

    # 3. Local Webcam
    info_cam = relay_service.parse_camera_info({"rtsp_url": "0", "name": "Webcam 0"})
    assert info_cam["is_network_camera"] is False

def test_signal_classrooms_before_capture():
    mock_classes = [
        {"id": 1, "name": "Lớp Test 1", "rtsp_url": "0"},
        {"id": 2, "name": "Lớp Test 2", "rtsp_url": "rtsp://admin:123@127.0.0.1:554/cam/realmonitor?channel=1"}
    ]
    # Báo hiệu 0s để test chạy nhanh
    res = relay_service.signal_classrooms_before_capture(mock_classes, signal_seconds=0, capture_color=True)
    assert res["success"] is True
    assert res["classes_count"] == 2
    assert res["capture_color"] is True

def test_restore_classrooms_auto():
    mock_classes = [{"id": 1, "name": "Lớp Test 1", "rtsp_url": "0"}]
    # Không ném ngoại lệ
    relay_service.restore_classrooms_auto(mock_classes)

def test_api_test_connection_with_trigger_signal():
    response = client.post("/api/cameras/test-connection", json={
        "source_url": "dataset/samples/classroom_sample_1.jpg",
        "trigger_signal": True
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Đã kích hoạt đèn hồng ngoại báo hiệu" in data["message"]
    assert data["preview_url"].startswith("data:image/jpeg;base64,")

def test_api_test_ir_by_url():
    response = client.post("/api/cameras/test-ir-by-url", json={
        "source_url": "rtsp://admin:L288AF23@192.168.100.194:554/cam/realmonitor?channel=1&subtype=0",
        "relay_ip": "192.168.100.194"
    })
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data

def test_api_test_classroom_ir():
    db = SessionLocal()
    first_cls = db.query(Classroom).first()
    db.close()
    if first_cls:
        response = client.post(f"/api/cameras/{first_cls.id}/test-ir", json={
            "duration_seconds": 1,
            "mode": "IR_ON"
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "hồng ngoại" in data["message"]

def test_attendance_engine_signal_and_color_capture():
    db = SessionLocal()
    # Chỉ bật 1 lớp để test chạy nhanh
    db.query(Classroom).update({Classroom.is_active: False})
    c = db.query(Classroom).first()
    if c:
        c.is_active = True
        db.commit()
    db.close()

    result = attendance_engine.run_daily_attendance(trigger_led=True)
    assert result["success"] is True
    assert result["total_classes"] >= 1
    assert result["total_standard"] > 0

    # Khôi phục bật lại lớp
    db = SessionLocal()
    db.query(Classroom).update({Classroom.is_active: True})
    db.commit()
    db.close()
