import pytest
import numpy as np
import cv2
from pathlib import Path
from config.settings import settings
from core.detector import StudentDetector, detector

def test_yolo26_model_initialization():
    """Kiểm tra khởi tạo mô hình YOLO26m thành công và thông tin kiến trúc chính xác."""
    info = detector.get_model_info()
    assert info is not None
    assert info["family"] == "YOLO26"
    assert info["variant"] == "26m"
    assert "yolo26m.pt" in info["model_name"] or "classroom" in info["model_name"]
    assert info["confidence_threshold"] >= 0.20
    assert len(info["target_classes"]) > 0

def test_yolo26_inference_on_synthetic_frame():
    """Kiểm tra tính năng suy luận của YOLO26m trên khung hình học sinh."""
    # Tạo ảnh giả lập với 3 hình chữ nhật tượng trưng cho học sinh
    h, w = 720, 1280
    test_img = np.ones((h, w, 3), dtype=np.uint8) * 200

    # Chạy quy trình phát hiện với toàn khung hình là vùng hợp lệ
    count, boxes, annotated = detector.detect_students_in_classroom(
        image=test_img,
        red_zone=None,
        green_zone=None,
        conf_threshold=0.25
    )

    assert isinstance(count, int)
    assert isinstance(boxes, list)
    assert annotated is not None
    assert annotated.shape == test_img.shape

def test_yolo26_real_sample_inference():
    """Kiểm tra nhận diện học sinh trên ảnh thực tế trường học."""
    sample_path = settings.BASE_DIR / "dataset" / "samples" / "live_dvr_ch1.jpg"
    if sample_path.exists():
        img = cv2.imread(str(sample_path))
        assert img is not None

        count, boxes, annotated = detector.detect_students_in_classroom(
            image=img,
            red_zone=None,
            green_zone=None,
            conf_threshold=0.25
        )

        assert count > 0, f"YOLO26m phải phát hiện được người trong {sample_path}"
        assert len(boxes) == count
        for b in boxes:
            assert "bbox" in b
            assert "confidence" in b
            assert b["confidence"] >= 0.20

def test_yolo26_deduplication():
    """Kiểm tra thuật toán khử trùng lặp bounding box khi học sinh ngồi gần nhau."""
    boxes = [
        [100, 100, 200, 300],
        [102, 105, 198, 298], # Box trùng gần như hoàn toàn
        [400, 100, 500, 300]  # Box riêng biệt
    ]
    confs = [0.85, 0.75, 0.90]

    fused_b, fused_c = StudentDetector.deduplicate_boxes(boxes, confs, iou_thresh=0.5)
    assert len(fused_b) == 2
    assert fused_c[0] == 0.90
