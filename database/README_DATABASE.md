# Hướng Dẫn Dành Cho Quản Trị Cơ Sở Dữ Liệu (Database Team)

Phân hệ Database quản lý cấu trúc lưu trữ quan hệ (RDBMS) của hệ thống điểm danh THPT Điều Cải, sử dụng SQLAlchemy ORM tương thích hoàn toàn với SQLite, PostgreSQL và MySQL.

---

## 1. Cấu Trúc Phân Hệ Database

```text
database/
├── models.py                       # Định nghĩa bảng ORM (Entity Relationship)
├── db_session.py                   # Quản lý Engine, Scoped Session & Hàm init_db()
├── attendance.db                   # Tệp CSDL SQLite chính thức
└── attendance_backup_*.db          # Bản sao lưu dự phòng CSDL
```

---

## 2. Sơ Đồ Thực Thể - Quan Hệ (ERD)

```text
+-----------------------+           1 : 1           +-----------------------+
|      Classroom        |---------------------------|      ROIPolygon       |
+-----------------------+                           +-----------------------+
| id (PK)               |                           | id (PK)               |
| code (e.g. LOP_10A1)  |                           | classroom_id (FK)     |
| name                  |                           | red_zone_json (Bàn HS)|
| room_number           |                           | green_zone_json (Bục) |
| standard_count        |                           | image_width / height  |
| rtsp_url              |                           +-----------------------+
| relay_ip              |                                      |
| is_active             |                                      |
+-----------------------+                                      |
           | 1                                                 |
           |                                                   |
           | 1 : N                                             |
           v                                                   v
+-----------------------+           N : 1           +-----------------------+
|   AttendanceDetail    |-------------------------->|   AttendanceSession   |
+-----------------------+                           +-----------------------+
| id (PK)               |                           | id (PK)               |
| session_id (FK)       |                           | session_code          |
| classroom_id (FK)     |                           | scan_date / scan_time |
| standard_count        |                           | total_classes (30)    |
| present_count         |                           | total_standard (1245) |
| absent_count          |                           | total_present         |
| raw_image_path        |                           | total_absent          |
| annotated_image_path  |                           | excel_report_path     |
| confidence_avg        |                           | status                |
+-----------------------+                           +-----------------------+
```

---

## 3. Khởi Tạo & Seed Dữ Liệu Mẫu

Để tái khởi tạo bảng và tự động seed 30 lớp học chuẩn THPT Điều Cải:
```powershell
python -c "from database.db_session import init_db; init_db()"
```
