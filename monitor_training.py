"""
Script theo dõi trực tiếp tiến trình huấn luyện YOLOv8 trong thời gian thực.
Hỗ trợ hiển thị trên mọi cửa sổ Terminal / PowerShell / Command Prompt.
"""

import os
import sys
import time
from pathlib import Path

# Đảm bảo mã hóa UTF-8 cho console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

LOG_FILE = Path(r"C:\Users\Admin\.gemini\antigravity-ide\brain\5f018aba-550c-4efb-96fe-c7d6b270f9e5\.system_generated\tasks\task-208.log")
CSV_FILE = Path(r"D:\Vibe Code\hethongdiemdanh Dieu Cai\runs\train\dieucai_classroom\results.csv")

def main():
    print("=" * 70)
    print("   THEO DÕI TIẾN ĐỘ HUẤN LUYỆN YOLOv8 - THPT ĐIỀU CẢI (RTX 3050)")
    print("=" * 70)
    print(f"[*] Đang kết nối luồng nhật ký: {LOG_FILE.name}")
    print("[*] Nhấn Ctrl + C bất kỳ lúc nào để thoát màn hình theo dõi.\n")

    if not LOG_FILE.exists():
        print("[!] Chưa tìm thấy file log tiến trình. Vui lòng chờ vài giây...")
        while not LOG_FILE.exists():
            time.sleep(1)

    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        # Nhảy về 2000 ký tự cuối để hiển thị ngay dòng mới nhất
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - 2000), os.SEEK_SET)
        
        # Bỏ dòng dở đầu tiên nếu có
        if size > 2000:
            f.readline()

        last_line = ""
        while True:
            line = f.readline()
            if line:
                cleaned = line.strip()
                if cleaned and cleaned != last_line:
                    # In trực tiếp tiến độ
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    last_line = cleaned
            else:
                time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[*] Đã dừng màn hình theo dõi.")
