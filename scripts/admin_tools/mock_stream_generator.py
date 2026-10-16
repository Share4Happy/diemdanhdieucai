"""
Script tao video ao va ho tro phat luong video (Mock Stream) de test he thong diem danh.
Cach dung:
    python tests/mock_stream_generator.py
"""
import os
import sys
import time
from pathlib import Path
import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import settings

def generate_mock_video(output_filename="mock_classroom_lop1.mp4", duration_sec=10, fps=15):
    """
    Tao 1 file video MP4 mo phong lop hoc tu anh chup thuc te co san trong he thong.
    Co OSD thoi gian chay lien tuc de kiem thu tinh nang Virtual Live Stream va Anti-Motion-Blur.
    """
    storage_dir = settings.STORAGE_DIR
    sample_images = list((storage_dir / "captures").glob("**/*.jpg"))
    
    if not sample_images:
        print("[!] Khong tim thay anh mau trong storage/captures, tao anh gia lap...")
        base_img = np.zeros((720, 1280, 3), dtype=np.uint8)
        base_img[:] = (50, 60, 75)
        cv2.putText(base_img, "PHONG HOC DIEU CAI (MOCK)", (200, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 3)
    else:
        sample_path = sample_images[0]
        base_img = cv2.imread(str(sample_path))
        print(f"[+] Su dung anh goc: {sample_path.name}")

    h, w = base_img.shape[:2]
    out_path = storage_dir / output_filename
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(out_path), fourcc, float(fps), (w, h))
    
    total_frames = int(duration_sec * fps)
    print(f"[+] Dang sinh video: {out_path} ({total_frames} frames, {fps} fps)...")
    
    for i in range(total_frames):
        frame = base_img.copy()
        cur_time = time.strftime("%Y-%m-%d %H:%M:%S")
        osd_text = f"CAM LOP 10A1 (TEST STREAM) | {cur_time} | F:{i+1:04d}"
        
        # OSD box
        cv2.rectangle(frame, (20, 20), (700, 70), (0, 0, 0), -1)
        cv2.putText(frame, osd_text, (30, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 200), 2)
        out.write(frame)
        
    out.release()
    print(f"[OK] Da tao thanh cong file video ao tai: {out_path}")
    print(f"     File size: {out_path.stat().st_size:,} bytes")
    return out_path

if __name__ == "__main__":
    v_path = generate_mock_video()
