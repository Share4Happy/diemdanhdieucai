"""
=============================================================================
GIÁM SÁT TIẾN TRÌNH HUẤN LUYỆN YOLO THỜI GIAN THỰC (CHỐNG LỖI FONT & CUỘN RÁC)
Tự động tìm kiếm file log mới nhất và hiển thị thanh tiến trình mượt mà
=============================================================================
"""

import os
import sys
import time
from pathlib import Path

# Cấu hình UTF-8 cho Windows Console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_CSV = PROJECT_ROOT / "runs" / "train" / "dieucai_merged_12k" / "results.csv"

def get_latest_log():
    """Tự động tìm file log của tiến trình train gần nhất."""
    # 1. Kiểm tra log trực tiếp trong thư mục project nếu có
    local_log = PROJECT_ROOT / "runs" / "train" / "dieucai_merged_12k" / "train_live.log"
    if local_log.exists() and local_log.stat().st_size > 0:
        return local_log

    # 2. Tìm kiếm trong các task log của IDE
    brain_dir = Path(r"C:\Users\Admin\.gemini\antigravity-ide\brain")
    if brain_dir.exists():
        logs = sorted(brain_dir.glob(r"*\.system_generated\tasks\*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        for l in logs:
            try:
                if l.stat().st_size > 0:
                    with open(l, "r", encoding="utf-8", errors="ignore") as f:
                        head = f.read(500)
                        if "HUẤN LUYỆN" in head or "train_real_camera" in head or "Ultralytics" in head or "Epoch" in head:
                            return l
            except Exception:
                pass
        if logs:
            return logs[0]

    # 3. Fallback mặc định
    return Path(r"C:\Users\Admin\.gemini\antigravity-ide\brain\b9691be1-b1e4-484a-b8c4-57cdc37c77aa\.system_generated\tasks\task-159.log")

def print_header():
    print("=" * 72)
    print(" 🚀 GIÁM SÁT TIẾN TRÌNH HUẤN LUYỆN AI ĐIỂM DANH - THPT ĐIỀU CẢI")
    print("    GPU: NVIDIA GeForce RTX 3050 Laptop GPU (12.767 ảnh, 20 epochs)")
    print("    Bấm [Ctrl + C] bất cứ lúc nào để thoát (Tiến trình train vẫn chạy ngầm)")
    print("=" * 72)

    # Hiển thị tóm tắt tiến trình đã lưu trong results.csv
    if RESULTS_CSV.exists():
        try:
            with open(RESULTS_CSV, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
                if len(lines) > 1:
                    last_line = lines[-1].split(",")
                    epoch_done = last_line[0]
                    precision = float(last_line[5]) * 100 if len(last_line) > 5 else 0
                    recall = float(last_line[6]) * 100 if len(last_line) > 6 else 0
                    map50 = float(last_line[7]) * 100 if len(last_line) > 7 else 0
                    print(f"[*] Tiến độ đã hoàn thành: Epoch {epoch_done}/20")
                    print(f"    - Độ chính xác (Precision): {precision:.2f}%")
                    print(f"    - Tỷ lệ phát hiện (Recall): {recall:.2f}%")
                    print(f"    - Chỉ số mAP50:             {map50:.2f}%\n")
        except Exception:
            pass

def monitor():
    print_header()
    log_path = get_latest_log()
    print(f"[*] Đang theo dõi log: {log_path.name}")
    if not log_path.exists():
        print(f"[!] Đang chờ khởi tạo file log...")
        while not log_path.exists():
            time.sleep(1)

    print("[*] Đang kết nối luồng hiển thị thời gian thực...\n")
    
    last_rendered_line = ""

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        # Đọc từ khoảng 4KB cuối file
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        f.seek(max(0, file_size - 4096), os.SEEK_SET)

        buffer = ""
        while True:
            chunk = f.read(1024)
            if not chunk:
                # Kiểm tra nếu có log mới hơn được tạo
                newest = get_latest_log()
                if newest != log_path and newest.exists() and newest.stat().st_mtime > log_path.stat().st_mtime:
                    print(f"\n[*] Phát hiện phiên train mới: {newest.name}. Đang chuyển kênh...")
                    log_path = newest
                    f.close()
                    f = open(log_path, "r", encoding="utf-8", errors="replace")
                    buffer = ""
                    continue
                time.sleep(0.4)
                continue

            buffer += chunk
            parts = buffer.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            buffer = parts[-1]

            for line in parts[:-1]:
                line_clean = line.strip()
                if not line_clean:
                    continue

                if "%" in line_clean and ("/" in line_clean or "it/s" in line_clean or "G" in line_clean):
                    if line_clean != last_rendered_line:
                        sys.stdout.write(f"\r\033[K[TRAIN] {line_clean}")
                        sys.stdout.flush()
                        last_rendered_line = line_clean
                else:
                    sys.stdout.write(f"\n{line_clean}\n")
                    sys.stdout.flush()
                    last_rendered_line = ""

if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        print("\n\n[*] Đã đóng màn hình theo dõi. AI vẫn đang tiếp tục huấn luyện trong nền.")
