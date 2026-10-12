"""
Script kiểm tra kết nối trực tiếp, độ trễ và chất lượng hình ảnh (Main Stream vs Sub Stream)
từ Đầu Ghi Hình NVR Hikvision (192.168.1.200) trường THPT Điều Cải.
"""
import sys
import os
import time
import socket
from pathlib import Path

# Đảm bảo đường dẫn gốc dự án trong sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
from config.settings import settings
from config.logging_config import logger
from core.rtsp_client import rtsp_client, is_valid_frame
from database.db_session import SessionLocal
from database.models import Classroom, NVRDevice

def test_socket(host: str, port: int = 554, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def analyze_frame_quality(frame: np.ndarray) -> dict:
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    b_mean, g_mean, r_mean = frame.mean(axis=(0, 1))
    std_val = float(frame.std())
    is_valid = is_valid_frame(frame)
    
    # Đánh giá độ nét
    if lap_var > 100:
        sharpness_label = "Rất Sắc Nét (Tuyệt vời cho AI điểm danh)"
    elif lap_var > 40:
        sharpness_label = "Sắc Nét Đạt Chuẩn (Tốt)"
    elif lap_var > 15:
        sharpness_label = "Chấp Nhận Được"
    else:
        sharpness_label = "Mờ / Thiếu chi tiết / Nguy cơ frame xám"

    return {
        "resolution": f"{w}x{h}",
        "width": w,
        "height": h,
        "laplacian_var": round(lap_var, 2),
        "sharpness_label": sharpness_label,
        "std": round(std_val, 2),
        "mean_bgr": (round(b_mean, 1), round(g_mean, 1), round(r_mean, 1)),
        "is_valid": is_valid
    }

def probe_stream(url: str, label: str = ""):
    print(f"\n---> Đang kết nối thử nghiệm: {label}")
    print(f"     URL: {url}")
    
    t0 = time.time()
    frame = rtsp_client._read_rtsp_stream(url, timeout=4.0)
    elapsed_ms = int((time.time() - t0) * 1000)

    if frame is None:
        print(f"     [THAT BAI] Không lấy được khung hình hợp lệ sau {elapsed_ms}ms.")
        return None

    stats = analyze_frame_quality(frame)
    print(f"     [THANH CONG] Thời gian bắt hình: {elapsed_ms}ms")
    print(f"     * Do phan giai: {stats['resolution']}")
    print(f"     * Chi so do net (Laplacian): {stats['laplacian_var']} - {stats['sharpness_label']}")
    print(f"     * Mau sac trung binh (B, G, R): {stats['mean_bgr']}")
    print(f"     * Trang thai Frame sach: {'HOP LE (Sach 100%)' if stats['is_valid'] else 'CHUA DAT CHUAN'}")
    return frame

def main():
    print("=" * 70)
    print("  KIEM TRA TRUC TIEP DAU GHI NVR HIKVISION - THPT DIEU CAI")
    print("=" * 70)

    db = SessionLocal()
    nvr = db.query(NVRDevice).filter(NVRDevice.ip_address.like("192.168.1.%")).first()
    host = nvr.ip_address if nvr else settings.DVR_HOST
    port = nvr.rtsp_port if nvr else settings.DVR_PORT
    user = nvr.username if nvr else settings.DVR_USER
    pwd = nvr.password if nvr else (settings.DVR_PASSWORD or "Dieucai1982")
    db.close()

    print(f"Thong tin NVR: {host}:{port} (User: {user})")
    
    # 1. Kiem tra cong mang TCP
    print(f"\n[1/3] Kiem tra ket noi cong RTSP ({host}:{port})...")
    is_open = test_socket(host, port, timeout=1.2)
    if is_open:
        print("  ==> Cong RTSP DANG MO. San sang bat luong video!")
    else:
        print(f"  ==> KHONG THE KET NOI tới {host}:{port}.")
        print("      Luu y: May tinh can cam cung mang LAN 192.168.1.x voi dau ghi.")
        print("      Kiem tra day mang va dia chi IP cua dau ghi.")
        return

    # 2. Thu nghiem Kenh 1 (Lop 12A1)
    print("\n[2/3] Thu nghiem Kenh 1 (Lop 12A1):")
    main_url_ch1 = f"rtsp://{user}:{pwd}@{host}:{port}/Streaming/Channels/101"
    sub_url_ch1 = f"rtsp://{user}:{pwd}@{host}:{port}/Streaming/Channels/102"
    
    probe_stream(main_url_ch1, "Kenh 1 - LUONG CHINH 1080p (Diem danh AI)")
    probe_stream(sub_url_ch1, "Kenh 1 - LUONG PHU (Xem truoc TV Wall)")

    # 3. Thu nghiem Kenh 17 (Lop 11A7 - Kenh tung bi loi xanh la)
    print("\n[3/3] Thu nghiem Kenh 17 (Lop 11A7 - Kenh tung bi loi xanh la):")
    main_url_ch17 = f"rtsp://{user}:{pwd}@{host}:{port}/Streaming/Channels/1701"
    sub_url_ch17 = f"rtsp://{user}:{pwd}@{host}:{port}/Streaming/Channels/1702"
    
    probe_stream(main_url_ch17, "Kenh 17 - LUONG CHINH 1080p (Diem danh AI)")
    probe_stream(sub_url_ch17, "Kenh 17 - LUONG PHU (Xem truoc TV Wall)")

    print("\n" + "=" * 70)
    print("  HOAN TAT KIEM TRA.")
    print("=" * 70)

if __name__ == "__main__":
    main()
