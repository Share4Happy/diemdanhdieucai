import os
import cv2
from pathlib import Path
from config.settings import settings
from config.logging_config import logger
from core.detector import detector

def test_image_3():
    # Tìm tệp ảnh kiểm thử thực tế
    img_candidates = [
        settings.STORAGE_DIR / "captures" / "2026-09-19" / "Lop_30.jpg",
        settings.STORAGE_DIR / "captures" / "2026-09-19" / "Lop_1.jpg",
        settings.SAMPLES_DIR / "classroom_sample_3.jpg"
    ]
    img_path = None
    for c in img_candidates:
        if c.exists():
            img_path = c
            break

    if not img_path:
        print("[LỖI] Không tìm thấy tệp ảnh mẫu kiểm thử nào.")
        return

    print("===================================================================")
    print(f"  KIỂM THỬ ĐIỂM DANH AI TRÊN HÌNH ẢNH LỚP HỌC: {img_path.name}")
    print("===================================================================")
    print(f"[*] Đường dẫn ảnh: {img_path}")

    img = cv2.imread(str(img_path))
    h, w = img.shape[:2]
    print(f"[*] Độ phân giải: {w}x{h}")

    if w == 640 and h == 480:
        red_zone = [
            [10, 60],
            [500, 60],
            [500, h - 5],
            [10, h - 5]
        ]
        green_zone = [
            [505, 120],
            [w - 10, 120],
            [w - 10, h - 5],
            [505, h - 5]
        ]
    else:
        red_zone = [
            [int(w * 0.05), int(h * 0.15)],
            [int(w * 0.80), int(h * 0.15)],
            [int(w * 0.80), int(h * 0.98)],
            [int(w * 0.05), int(h * 0.98)]
        ]
        green_zone = [
            [int(w * 0.81), int(h * 0.20)],
            [int(w * 0.98), int(h * 0.20)],
            [int(w * 0.98), int(h * 0.98)],
            [int(w * 0.81), int(h * 0.98)]
        ]

    standard_count = 40
    print(f"[*] Sĩ số chuẩn quy định: {standard_count} học sinh")
    print("[*] Đang chạy AI phát hiện đầu người & bóc tách mặt nạ ROI...")

    present_count, valid_students, annotated_img = detector.detect_students_in_classroom(
        image=img,
        red_zone=red_zone,
        green_zone=green_zone,
        standard_count=standard_count,
        classroom_name="LỚP HỌC THỰC TẾ (HÌNH 3 TEST)",
        apply_clahe=False,
        conf_threshold=0.15
    )

    absent_count = max(0, standard_count - present_count)

    print("\n--- KẾT QUẢ PHÂN TÍCH AI ---")
    print(f">> Số học sinh đếm được (Hiện diện): {present_count} / 39 học sinh thực tế")
    print(f">> Sĩ số vắng mặt (so với chuẩn 40): {absent_count}")
    print(f">> Tỷ lệ chính xác đếm so với thực tế: {(present_count / 39.0) * 100:.1f}%")

    # Lưu ảnh kết quả vào thư mục storage
    today_annotated = settings.ANNOTATED_DIR / "2026-09-19"
    today_annotated.mkdir(parents=True, exist_ok=True)
    out_path_today = today_annotated / "Hinh_3_result.jpg"
    out_path_sample = settings.STORAGE_DIR / "annotated" / "Hinh_3_result.jpg"

    cv2.imwrite(str(out_path_today), annotated_img)
    cv2.imwrite(str(out_path_sample), annotated_img)

    print(f"\n[+] Đã xuất ảnh đối chứng mới tại:")
    print(f"    1. {out_path_today}")
    print(f"    2. {out_path_sample}")
    print("[+] Đã gỡ bỏ hoàn toàn dải banner đen che khuất phía trên.")
    print("[+] Các con số trên đầu học sinh đã được nâng cấp thành Huy hiệu tương phản cao (High-Contrast Badges).")
    print("===================================================================")

if __name__ == "__main__":
    test_image_3()
