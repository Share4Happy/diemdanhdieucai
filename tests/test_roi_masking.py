import pytest
import numpy as np
from core.roi_manager import ROIManager

def test_roi_point_test():
    red_zone = [[100, 100], [500, 100], [500, 500], [100, 500]]
    green_zone = [[150, 150], [250, 150], [250, 250], [150, 250]]

    # Điểm nằm trong Red Zone và ngoài Green Zone -> Hợp lệ (Học sinh)
    student_pos = (350, 350)
    assert ROIManager.is_point_in_roi(student_pos, red_zone, green_zone) is True

    # Điểm nằm trong Green Zone (Bục giảng) -> Bị loại trừ (Giáo viên)
    teacher_pos = (200, 200)
    assert ROIManager.is_point_in_roi(teacher_pos, red_zone, green_zone) is False

    # Điểm nằm ngoài cả 2 -> Bị loại trừ
    outside_pos = (50, 50)
    assert ROIManager.is_point_in_roi(outside_pos, red_zone, green_zone) is False

def test_spatial_mask_creation():
    shape = (600, 800)
    red_zone = [[100, 100], [500, 100], [500, 500], [100, 500]]
    green_zone = [[150, 150], [250, 150], [250, 250], [150, 250]]

    mask = ROIManager.create_spatial_mask(shape, red_zone, green_zone)

    assert mask.shape == shape
    # Kiểm tra pixel học sinh phải có giá trị 255
    assert mask[350, 350] == 255
    # Kiểm tra pixel giáo viên (bục giảng) phải bị bôi đen 0
    assert mask[200, 200] == 0
    # Kiểm tra pixel ngoài vùng phải bị bôi đen 0
    assert mask[50, 50] == 0
