"""
Kiểm thử tự động cho endpoint /api/predict (Depth-NMS Predict)
Kiểm tra các trường hợp:
1. File sai định dạng (.txt) -> 400 Bad Request
2. File rỗng (0 bytes) -> 400 Bad Request
3. File hỏng -> 400 Bad Request
4. File ảnh hợp lệ -> 200 OK với đúng schema PredictResponse
"""
import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_predict_invalid_file_type():
    file_content = b"Not an image content"
    files = {"image": ("test.txt", io.BytesIO(file_content), "text/plain")}
    response = client.post("/api/predict", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "Invalid file type" in data["detail"]

def test_predict_empty_file():
    files = {"image": ("empty.png", io.BytesIO(b""), "image/png")}
    response = client.post("/api/predict", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "Uploaded file is empty" in data["detail"]

def test_predict_corrupted_image():
    # File png nhưng nội dung là rác không giải mã được
    corrupted_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRcorruptedcontent"
    files = {"image": ("corrupt.png", io.BytesIO(corrupted_data), "image/png")}
    response = client.post("/api/predict", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "Failed to decode image" in data["detail"]

def test_predict_valid_image():
    import cv2
    import numpy as np

    # Tạo ảnh trắng 800x600 chuẩn OpenCV
    img = np.ones((600, 800, 3), dtype=np.uint8) * 200
    _, img_encoded = cv2.imencode(".png", img)
    img_bytes = img_encoded.tobytes()

    files = {"image": ("classroom.png", io.BytesIO(img_bytes), "image/png")}
    response = client.post("/api/predict", files=files)

    assert response.status_code == 200
    data = response.json()

    assert "id" in data
    assert "people_count" in data
    assert "kept_count" in data
    assert "suppressed_count" in data
    assert "detections" in data

    assert data["people_count"] == data["kept_count"]
    assert len(data["detections"]) == (data["kept_count"] + data["suppressed_count"])

    # Kiểm tra cấu trúc DetectionItem
    for det in data["detections"]:
        assert "box_id" in det
        assert "bbox" in det
        assert len(det["bbox"]) == 4
        assert "confidence" in det
        assert "depth" in det
        assert "depth_std" in det
        assert "kept" in det
        if not det["kept"]:
            assert det["suppressed_by"] is not None
            assert det["suppression_reason"] is not None
