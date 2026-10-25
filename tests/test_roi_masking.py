import pytest
import numpy as np
from backend.core.roi_manager import ROIManager

def test_roi_point_test():
    """Kiểm tra chế độ quét toàn diện: Mọi điểm trong phòng đều được giữ lại cho AI."""
    green_zone = [[100, 100], [500, 100], [500, 500], [100, 500]]

    student_pos = (350, 350)
    assert ROIManager.is_point_in_roi(student_pos, green_zone=green_zone) is True

    podium_pos = (50, 50)
    assert ROIManager.is_point_in_roi(podium_pos, green_zone=green_zone) is True

    outside_pos = (600, 300)
    assert ROIManager.is_point_in_roi(outside_pos, green_zone=green_zone) is True

def test_spatial_mask_creation():
    """Kiểm tra mặt nạ không gian trả về 255 (toàn ảnh sáng) để AI quét toàn phòng."""
    shape = (600, 800)
    green_zone = [[100, 100], [500, 100], [500, 500], [100, 500]]

    mask = ROIManager.create_spatial_mask(shape, green_zone=green_zone)

    assert mask.shape == shape
    assert np.all(mask == 255)
