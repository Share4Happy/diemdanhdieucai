import numpy as np
from backend.app.core.attendance_engine import compute_weighted_attendance_result

def test_compute_weighted_attendance_winner():
    # Giả lập 8 lần quét: 5 lần ra 44, 2 lần ra 43, 1 lần ra 42
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    samples = [
        {"pass_index": 1, "present_count": 43, "confidence_avg": 0.81, "laplacian_sharpness": 22.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 2, "present_count": 44, "confidence_avg": 0.85, "laplacian_sharpness": 25.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 3, "present_count": 44, "confidence_avg": 0.84, "laplacian_sharpness": 24.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 4, "present_count": 44, "confidence_avg": 0.86, "laplacian_sharpness": 26.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 5, "present_count": 42, "confidence_avg": 0.78, "laplacian_sharpness": 20.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 6, "present_count": 44, "confidence_avg": 0.87, "laplacian_sharpness": 27.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 7, "present_count": 44, "confidence_avg": 0.85, "laplacian_sharpness": 25.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 8, "present_count": 43, "confidence_avg": 0.82, "laplacian_sharpness": 23.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
    ]

    result = compute_weighted_attendance_result(samples, standard_count=45)
    assert result["success"] is True
    assert result["present_count"] == 44
    assert result["absent_count"] == 1
    assert result["winning_freq"] == 5
    assert result["best_pass_index"] == 6 # Lần 6 có conf 0.87 và sharpness 27.0 cao nhất
    assert "Quét 8 lần: [43, 44, 44, 44, 42, 44, 44, 43] -> Chốt 44 HS" in result["audit_notes"]

def test_compute_weighted_attendance_tie_breaker():
    # Giả lập hòa điểm (4 lần 43, 4 lần 44 có cùng score): Phải ưu tiên số lớn hơn là 44
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    samples = [
        {"pass_index": 1, "present_count": 43, "confidence_avg": 0.80, "laplacian_sharpness": 20.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 2, "present_count": 43, "confidence_avg": 0.80, "laplacian_sharpness": 20.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 3, "present_count": 43, "confidence_avg": 0.80, "laplacian_sharpness": 20.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 4, "present_count": 43, "confidence_avg": 0.80, "laplacian_sharpness": 20.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 5, "present_count": 44, "confidence_avg": 0.80, "laplacian_sharpness": 20.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 6, "present_count": 44, "confidence_avg": 0.80, "laplacian_sharpness": 20.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 7, "present_count": 44, "confidence_avg": 0.80, "laplacian_sharpness": 20.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 8, "present_count": 44, "confidence_avg": 0.80, "laplacian_sharpness": 20.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
    ]

    result = compute_weighted_attendance_result(samples, standard_count=45)
    assert result["success"] is True
    assert result["present_count"] == 44 # Hòa điểm -> Ưu tiên 44

def test_compute_weighted_attendance_all_invalid():
    samples = [
        {"pass_index": 1, "is_valid": False, "present_count": None},
        {"pass_index": 2, "is_valid": False, "present_count": None},
    ]
    result = compute_weighted_attendance_result(samples, standard_count=40)
    assert result["success"] is False
    assert result["present_count"] == 0
    assert result["status"] == "NO_SIGNAL"

def test_compute_weighted_attendance_10_passes():
    # Giả lập 10 lần quét (chu kỳ 10 lần nghỉ 10s)
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    samples = [
        {"pass_index": 1, "present_count": 45, "confidence_avg": 0.82, "laplacian_sharpness": 20.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 2, "present_count": 46, "confidence_avg": 0.88, "laplacian_sharpness": 28.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 3, "present_count": 46, "confidence_avg": 0.86, "laplacian_sharpness": 25.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 4, "present_count": 45, "confidence_avg": 0.84, "laplacian_sharpness": 21.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 5, "present_count": 46, "confidence_avg": 0.89, "laplacian_sharpness": 30.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 6, "present_count": 46, "confidence_avg": 0.87, "laplacian_sharpness": 26.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 7, "present_count": 46, "confidence_avg": 0.88, "laplacian_sharpness": 29.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 8, "present_count": 45, "confidence_avg": 0.83, "laplacian_sharpness": 22.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 9, "present_count": 46, "confidence_avg": 0.87, "laplacian_sharpness": 27.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
        {"pass_index": 10, "present_count": 46, "confidence_avg": 0.90, "laplacian_sharpness": 31.0, "frame": dummy_frame, "annotated_img": dummy_frame, "is_valid": True},
    ]
    res = compute_weighted_attendance_result(samples, standard_count=46)
    assert res["success"] is True
    assert res["present_count"] == 46
    assert res["winning_freq"] == 7
    assert res["best_pass_index"] == 10
    assert "Quét 10 lần:" in res["audit_notes"]
    assert "Tần suất 7/10" in res["audit_notes"]

if __name__ == "__main__":
    test_compute_weighted_attendance_winner()
    test_compute_weighted_attendance_tie_breaker()
    test_compute_weighted_attendance_all_invalid()
    test_compute_weighted_attendance_10_passes()
    print("ALL TESTS PASSED!")
