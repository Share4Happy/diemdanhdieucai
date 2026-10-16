"""
=============================================================================
KỊCH BẢN LÀM SẠCH VÀ TẠO DATASET CHUẨN XÁC 100% (LOẠI BỎ BA LÔ & RÁC)
=============================================================================
NGUYÊN NHÂN GỐC RỄ ĐÃ TÌM THẤY:
- Dataset 12k gốc (Roboflow) có 3 class: ['.', 'head', 'object'].
  + Class 1: 'head' (294.565 nhãn đầu người thật).
  + Class 2: 'object' (171.395 nhãn ba lô, cặp sách, rác, bàn ghế).
- Trong lần gộp trước, toàn bộ class 2 ('object') đã bị đổi thành class 0 ('student_head')!
  Dẫn đến mô hình học nhầm rằng 171 nghìn chiếc ba lô chính là đầu học sinh!

GIẢI PHÁP TRIỆT ĐỂ:
- Chỉ lấy class 1 ('head') từ bộ 12k và đổi thành class 0 ('student_head').
- LOẠI BỎ 100% class 2 ('object' - ba lô, rác) và class 0 ('.').
- Gộp cùng bộ ảnh gốc trường THPT Điều Cải (studenthead1.v1-1.yolo26).
- Kết quả: Bộ dữ liệu thuần khiết ~300.000 đầu học sinh, 0 ba lô rác!
=============================================================================
"""

import os
import sys
import shutil
from pathlib import Path
from collections import Counter

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
DEST_DIR = DATASET_DIR / "clean_dieucai_head"


def link_or_copy(src: Path, dst: Path):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except Exception:
        shutil.copy2(src, dst)


def process_clean_label_file(src_lbl: Path, dst_lbl: Path, is_src2: bool = False) -> int:
    """
    Xử lý lọc nhãn:
    - Nếu từ src_1 (studenthead1): giữ nguyên class 0 (student_head).
    - Nếu từ src_2 (12k Project): CHỈ LẤY class 1 ('head'), đổi thành 0. LOẠI BỎ class 2 ('object' - ba lô)!
    """
    if dst_lbl.exists():
        return 0

    lines_out = []
    box_count = 0

    if src_lbl.exists():
        try:
            content = src_lbl.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in content:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    cls_id = parts[0]
                    if is_src2:
                        # Trong bộ 12k:
                        # class 1 = head -> giữ lại và gán thành 0
                        # class 2 = object (ba lô, rác) -> VỨT BỎ!
                        # class 0 = '.' -> VỨT BỎ!
                        if cls_id == "1":
                            parts[0] = "0"
                            lines_out.append(" ".join(parts))
                            box_count += 1
                    else:
                        # Bộ Điều Cải thực tế: giữ nguyên
                        parts[0] = "0"
                        lines_out.append(" ".join(parts))
                        box_count += 1
        except Exception as e:
            print(f"[!] Lỗi đọc {src_lbl}: {e}")

    dst_lbl.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")
    return box_count


def clean_and_merge():
    print("=" * 70)
    print(" LÀM SẠCH VÀ TẠO DATASET THUẦN KHIẾT TRƯỜNG THPT ĐIỀU CẢI")
    print(" (Loại bỏ 171.395 nhãn ba lô, cặp sách, rác để mô hình không đếm nhầm)")
    print("=" * 70)

    if not SRC_1.exists() or not SRC_2.exists():
        print("[LỖI] Không tìm thấy một trong hai thư mục dữ liệu nguồn.")
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

        # Nguồn 1: studenthead1 (Dieu Cai)
        s1_split = SRC_1 / split
        if s1_split.exists():
            s1_imgs = s1_split / "images"
            s1_lbls = s1_split / "labels"
            if s1_imgs.exists():
                for img_file in s1_imgs.glob("*.*"):
                    if img_file.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"]:
                        dst_img = img_dest / f"dieucai_{img_file.name}"
                        link_or_copy(img_file, dst_img)

                        lbl_file = s1_lbls / f"{img_file.stem}.txt"
                        dst_lbl = lbl_dest / f"dieucai_{img_file.stem}.txt"
                        boxes = process_clean_label_file(lbl_file, dst_lbl, is_src2=False)
                        total_imgs += 1
                        total_boxes += boxes

        # Nguồn 2: 12k img Project (Roboflow - LỌC BỎ CLASS 2 OBJECT)
        s2_split = SRC_2 / split
        if s2_split.exists():
            s2_imgs = s2_split / "images"
            s2_lbls = s2_split / "labels"
            if s2_imgs.exists():
                for img_file in s2_imgs.glob("*.*"):
                    if img_file.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"]:
                        dst_img = img_dest / f"rf_{img_file.name}"
                        link_or_copy(img_file, dst_img)

                        lbl_file = s2_lbls / f"{img_file.stem}.txt"
                        dst_lbl = lbl_dest / f"rf_{img_file.stem}.txt"
                        boxes = process_clean_label_file(lbl_file, dst_lbl, is_src2=True)
                        total_imgs += 1
                        total_boxes += boxes

        stats[split] = (total_imgs, total_boxes)
        print(f"[*] Tập {split:<5}: {total_imgs:>6} ảnh | {total_boxes:>8} nhãn đầu học sinh (Đã loại bỏ ba lô/rác)")

    # Ghi file data.yaml chuẩn
    yaml_content = f"""train: {DEST_DIR.resolve().as_posix()}/train/images
val: {DEST_DIR.resolve().as_posix()}/valid/images
test: {DEST_DIR.resolve().as_posix()}/test/images

nc: 1
names: ['student_head']
"""
    yaml_file = DEST_DIR / "data.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")
    print("\n[OK] Đã ghi cấu hình dataset sạch vào:", yaml_file)
    print("=" * 70)
    return True


if __name__ == "__main__":
    clean_and_merge()
