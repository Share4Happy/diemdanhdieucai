"""
=============================================================================
CÔNG CỤ KIỂM TRA TRỰC TIẾP ĐẦU GHI NVR / CAMERA RTSP - THPT ĐIỀU CẢI
=============================================================================
Kiểm tra kết nối trực tiếp, độ trễ và chất lượng hình ảnh (Main Stream vs Sub Stream)
từ Đầu Ghi Hình NVR Hikvision / Dahua (192.168.1.200) trường THPT Điều Cải.
"""
import sys
import os
import time
import socket
from pathlib import Path

# Đảm bảo đường dẫn gốc dự án trong sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
APP_DIR = BACKEND_DIR / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    import cv2
    import numpy as np
    from config.settings import settings
    from config.logging_config import logger
    from backend.app.core.rtsp_client import rtsp_client, is_valid_frame
    from database.db_session import SessionLocal
    from database.models import Classroom, NVRDevice
except ImportError as e:
    print(f"[!] Lỗi nạp thư viện: {e}")
    print("    Vui lòng kích hoạt môi trường ảo (virtualenv) trước khi chạy script:")
    print("    Linux/Mac: source venv/bin/activate")
    print("    Windows:   call venv_cuda\\Scripts\\activate.bat")
    sys.exit(1)

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
    
    start_time = time.time()
    try:
        frame, error = rtsp_client.grab_snapshot(url, timeout=3.5, retry_rounds=1)
        latency = (time.time() - start_time) * 1000
        
        if frame is not None:
            stats = analyze_frame_quality(frame)
            print(f"     [OK] Nhận frame thành công trong {latency:.1f}ms")
            print(f"     - Độ phân giải: {stats['resolution']}")
            print(f"     - Độ sắc nét (Laplacian Var): {stats['laplacian_var']} -> {stats['sharpness_label']}")
            print(f"     - Độ tương phản (Std): {stats['std']}")
            print(f"     - Màu sắc trung bình BGR: {stats['mean_bgr']}")
            print(f"     - Frame hợp lệ (không lỗi sọc xám/xanh): {'ĐẠT' if stats['is_valid'] else 'KHÔNG ĐẠT'}")
            return True, stats
        else:
            print(f"     [LỖI] Không thể chụp frame: {error} (thời gian: {latency:.1f}ms)")
            return False, {"error": error}
    except Exception as e:
        print(f"     [NGOẠI LỆ] {e}")
        return False, {"error": str(e)}

def main():
    print("=" * 80)
    print(" BỘ KIỂM TRA ĐẦU GHI NVR & CAMERA TRỰC TIẾP - THPT ĐIỀU CẢI")
    print("=" * 80)
    
    host = settings.DVR_HOST
    port = settings.DVR_PORT
    print(f"\n[1] Kiểm tra cổng TCP kết nối NVR {host}:{port}...")
    is_open = test_socket(host, port)
    if is_open:
        print(f" -> CỔNG {port} ĐANG MỞ! Kết nối mạng tới NVR hoàn toàn thông suốt.")
    else:
        print(f" -> [CẢNH BÁO] Cổng {port} không phản hồi hoặc bị chặn tường lửa.")
        print("    (Nếu đang chạy trên máy không cùng dải LAN trường THPT Điều Cải, kết quả chụp sẽ thất bại)")

    print(f"\n[2] Kiểm tra danh sách lớp học và camera cấu hình trong Cơ sở dữ liệu...")
    db = SessionLocal()
    try:
        classrooms = db.query(Classroom).order_by(Classroom.channel_number).all()
        print(f" -> Tìm thấy {len(classrooms)} phòng học trong CSDL.")
        
        test_classes = classrooms[:3] if len(classrooms) >= 3 else classrooms
        
        for cls in test_classes:
            print("\n" + "-" * 60)
            print(f"Phòng: {cls.name} ({cls.room_number}) - Kênh camera NVR: {cls.channel_number}")
            print("-" * 60)
            
            # 1. Main stream
            main_url = settings.get_dvr_rtsp_url(cls.channel_number, subtype=0)
            probe_stream(main_url, f"Kênh {cls.channel_number} - Main Stream (Chất lượng cao)")
            
            # 2. Sub stream
            sub_url = settings.get_dvr_rtsp_url(cls.channel_number, subtype=1)
            probe_stream(sub_url, f"Kênh {cls.channel_number} - Sub Stream (Phụ/Preview)")

    finally:
        db.close()
        
    print("\n" + "=" * 80)
    print(" HOÀN TẤT KIỂM TRA TOÀN DIỆN NVR")
    print("=" * 80)

if __name__ == "__main__":
    main()
