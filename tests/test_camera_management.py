import pytest
from fastapi.testclient import TestClient
from app import app
from database.db_session import init_db, SessionLocal
from database.models import Classroom, ROIPolygon
from config.settings import settings

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    yield

def test_get_cameras_list():
    response = client.get("/api/cameras")
    assert response.status_code == 200
    data = response.json()
    assert "cameras" in data
    assert len(data["cameras"]) >= 1
    
    first_cam = data["cameras"][0]
    assert "code" in first_cam
    assert "name" in first_cam
    assert "rtsp_url" in first_cam
    assert "source_type" in first_cam

def test_create_and_delete_camera():
    # 1. Thêm camera test
    new_cam_data = {
        "code": "CAM_TEST_UNIT_01",
        "name": "Lớp Test Phòng Nghiên Cứu",
        "room_number": "Lab 401",
        "standard_count": 35,
        "rtsp_url": "0", # Dạng webcam
        "relay_ip": "192.168.10.250",
        "is_active": True
    }
    create_res = client.post("/api/cameras", json=new_cam_data)
    assert create_res.status_code == 200
    res_json = create_res.json()
    assert res_json["success"] is True
    cam_id = res_json["camera_id"]
    assert cam_id is not None

    # Kiểm tra camera có trong CSDL và có kèm ROI mặc định
    db = SessionLocal()
    cls = db.query(Classroom).filter(Classroom.id == cam_id).first()
    assert cls is not None
    assert cls.name == "Lớp Test Phòng Nghiên Cứu"
    assert cls.roi is not None
    assert len(cls.roi.red_zone) == 4
    db.close()

    # 2. Cập nhật thông tin camera
    update_res = client.put(f"/api/cameras/{cam_id}", json={
        "name": "Lớp Test Đã Đổi Tên",
        "standard_count": 38
    })
    assert update_res.status_code == 200
    assert update_res.json()["success"] is True

    # 3. Xóa camera
    del_res = client.delete(f"/api/cameras/{cam_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Xác nhận đã bị xóa khỏi DB
    db = SessionLocal()
    cls_after = db.query(Classroom).filter(Classroom.id == cam_id).first()
    assert cls_after is None
    db.close()

def test_camera_connection_with_mock_file():
    # Kiểm tra test connection với 1 file ảnh có sẵn trong dataset
    sample_file = settings.SAMPLES_DIR / "classroom_sample_1.jpg"
    test_res = client.post("/api/cameras/test-connection", json={
        "source_url": str(sample_file)
    })
    assert test_res.status_code == 200
    data = test_res.json()
    assert data["success"] is True
    assert "latency_ms" in data
    assert data["source_type"] == "IMAGE_FILE"
    assert data["preview_url"].startswith("data:image/jpeg;base64,")

def test_cameras_page_route():
    response = client.get("/cameras")
    assert response.status_code == 200
    assert "QUẢN LÝ CAMERA" in response.text

def test_get_available_webcams():
    response = client.get("/api/cameras/available-webcams")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "webcams" in data
    assert "count" in data
    assert isinstance(data["webcams"], list)
    if len(data["webcams"]) > 0:
        first_cam = data["webcams"][0]
        assert "id" in first_cam
        assert "index" in first_cam
        assert "name" in first_cam
        assert "resolution" in first_cam
