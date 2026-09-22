import pytest
from fastapi.testclient import TestClient
from backend.main import app
from services.nvr_service import nvr_service
from database.db_session import SessionLocal, init_db
from backend.api.deps import get_current_user
from database.models import User

app.dependency_overrides[get_current_user] = lambda: User(id=1, email="admin@truongdieucai.edu.vn", role="admin")

client = TestClient(app)

def setup_module():
    init_db()

def test_nvr_service_build_rtsp_url():
    # 1. Dahua
    url_dahua = nvr_service.build_rtsp_url("DAHUA", "192.168.10.200", 554, "admin", "Lhu@2025", 1, 0)
    assert "rtsp://admin:Lhu%402025@192.168.10.200:554/cam/realmonitor?channel=1&subtype=0" in url_dahua

    # 2. Hikvision
    url_hik = nvr_service.build_rtsp_url("HIKVISION", "192.168.10.201", 554, "admin", "123456", 5, 0)
    assert "rtsp://admin:123456@192.168.10.201:554/Streaming/Channels/501" in url_hik

    # 3. Uniview
    url_unv = nvr_service.build_rtsp_url("UNIVIEW", "192.168.10.202", 554, "admin", "pass", 10, 0)
    assert "rtsp://admin:pass@192.168.10.202:554/unicast/c10/s0/live" in url_unv

def test_nvr_probe_endpoint():
    payload = {
        "ip_address": "192.168.10.200",
        "rtsp_port": 554,
        "username": "admin",
        "password": "Lhu@2025",
        "brand": "DAHUA",
        "channels_count": 30,
        "naming_mode": "DEFAULT_30_CLASSES"
    }
    response = client.post("/api/cameras/nvr/probe", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_channels"] == 30
    assert len(data["channels"]) == 30
    # Kênh 1 phải là 10A1
    ch1 = data["channels"][0]
    assert ch1["channel"] == 1
    assert "10A1" in ch1["name"]
    assert ch1["thumbnail"].startswith("data:image/jpeg;base64,")

def test_nvr_batch_import_and_independent_crud():
    # 1. Quét trước để có danh sách channels
    probe_resp = client.post("/api/cameras/nvr/probe", json={
        "ip_address": "192.168.10.200",
        "channels_count": 30
    })
    channels = probe_resp.json()["channels"]

    # 2. Batch import 30 channels
    import_payload = {
        "nvr_name": "Đầu Ghi NVR Trường Điều Cải 30 Kênh",
        "ip_address": "192.168.10.200",
        "rtsp_port": 554,
        "username": "admin",
        "password": "Lhu@2025",
        "brand": "DAHUA",
        "channels_count": 30,
        "replace_existing": True,
        "channels": channels
    }
    import_resp = client.post("/api/cameras/nvr/batch-import", json=import_payload)
    assert import_resp.status_code == 200
    import_data = import_resp.json()
    assert import_data["success"] is True
    assert import_data["imported_count"] == 30

    # 3. Kiểm tra danh sách cameras sau khi import đủ 30 camera
    all_cams_resp = client.get("/api/cameras")
    assert all_cams_resp.status_code == 200
    cams = all_cams_resp.json()["cameras"]
    assert len(cams) == 30
    first_cam = cams[0]
    first_cam_id = first_cam["id"]

    # 4. KIỂM TRA CHỈNH SỬA ĐỘC LẬP TỪNG CAMERA
    # Người dùng sửa riêng camera thứ 1 thành "Phòng Thực Hành Tin Học" và sĩ số 35
    edit_resp = client.put(f"/api/cameras/{first_cam_id}", json={
        "name": "Phòng Thực Hành Tin Học",
        "standard_count": 35
    })
    assert edit_resp.status_code == 200
    
    # Xác nhận camera thứ 1 đã đổi, các camera khác giữ nguyên
    check_cam_resp = client.get("/api/cameras")
    updated_cams = check_cam_resp.json()["cameras"]
    cam_1 = next(c for c in updated_cams if c["id"] == first_cam_id)
    assert cam_1["name"] == "Phòng Thực Hành Tin Học"
    assert cam_1["standard_count"] == 35
    # Camera thứ 2 vẫn là 10A2
    cam_2 = next(c for c in updated_cams if c["id"] != first_cam_id)
    assert "10A" in cam_2["name"]

    # 5. KIỂM TRA XÓA ĐỘC LẬP TỪNG CAMERA
    # Xóa riêng lẻ camera thứ 1
    del_resp = client.delete(f"/api/cameras/{first_cam_id}")
    assert del_resp.status_code == 200

    # Danh sách bây giờ còn đúng 29 camera
    after_del_resp = client.get("/api/cameras")
    remaining_cams = after_del_resp.json()["cameras"]
    assert len(remaining_cams) == 29
    assert not any(c["id"] == first_cam_id for c in remaining_cams)

def test_matrix_wall_endpoint():
    resp = client.get("/api/cameras/matrix-wall")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "cameras" in data
