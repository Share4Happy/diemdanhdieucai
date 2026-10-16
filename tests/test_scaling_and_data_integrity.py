import pytest
import uuid
import numpy as np
import cv2
from fastapi.testclient import TestClient
from backend.main import app
from database.db_session import init_db, SessionLocal
from database.models import Classroom, AttendanceSession, AttendanceDetail, User
from backend.core.rtsp_client import rtsp_client, is_valid_frame
from backend.api.deps import get_current_user

app.dependency_overrides[get_current_user] = lambda: User(id=1, email="admin@truongdieucai.edu.vn", role="admin")
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db(force_seed_classes=True)
    yield

def test_per_nvr_semaphore_registry():
    # Kiểm tra registry Semaphore tạo đúng và tách biệt theo từng host
    sem1 = rtsp_client._get_nvr_semaphore("192.168.1.200")
    sem2 = rtsp_client._get_nvr_semaphore("192.168.1.201")
    sem1_again = rtsp_client._get_nvr_semaphore("192.168.1.200")

    assert sem1 is sem1_again
    assert sem1 is not sem2
    assert sem1._value == 3

def test_http_snapshot_probe_mock(monkeypatch):
    # Tạo ảnh có cấu trúc không gian lớp học để vượt qua bộ lọc is_valid_frame
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    img[:, :] = (180, 160, 140)
    cv2.rectangle(img, (100, 100), (600, 500), (40, 40, 180), -1)
    cv2.rectangle(img, (700, 100), (1200, 500), (180, 80, 40), -1)
    cv2.putText(img, "THPT DIEU CAI CAM 01", (150, 300), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)

    class MockResponse:
        status_code = 200
        content = cv2.imencode('.jpg', img)[1].tobytes()

    import requests
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: MockResponse())
    monkeypatch.setattr(rtsp_client, "is_host_reachable", lambda *args, **kwargs: True)

    frame = rtsp_client._fetch_http_snapshot("rtsp://admin:pass@192.168.1.200:554/Streaming/Channels/101")
    assert frame is not None
    assert is_valid_frame(frame) is True

def test_manual_override_api_audit_trail():
    db = SessionLocal()
    unique_code = f"SESSION_OVERRIDE_{uuid.uuid4().hex[:8]}"
    session = AttendanceSession(
        session_code=unique_code,
        scan_date="2026-10-13",
        scan_time="10:00:00",
        total_classes=1,
        total_standard=45,
        total_present=40,
        total_absent=5,
        status="COMPLETED"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    sess_id = session.id

    cls = db.query(Classroom).first()
    detail = AttendanceDetail(
        session_id=sess_id,
        classroom_id=cls.id,
        standard_count=45,
        present_count=40,
        absent_count=5,
        status="OK"
    )
    db.add(detail)
    db.commit()
    db.refresh(detail)
    detail_id = detail.id
    db.close()

    # Thực hiện override qua API
    response = client.put(f"/api/attendance/details/{detail_id}/override", json={
        "present_count": 43,
        "reason": "Học sinh vào lớp muộn 5 phút do xe hỏng"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["detail"]["present_count"] == 43
    assert data["detail"]["absent_count"] == 2
    assert data["detail"]["is_manual_override"] is True
    assert data["detail"]["override_by"] == "admin@truongdieucai.edu.vn"
    assert data["detail"]["override_reason"] == "Học sinh vào lớp muộn 5 phút do xe hỏng"
    assert data["detail"]["override_at"] is not None

    # Kiểm tra database cập nhật đúng và đồng bộ session cha
    db = SessionLocal()
    updated_d = db.query(AttendanceDetail).filter(AttendanceDetail.id == detail_id).first()
    assert updated_d.present_count == 43
    assert updated_d.absent_count == 2
    assert updated_d.is_manual_override is True
    assert updated_d.override_by == "admin@truongdieucai.edu.vn"

    updated_s = db.query(AttendanceSession).filter(AttendanceSession.id == sess_id).first()
    assert updated_s.total_present == 43
    assert updated_s.total_absent == 2
    db.close()

def test_trend_7days_no_fake_random():
    response = client.get("/api/attendance/trend-7days")
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert len(data["days"]) == 7

    for d in data["days"]:
        if not d["is_actual"]:
            assert d["present"] == 0
            assert d["absent"] == 0
            assert d["rate"] == 0.0

def test_get_session_by_id():
    db = SessionLocal()
    unique_code = f"SESSION_GET_{uuid.uuid4().hex[:8]}"
    session = AttendanceSession(
        session_code=unique_code,
        scan_date="2026-10-13",
        scan_time="10:30:00",
        total_classes=1,
        total_standard=45,
        total_present=42,
        total_absent=3,
        status="COMPLETED"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    s_id = session.id
    db.close()

    response = client.get(f"/api/attendance/sessions/{s_id}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["session"]["id"] == s_id
    assert res_data["session"]["session_code"] == unique_code
