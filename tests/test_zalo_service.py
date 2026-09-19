import pytest
from services.zalo_service import zalo_service
from database.db_session import init_db, SessionLocal
from database.models import AttendanceSession, AttendanceDetail, Classroom
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield

def test_zalo_format_message():
    db = SessionLocal()
    # Tạo một phiên điểm danh mẫu để test
    session = AttendanceSession(
        session_code="TEST_SESSION_ZALO",
        scan_date="2026-09-18",
        scan_time="06:45:00",
        total_classes=2,
        total_standard=80,
        total_present=78,
        total_absent=2,
        status="COMPLETED"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    cls1 = db.query(Classroom).first()
    detail = AttendanceDetail(
        session_id=session.id,
        classroom_id=cls1.id,
        standard_count=40,
        present_count=38,
        absent_count=2
    )
    db.add(detail)
    db.commit()

    msg = zalo_service.format_attendance_message(session.id)
    assert "[THPT ĐIỀU CẢI] BÁO CÁO ĐIỂM DANH SĨ SỐ" in msg
    assert "78/80" in msg
    assert "Vắng 2 em" in msg

    # Dọn dẹp
    db.delete(detail)
    db.delete(session)
    db.commit()
    db.close()

def test_zalo_status_endpoint():
    res = client.get("/api/reports/zalo-status")
    assert res.status_code == 200
    data = res.json()
    assert "enabled" in data
    assert "notification_type" in data

def test_zalo_send_simulation_endpoint():
    res = client.post("/api/reports/send-zalo", json={
        "target_type": "WEBHOOK",
        "webhook_url": "" # Rỗng để test fallback mô phỏng
    })
    assert res.status_code == 200
    data = res.json()
    assert "message" in data
