import pytest
import numpy as np
from core.roi_manager import ROIManager

def test_roi_point_test():
    # Green Zone: Vùng nhận diện (Bàn học sinh)
    green_zone = [[100, 100], [500, 100], [500, 500], [100, 500]]

    # Điểm nằm trong Green Zone -> Hợp lệ (Học sinh)
    student_pos = (350, 350)
    assert ROIManager.is_point_in_roi(student_pos, green_zone=green_zone) is True

    # Điểm nằm ngoài Green Zone (Bục giảng / hành lang) -> Mặc định tự động bị bỏ qua
    podium_pos = (50, 50)
    assert ROIManager.is_point_in_roi(podium_pos, green_zone=green_zone) is False

    outside_pos = (600, 300)
    assert ROIManager.is_point_in_roi(outside_pos, green_zone=green_zone) is False

def test_spatial_mask_creation():
    shape = (600, 800)
    # Green Zone: Vùng nhận diện (Bàn học sinh)
    green_zone = [[100, 100], [500, 100], [500, 500], [100, 500]]

    mask = ROIManager.create_spatial_mask(shape, green_zone=green_zone)

    assert mask.shape == shape
    # Kiểm tra pixel học sinh bên trong Green Zone có giá trị 255
    assert mask[350, 350] == 255
    # Kiểm tra pixel ngoài vùng Green Zone (bục giảng, ngoài lớp) mặc định bị bôi đen 0 (bỏ qua)
    assert mask[50, 50] == 0
    assert mask[550, 550] == 0

