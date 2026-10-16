import pytest
from fastapi.testclient import TestClient
from backend.main import app
from database.models import User
from backend.api.deps import require_admin, get_current_user

app.dependency_overrides[require_admin] = lambda: User(id=1, email="admin@truongdieucai.edu.vn", role="admin")
app.dependency_overrides[get_current_user] = lambda: User(id=1, email="admin@truongdieucai.edu.vn", role="admin")

client = TestClient(app)

def test_mock_video_in_wizard():
    res = client.post("/api/cameras/validate-new-camera", json={
        "source_url": "storage/mock_classroom_lop1.mp4",
        "standard_count": 40
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["ready_for_save"] is True
    assert data["step1_connection"]["ok"] is True
    assert data["step2_frames"]["ok"] is True
    assert data["step3_resolution"]["ok"] is True
    assert data["step4_roi"]["ok"] is True
    assert data["step5_ai"]["ok"] is True
    print("\n--- KET QUA WIZARD KIEM DINH VIDEO AO ---")
    print("Step 1 (Ket noi):", data["step1_connection"]["message"])
    print("Step 2 (Frames doc duoc):", data["step2_frames"]["frames_read"])
    print("Step 3 (Do phan giai):", data["step3_resolution"]["resolution"], "- Sharpness:", data["step3_resolution"]["sharpness"])
    print("Step 4 (Vung ROI): OK")
    print("Step 5 (Ket qua AI):", data["step5_ai"]["students_detected"], "hoc sinh phat hien")
    assert data["step5_ai"]["annotated_preview_url"].startswith("data:image/jpeg;base64,")
