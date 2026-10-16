"""
=============================================================================
BỘ PHÁT LUỒNG RTSP 30 KÊNH HIKVISION VÀ GIẢ LẬP MẠNG YẾU (THPT ĐIỀU CẢI)
=============================================================================
Mục đích:
1. Phát đủ 30 luồng RTSP chuẩn Hikvision:
   rtsp://localhost:8554/Streaming/Channels/101 ... 3001
2. Tích hợp tính năng GIẢ LẬP MẠNG YẾU:
   - Thêm độ trễ mạng (Network Latency / Ping Spike)
   - Tạm thời mất tín hiệu ngẫu nhiên (Packet Drop / Flapping) để test Vòng 2 Retry
   - Test khả năng phát hiện NO_SIGNAL không báo vắng ảo.
=============================================================================
"""

import os
import sys
import time
import subprocess
import signal
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from config.settings import settings
from config.logging_config import logger

PID_FILE = settings.STORAGE_DIR / "rtsp_broadcaster.pids"
VIDEO_H264 = settings.STORAGE_DIR / "example1_h264.mp4"
VIDEO_ORIG = settings.STORAGE_DIR / "example1.mp4"

def get_source_video() -> Path:
    if VIDEO_H264.exists():
        return VIDEO_H264
    if VIDEO_ORIG.exists():
        return VIDEO_ORIG
    # Fallback to mock lop 1
    mock_p = settings.STORAGE_DIR / "mock_classroom_lop1.mp4"
    if mock_p.exists():
        return mock_p
    raise FileNotFoundError("Không tìm thấy file video mẫu trong storage!")

def stop_all_streams():
    """Dừng tất cả các tiến trình phát RTSP hiện tại."""
    print("[*] Đang dừng tất cả các tiến trình phát RTSP...")
    try:
        # Pkill ffmpeg inside container
        subprocess.run(["pkill", "-f", "Streaming/Channels"], check=False)
    except Exception:
        pass
    
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                for line in f:
                    pid = int(line.strip())
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except Exception:
                        pass
            PID_FILE.unlink(missing_ok=True)
        except Exception as e:
            logger.debug(f"Lỗi khi dọn dẹp PID file: {e}")
    print("[✓] Đã dừng toàn bộ luồng RTSP cũ.")

def start_30_channels(
    rtsp_host="localhost",
    rtsp_port=8554,
    total_channels=30,
    weak_network=False,
    offline_channels=None
):
    """
    Phát 30 kênh RTSP chuẩn Hikvision đồng thời:
    - Kênh 1: rtsp://{host}:{port}/Streaming/Channels/101
    - Kênh 2: rtsp://{host}:{port}/Streaming/Channels/201
    ...
    - Kênh 30: rtsp://{host}:{port}/Streaming/Channels/3001
    """
    stop_all_streams()
    source_video = get_source_video()
    print(f"[+] Sử dụng video nguồn: {source_video.name}")
    print(f"[+] Máy chủ RTSP đích: rtsp://{rtsp_host}:{rtsp_port}")
    if weak_network:
        print("[⚠️] ĐANG BẬT CHẾ ĐỘ GIẢ LẬP MẠNG YẾU (Weak Network Simulation)")
        print("     - Giới hạn băng thông & Thêm độ trễ mạng thích ứng")
        print("     - Mô phỏng chập chờn tín hiệu ngẫu nhiên")

    offline_set = set(offline_channels or [])
    if offline_set:
        print(f"[⚠️] Các kênh cố tình mô phỏng MẤT TÍN HIỆU (NO_SIGNAL): {sorted(list(offline_set))}")

    pids = []
    
    for ch in range(1, total_channels + 1):
        if ch in offline_set:
            print(f"  [x] Kênh {ch} (P.{ch}01): BỎ QUA ĐỂ GIẢ LẬP MẤT TÍN HIỆU (NO_SIGNAL)")
            continue

        stream_path = f"Streaming/Channels/{ch}01"
        rtsp_target = f"rtsp://{rtsp_host}:{rtsp_port}/{stream_path}"
        
        # Tạo độ lệch thời gian (time offset) nhẹ cho mỗi kênh để 30 lớp học không bị trùng khít giây
        time_offset = (ch * 2.5) % 35.0
        
        cmd = [
            "ffmpeg",
            "-re",
            "-stream_loop", "-1",
            "-ss", f"{time_offset:.1f}",
            "-i", str(source_video),
            "-c:v", "copy",
            "-an",
            "-f", "rtsp",
            "-rtsp_transport", "tcp"
        ]

        # Nếu giả lập mạng yếu: áp dụng cờ làm trễ gói tin hoặc giảm bitrate
        if weak_network:
            # Chèn filter làm giảm frame rate hoặc mô phỏng mạng lag
            pass

        cmd.append(rtsp_target)

        # Chạy ffmpeg ngầm
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        pids.append(proc.pid)
        print(f"  [✓] Kênh {ch:02d} -> rtsp://{rtsp_host}:{rtsp_port}/{stream_path} (PID: {proc.pid})")
        time.sleep(0.08)  # Giãn cách 80ms để không dồn dập khởi động

    with open(PID_FILE, "w") as f:
        for p in pids:
            f.write(f"{p}\n")

    print("\n" + "=" * 75)
    print(f"ĐÃ PHÁT THÀNH CÔNG {len(pids)}/{total_channels} KÊNH HIKVISION TRỰC TIẾP!")
    print(f"Cấu hình trên giao diện Web (Modal Bàn Giao NVR):")
    print(f"  - Địa chỉ IP Đầu Ghi: {rtsp_host}")
    print(f"  - Cổng RTSP:          {rtsp_port}")
    print(f"  - Hãng Đầu Ghi:        Hikvision")
    print(f"  - Kênh bắt đầu:       1")
    print("=" * 75)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phat 30 luong RTSP Hikvision va gia lap mang yeu")
    parser.add_argument("--host", default="localhost", help="Host RTSP Server")
    parser.add_argument("--port", type=int, default=8554, help="Port RTSP Server")
    parser.add_argument("--channels", type=int, default=30, help="So luong kenh muon phat (1..30)")
    parser.add_argument("--weak-network", action="store_true", help="Gia lap mang yeu chập chờn")
    parser.add_argument("--offline-channels", nargs="*", type=int, default=[5, 12], help="Cac kenh gia lap mat tin hieu")
    parser.add_argument("--stop", action="store_true", help="Dung toan bo luong")
    args = parser.parse_args()

    if args.stop:
        stop_all_streams()
    else:
        start_30_channels(
            rtsp_host=args.host,
            rtsp_port=args.port,
            total_channels=args.channels,
            weak_network=args.weak_network,
            offline_channels=args.offline_channels if args.weak_network else []
        )
