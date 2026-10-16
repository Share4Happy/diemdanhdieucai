"""
=============================================================================
CÔNG CỤ TRÍCH XUẤT MẪU KIỂM THỬ KHUNG HÌNH (SAMPLE EXTRACTOR MODULE)
=============================================================================
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from config.logging_config import logger

EXTRACTED_DIR = settings.BASE_DIR / "dataset" / "extracted_frames"
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

def generate_mock_classroom_data():
    """Tạo dữ liệu giả lập 5 ảnh lớp học và 1 video 15s nếu chưa có."""
    sample_files = list(settings.SAMPLES_DIR.glob("*.*"))
    if sample_files:
        logger.info(f"Tìm thấy {len(sample_files)} file mẫu trong {settings.SAMPLES_DIR}")
        return

    logger.info("Chưa có file mẫu thực tế. Đang tự động tạo 5 ảnh mẫu và 1 video 15s...")
    h, w = 1080, 1920

    for i in range(1, 6):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (220, 225, 230)
        cv2.rectangle(img, (1600, 100), (1900, 900), (255, 255, 255), -1)
        for r in range(1500, 1920, 40):
            cv2.line(img, (r, 0), (r - 200, 1080), (245, 250, 255), 15)

        cv2.rectangle(img, (350, 80), (950, 280), (180, 200, 180), -1)
        cv2.putText(img, "BUC GIANG GIAO VIEN", (450, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (30, 80, 30), 2)
        cv2.circle(img, (600, 200), 30, (80, 60, 50), -1)
        cv2.ellipse(img, (600, 250), (45, 25), 0, 0, 360, (50, 50, 180), -1)

        num_students = 36 + (i % 6)
        student_count = 0
        for row in range(5):
            y = 380 + row * 130
            for col in range(8):
                x = 300 + col * 170
                cv2.rectangle(img, (x - 60, y + 20), (x + 60, y + 70), (140, 100, 60), -1)
                if student_count < num_students:
                    cv2.circle(img, (x, y), 22, (40, 35, 30), -1)
                    cv2.ellipse(img, (x, y + 30), (35, 18), 0, 0, 360, (180, 120, 60 + col*15), -1)
                    student_count += 1

        cv2.putText(img, f"CAMERA LOP HOC DIEU CAI - SAMPLE #{i} (Students: {num_students})", 
                    (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3)

        out_path = settings.SAMPLES_DIR / f"classroom_sample_{i}.jpg"
        cv2.imwrite(str(out_path), img)

    video_path = settings.SAMPLES_DIR / "classroom_sample_15s.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_vid = cv2.VideoWriter(str(video_path), fourcc, 15, (w, h))

    base_frame = cv2.imread(str(settings.SAMPLES_DIR / "classroom_sample_1.jpg"))
    for frame_idx in range(225):
        frame = base_frame.copy()
        cv2.putText(frame, f"REC 15s | Frame {frame_idx + 1}/225 | Time: 06:45:{(frame_idx // 15):02d}", 
                    (50, 1030), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        out_vid.write(frame)
    out_vid.release()

def extract_frames_from_samples(sample_interval: int = 30):
    generate_mock_classroom_data()
    extracted_count = 0
    image_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    for img_file in settings.SAMPLES_DIR.glob("*.*"):
        if img_file.suffix.lower() in image_exts and not img_file.name.startswith("extracted_"):
            img = cv2.imread(str(img_file))
            if img is not None:
                save_name = f"extracted_img_{img_file.stem}.jpg"
                cv2.imwrite(str(EXTRACTED_DIR / save_name), img)
                extracted_count += 1

    video_exts = {".mp4", ".avi", ".mkv", ".mov"}
    for vid_file in settings.SAMPLES_DIR.glob("*.*"):
        if vid_file.suffix.lower() in video_exts:
            cap = cv2.VideoCapture(str(vid_file))
            frame_idx = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % sample_interval == 0:
                    save_name = f"extracted_vid_{vid_file.stem}_frame_{frame_idx:04d}.jpg"
                    cv2.imwrite(str(EXTRACTED_DIR / save_name), frame)
                    extracted_count += 1
                frame_idx += 1
            cap.release()

    return extracted_count

def extract_from_classrooms_media(class_code: str = None, sample_interval: int = 45):
    media_dir = settings.CLASSROOMS_MEDIA_DIR
    if not media_dir.exists():
        return 0

    target_dirs = [media_dir / f"Lop_{class_code}"] if class_code else [d for d in media_dir.iterdir() if d.is_dir() and d.name.startswith("Lop_")]
    extracted_total = 0

    for c_dir in target_dirs:
        vid_file = c_dir / "video_15s.mp4"
        if vid_file.exists():
            cap = cv2.VideoCapture(str(vid_file))
            f_idx = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                if f_idx % sample_interval == 0:
                    out_name = f"extracted_{c_dir.name}_f{f_idx:04d}.jpg"
                    cv2.imwrite(str(EXTRACTED_DIR / out_name), frame)
                    extracted_total += 1
                f_idx += 1
            cap.release()

    return extracted_total

if __name__ == "__main__":
    extract_frames_from_samples()
