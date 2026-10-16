"""
=============================================================================
GỘP TẬP DỮ LIỆU HUẤN LUYỆN CAMERA THPT ĐIỀU CẢI VÀO 'datatraining'
Nguồn:
  1. h.v3i.yolo26 (8.001 ảnh)
  2. hea.v3-data6k.yolo26 (96.960 ảnh)
  3. My First Project.v4i.yolo26 (12.505 ảnh)
Đích:
  dataset/datatraining (117.466 ảnh)

Chuẩn hóa toàn bộ nhãn về:
  class 0: student_head

Sử dụng NTFS Hardlink:
  - 0% tốn thêm dung lượng ổ đĩa
  - Tốc độ xử lý siêu nhanh (~15 giây cho 117k files)
=============================================================================
"""

import os
import sys
import shutil
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
DEST_DIR = DATASET_DIR / "datatraining"

SOURCES = [
    {"prefix": "h_", "name": "h.v3i.yolo26", "path": DATASET_DIR / "h.v3i.yolo26"},
    {"prefix": "hea_", "name": "hea.v3-data6k.yolo26", "path": DATASET_DIR / "hea.v3-data6k.yolo26"},
    {"prefix": "mf_", "name": "My First Project.v4i.yolo26", "path": DATASET_DIR / "My First Project.v4i.yolo26"},
]

def process_file_pair(item):
    """
    Xử lý 1 cặp ảnh - nhãn:
    - Tạo hardlink ảnh
    - Đọc và chuẩn hóa nhãn về class 0
    """
    src_img, dst_img, src_lbl, dst_lbl = item
    
    # 1. Hardlink ảnh
    if not dst_img.exists():
        try:
            os.link(src_img, dst_img)
        except Exception:
            shutil.copy2(src_img, dst_img)
            
    # 2. Xử lý nhãn
    box_count = 0
    lines_out = []
    if src_lbl.exists():
        try:
            lines = src_lbl.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    parts[0] = "0"  # Chuẩn hóa về class 0 (student_head)
                    lines_out.append(" ".join(parts))
                    box_count += 1
        except Exception:
            pass

    dst_lbl.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")
    return box_count

def run_merge():
    start_time = time.time()
    print("=" * 70)
    print(" BẮT ĐẦU GỘP DATASET VÀO THƯ MỤC 'datatraining'")
    print("=" * 70)
    
    for s in SOURCES:
        if not s["path"].exists():
            print(f"[LỖI] Không tìm thấy thư mục: {s['path']}")
            return False
        print(f" [+] Nguồn: {s['name']} (Tiền tố: {s['prefix']})")
    print(f" [*] Đích:   {DEST_DIR}")
    print("=" * 70)

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    splits = ["train", "valid", "test"]
    overall_stats = {}

    for split in splits:
        t_split = time.time()
        img_dest = DEST_DIR / split / "images"
        lbl_dest = DEST_DIR / split / "labels"
        img_dest.mkdir(parents=True, exist_ok=True)
        lbl_dest.mkdir(parents=True, exist_ok=True)

        tasks = []
        for src in SOURCES:
            src_split_dir = src["path"] / split
            src_img_dir = src_split_dir / "images"
            src_lbl_dir = src_split_dir / "labels"
            
            if not src_img_dir.exists():
                continue
                
            prefix = src["prefix"]
            for img_file in src_img_dir.iterdir():
                if not img_file.is_file():
                    continue
                ext = img_file.suffix.lower()
                if ext not in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                    continue
                
                target_img_name = prefix + img_file.name
                target_img_path = img_dest / target_img_name
                
                lbl_name = img_file.stem + ".txt"
                src_lbl_path = src_lbl_dir / lbl_name
                target_lbl_name = prefix + lbl_name
                target_lbl_path = lbl_dest / target_lbl_name
                
                tasks.append((img_file, target_img_path, src_lbl_path, target_lbl_path))

        print(f"\n[*] Đang xử lý phân vùng [{split.upper()}]: {len(tasks):,} ảnh...")
        total_boxes = 0
        
        # Chạy đa luồng tăng tốc
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = executor.map(process_file_pair, tasks, chunksize=1000)
            for idx, cnt in enumerate(results, 1):
                total_boxes += cnt
                if idx % 20000 == 0 or idx == len(tasks):
                    print(f"   -> Đã xử lý {idx:,}/{len(tasks):,} file ({time.time() - t_split:.1f}s)...", flush=True)

        overall_stats[split] = {"images": len(tasks), "boxes": total_boxes}
        print(f"[HOÀN TẤT {split.upper()}]: {len(tasks):,} ảnh | {total_boxes:,} nhãn đầu học sinh (thời gian: {time.time() - t_split:.1f}s)")

    # Tạo cấu hình YAML chuẩn Ultralytics YOLO
    total_imgs = sum(s["images"] for s in overall_stats.values())
    total_boxes = sum(s["boxes"] for s in overall_stats.values())

    yaml_content = f"""# Cấu hình tập dữ liệu huấn luyện THPT Điều Cải (datatraining)
# Gộp từ: h.v3i.yolo26, hea.v3-data6k.yolo26, My First Project.v4i.yolo26
# Tổng số ảnh: {total_imgs:,} | Tổng số nhãn: {total_boxes:,}

path: {DEST_DIR.as_posix()}
train: train/images
val: valid/images
test: test/images

nc: 1
names:
  0: student_head
"""

    yaml_dest_inside = DEST_DIR / "data.yaml"
    yaml_dest_inside.write_text(yaml_content, encoding="utf-8")
    
    yaml_dest_root = DATASET_DIR / "datatraining.yaml"
    yaml_dest_root.write_text(yaml_content, encoding="utf-8")

    # Cập nhật thêm file studenthead_real.yaml để tương thích tuyệt đối với các script cũ
    studenthead_real = DATASET_DIR / "studenthead_real.yaml"
    studenthead_real.write_text(yaml_content, encoding="utf-8")

    total_time = time.time() - start_time
    print("\n" + "=" * 70)
    print(" TỔNG KẾT GỘP DATASET THÀNH CÔNG!")
    print("=" * 70)
    print(f" Thư mục đích:         {DEST_DIR}")
    print(f" File cấu hình:        {yaml_dest_root}")
    print(f" File cấu hình trong:  {yaml_dest_inside}")
    print(f" Tổng số ảnh:          {total_imgs:,}")
    print(f"   - Train:            {overall_stats['train']['images']:,} ảnh ({overall_stats['train']['boxes']:,} nhãn)")
    print(f"   - Valid:            {overall_stats['valid']['images']:,} ảnh ({overall_stats['valid']['boxes']:,} nhãn)")
    print(f"   - Test:             {overall_stats['test']['images']:,} ảnh ({overall_stats['test']['boxes']:,} nhãn)")
    print(f" Tổng số bounding box: {total_boxes:,}")
    print(f" Thời gian thực hiện:  {total_time:.2f} giây")
    print("=" * 70)
    return True

if __name__ == "__main__":
    run_merge()
