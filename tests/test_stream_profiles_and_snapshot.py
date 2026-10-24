import pytest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

try:
    from backend.app.main import app
    from backend.app.api.deps import get_current_user, require_admin
    from backend.app.core.rtsp_client import rtsp_client
except ModuleNotFoundError:
    from main import app
    from api.deps import get_current_user, require_admin
    from core.rtsp_client import rtsp_client

from database.models import User, Classroom
from database.db_session import SessionLocal
from config.settings import settings

admin_user = User(id=1, email="admin@truongdieucai.edu.vn", role="admin", is_active=True, full_name="Admin")

@pytest.fixture(autouse=True)
def setup_auth():
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[require_admin] = lambda: admin_user
    yield

client = TestClient(app)

def test_fetch_http_snapshot_rejects_low_res_for_main_stream():
    """Kiểm tra _fetch_http_snapshot từ chối ảnh D1 (704x576) khi luồng yêu cầu là Luồng Chính."""
    np.random.seed(42)
    low_res_d1 = np.random.randint(30, 220, (576, 704, 3), dtype=np.uint8)

    with patch("requests.get") as mock_get, \
         patch.object(rtsp_client, "is_host_reachable", return_value=True):
        
        _, buf = cv2.imencode(".jpg", low_res_d1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = buf.tobytes()
        mock_get.return_value = mock_resp

        # 1. Luồng chính (kết thúc 01): Phải từ chối D1 704x576 và trả về None để ép sang RTSP
        main_url = "rtsp://admin:pass@192.168.1.200:554/Streaming/Channels/101"
        res_main = rtsp_client._fetch_http_snapshot(main_url)
        assert res_main is None, "Phải từ chối ảnh D1 704x576 cho Luồng Chính!"

        # 2. Luồng phụ (kết thúc 02): Được phép chấp nhận D1/VGA
        sub_url = "rtsp://admin:pass@192.168.1.200:554/Streaming/Channels/102"
        res_sub = rtsp_client._fetch_http_snapshot(sub_url)
        assert res_sub is not None, "Được phép nhận ảnh D1 cho Luồng Phụ!"
        assert res_sub.shape == (576, 704, 3)

def test_fetch_http_snapshot_accepts_1080p_for_main_stream():
    """Kiểm tra _fetch_http_snapshot chấp nhận nếu ảnh trả về đạt chuẩn Full HD 1080P."""
    sample_file = settings.SAMPLES_DIR / "classroom_sample_1.jpg"
    if sample_file.exists():
        fhd = cv2.imread(str(sample_file))
    else:
        fhd = np.zeros((1080, 1920, 3), dtype=np.uint8)
        fhd[:540, :] = (200, 50, 50)
        fhd[540:, :] = (50, 200, 50)
        cv2.circle(fhd, (960, 540), 200, (255, 255, 0), -1)

    with patch("requests.get") as mock_get, \
         patch.object(rtsp_client, "is_host_reachable", return_value=True):
        
        _, buf = cv2.imencode(".jpg", fhd)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = buf.tobytes()
        mock_get.return_value = mock_resp

        main_url = "rtsp://admin:pass@192.168.1.200:554/Streaming/Channels/101"
        res = rtsp_client._fetch_http_snapshot(main_url)
        assert res is not None
        assert res.shape == (1080, 1920, 3)

def test_get_stream_profiles_api():
    """Kiểm tra API /api/cameras/stream-profiles trả về đúng cấu trúc và codec H.265."""
    resp = client.get("/api/cameras/stream-profiles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "kpi" in data
    assert "cameras" in data
    assert len(data["cameras"]) > 0
    # Codec mặc định phải là H.265 theo chuẩn đầu ghi
    assert data["cameras"][0]["codec"] == "H.265"
