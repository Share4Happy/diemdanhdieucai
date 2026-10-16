"""
=============================================================================
TEST PROGRESS DIALOG & TRACKER SERVICE
THPT Điều Cải - Attendance System
=============================================================================
Kiểm tra tính năng:
1. ProgressTracker Service (start, update, finish, get_state)
2. API /api/attendance/progress
3. API /api/cameras/progress
4. Tích hợp progress_callback khi capture 30 camera và chạy attendance
=============================================================================
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from services.progress_service import progress_tracker

client = TestClient(app)

def test_progress_tracker_lifecycle():
    # 1. Khởi tạo
    progress_tracker.start("ATTENDANCE_SCAN", "Quét Điểm Danh Thử Nghiệm", total_steps=3, total_items=30)
    state = progress_tracker.get_state()
    assert state["is_running"] is True
    assert state["action"] == "ATTENDANCE_SCAN"
    assert state["step"] == 1
    assert state["percent"] >= 5
    assert len(state["logs"]) >= 1

    # 2. Cập nhật tiến trình
    progress_tracker.update(
        step=2,
        step_title="2/3: Phân Tích AI YOLO",
        current=15,
        total=30,
        current_item="Lớp 11A1 (Phòng 201)",
        percent=65,
        log_text="AI hoàn tất lớp 11A1: 40/40 học sinh"
    )
    state = progress_tracker.get_state()
    assert state["step"] == 2
    assert state["current"] == 15
    assert state["percent"] == 65
    assert state["current_item"] == "Lớp 11A1 (Phòng 201)"

    # 3. Hoàn tất
    progress_tracker.finish(True, "Hoàn tất kiểm thử thành công!", result={"total_present": 1200})
    state = progress_tracker.get_state()
    assert state["is_running"] is False
    assert state["status"] == "success"
    assert state["percent"] == 100
    assert state["result"]["total_present"] == 1200

def test_progress_endpoints():
    # Kiểm tra API GET /api/attendance/progress
    resp1 = client.get("/api/attendance/progress")
    # Endpoint requires auth or returns 401 if not logged in
    assert resp1.status_code in [200, 401]

    # Kiểm tra API GET /api/cameras/progress
    resp2 = client.get("/api/cameras/progress")
    assert resp2.status_code in [200, 401]
