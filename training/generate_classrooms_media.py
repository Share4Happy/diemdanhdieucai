"""
=============================================================================
BỘ TẠO DỮ LIỆU ĐA PHƯƠNG TIỆN 30 LỚP HỌC - TRƯỜNG THPT ĐIỀU CẢI
=============================================================================
Cung cấp:
- Mỗi lớp: 5 hình ảnh Full HD (1920x1080) và 1 video 15 giây (225 frames, 15fps)
- Cấu trúc: Đặt trong thư mục riêng của từng lớp tại `dataset/classrooms_media/Lop_{code}`
- Thông tin sĩ số: Tệp `info.json`, `thong_tin_lop.txt` cho từng lớp
- Báo cáo tổng: `danh_sach_si_so_toan_truong.json`, `danh_sach_si_so_toan_truong.xlsx`, `README.md`
=============================================================================
"""

import os
import sys
import json
import time
import math
import random
from pathlib import Path
import cv2
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Đảm bảo UTF-8 trên Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_BASE_DIR = PROJECT_ROOT / "dataset" / "classrooms_media"

# Danh mục 30 lớp học chuẩn THPT Điều Cải
CLASSROOMS_DATA = [
    # Khối 10 (10 lớp: Phòng 101 - 110)
    {"code": "10A1", "name": "Lớp 10A1", "grade": 10, "room": "Phòng 101", "standard_count": 42},
    {"code": "10A2", "name": "Lớp 10A2", "grade": 10, "room": "Phòng 102", "standard_count": 40},
    {"code": "10A3", "name": "Lớp 10A3", "grade": 10, "room": "Phòng 103", "standard_count": 41},
    {"code": "10A4", "name": "Lớp 10A4", "grade": 10, "room": "Phòng 104", "standard_count": 43},
    {"code": "10A5", "name": "Lớp 10A5", "grade": 10, "room": "Phòng 105", "standard_count": 39},
    {"code": "10A6", "name": "Lớp 10A6", "grade": 10, "room": "Phòng 106", "standard_count": 42},
    {"code": "10A7", "name": "Lớp 10A7", "grade": 10, "room": "Phòng 107", "standard_count": 40},
    {"code": "10A8", "name": "Lớp 10A8", "grade": 10, "room": "Phòng 108", "standard_count": 41},
    {"code": "10A9", "name": "Lớp 10A9", "grade": 10, "room": "Phòng 109", "standard_count": 40},
    {"code": "10A10", "name": "Lớp 10A10", "grade": 10, "room": "Phòng 110", "standard_count": 42},

    # Khối 11 (10 lớp: Phòng 111 - 120)
    {"code": "11A1", "name": "Lớp 11A1", "grade": 11, "room": "Phòng 111", "standard_count": 44},
    {"code": "11A2", "name": "Lớp 11A2", "grade": 11, "room": "Phòng 112", "standard_count": 43},
    {"code": "11A3", "name": "Lớp 11A3", "grade": 11, "room": "Phòng 113", "standard_count": 42},
    {"code": "11A4", "name": "Lớp 11A4", "grade": 11, "room": "Phòng 114", "standard_count": 40},
    {"code": "11A5", "name": "Lớp 11A5", "grade": 11, "room": "Phòng 115", "standard_count": 41},
    {"code": "11A6", "name": "Lớp 11A6", "grade": 11, "room": "Phòng 116", "standard_count": 42},
    {"code": "11A7", "name": "Lớp 11A7", "grade": 11, "room": "Phòng 117", "standard_count": 39},
    {"code": "11A8", "name": "Lớp 11A8", "grade": 11, "room": "Phòng 118", "standard_count": 41},
    {"code": "11A9", "name": "Lớp 11A9", "grade": 11, "room": "Phòng 119", "standard_count": 40},
    {"code": "11A10", "name": "Lớp 11A10", "grade": 11, "room": "Phòng 120", "standard_count": 43},

    # Khối 12 (10 lớp: Phòng 121 - 130)
    {"code": "12A1", "name": "Lớp 12A1", "grade": 12, "room": "Phòng 121", "standard_count": 45},
    {"code": "12A2", "name": "Lớp 12A2", "grade": 12, "room": "Phòng 122", "standard_count": 44},
    {"code": "12A3", "name": "Lớp 12A3", "grade": 12, "room": "Phòng 123", "standard_count": 42},
    {"code": "12A4", "name": "Lớp 12A4", "grade": 12, "room": "Phòng 124", "standard_count": 43},
    {"code": "12A5", "name": "Lớp 12A5", "grade": 12, "room": "Phòng 125", "standard_count": 41},
    {"code": "12A6", "name": "Lớp 12A6", "grade": 12, "room": "Phòng 126", "standard_count": 40},
    {"code": "12A7", "name": "Lớp 12A7", "grade": 12, "room": "Phòng 127", "standard_count": 42},
    {"code": "12A8", "name": "Lớp 12A8", "grade": 12, "room": "Phòng 128", "standard_count": 41},
    {"code": "12A9", "name": "Lớp 12A9", "grade": 12, "room": "Phòng 129", "standard_count": 40},
    {"code": "12A10", "name": "Lớp 12A10", "grade": 12, "room": "Phòng 130", "standard_count": 42},
]

# Bảng màu trang phục học sinh THPT Điều Cải
UNIFORM_COLORS = [
    (240, 240, 245), # Áo sơ mi trắng chuẩn
    (230, 235, 240), # Áo trắng hơi xám
    (185, 140, 70),  # Áo khoác xanh navy nhạt
    (160, 110, 50),  # Áo khoác xanh đậm
    (200, 180, 160), # Màu carô / be
    (225, 230, 238), # Áo trắng đồng phục
]

HAIR_COLORS = [
    (30, 25, 20),
    (40, 35, 25),
    (25, 20, 18),
    (45, 38, 30),
    (20, 18, 15)
]

def render_classroom_scene(
    cls_info: dict,
    present_count: int,
    frame_idx: int = 0,
    time_str: str = "06:45:00",
    is_video: bool = False,
    motion_seed: float = 0.0
) -> np.ndarray:
    """
    Vẽ khung cảnh phòng học chi tiết độ phân giải 1920x1080:
    - Bục giảng giáo viên (Green Zone)
    - Dãy bàn học sinh (Red Zone)
    - Học sinh ngồi theo đúng số lượng hiện diện (present_count)
    - Hiệu ứng ánh sáng cửa sổ góc phải
    - Thanh OSD hiển thị tên lớp, phòng học, sĩ số chuẩn, số có mặt/vắng
    """
    w, h = 1920, 1080
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # 1. Nền tường và sàn phòng học
    # Tường trên: Màu kem xám nhẹ
    img[0:360, :] = (215, 222, 228)
    # Sàn gạch phòng học: Màu xám xi măng ấm
    img[360:, :] = (195, 202, 208)

    # Đường chỉ chân tường
    cv2.line(img, (0, 360), (w, 360), (140, 145, 150), 3)

    # 2. Cửa sổ bên phải mô phỏng ánh sáng ban mai
    cv2.rectangle(img, (1620, 60), (1910, 850), (245, 250, 255), -1)
    cv2.rectangle(img, (1620, 60), (1910, 850), (160, 170, 180), 3)
    # Nan cửa sổ
    cv2.line(img, (1765, 60), (1765, 850), (160, 170, 180), 2)
    cv2.line(img, (1620, 450), (1910, 450), (160, 170, 180), 2)
    # Vệt nắng xiên nhẹ
    for line_x in range(1550, 1920, 45):
        cv2.line(img, (line_x, 0), (line_x - 220, 1080), (240, 246, 252), 8)

    # 3. Bảng đen & Khẩu hiệu phía trước
    cv2.rectangle(img, (300, 70), (1050, 250), (45, 60, 45), -1)
    cv2.rectangle(img, (300, 70), (1050, 250), (90, 110, 90), 4)
    cv2.putText(img, f"TRUONG THPT DIEU CAI - {cls_info['name'].upper()}", 
                (340, 120), cv2.FONT_HERSHEY_DUPLEX, 0.9, (220, 235, 220), 2)
    cv2.putText(img, "HOC TAP TOT - REN LUYEN TOT", 
                (420, 170), cv2.FONT_HERSHEY_DUPLEX, 0.7, (180, 210, 180), 1)

    # 4. Bục giảng giáo viên (Green Zone - Bỏ qua khi đếm)
    cv2.rectangle(img, (260, 240), (750, 340), (175, 195, 175), -1)
    cv2.rectangle(img, (260, 240), (750, 340), (120, 150, 120), 2)
    cv2.putText(img, "BUC GIANG GV", (340, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 70, 40), 1)
    # Bàn giáo viên
    cv2.rectangle(img, (520, 250), (720, 325), (90, 125, 160), -1)
    # Giáo viên đứng tại bục giảng
    gv_dx = int(math.sin(motion_seed + frame_idx * 0.05) * 4) if is_video else 0
    cv2.circle(img, (400 + gv_dx, 225), 26, (50, 40, 35), -1) # Đầu giáo viên
    cv2.ellipse(img, (400 + gv_dx, 275), (38, 22), 0, 0, 360, (70, 70, 160), -1) # Áo vest giáo viên

    # 5. Khu vực bàn ghế học sinh (Red Zone)
    # Bố trí 5 hàng x 9 cột = 45 chỗ ngồi tiêu chuẩn
    std_count = cls_info["standard_count"]
    student_rendered = 0

    # Lập danh sách tọa độ chỗ ngồi (5 hàng x 9 cột)
    seats = []
    for row in range(5):
        base_y = 390 + row * 135
        scale = 1.0 + row * 0.08
        desk_w = int(120 * scale)
        desk_h = int(48 * scale)
        for col in range(9):
            base_x = 220 + col * 175
            seats.append({
                "x": base_x,
                "y": base_y,
                "desk_w": desk_w,
                "desk_h": desk_h,
                "row": row,
                "col": col,
                "scale": scale
            })

    # Số lượng ghế có người
    num_to_seat = min(present_count, len(seats))

    # Ghế vắng ngẫu nhiên có định hướng
    rng = random.Random(cls_info["grade"] * 100 + int(cls_info["code"][-1] if cls_info["code"][-1].isdigit() else 1))
    available_indices = list(range(len(seats)))
    occupied_indices = set(available_indices[:num_to_seat])

    for idx, seat in enumerate(seats):
        x = seat["x"]
        y = seat["y"]
        dw = seat["desk_w"]
        dh = seat["desk_h"]
        row = seat["row"]
        col = seat["col"]
        scale = seat["scale"]

        # Vẽ bàn học sinh
        cv2.rectangle(img, (x - dw//2, y + int(18 * scale)), 
                           (x + dw//2, y + int(18 * scale) + dh), 
                           (110, 85, 55), -1)
        cv2.rectangle(img, (x - dw//2, y + int(18 * scale)), 
                           (x + dw//2, y + int(18 * scale) + dh), 
                           (70, 50, 30), 2)
        # Sách vở trên bàn
        cv2.rectangle(img, (x - 20, y + int(24 * scale)), 
                           (x + 20, y + int(40 * scale)), 
                           (240, 245, 250), -1)

        # Vẽ học sinh nếu ghế này có người
        if idx in occupied_indices:
            if is_video:
                phase = (frame_idx / 8.0) + (row * 1.5) + col
                h_shift_x = int(math.sin(phase) * 2.5)
                h_shift_y = int(math.cos(phase * 0.7) * 1.5)
            else:
                h_shift_x = int(math.sin(frame_idx + col * 0.8) * 3)
                h_shift_y = int(math.cos(frame_idx + row * 0.5) * 2)

            head_x = x + h_shift_x
            head_y = y + h_shift_y
            head_radius = int(21 * scale)

            u_color = UNIFORM_COLORS[(idx + row) % len(UNIFORM_COLORS)]
            h_color = HAIR_COLORS[(idx * 3 + col) % len(HAIR_COLORS)]

            # Thân / Vai học sinh
            cv2.ellipse(img, (head_x, head_y + int(26 * scale)), 
                        (int(32 * scale), int(18 * scale)), 
                        0, 0, 360, u_color, -1)
            cv2.ellipse(img, (head_x, head_y + int(26 * scale)), 
                        (int(32 * scale), int(18 * scale)), 
                        0, 0, 360, (100, 100, 100), 1)

            # Cổ áo học sinh
            cv2.circle(img, (head_x, head_y + int(14 * scale)), int(7 * scale), (210, 180, 160), -1)

            # Đầu tóc học sinh (Head Circle)
            cv2.circle(img, (head_x, head_y), head_radius, h_color, -1)
            # Điểm nhấn tóc / gáy
            cv2.circle(img, (head_x, head_y - int(3 * scale)), int(head_radius * 0.75), (h_color[0] + 15, h_color[1] + 15, h_color[2] + 15), -1)

            student_rendered += 1

    # 6. OSD HEADER BAR (Băng thông tin camera chuẩn trường học)
    cv2.rectangle(img, (0, 0), (w, 65), (28, 24, 24), -1)
    cv2.line(img, (0, 65), (w, 65), (220, 120, 30), 3)

    absent_count = max(0, std_count - present_count)
    header_title = f"TRUONG THPT DIEU CAI | CAMERA {cls_info['name'].upper()} ({cls_info['room']})"
    cv2.putText(img, header_title, (25, 42), cv2.FONT_HERSHEY_DUPLEX, 0.95, (255, 255, 255), 2)

    status_text = f"Si So: {std_count} HS | Hien Dien: {present_count:02d} | Vang: {absent_count:02d}"
    cv2.putText(img, status_text, (950, 42), cv2.FONT_HERSHEY_DUPLEX, 0.9, (80, 240, 140), 2)

    cv2.putText(img, time_str, (1680, 42), cv2.FONT_HERSHEY_DUPLEX, 0.9, (240, 240, 240), 2)

    # 7. OSD FOOTER BAR (Góc dưới camera)
    cv2.rectangle(img, (0, h - 45), (w, h), (20, 18, 18), -1)
    footer_text = f"FHD 1920x1080 | CODE: LOP_{cls_info['code']} | NGUON: NVR-DAHUA-P1 | KHOI: {cls_info['grade']}"
    cv2.putText(img, footer_text, (25, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (190, 195, 200), 1)

    if is_video:
        blink = (frame_idx // 15) % 2 == 0
        if blink:
            cv2.circle(img, (1620, h - 22), 8, (0, 0, 255), -1)
        cv2.putText(img, f"REC 15s | Frame {frame_idx + 1:03d}/225", 
                    (1640, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255) if blink else (150, 150, 150), 2)
    else:
        cv2.putText(img, f"ANH MAU CHAT LUONG CAO #{frame_idx}", 
                    (1600, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 220, 240), 1)

    return img

def generate_classrooms_dataset():
    """
    Hàm thực thi chính:
    Tạo toàn bộ cấu trúc thư mục, 5 ảnh và 1 video 15s cho 30 lớp học,
    kèm theo info.json, file Excel và tệp hướng dẫn.
    """
    start_time = time.time()
    OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)

    print("=============================================================================")
    print("   BẮT ĐẦU TẠO BỘ DỮ LIỆU ĐA PHƯƠNG TIỆN 30 LỚP HỌC - THPT ĐIỀU CẢI")
    print(f"   Thư mục tổng: {OUTPUT_BASE_DIR}")
    print("=============================================================================")

    total_classes = len(CLASSROOMS_DATA)
    master_summary = []
    total_images_generated = 0
    total_videos_generated = 0

    for idx, cls in enumerate(CLASSROOMS_DATA, 1):
        class_folder_name = f"Lop_{cls['code']}"
        class_dir = OUTPUT_BASE_DIR / class_folder_name
        class_dir.mkdir(parents=True, exist_ok=True)

        std_count = cls["standard_count"]
        print(f"\n[{idx:02d}/{total_classes:02d}] Đang xử lý {cls['name']} ({cls['room']}, Sĩ số chuẩn: {std_count} HS)...")

        images_plan = [
            {"id": 1, "present": std_count, "absent": 0, "desc": "Ảnh 1 - Đầu giờ học sinh đủ 100% sĩ số", "time": "06:45:01"},
            {"id": 2, "present": std_count - 1, "absent": 1, "desc": "Ảnh 2 - Vắng 1 học sinh dãy bàn cuối", "time": "06:45:04"},
            {"id": 3, "present": std_count - 1, "absent": 1, "desc": "Ảnh 3 - Vắng 1 học sinh dãy giữa", "time": "06:45:08"},
            {"id": 4, "present": std_count - 2, "absent": 2, "desc": "Ảnh 4 - Vắng 2 học sinh có phép", "time": "06:45:11"},
            {"id": 5, "present": std_count, "absent": 0, "desc": "Ảnh 5 - Kiểm tra sĩ số chốt giờ vào lớp", "time": "06:45:15"},
        ]

        images_meta = []
        for plan in images_plan:
            img = render_classroom_scene(
                cls_info=cls,
                present_count=plan["present"],
                frame_idx=plan["id"],
                time_str=plan["time"],
                is_video=False
            )
            img_filename = f"image_{plan['id']}.jpg"
            img_path = class_dir / img_filename
            cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            total_images_generated += 1

            images_meta.append({
                "file_name": img_filename,
                "relative_path": f"{class_folder_name}/{img_filename}",
                "resolution": "1920x1080",
                "standard_count": std_count,
                "present_count": plan["present"],
                "absent_count": plan["absent"],
                "timestamp": plan["time"],
                "description": plan["desc"]
            })

        # Tạo 1 video thời lượng đúng 15 giây (15 fps = 225 frames)
        video_filename = "video_15s.mp4"
        video_path = class_dir / video_filename
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        vid_writer = cv2.VideoWriter(str(video_path), fourcc, 15, (1920, 1080))

        vid_absent = 1 if (idx % 2 == 0) else 0
        vid_present = std_count - vid_absent

        for frame_num in range(225):
            sec = frame_num // 15
            vid_time = f"06:45:{sec:02d}"
            frame = render_classroom_scene(
                cls_info=cls,
                present_count=vid_present,
                frame_idx=frame_num,
                time_str=vid_time,
                is_video=True,
                motion_seed=idx * 1.7
            )
            vid_writer.write(frame)
        vid_writer.release()
        total_videos_generated += 1

        video_meta = {
            "file_name": video_filename,
            "relative_path": f"{class_folder_name}/{video_filename}",
            "duration_seconds": 15,
            "fps": 15,
            "total_frames": 225,
            "resolution": "1920x1080",
            "standard_count": std_count,
            "present_count": vid_present,
            "absent_count": vid_absent,
            "time_range": "06:45:00 - 06:45:15",
            "description": f"Video giám sát 15s lớp {cls['name']} Full HD"
        }

        # Tạo file info.json cho từng lớp
        class_info_data = {
            "class_code": f"LOP_{cls['code']}",
            "class_name": cls["name"],
            "grade": cls["grade"],
            "room_number": cls["room"],
            "standard_count": std_count,
            "total_images": 5,
            "total_videos": 1,
            "video_duration_seconds": 15,
            "images": images_meta,
            "video": video_meta
        }
        with open(class_dir / "info.json", "w", encoding="utf-8") as f:
            json.dump(class_info_data, f, ensure_ascii=False, indent=2)

        # Tạo file text thông tin lớp
        with open(class_dir / "thong_tin_lop.txt", "w", encoding="utf-8") as f:
            f.write(f"TRƯỜNG THPT ĐIỀU CẢI - THÔNG TIN LỚP HỌC\n")
            f.write(f"----------------------------------------\n")
            f.write(f"Lớp:               {cls['name']}\n")
            f.write(f"Mã định danh:      LOP_{cls['code']}\n")
            f.write(f"Khối học:          Khối {cls['grade']}\n")
            f.write(f"Phòng học:         {cls['room']}\n")
            f.write(f"Sĩ số chuẩn:       {std_count} học sinh\n")
            f.write(f"Số lượng ảnh cấp:  5 ảnh (1920x1080)\n")
            f.write(f"Số lượng video:    1 video 15 giây (225 khung hình, 15 fps)\n")
            f.write(f"Tình trạng video:  Hiện diện {vid_present} HS | Vắng {vid_absent} HS\n")

        master_summary.append({
            "stt": idx,
            "code": f"LOP_{cls['code']}",
            "name": cls["name"],
            "grade": cls["grade"],
            "room": cls["room"],
            "standard_count": std_count,
            "folder": class_folder_name,
            "images_count": 5,
            "video_file": f"{class_folder_name}/{video_filename}",
            "sample_image": f"{class_folder_name}/image_1.jpg"
        })

    # 8. Xuất file master JSON toàn trường
    with open(OUTPUT_BASE_DIR / "danh_sach_si_so_toan_truong.json", "w", encoding="utf-8") as f:
        json.dump({
            "school_name": "Trường THPT Điều Cải",
            "total_classes": total_classes,
            "total_standard_students": sum(c["standard_count"] for c in CLASSROOMS_DATA),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "classes": master_summary
        }, f, ensure_ascii=False, indent=2)

    # 9. Xuất file Excel báo cáo sĩ số toàn trường chuẩn hóa
    export_excel_summary(master_summary, OUTPUT_BASE_DIR / "danh_sach_si_so_toan_truong.xlsx")

    # 10. Tạo file README.md cho thư mục tổng
    generate_readme_file(OUTPUT_BASE_DIR, total_classes)

    elapsed = time.time() - start_time
    print("\n=============================================================================")
    print(f"[HOÀN TẤT THÀNH CÔNG] Đã cấp đủ dữ liệu đa phương tiện cho {total_classes} lớp!")
    print(f" - Tổng số ảnh Full HD đã tạo:    {total_images_generated} ảnh (5 ảnh/lớp)")
    print(f" - Tổng số video 15s đã tạo:       {total_videos_generated} video (1 video 15s/lớp)")
    print(f" - Tệp Excel tổng hợp sĩ số:       {OUTPUT_BASE_DIR / 'danh_sach_si_so_toan_truong.xlsx'}")
    print(f" - Tệp JSON thông tin toàn trường: {OUTPUT_BASE_DIR / 'danh_sach_si_so_toan_truong.json'}")
    print(f" - Thời gian thực thi:             {elapsed:.2f} giây")
    print("=============================================================================")

def export_excel_summary(classes_summary: list, excel_path: Path):
    """Xuất file Excel trình bày chuyên nghiệp danh sách sĩ số 30 lớp học."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sĩ Số 30 Lớp Học"

    # Font styles
    title_font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
    subtitle_font = Font(name="Calibri", size=11, italic=True, color="475569")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=11)
    bold_font = Font(name="Calibri", size=11, bold=True)

    header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
    total_fill = PatternFill(start_color="E0E7FF", end_color="E0E7FF", fill_type="solid")
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    # Tiêu đề
    ws.merge_cells("A1:G1")
    ws["A1"] = "TRƯỜNG TRUNG HỌC PHỔ THÔNG ĐIỀU CẢI"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A2:G2")
    ws["A2"] = "DANH SÁCH SĨ SỐ CHUẨN VÀ DỮ LIỆU ĐA PHƯƠNG TIỆN 30 LỚP HỌC"
    ws["A2"].font = Font(name="Calibri", size=13, bold=True, color="0F172A")
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A3:G3")
    ws["A3"] = f"Ngày cập nhật: {time.strftime('%d/%m/%Y')} | Mỗi lớp gồm 5 ảnh Full HD và 1 video 15 giây"
    ws["A3"].font = subtitle_font
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

    # Header bảng
    headers = [
        ("STT", 8),
        ("Khối", 10),
        ("Mã Lớp", 15),
        ("Tên Lớp", 16),
        ("Phòng Học", 15),
        ("Sĩ Số Chuẩn (HS)", 18),
        ("Thư Mục Chứa Dữ Liệu", 28)
    ]

    for col_num, (h_title, h_width) in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_num, value=h_title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        col_letter = get_column_letter(col_num)
        ws.column_dimensions[col_letter].width = h_width

    # Ghi dữ liệu 30 lớp
    total_std = 0
    start_row = 6
    for idx, c in enumerate(classes_summary):
        row_num = start_row + idx
        total_std += c["standard_count"]

        cells = [
            (c["stt"], "center"),
            (f"Khối {c['grade']}", "center"),
            (c["code"], "center"),
            (c["name"], "center"),
            (c["room"], "center"),
            (c["standard_count"], "center"),
            (f"classrooms_media/{c['folder']}/", "left")
        ]

        row_fill = alt_fill if idx % 2 == 1 else None
        for col_num, (val, align) in enumerate(cells, 1):
            cell = ws.cell(row=row_num, column=col_num, value=val)
            cell.font = data_font
            cell.alignment = Alignment(horizontal=align, vertical="center")
            cell.border = thin_border
            if row_fill:
                cell.fill = row_fill

    # Hàng tổng cộng
    total_row = start_row + len(classes_summary)
    ws.merge_cells(f"A{total_row}:E{total_row}")
    sum_cell = ws.cell(row=total_row, column=1, value="TỔNG CỘNG TOÀN TRƯỜNG (30 LỚP)")
    sum_cell.font = bold_font
    sum_cell.alignment = Alignment(horizontal="center", vertical="center")
    sum_cell.fill = total_fill

    for c in range(1, 6):
        ws.cell(row=total_row, column=c).border = thin_border
        ws.cell(row=total_row, column=c).fill = total_fill

    std_sum_cell = ws.cell(row=total_row, column=6, value=total_std)
    std_sum_cell.font = bold_font
    std_sum_cell.alignment = Alignment(horizontal="center", vertical="center")
    std_sum_cell.border = thin_border
    std_sum_cell.fill = total_fill

    end_cell = ws.cell(row=total_row, column=7, value="30 Thư mục | 150 Ảnh | 30 Video")
    end_cell.font = bold_font
    end_cell.alignment = Alignment(horizontal="center", vertical="center")
    end_cell.border = thin_border
    end_cell.fill = total_fill

    wb.save(str(excel_path))

def generate_readme_file(target_dir: Path, total_classes: int):
    """Tạo tệp README.md hướng dẫn cấu trúc thư mục và thông tin sĩ số."""
    readme_content = f"""# BỘ DỮ LIỆU ĐA PHƯƠNG TIỆN 30 LỚP HỌC - TRƯỜNG THPT ĐIỀU CẢI

Bộ dữ liệu cung cấp đầy đủ **5 hình ảnh Full HD** và **1 video 15 giây chuẩn** cho từng lớp trong tổng số **{total_classes} lớp học** của Trường THPT Điều Cải, phục vụ điểm danh AI tự động, thử nghiệm kiểm chuẩn benchmark và giả lập nguồn camera cục bộ.

## 1. Cấu Trúc Thư Mục

```text
dataset/classrooms_media/
├── danh_sach_si_so_toan_truong.xlsx   <- Báo cáo Excel chi tiết sĩ số 30 lớp
├── danh_sach_si_so_toan_truong.json   <- Dữ liệu cấu trúc JSON toàn trường
├── README.md                          <- Tài liệu thuyết minh bộ dữ liệu
│
├── Lop_10A1/                          <- Thư mục riêng từng lớp
│   ├── image_1.jpg                    <- Ảnh Full HD 1920x1080 (Đủ 100% sĩ số)
│   ├── image_2.jpg                    <- Ảnh Full HD 1920x1080 (Vắng 1 HS)
│   ├── image_3.jpg                    <- Ảnh Full HD 1920x1080 (Góc nhìn học tập)
│   ├── image_4.jpg                    <- Ảnh Full HD 1920x1080 (Vắng 2 HS)
│   ├── image_5.jpg                    <- Ảnh Full HD 1920x1080 (Kiểm tra chốt)
│   ├── video_15s.mp4                  <- Video chuẩn 15 giây (225 frames, 15fps)
│   ├── info.json                      <- Siêu dữ liệu máy đọc về sĩ số và tệp tin
│   └── thong_tin_lop.txt              <- Thông tin lớp dạng văn bản ngắn gọn
├── Lop_10A2/
...
└── Lop_12A10/
```

## 2. Bảng Thống Kê Sĩ Số Học Sinh 30 Lớp

| STT | Khối | Mã Lớp | Tên Lớp | Phòng Học | Sĩ Số Chuẩn | Số Ảnh Cấp | Video Cấp |
|:---:|:---:|:---:|:---|:---:|:---:|:---:|:---:|
| 01 | 10 | LOP_10A1 | Lớp 10A1 | Phòng 101 | **42** | 5 ảnh 1080p | 1 video 15s |
| 02 | 10 | LOP_10A2 | Lớp 10A2 | Phòng 102 | **40** | 5 ảnh 1080p | 1 video 15s |
| 03 | 10 | LOP_10A3 | Lớp 10A3 | Phòng 103 | **41** | 5 ảnh 1080p | 1 video 15s |
| 04 | 10 | LOP_10A4 | Lớp 10A4 | Phòng 104 | **43** | 5 ảnh 1080p | 1 video 15s |
| 05 | 10 | LOP_10A5 | Lớp 10A5 | Phòng 105 | **39** | 5 ảnh 1080p | 1 video 15s |
| 06 | 10 | LOP_10A6 | Lớp 10A6 | Phòng 106 | **42** | 5 ảnh 1080p | 1 video 15s |
| 07 | 10 | LOP_10A7 | Lớp 10A7 | Phòng 107 | **40** | 5 ảnh 1080p | 1 video 15s |
| 08 | 10 | LOP_10A8 | Lớp 10A8 | Phòng 108 | **41** | 5 ảnh 1080p | 1 video 15s |
| 09 | 10 | LOP_10A9 | Lớp 10A9 | Phòng 109 | **40** | 5 ảnh 1080p | 1 video 15s |
| 10 | 10 | LOP_10A10 | Lớp 10A10 | Phòng 110 | **42** | 5 ảnh 1080p | 1 video 15s |
| 11 | 11 | LOP_11A1 | Lớp 11A1 | Phòng 111 | **44** | 5 ảnh 1080p | 1 video 15s |
| 12 | 11 | LOP_11A2 | Lớp 11A2 | Phòng 112 | **43** | 5 ảnh 1080p | 1 video 15s |
| 13 | 11 | LOP_11A3 | Lớp 11A3 | Phòng 113 | **42** | 5 ảnh 1080p | 1 video 15s |
| 14 | 11 | LOP_11A4 | Lớp 11A4 | Phòng 114 | **40** | 5 ảnh 1080p | 1 video 15s |
| 15 | 11 | LOP_11A5 | Lớp 11A5 | Phòng 115 | **41** | 5 ảnh 1080p | 1 video 15s |
| 16 | 11 | LOP_11A6 | Lớp 11A6 | Phòng 116 | **42** | 5 ảnh 1080p | 1 video 15s |
| 17 | 11 | LOP_11A7 | Lớp 11A7 | Phòng 117 | **39** | 5 ảnh 1080p | 1 video 15s |
| 18 | 11 | LOP_11A8 | Lớp 11A8 | Phòng 118 | **41** | 5 ảnh 1080p | 1 video 15s |
| 19 | 11 | LOP_11A9 | Lớp 11A9 | Phòng 119 | **40** | 5 ảnh 1080p | 1 video 15s |
| 20 | 11 | LOP_11A10 | Lớp 11A10 | Phòng 120 | **43** | 5 ảnh 1080p | 1 video 15s |
| 21 | 12 | LOP_12A1 | Lớp 12A1 | Phòng 121 | **45** | 5 ảnh 1080p | 1 video 15s |
| 22 | 12 | LOP_12A2 | Lớp 12A2 | Phòng 122 | **44** | 5 ảnh 1080p | 1 video 15s |
| 23 | 12 | LOP_12A3 | Lớp 12A3 | Phòng 123 | **42** | 5 ảnh 1080p | 1 video 15s |
| 24 | 12 | LOP_12A4 | Lớp 12A4 | Phòng 124 | **43** | 5 ảnh 1080p | 1 video 15s |
| 25 | 12 | LOP_12A5 | Lớp 12A5 | Phòng 125 | **41** | 5 ảnh 1080p | 1 video 15s |
| 26 | 12 | LOP_12A6 | Lớp 12A6 | Phòng 126 | **40** | 5 ảnh 1080p | 1 video 15s |
| 27 | 12 | LOP_12A7 | Lớp 12A7 | Phòng 127 | **42** | 5 ảnh 1080p | 1 video 15s |
| 28 | 12 | LOP_12A8 | Lớp 12A8 | Phòng 128 | **41** | 5 ảnh 1080p | 1 video 15s |
| 29 | 12 | LOP_12A9 | Lớp 12A9 | Phòng 129 | **40** | 5 ảnh 1080p | 1 video 15s |
| 30 | 12 | LOP_12A10 | Lớp 12A10 | Phòng 130 | **42** | 5 ảnh 1080p | 1 video 15s |
| **TỔNG** | - | **30 Lớp** | **Toàn Trường** | **30 Phòng** | **1.245 HS** | **150 Ảnh** | **30 Video** |

## 3. Cách Sử Dụng Trong Hệ Thống Điểm Danh

1. **Dùng làm nguồn giả lập camera cho lớp học:**
   - Trong trang Quản lý Camera (`cameras.html`), chọn loại nguồn **File cục bộ**.
   - Nhập đường dẫn: `dataset/classrooms_media/Lop_10A1/video_15s.mp4` hoặc `dataset/classrooms_media/Lop_10A1/image_1.jpg`.
2. **Khởi chạy quét điểm danh toàn diện:**
   - Hệ thống AI sẽ đọc trực tiếp khung hình từ file video/ảnh, áp dụng nhận diện YOLOv8 và đối soát chuẩn xác với sĩ số lớp.
"""
    with open(target_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

if __name__ == "__main__":
    generate_classrooms_dataset()
