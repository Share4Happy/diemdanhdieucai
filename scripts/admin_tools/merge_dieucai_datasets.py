"""
=============================================================================
KỊCH BẢN GỘP DATASET AI ĐIỂM DANH TRƯỜNG THPT ĐIỀU CẢI
- Nguồn 1: dataset/studenthead1.v1-1.yolo26 (Camera 1 & 2 - 182 ảnh)
- Nguồn 2: dataset/12k img Project.v2i.yolo26 (Trích xuất mở rộng - 12.585 ảnh)
- Đích:    dataset/merged_dieucai_head (Tổng cộng ~12.767 ảnh)
- Chuẩn hóa: Toàn bộ nhãn (. / head / object / student_head) -> class 0: student_head
- Cơ chế: Sử dụng hardlink (không tốn thêm dung lượng ổ cứng, tốc độ tức thì)
=============================================================================
"""

import os
import sys
import shutil
from pathlib import Path
from collections import Counter

# Root directory
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATASET_DIR = PROJECT_ROOT / "dataset"

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_1 = DATASET_DIR / "studenthead1.v1-1.yolo26"
SRC_2 = DATASET_DIR / "12k img Project.v2i.yolo26"
DEST_DIR = DATASET_DIR / "merged_dieucai_head"

def link_or_copy(src: Path, dst: Path):
    """Tạo hardlink nếu cùng ổ đĩa, nếu lỗi thì copy."""
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except Exception:
        shutil.copy2(src, dst)

def process_label_file(src_lbl: Path, dst_lbl: Path) -> int:
    """Đọc file nhãn, chuẩn hóa toàn bộ class_id về 0 (student_head)."""
    if dst_lbl.exists():
        return 0
    box_count = 0
    lines_out = []
    if src_lbl.exists():
        try:
            content = src_lbl.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in content:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    # Gán class_id = 0, giữ nguyên x_center, y_center, width, height
                    parts[0] = "0"
                    lines_out.append(" ".join(parts))
                    box_count += 1
        except Exception as e:
            print(f"[!] Lỗi đọc {src_lbl}: {e}")
    
    dst_lbl.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")
    return box_count

def merge_datasets():
    print("=" * 70)
    print(" GỘP DỮ LIỆU HUẤN LUYỆN CAMERA THỰC TẾ TRƯỜNG THPT ĐIỀU CẢI")
    print("=" * 70)
    print(f"[*] Nguồn 1: {SRC_1.name}")
    print(f"[*] Nguồn 2: {SRC_2.name}")
    print(f"[*] Đích:    {DEST_DIR.name}")
    print("=" * 70)

    if not SRC_1.exists():
        print(f"[LỖI] Không tìm thấy thư mục {SRC_1}")
        return False
    if not SRC_2.exists():
        print(f"[LỖI] Không tìm thấy thư mục {SRC_2}")
        return False

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    splits = ["train", "valid", "test"]
    stats = {}

    for split in splits:
        img_dest = DEST_DIR / split / "images"
        lbl_dest = DEST_DIR / split / "labels"
        img_dest.mkdir(parents=True, exist_ok=True)
        lbl_dest.mkdir(parents=True, exist_ok=True)

        total_imgs = 0
        total_boxes = 0

        # Duyệt qua cả 2 nguồn
        for src_dataset in [SRC_1, SRC_2]:
            src_split = src_dataset / split
            if not src_split.exists():
                continue

            src_img_dir = src_split / "images"
            src_lbl_dir = src_split / "labels"

            if not src_img_dir.exists():
                continue

            for img_file in src_img_dir.iterdir():
                if not img_file.is_file() or img_file.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                    continue

                target_img_name = img_file.name
                target_img_path = img_dest / target_img_name

                # Nếu bị trùng tên, thêm tiền tố tên thư mục nguồn
                if target_img_path.exists() and target_img_path.stat().st_size != img_file.stat().st_size:
                    prefix = "ds1_" if src_dataset == SRC_1 else "ds2_"
                    target_img_name = prefix + target_img_name
                    target_img_path = img_dest / target_img_name

                link_or_copy(img_file, target_img_path)
                total_imgs += 1

                # Xử lý nhãn
                lbl_name = img_file.stem + ".txt"
                src_lbl_path = src_lbl_dir / lbl_name
                target_lbl_name = target_img_path.stem + ".txt"
                target_lbl_path = lbl_dest / target_lbl_name

                boxes = process_label_file(src_lbl_path, target_lbl_path)
                total_boxes += boxes

        stats[split] = {"images": total_imgs, "boxes": total_boxes}
        print(f"[+] Phân chia [{split.upper()}]: {total_imgs:,} ảnh | {total_boxes:,} nhãn đầu học sinh (class 0)")

    # Tạo file cấu hình YAML chuẩn Ultralytics YOLO
    yaml_content = f"""# Cấu hình tập dữ liệu tổng hợp Camera THPT Điều Cải
# Tự động tạo bởi scripts/merge_dieucai_datasets.py
# Tổng cộng: {sum(s['images'] for s in stats.values()):,} ảnh, {sum(s['boxes'] for s in stats.values()):,} nhãn đầu học sinh

path: {DEST_DIR.as_posix()}
train: train/images
val: valid/images
test: test/images

nc: 1
names:
  0: student_head
"""
    yaml_path = DATASET_DIR / "merged_dieucai_head.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")
    print(f"\n[+] Đã tạo cấu hình YOLO dataset tại: {yaml_path}")

    # Đồng bộ sang studenthead_real.yaml để giữ tương thích với các script cũ
    studenthead_real_yaml = DATASET_DIR / "studenthead_real.yaml"
    if studenthead_real_yaml.exists():
        backup_yaml = DATASET_DIR / "studenthead_real_backup_orig.yaml"
        if not backup_yaml.exists():
            shutil.copy2(studenthead_real_yaml, backup_yaml)
            print(f"[+] Đã sao lưu cấu hình cũ: {backup_yaml.name}")
    
    studenthead_real_yaml.write_text(yaml_content, encoding="utf-8")
    print(f"[+] Đã cập nhật {studenthead_real_yaml.name} trỏ sang bộ dữ liệu hợp nhất 12k!")

    print("\n" + "=" * 70)
    print(f"[THÀNH CÔNG] ĐÃ GỘP XONG TOÀN BỘ DATASET!")
    print(f"Tổng số ảnh: {sum(s['images'] for s in stats.values()):,}")
    print(f"Tổng số nhãn đầu học sinh: {sum(s['boxes'] for s in stats.values()):,}")
    print("=" * 70)
    return True

if __name__ == "__main__":
    merge_datasets()
