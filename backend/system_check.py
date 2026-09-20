"""
=============================================================================
BẢNG KIỂM TRA TIẾN ĐỘ & TRẠNG THÁI HỆ THỐNG - THPT ĐIỀU CẢI
=============================================================================
"""
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

print("=========================================================================")
print("   BẢNG KIỂM TRA TIẾN ĐỘ & TRẠNG THÁI HỆ THỐNG - THPT ĐIỀU CẢI")
print("=========================================================================")

print("\n[1] KIỂM TRA MÔI TRƯỜNG & PHẦN CỨNG:")
try:
    import torch
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        print(f" - PyTorch: {torch.__version__} | NVIDIA CUDA: SẴN SÀNG (GPU: {gpu_name})")
    else:
        print(f" - PyTorch: {torch.__version__} | NVIDIA CUDA: CHẠY TRÊN CPU")
except Exception as e:
    print(f" - PyTorch Error: {e}")

print("\n[2] KIỂM TRA CƠ SỞ DỮ LIỆU (DATABASE):")
try:
    from database.db_session import SessionLocal
    from database.models import Classroom, AttendanceSession, AttendanceDetail
    db = SessionLocal()
    total_classes = db.query(Classroom).count()
    total_sessions = db.query(AttendanceSession).count()
    last_session = db.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()
    print(f" - Tổng số lớp học trong DB: {total_classes} lớp")
    print(f" - Tổng số phiên điểm danh:   {total_sessions} phiên")
    if last_session:
        print(f" - Phiên gần nhất:            {last_session.session_code} ({last_session.scan_date} {last_session.scan_time}) | Tỉ lệ: {last_session.total_present}/{last_session.total_standard}")
    db.close()
except Exception as e:
    print(f" - Database Error: {e}")

print("\n[3] KIỂM TRA BỘ DỮ LIỆU & TRỌNG SỐ AI:")
media_dir = ROOT_DIR / "dataset" / "classrooms_media"
if media_dir.exists():
    classes_media = [d for d in media_dir.iterdir() if d.is_dir() and d.name.startswith("Lop_")]
    print(f" - Dữ liệu 30 lớp học:        SẴN SÀNG ({len(classes_media)}/30 lớp)")
else:
    print(" - Dữ liệu 30 lớp học:        CHƯA KHỞI TẠO")

model_best = ROOT_DIR / "models" / "classroom_best.pt"
if model_best.exists():
    mb_size = round(model_best.stat().st_size / (1024 * 1024), 1)
    print(f" - Trọng số AI (classroom_best.pt): SẴN SÀNG ({mb_size} MB)")
else:
    print(" - Trọng số AI (classroom_best.pt): CHƯA CÓ")

print("\n[4] TÌNH TRẠNG CÁC PHÂN HỆ:")
modules = [
    ("Frontend UI", "frontend"),
    ("Backend API", "backend"),
    ("Core Engine", "core"),
    ("Services", "services"),
    ("AI Training", "training"),
    ("Database", "database"),
]
for name, p in modules:
    status = "HOẠT ĐỘNG" if (ROOT_DIR / p).exists() else "THIẾU"
    print(f" - {name:15}: {status}")

print("=========================================================================")
