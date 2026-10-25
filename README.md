# 🎓 HỆ THỐNG ĐIỂM DANH HỌC SINH TỰ ĐỘNG BẰNG AI CAMERA
### Trường THPT Điều Cải

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)
![Ultralytics YOLO](https://img.shields.io/badge/Ultralytics-YOLO26%20%2F%20v8-FF7F00?logo=yolo)
![PyTorch CUDA](https://img.shields.io/badge/PyTorch-CUDA%2012.1%20%2F%20RTX%203050-EE4C2C?logo=pytorch)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?logo=opencv)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker)
![Nginx](https://img.shields.io/badge/Nginx-Reverse%20Proxy-009639?logo=nginx)
![Tests](https://img.shields.io/badge/Tests-36%20Passed%20(100%25)-brightgreen)
![Auth](https://img.shields.io/badge/Auth-JWT%20%2B%20HttpOnly%20Cookie-orange)
![Security](https://img.shields.io/badge/Security-Hardened%20Production-success)

Hệ thống điểm danh học sinh thông minh bằng thị giác máy tính AI phục vụ **30 phòng học** (khoảng **1.246 học sinh**) tại **Trường THPT Điều Cải**. Hệ thống ứng dụng kiến trúc phân tầng chuẩn mực (**Clean Layered Architecture**), động cơ điểm danh xoay vòng đa lượt (**Round-Robin Multi-Pass**), cơ chế suy luận AI 2 tầng chịu lỗi cao (**Hybrid Failover AI Engine**), hệ thống bảo mật **JWT HttpOnly Cookie**, tự động quét lúc **06:45 AM**, xuất báo cáo Excel chuẩn mẫu Sở GD&ĐT và gửi thông báo Zalo tức thời.

> 📖 **Tài liệu kiến trúc hệ thống chi tiết**: Xem đầy đủ sơ đồ C4, luồng điểm danh đa vòng và kiến trúc an ninh tại [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 🌟 TÍNH NĂNG NỔI BẬT

### 1. Cơ Chế Điểm Danh Đa Lượt Xoay Vòng (Round-Robin Multi-Pass Batches)
- **Khắc phục triệt để điểm mù chụp 1 lần:** Thay vì chỉ chụp 1 bức ảnh tĩnh duy nhất (dễ bị sai số khi học sinh cúi đầu, xoay người trao đổi hoặc rớt gói tin RTSP), hệ thống thực hiện quét xoay vòng toàn trường **8 - 10 lượt** (mỗi lượt cách nhau 10 giây).
- **Thuật toán Bầu Chọn Trọng Số (Confidence-Weighted Frequency Mode):** Tự động phân nhóm kết quả điểm danh theo mức sĩ số, tính điểm trọng số kết hợp độ tin cậy AI ($\text{Confidence}$) và độ nét ảnh ($\text{Laplacian Sharpness}$). Mức sĩ số có tổng điểm cao nhất sẽ được chốt làm kết quả chính thức.
- **Tự động chọn ảnh đối chứng tốt nhất:** Lưu trữ khung hình nét nhất, có độ tin cậy AI cao nhất trong nhóm chiến thắng làm bằng chứng CSDL và hiển thị trên giao diện đối chứng.

### 2. Kiến Trúc Suy Luận AI 2 Tầng Chịu Lỗi Cao (Hybrid Failover AI)
- **Tầng 1 - Microservice Chuyên Biệt (`/api/predict`):** Ưu tiên kết nối tới service `student-detection` chạy trên GPU máy chủ, tích hợp mô hình phát hiện đầu học sinh (`student_head`) và mô hình phân tích không gian chiều sâu phòng học (**Depth Anything V2**) để loại trừ triệt để hiện tượng che khuất trước - sau qua thuật toán **Depth-NMS**.
- **Tầng 2 - Fallback Cục Bộ An Toàn (Offline Safety Net):** Khi mạng LAN gián đoạn hoặc microservice AI ngoại vi gặp sự cố, hệ thống tự động kích hoạt model cục bộ [`data/models/yolo26m.pt`](data/models/yolo26m.pt) trong bộ nhớ để tiếp tục điểm danh mà không làm gián đoạn ca làm việc của trường học.

### 3. Bộ Lọc Khung Hình Thông Minh (Video Stream Quality Assurance)
- **Loại bỏ khung hình lỗi decoder:** Tự động phát hiện và loại bỏ các khung hình lỗi macroblock, sọc xanh lá, khung hình xám un-synced (P-frame chưa có I-frame).
- **Chống vỡ luồng kéo sọc dọc (Vertical Smear Filter):** Thuật toán tính toán sai phân đạo hàm dọc $dy / dx$ phát hiện hiện tượng kéo dải pixel khi mất gói mạng RTSP.
- **Tăng tốc lấy mẫu qua Fast HTTP Snapshot:** Tự động dò tìm endpoint chụp ảnh tĩnh siêu tốc (`ISAPI picture` / `snapshot.cgi`) của Hikvision/Dahua, rút ngắn thời gian lấy mẫu từ 2-3s xuống còn ~150-300ms.

### 4. Quản Lý Camera & Ma Trận Giám Sát (Camera Matrix Wall)
- **Quản lý đa dạng giao thức:** Hỗ trợ camera IP RTSP/RTSPS, luồng phụ Sub-stream tải nhẹ, đầu ghi NVR đa kênh, webcam và file video mô phỏng.
- **Trình dò tìm kênh NVR tự động (NVR Wizard):** Tự động phát hiện danh sách kênh từ đầu ghi qua giao thức ONVIF/ISAPI và nhập hàng loạt vào CSDL trường học.
- **Điều khiển tín hiệu đèn hồng ngoại:** Kích hoạt đèn rơ-le nhấp nháy 3 giây trước giờ điểm danh để học sinh ổn định vị trí ngồi.

### 5. Tự Động Hóa Vận Hành & Báo Cáo Sở GD&ĐT
- **Lập lịch tự động 06:45 AM:** Tự động vận hành từ Thứ 2 đến Thứ 7 thông qua **APScheduler**.
- **Xuất báo cáo Excel (.xlsx):** Định dạng bảng biểu chuẩn Sở GD&ĐT, tự động phân loại học sinh có mặt, vắng mặt có phép/không phép.
- **Đa kênh thông báo:** Tự động gửi tin nhắn báo cáo sĩ số qua **Zalo Bot Gateway / Zalo OA** và gửi email kèm file Excel tới Ban Giám Hiệu.
- **Sao lưu đám mây:** Đồng bộ CSDL và báo cáo lên **Google Drive** theo lịch trình hàng ngày.

---

## 🔒 AN NINH & BẢO MẬT (HARDENED SECURITY)

Hệ thống được thiết kế theo mô hình phòng vệ chiều sâu (**Defense-in-Depth**):

| Tầng bảo vệ | Cơ chế triển khai | Mục tiêu bảo mật |
| :--- | :--- | :--- |
| **Cô lập Cổng Mạng** | Backend chỉ bind cổng `127.0.0.1:8000:8000` trong Docker | Chặn đứng 100% các cuộc tấn công quét cổng trực tiếp từ Internet vào FastAPI. |
| **Đóng Swagger khi Deploy** | Tự động tắt `/docs`, `/redoc`, `/openapi.json` khi `DEBUG=false` | Loại bỏ nguy cơ lộ cấu trúc API nhạy cảm ra ngoài thế giới. |
| **Xác thực JWT An Toàn** | Token mã hóa `HS256`, lưu trữ trong **HttpOnly Cookie** (`SameSite=Lax`) | Miễn nhiễm hoàn toàn với các cuộc tấn công XSS và CSRF. |
| **Thu hồi phiên tức thì** | Lưu `jti` vào danh sách đen trong RAM khi người dùng Logout | Vô hiệu hóa token ngay lập tức khi đăng xuất. |
| **Phân quyền RBAC** | Middleware `get_current_user` và `require_admin` | Chặn tài khoản thường can thiệp vào cấu hình camera, NVR hoặc CSDL. |
| **Tường lửa Chống Brute-force** | Rate-limiting trượt (10 lần/IP/5 phút, 15 lần/Email/15 phút) | Chống tấn công dò mật khẩu quản trị viên. |
| **Chống SSRF & LFI** | Bộ lọc `validate_stream_source` chặn `file://`, `127.0.0.1`, `169.254.x.x` | Chống đọc trộm file hệ thống và chống tấn công hạ tầng máy chủ. |
| **HTTP Security Headers** | Nginx chèn `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection` | Chống Clickjacking, MIME type sniffing và chèn script chéo trang. |

---

## 🏛️ SƠ ĐỒ CẤU TRÚC THƯ MỤC CHUẨN HÓA

```text
hethongdiemdanh-dieucai/
│
├── 🎨 frontend/                     # GIAO DIỆN NGƯỜI DÙNG WEB SPA (Glassmorphism UI)
│   ├── index.html                  # Dashboard giám sát sĩ số 30 lớp thời gian thực
│   ├── login.html                  # Đăng nhập an toàn xác thực Cookie
│   ├── classrooms.html             # Quản lý danh mục lớp học & phân phòng
│   ├── cameras.html                # Quản lý camera, quét NVR & xem ma trận Camera Wall
│   ├── reports.html                # Báo cáo tổng hợp, xem ảnh đối chứng & xuất Excel
│   ├── settings.html               # Cấu hình hệ thống, quản trị người dùng, Zalo & Email
│   ├── notifications.html          # Lịch sử thông báo tự động
│   ├── css/                        # Hệ thống CSS Design System (variables, typography, layout)
│   └── js/                         # API Client trung tâm (api.js) và các module chức năng
│
├── ⚙️ backend/app/                  # MÁY CHỦ REST API (FastAPI Framework)
│   ├── main.py                     # Khởi tạo FastAPI, CORS, Middleware & Lifespan
│   ├── api/
│   │   ├── deps.py                 # Dependency Injection (Cấp phát DB Session, Auth User)
│   │   ├── security.py             # Bộ lọc an ninh (Rate limiting, SSRF, URL masking)
│   │   └── routers/                # Các APIRouter chuẩn hóa:
│   │       ├── attendance.py       # API Quét điểm danh & quản lý phiên
│   │       ├── cameras.py          # API Quản lý Camera, NVR Discovery & Snapshot Live
│   │       ├── classrooms.py       # API Danh mục lớp học
│   │       ├── reports.py          # API Lịch sử điểm danh & xuất Excel
│   │       ├── auth.py             # API Đăng nhập, Đăng xuất, Phân quyền RBAC
│   │       ├── backup.py           # API Sao lưu CSDL local & Google Drive
│   │       ├── predict.py          # API Suy luận AI Depth-NMS & Proxy Microservice
│   │       └── system.py           # API Giám sát tài nguyên máy chủ & Health Check
│   ├── core/                       # CỐT LÕI AI & GIAO TIẾP PHẦN CỨNG
│   │   ├── attendance_engine.py    # Động cơ điều phối quét đa vòng (Round-Robin Multi-Pass)
│   │   ├── rtsp_client.py          # Thu nhận luồng RTSP đa luồng & HTTP Snapshot
│   │   ├── detector.py             # Bộ nhận diện AI cục bộ dự phòng (Fallback Safety Net)
│   │   ├── raw_ai_engine.py        # Thuật toán vẽ đối chứng chấm tròn phát sáng neon
│   │   └── relay_service.py        # Giao tiếp điều khiển rơ-le đèn tín hiệu camera
│   ├── services/                   # DỊCH VỤ NGOẠI VI
│   │   ├── zalo_service.py         # Gửi tin nhắn qua Zalo Bot Gateway / Zalo OA
│   │   ├── email_service.py        # Gửi email SMTP thông báo BGH
│   │   ├── excel_exporter.py       # Xuất file Excel chuẩn quy cách Sở GD&ĐT
│   │   ├── gdrive_service.py       # Tích hợp OAuth 2.0 sao lưu Google Drive
│   │   └── scheduler.py            # Lập lịch tự động quét lúc 06:45 AM (APScheduler)
│   ├── database/                   # TẦNG CƠ SỞ DỮ LIỆU
│   │   ├── models.py               # ORM Models (Classroom, AttendanceSession, User...)
│   │   └── db_session.py           # Kết nối SessionLocal & Khởi tạo dữ liệu mẫu
│   └── config/                     # Cấu hình tập trung (settings.py, logging_config.py)
│
├── 📦 data/                         # THƯ MỤC DỮ LIỆU RUNTIME (Mount vào Docker)
│   ├── database/attendance.db      # Tệp CSDL SQLite chính thức
│   ├── models/yolo26m.pt           # Trọng số mô hình AI dự phòng cục bộ (44.25 MB)
│   ├── storage/                    # Ảnh captures gốc, ảnh đối chứng AI, báo cáo Excel
│   └── dataset/                    # Dữ liệu ảnh máy học phục vụ huấn luyện
│
├── 🐳 docker/                       # CẤU HÌNH DOCKER & NGINX
│   ├── backend/Dockerfile          # Container Backend FastAPI (Python 3.10)
│   └── frontend/nginx.conf         # Nginx Reverse Proxy, Gzip, Security Headers
│
├── 🧪 tests/                        # BỘ KIỂM THỬ TỰ ĐỘNG (36/36 tests PASSED)
│   ├── conftest.py                 # Fixtures bảo vệ CSDL thật & Test Debug Mode
│   ├── test_attendance_engine.py   # Kiểm tra quy trình quét điểm danh
│   ├── test_camera_management.py   # Kiểm tra nghiệp vụ camera & NVR
│   ├── test_weighted_attendance.py # Kiểm tra thuật toán bầu chọn sĩ số đa vòng
│   └── ...                         # Các bộ kiểm thử tích hợp khác
│
├── student-detection/              # SUBMODULE DỊCH VỤ AI ĐỘC LẬP (/api/predict)
├── docker-compose.yml              # Điều phối cụm container Frontend & Backend
├── requirements.txt                # Danh sách thư viện Python
└── .env                            # Biến môi trường bảo mật
```

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & VẬN HÀNH

### Cách 1: Triển Khai Bằng Docker & Docker Compose (Khuyến nghị cho Production)

Đây là phương pháp chuẩn mực, an toàn và tối ưu nhất cho việc triển khai trường học:

1. **Chuẩn bị file cấu hình môi trường (`.env`):**
   ```env
   # Đặt false để tắt hoàn toàn Swagger UI bảo mật khi deploy
   DEBUG=false

   # Khóa bảo mật JWT (khóa ngẫu nhiên 256-bit)
   JWT_SECRET=81bc0fdf3f5c1960c3302bbcdc19285680a1719d9044219fe09eced850edbec8
   JWT_EXPIRE_HOURS=4320

   # Tài khoản quản trị mặc định ban đầu
   ADMIN_EMAIL=admin@truongdieucai.edu.vn
   ADMIN_PASSWORD=Admin@2025

   # Cấu hình đầu ghi NVR trường học
   DVR_HOST=192.168.1.200
   DVR_PORT=554

   # Tên miền truy cập chính thức (CORS & Link reset mật khẩu)
   APP_PUBLIC_URL=https://eyeai.share4happy.com
   COOKIE_SECURE=false
   ```

2. **Khởi động cụm Container:**
   ```bash
   docker compose up -d --build
   ```

3. **Kiểm tra trạng thái container:**
   ```bash
   docker ps
   ```
   Hệ thống sẽ chạy 2 container độc lập:
   - `diemdanh_dieucai_frontend`: Cổng `3000` (Nginx Gateway).
   - `diemdanh_dieucai_backend`: Cổng nội bộ `127.0.0.1:8000` (FastAPI).

---

### Cách 2: Chạy Trực Tiếp Bằng Môi Trường Python Local

1. **Cài đặt thư viện phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Nếu máy chủ có GPU NVIDIA: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`).*

2. **Khởi động máy chủ backend:**
   - Trên Linux / macOS:
     ```bash
     uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
     ```
   - Trên Windows:
     Nhấp đúp chuột vào file `run.bat`.

---

## 🌐 DANH MỤC TRUY CẬP HỆ THỐNG

| Giao diện / Chức năng | Địa chỉ qua Nginx (Khuyến nghị) | Mô tả chi tiết |
| :--- | :--- | :--- |
| **🔐 Đăng Nhập** | [http://localhost:3000/login](http://localhost:3000/login) | Xác thực danh tính qua HttpOnly Cookie JWT |
| **📊 Dashboard Điểm Danh** | [http://localhost:3000](http://localhost:3000) | Giám sát sĩ số thời gian thực 30 lớp, xem ảnh đối chứng AI |
| **🏫 Danh Mục Lớp Học** | [http://localhost:3000/classrooms](http://localhost:3000/classrooms) | Quản lý danh sách lớp học, phòng học và sĩ số chuẩn |
| **📷 Quản Lý Camera & Ma Trận** | [http://localhost:3000/cameras](http://localhost:3000/cameras) | Thêm, sửa, test kết nối RTSP/NVR, xem Ma Trận Camera Wall |
| **📑 Báo Cáo & Dữ Liệu** | [http://localhost:3000/reports](http://localhost:3000/reports) | Tra cứu lịch sử, xem ảnh Lightbox phóng to, xuất file Excel |
| **⚙️ Cài Đặt & Người Dùng** | [http://localhost:3000/settings](http://localhost:3000/settings) | Quản lý tài khoản, cấu hình Zalo, Email và Google Drive |
| **🔔 Lịch Sử Thông Báo** | [http://localhost:3000/notifications](http://localhost:3000/notifications) | Xem nhật ký các tin nhắn Zalo và Email đã phát đi |
| **📖 Swagger API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | *(Chỉ mở khi `DEBUG=true` trong môi trường phát triển)* |

---

## 🧪 BỘ KIỂM THỬ TỰ ĐỘNG (AUTOMATED TEST SUITE)

Hệ thống tích hợp quy trình kiểm thử tự động toàn diện với kết quả **100% test cases nghiệp vụ PASSED**:

```bash
docker exec diemdanh_dieucai_backend pytest tests/ -v
```

Hoặc chạy trên môi trường Python cục bộ:
```bash
pytest tests/ -v
```

Danh mục các bộ kiểm thử tự động:
1. `tests/test_attendance_engine.py`: Quy trình điều phối quét sĩ số 30 camera và tính toán vắng.
2. `tests/test_weighted_attendance.py`: Kiểm tra thuật toán bầu chọn sĩ số theo trọng số tin cậy và độ nét.
3. `tests/test_camera_management.py`: Kiểm tra thêm, sửa, xóa camera và bảo vệ an ninh luồng RTSP.
4. `tests/test_nvr_import.py`: Kiểm tra cơ chế tự động dò tìm và nạp danh sách kênh NVR.
5. `tests/test_predict_endpoint.py`: Kiểm tra tính toàn vẹn của Endpoint AI Depth-NMS `/api/predict`.
6. `tests/test_camera_wizard_and_frozen_detection.py`: Kiểm tra quy trình Wizard 5 bước thêm camera mới và TTL ảnh.
7. `tests/test_scaling_and_data_integrity.py`: Kiểm tra Semaphore chống nghẽn NVR và kiểm thử HTTP Snapshot.
8. `tests/test_camera_signal_workflow.py`: Kiểm tra kích hoạt tín hiệu đèn hồng ngoại rơ-le.
9. `tests/test_logging_redaction.py`: Kiểm tra tự động che giấu mật khẩu camera trong log hệ thống.
10. `tests/test_roi_masking.py`: Kiểm tra cơ chế quét tương thích toàn khung hình chuẩn hóa.

---

## 📜 BẢN QUYỀN & CHUYỂN GIAO

Dự án được nghiên cứu, phát triển và triển khai thực tế phục vụ đề án chuyển đổi số giáo dục tại:  
**TRƯỜNG TRUNG HỌC PHỔ THÔNG ĐIỀU CẢI**  
*Mọi quyền sở hữu trí tuệ và quyền sử dụng thuộc về nhóm tác giả và nhà trường.*
