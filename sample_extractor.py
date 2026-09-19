import os
import cv2
import numpy as np
from pathlib import Path
from config.settings import settings
from config.logging_config import logger

EXTRACTED_DIR = settings.BASE_DIR / "dataset" / "extracted_frames"
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

def generate_mock_classroom_data():
    """
    Tạo dữ liệu giả lập 5 ảnh lớp học và 1 video 15s nếu trường học chưa kịp nạp file vào dataset/samples.
    Giúp hệ thống có thể chạy kiểm thử benchmark ngay lập tức.
    """
    logger.info("Đang kiểm tra thư mục dataset/samples...")
    sample_files = list(settings.SAMPLES_DIR.glob("*.*"))
    if sample_files:
        logger.info(f"Tìm thấy {len(sample_files)} file mẫu do người dùng cung cấp trong {settings.SAMPLES_DIR}")
        return

    logger.info("Chưa có file mẫu thực tế. Đang tự động tạo 5 ảnh mẫu và 1 video 15s mô phỏng lớp học Điều Cải...")
    h, w = 1080, 1920

    for i in range(1, 6):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        # Nền lớp học màu xám sáng
        img[:] = (220, 225, 230)

        # Cửa sổ bên phải (mô phỏng ngược sáng như yêu cầu Giai đoạn 5)
        cv2.rectangle(img, (1600, 100), (1900, 900), (255, 255, 255), -1)
        # Hiệu ứng lóa sáng từ cửa sổ
        for r in range(1500, 1920, 40):
            cv2.line(img, (r, 0), (r - 200, 1080), (245, 250, 255), 15)

        # Bục giảng giáo viên (Green Zone)
        cv2.rectangle(img, (350, 80), (950, 280), (180, 200, 180), -1)
        cv2.putText(img, "BUC GIANG GIAO VIEN", (450, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (30, 80, 30), 2)
        # Giả lập 1 giáo viên đứng ở bục giảng
        cv2.circle(img, (600, 200), 30, (80, 60, 50), -1) # Đầu giáo viên
        cv2.ellipse(img, (600, 250), (45, 25), 0, 0, 360, (50, 50, 180), -1)

        # Dãy bàn học sinh (Red Zone)
        # Giả lập 35 - 42 học sinh ngồi trong lớp
        num_students = 36 + (i % 6)
        student_count = 0
        for row in range(5):
            y = 380 + row * 130
            for col in range(8):
                x = 300 + col * 170
                # Bàn học
                cv2.rectangle(img, (x - 60, y + 20), (x + 60, y + 70), (140, 100, 60), -1)
                if student_count < num_students:
                    # Đầu học sinh (Head)
                    cv2.circle(img, (x, y), 22, (40, 35, 30), -1)
                    # Thân trên học sinh
                    cv2.ellipse(img, (x, y + 30), (35, 18), 0, 0, 360, (180, 120, 60 + col*15), -1)
                    student_count += 1

        cv2.putText(img, f"CAMERA LOP HOC DIEU CAI - SAMPLE #{i} (Students: {num_students})", 
                    (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3)

        out_path = settings.SAMPLES_DIR / f"classroom_sample_{i}.jpg"
        cv2.imwrite(str(out_path), img)
        logger.info(f"Đã tạo ảnh mẫu: {out_path.name}")

    # Tạo video 15s (15 fps = 225 frames)
    video_path = settings.SAMPLES_DIR / "classroom_sample_15s.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_vid = cv2.VideoWriter(str(video_path), fourcc, 15, (w, h))

    base_frame = cv2.imread(str(settings.SAMPLES_DIR / "classroom_sample_1.jpg"))
    for frame_idx in range(225):
        frame = base_frame.copy()
        # Mô phỏng cử động nhẹ của học sinh
        shift = int(np.sin(frame_idx / 10.0) * 3)
        cv2.putText(frame, f"REC 15s | Frame {frame_idx + 1}/225 | Time: 06:45:{(frame_idx // 15):02d}", 
                    (50, 1030), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        out_vid.write(frame)
    out_vid.release()
    logger.info(f"Đã tạo video mẫu 15s: {video_path.name}")

def extract_frames_from_samples(sample_interval: int = 30):
    """
    Cắt trích xuất các khung hình chất lượng cao từ 5 ảnh và 1 video trong dataset/samples/
    để làm dữ liệu kiểm thử và đánh giá độ chính xác của AI.
    """
    generate_mock_classroom_data()
    
    extracted_count = 0
    logger.info("Bắt đầu trích xuất khung hình từ dataset/samples...")

    # 1. Trích xuất từ các file ảnh
    image_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    for img_file in settings.SAMPLES_DIR.glob("*.*"):
        if img_file.suffix.lower() in image_exts and not img_file.name.startswith("extracted_"):
            img = cv2.imread(str(img_file))
            if img is not None:
                save_name = f"extracted_img_{img_file.stem}.jpg"
                save_path = EXTRACTED_DIR / save_name
                cv2.imwrite(str(save_path), img)
                extracted_count += 1
                logger.info(f"Đã trích xuất ảnh mẫu: {save_name}")

    # 2. Trích xuất từ video 15s
    video_exts = {".mp4", ".avi", ".mkv", ".mov"}
    for vid_file in settings.SAMPLES_DIR.glob("*.*"):
        if vid_file.suffix.lower() in video_exts:
            cap = cv2.VideoCapture(str(vid_file))
            frame_idx = 0
            vid_extracted = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % sample_interval == 0:
                    save_name = f"extracted_vid_{vid_file.stem}_frame_{frame_idx:04d}.jpg"
                    save_path = EXTRACTED_DIR / save_name
                    cv2.imwrite(str(save_path), frame)
                    extracted_count += 1
                    vid_extracted += 1
                frame_idx += 1
            cap.release()
            logger.info(f"Đã trích xuất {vid_extracted} frames từ video: {vid_file.name}")

    logger.info(f"Hoàn tất Giai đoạn 1 (Trích xuất dữ liệu): Tổng cộng {extracted_count} frames đã sẵn sàng tại {EXTRACTED_DIR}")
    return extracted_count

if __name__ == "__main__":
    extract_frames_from_samples()
