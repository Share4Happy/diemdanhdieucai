import pytest
import os
from pathlib import Path
from core.rtsp_client import RTSPCameraClient
from config.settings import settings

def test_rtsp_multi_threaded_capture():
    client = RTSPCameraClient(timeout_seconds=2)

    # 30 camera giả lập
    mock_classrooms = [
        {"id": i, "name": f"Lớp {i}", "rtsp_url": f"rtsp://mock-cam-{i}"}
        for i in range(1, 31)
    ]

    date_str = "2026-09-18"
    results = client.capture_all_classrooms(mock_classrooms, date_str=date_str, max_workers=10)

    # Kiểm tra đủ 30 camera được xử lý
    assert len(results) == 30

    # Kiểm tra tỷ lệ thành công
    for c_id in range(1, 31):
        info = results[c_id]
        assert info["success"] is True
        assert os.path.exists(info["image_path"])

    # Kiểm tra cấu trúc đường dẫn đúng chuẩn YYYY-MM-DD/Lop_X.jpg
    sample_path = Path(results[1]["image_path"])
    assert sample_path.name == "Lop_1.jpg"
    assert sample_path.parent.name == date_str
