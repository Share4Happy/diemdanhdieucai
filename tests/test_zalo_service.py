import json
import pytest
from services.zalo_service import zalo_service
from database.db_session import init_db, SessionLocal
from database.models import AttendanceSession, AttendanceDetail, Classroom
from fastapi.testclient import TestClient
from app import app
from config.settings import settings

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

class FakeBotResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.content = json.dumps(payload).encode("utf-8")
    def json(self):
        return json.loads(self.content.decode("utf-8"))

def test_zalo_bot_api_builds_batch_payload(monkeypatch):
    """Kiểm tra URL, header x-api-key và body batch đúng theo API chuẩn."""
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return FakeBotResponse(200, {
            "success": True,
            "accepted": 2,
            "status": "completed",
            "results": [
                {"uid": "5002868751631677765", "status": "success"},
                {"uid": "1801874640219556137", "status": "success"}
            ]
        })

    monkeypatch.setattr("services.zalo_service.requests.post", fake_post)
    original = (settings.ZALO_BOT_API_BASE_URL, settings.ZALO_BOT_ID, settings.ZALO_BOT_API_KEY)
    settings.ZALO_BOT_API_BASE_URL = "http://localhost:3000/api/gateway/v1.0"
    settings.ZALO_BOT_ID = "BOT_1"
    settings.ZALO_BOT_API_KEY = "SECRET_API_KEY"
    try:
        res = zalo_service.send_via_bot_api(
            "Xin chào! Test từ API Batch.",
            recipients=[{"phone": "0334551531"}, {"phone": "0946734111"}]
        )
        assert res["success"] is True
        assert res["accepted"] == 2
        assert captured["url"].endswith("/bots/BOT_1/messages/send-batch")
        assert captured["headers"]["x-api-key"] == "SECRET_API_KEY"
        assert captured["json"]["mode"] == "safe"
        assert captured["json"]["content"] == {"type": "text", "data": {"text": "Xin chào! Test từ API Batch."}}
        assert captured["json"]["recipients"] == [
            {"phone": "0334551531"},
            {"phone": "0946734111"}
        ]
    finally:
        settings.ZALO_BOT_API_BASE_URL, settings.ZALO_BOT_ID, settings.ZALO_BOT_API_KEY = original

def test_zalo_bot_api_missing_config():
    original = (settings.ZALO_BOT_ID, settings.ZALO_BOT_API_KEY, settings.ZALO_BOT_API_BASE_URL)
    settings.ZALO_BOT_ID = ""
    settings.ZALO_BOT_API_KEY = ""
    settings.ZALO_BOT_API_BASE_URL = ""
    try:
        res = zalo_service.send_via_bot_api("test")
        assert res["success"] is False
        assert "Chưa cấu hình" in res["message"]
    finally:
        settings.ZALO_BOT_ID, settings.ZALO_BOT_API_KEY, settings.ZALO_BOT_API_BASE_URL = original

def test_zalo_bot_api_async_202(monkeypatch):
    """Batch 6-10 SĐT: gateway trả HTTP 202 + campaign_id, hệ thống phải xử lý bất đồng bộ."""
    monkeypatch.setattr("services.zalo_service.requests.post", lambda *a, **k: FakeBotResponse(202, {
        "campaign_id": "95379b1b-4170-abc",
        "total": 8,
        "status": "processing"
    }))
    original = (settings.ZALO_BOT_ID, settings.ZALO_BOT_API_KEY, settings.ZALO_BOT_API_BASE_URL, settings.ZALO_RECIPIENT_PHONES)
    settings.ZALO_BOT_ID = "BOT_1"
    settings.ZALO_BOT_API_KEY = "KEY"
    settings.ZALO_BOT_API_BASE_URL = "http://localhost:3000/api/gateway/v1.0"
    settings.ZALO_RECIPIENT_PHONES = "0334551531,0946734111,0330000001,0330000002,0330000003,0330000004"
    try:
        res = zalo_service.send_via_bot_api("test batch nền")
        assert res["success"] is True
        assert res["async"] is True
        assert res["campaign_ids"] == ["95379b1b-4170-abc"]
        assert res["chunks"] == 1
    finally:
        settings.ZALO_BOT_ID, settings.ZALO_BOT_API_KEY, settings.ZALO_BOT_API_BASE_URL, settings.ZALO_RECIPIENT_PHONES = original

def test_zalo_bot_api_chunks_more_than_10(monkeypatch):
    """25 SĐT → tự chia 3 đợt (10 + 10 + 5): 2 campaign nền + 1 đồng bộ."""
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        size = len(json["recipients"])
        calls.append(size)
        if size == 10:
            return FakeBotResponse(202, {"campaign_id": f"campaign_{len(calls)}", "total": size, "status": "processing"})
        return FakeBotResponse(200, {
            "success": True,
            "accepted": size,
            "status": "completed",
            "results": [{"uid": f"uid_{i}", "status": "success"} for i in range(size)]
        })

    monkeypatch.setattr("services.zalo_service.requests.post", fake_post)
    original = (settings.ZALO_BOT_ID, settings.ZALO_BOT_API_KEY, settings.ZALO_BOT_API_BASE_URL, settings.ZALO_RECIPIENT_PHONES)
    settings.ZALO_BOT_ID = "BOT_1"
    settings.ZALO_BOT_API_KEY = "KEY"
    settings.ZALO_BOT_API_BASE_URL = "http://localhost:3000/api/gateway/v1.0"
    phones = ",".join(f"03300000{i:02d}" for i in range(25))
    settings.ZALO_RECIPIENT_PHONES = phones
    try:
        res = zalo_service.send_via_bot_api("test 25 SĐT")
        # Mỗi đợt phải <= 10 SĐT
        assert all(s <= 10 for s in calls)
        assert sum(calls) == 25
        assert calls == [10, 10, 5]
        assert res["success"] is True
        assert res["chunks"] == 3
        assert len(res["campaign_ids"]) == 2  # 2 đợt nền
        assert res["accepted"] == 5           # 1 đợt đồng bộ cuối
        assert len(res["results"]) == 5
    finally:
        settings.ZALO_BOT_ID, settings.ZALO_BOT_API_KEY, settings.ZALO_BOT_API_BASE_URL, settings.ZALO_RECIPIENT_PHONES = original

def test_zalo_bot_api_save_endpoint():
    res = client.post("/api/reports/save-zalo-config", json={
        "enabled": True,
        "notification_type": "BOT_API",
        "bot_api_base_url": "http://localhost:3000/api/gateway/v1.0",
        "bot_id": "BOT_SAVE_TEST",
        "bot_api_key": "KEY_SAVE_TEST",
        "recipient_phones": "0334551531"
    })
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert settings.ZALO_BOT_ID == "BOT_SAVE_TEST"
    assert settings.ZALO_BOT_API_KEY == "KEY_SAVE_TEST"

def test_zalo_status_includes_bot_api():
    res = client.get("/api/reports/zalo-status")
    assert res.status_code == 200
    data = res.json()
    assert "bot_configured" in data
    assert "bot_id" in data
    assert "bot_api_key_masked" in data
    assert "recipient_phones" in data
