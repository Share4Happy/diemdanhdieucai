# BẢN THIẾT KẾ KIẾN TRÚC HỆ THỐNG & PHÂN CHIA VAI TRÒ DỰ ÁN
## HỆ THỐNG ĐIỂM DANH HỌC SINH TỰ ĐỘNG BẰNG AI CAMERA - THPT ĐIỀU CẢI

Tài liệu này định nghĩa cấu trúc phân tầng (Multi-tier Architecture) của dự án, quy ước giao tiếp giữa các phân hệ và hướng dẫn phân chia nhân sự để phát triển song song mà **không gây xung đột hay ảnh hưởng lẫn nhau**.

---

## 1. Sơ Đồ Kiến Trúc Tổng Thể

```mermaid
graph TD
    subgraph "1. LỚP TRÌNH DIỄN (FRONTEND)"
        UI_Dash["Dashboard Điểm Danh<br/>(index.html / dashboard.js)"]
        UI_Cam["Quản Lý Camera<br/>(cameras.html / cameras.js)"]
        UI_ROI["Cấu Hình Vùng ROI<br/>(roi-config.html / roi_config.js)"]
        UI_Rep["Báo Cáo & Thống Kê<br/>(reports.html / reports.js)"]
        API_Client["API Client Trung Tâm<br/>(frontend/js/api.js)"]
        UI_Dash --> API_Client
        UI_Cam --> API_Client
        UI_ROI --> API_Client
        UI_Rep --> API_Client
    end

    subgraph "2. LỚP DỊCH VỤ & API (BACKEND)"
        API_GW["FastAPI App Router<br/>(backend/main.py)"]
        R_Att["Router Điểm Danh (/api/attendance)"]
        R_Cam["Router Camera (/api/cameras)"]
        R_ROI["Router Vùng ROI (/api/roi)"]
        R_Rep["Router Báo Cáo (/api/reports)"]
        R_Sys["Router Hệ Thống (/api/system)"]
        
        API_Client -- "REST API (HTTP / JSON)" --> API_GW
        API_GW --> R_Att
        API_GW --> R_Cam
        API_GW --> R_ROI
        API_GW --> R_Rep
        API_GW --> R_Sys
    end

    subgraph "3. LỚP NGHIỆP VỤ CỐT LÕI (CORE & SERVICES)"
        Engine["attendance_engine.py<br/>(Bộ điều phối quét 30 lớp)"]
        Detector["detector.py<br/>(AI YOLOv8 + Tiled SAHI)"]
        RTSP["rtsp_client.py<br/>(Thu nhận luồng hình ảnh)"]
        Relay["relay_service.py<br/>(Điều khiển đèn LED)"]
        ROIMgr["roi_manager.py<br/>(Tọa độ Red/Green Zone)"]
        ExcelSvc["excel_exporter.py<br/>(Xuất file Excel)"]
        ZaloSvc["zalo_service.py<br/>(Gửi tin nhắn Zalo)"]
        Sched["scheduler.py<br/>(Hẹn giờ quét 06:45 AM)"]

        R_Att --> Engine
        Engine --> RTSP
        Engine --> Detector
        Engine --> Relay
        Engine --> ROIMgr
        Engine --> ExcelSvc
        Engine --> ZaloSvc
        Sched --> Engine
    end

    subgraph "4. LỚP CƠ SỞ DỮ LIỆU (DATABASE)"
        DB_Session["Session Local & Engine<br/>(database/db_session.py)"]
        DB_Models["SQLAlchemy ORM Models<br/>(database/models.py)"]
        SQLite_DB[("attendance.db<br/>(SQLite / PostgreSQL)")]

        Engine --> DB_Session
        R_Cam --> DB_Session
        DB_Session --> DB_Models
        DB_Models --> SQLite_DB
    end

    subgraph "5. PHÂN HỆ HUẤN LUYỆN AI (AI TRAINING)"
        TrainScript["train_yolo.py<br/>(Huấn luyện GPU PyTorch)"]
        PrepData["prepare_dataset.py<br/>(Chuẩn hóa nhãn nhãn)"]
        SampleExt["sample_extractor.py<br/>(Trích xuất frame mẫu)"]
        DatasetDir[("dataset/classroom_data<br/>(Ảnh & Nhãn YOLO)")]
        ModelBest[("models/classroom_best.pt<br/>(Trọng số AI)")]

        DatasetDir --> PrepData
        PrepData --> TrainScript
        TrainScript --> ModelBest
        ModelBest -. "Nạp vào khi chạy" .-> Detector
    end
```

---

## 2. Bảng Phân Chia Vai Trò & Trách Nhiệm Từng Nhóm

| Vai Trò | Thư Mục Phụ Trách | Trách Nhiệm Chính | Lệnh Chạy Riêng |
|:---|:---|:---|:---|
| **Frontend Developer** | `frontend/` (`html`, `css`, `js`) | Thiết kế giao diện, vẽ đồ thị Chart.js, hiển thị bảng điểm danh, form camera, cấu hình canvas ROI. Gọi API qua `api.js`. | `run_frontend.bat` (Cổng 3000) |
| **Backend Developer** | `backend/`, `core/`, `services/`, `config/` | Xây dựng REST API, xử lý nghiệp vụ điểm danh, tích hợp Zalo/Excel/Relay, lập lịch tự động, viết test case. | `run_backend.bat` (Cổng 8000) |
| **Database Developer** | `database/` | Thiết kế cấu trúc bảng ORM (`models.py`), quản lý kết nối (`db_session.py`), nạp dữ liệu mẫu, backup dữ liệu. | `python -c "from database.db_session import init_db; init_db()"` |
| **AI Training Engineer** | `training/`, `dataset/`, `models/` | Chuẩn bị dữ liệu ảnh/nhãn, gán nhãn, fine-tuning mô hình YOLOv8 trên GPU NVIDIA RTX, đánh giá mAP/Loss. | `training\train_gpu.bat` |

---

## 3. Quy Ước Cộng Tác (Team Collaboration Rules)

1. **Giao tiếp Frontend - Backend qua Hợp Đồng API (API Contract):**
   - Frontend không truy cập trực tiếp vào CSDL hay thư mục mã nguồn Backend.
   - Toàn bộ dữ liệu được trao đổi qua JSON REST API (`http://localhost:8000/api/...`).
   - Frontend Developer tra cứu định dạng Request/Response tại Swagger UI: `http://localhost:8000/docs`.

2. **Huấn luyện AI độc lập không làm treo hệ thống:**
   - Kỹ sư AI thử nghiệm mô hình trong thư mục `training/`.
   - Quá trình huấn luyện sinh ra file kết quả trong `runs/` và không can thiệp vào các tiến trình Backend đang chạy.
   - Khi có mô hình mới tốt hơn, chỉ cần copy vào `models/classroom_best.pt`.

3. **Cơ chế Tương Thích Ngược 100% (Zero Breaking Change):**
   - Các lệnh chạy quen thuộc ở thư mục gốc (`app.py`, `run.bat`, `train_yolo.py`, `prepare_dataset.py`, `train_gpu.bat`) được giữ nguyên dưới dạng Chuyển tiếp (Proxy), không làm gãy bất kỳ tài liệu hay kịch bản tự động nào trước đây.
