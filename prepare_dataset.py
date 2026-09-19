"""
Script chuẩn hóa nhãn dữ liệu huấn luyện YOLOv8 cho trường THPT Điều Cải:
- Gộp các lớp tư thế học sinh (0, 1, 2, 3, 4, 5, 6) thành lớp 0 (student_head).
- Loại bỏ lớp 7 (giáo viên hướng dẫn).
- Xóa các file .cache cũ để YOLO tái tạo cache mới.
"""

import sys
import time
from pathlib import Path

# Đảm bảo in tiếng Việt trên console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset" / "classroom_data"
TRAIN_LBL = DATASET_DIR / "labels" / "train"
VAL_LBL = DATASET_DIR / "labels" / "val"

def standardize_labels():
    start_time = time.time()
    print("=================================================================")
    print("   CHUẨN HÓA DỮ LIỆU NHÃN HỌC SINH THPT ĐIỀU CẢI")
    print("=================================================================")

    total_files = 0
    total_student_boxes = 0
    total_teacher_dropped = 0
    empty_files = 0

    target_dirs = [("Train", TRAIN_LBL), ("Val", VAL_LBL)]

    for split_name, lbl_dir in target_dirs:
        if not lbl_dir.exists():
            print(f"[!] Không tìm thấy thư mục: {lbl_dir}")
            continue

        split_files = list(lbl_dir.glob("*.txt"))
        print(f"[*] Đang xử lý {len(split_files)} files trong {split_name}...")

        for fpath in split_files:
            total_files += 1
            new_lines = []
            with open(fpath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if not parts:
                    continue
                cls_id = parts[0]
                if cls_id == "7":
                    total_teacher_dropped += 1
                    continue
                # Gộp tất cả lớp 0..6 về lớp 0
                parts[0] = "0"
                new_lines.append(" ".join(parts) + "\n")
                total_student_boxes += 1

            if not new_lines:
                empty_files += 1

            with open(fpath, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

    # Xóa file cache cũ
    for cache_name in ["train.cache", "val.cache"]:
        cache_path = DATASET_DIR / "labels" / cache_name
        if cache_path.exists():
            cache_path.unlink()
            print(f"[+] Đã xóa cache cũ: {cache_path.name}")

    elapsed = time.time() - start_time
    print("=================================================================")
    print(f"[THÀNH CÔNG] Đã chuẩn hóa {total_files:,} files nhãn trong {elapsed:.2f}s!")
    print(f" - Tổng số hộp học sinh (student_head - Lớp 0): {total_student_boxes:,}")
    print(f" - Tổng số hộp giáo viên đã loại bỏ (Lớp 7):   {total_teacher_dropped:,}")
    print(f" - Số ảnh nền không chứa nhãn:               {empty_files:,}")
    print("=================================================================")

if __name__ == "__main__":
    standardize_labels()
