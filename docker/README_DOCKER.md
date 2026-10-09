# Hướng Dẫn Triển Khai Docker - Hệ Thống Điểm Danh AI THPT Điều Cải

Tài liệu hướng dẫn chi tiết về kiến trúc đóng gói Container hóa (Docker & Docker Compose), phân tách Frontend/Backend và chiến lược lựa chọn Cơ sở dữ liệu (Database).

---

## 1. Kiến Trúc Container Hóa (Decoupled Architecture)

Hệ thống được module hóa thành các container độc lập giao tiếp qua mạng nội bộ Docker (`diemdanh_dieucai_network`):

```text
[ Người Dùng Trình Duyệt / Mạng Trường ]
       │                                │
       ▼ (Port 3000)                    ▼ (Port 8000)
┌───────────────────────────┐    ┌──────────────────────────────────────────────┐
│  Container: FRONTEND      │    │  Container: BACKEND                          │
│  - Image: nginx:alpine    │    │  - Image: python:3.10-slim                   │
│  - Nginx Web Server       │───>│  - FastAPI REST API Server                   │
│  - Phục vụ HTML/CSS/JS    │    │  - AI Vision: Ultralytics YOLO26m            │
│  - Reverse Proxy /api/    │    │  - Xử lý RTSP Camera 30 phòng học            │
│  - Nén Gzip & Caching     │    │  - Cơ chế lập lịch tự động (APScheduler)     │
└───────────────────────────┘    └──────────────────────┬───────────────────────┘
                                                        │
                         ┌──────────────────────────────┴──────────────────────────────┐
                         ▼ (Mặc định - Khuyến nghị)                                    ▼ (Tùy chọn mở rộng)
               ┌──────────────────────────┐                                  ┌──────────────────────────┐
               │  Cơ Sở Dữ Liệu: SQLite   │                                  │  Container: PostgreSQL   │
               │  - File: attendance.db   │                                  │  - Image: postgres:16    │
               │  - Gắn qua Docker Volume │                                  │  - Profile: postgres     │
               │  - Backup Google Drive   │                                  │  - Dành cho Multi-tenant │
               └──────────────────────────┘                                  └──────────────────────────┘
```

---

## 2. Trả Lời: Có Cần Thêm Database Độc Lập Không?

### Khuyến nghị kỹ thuật: **KHÔNG BẮT BUỘC, VÀ NÊN GIỮ SQLITE LÀM MẶC ĐỊNH.**

| Tiêu chí | SQLite (Mặc định) | PostgreSQL (Container riêng) |
| :--- | :--- | :--- |
| **Tài nguyên tiêu tốn** | **0 MB RAM phụ** (Tích hợp sẵn trong Python) | Thêm **150 - 300 MB RAM** chạy ngầm |
| **Quy mô trường Điều Cải** | **Hoàn toàn dư thừa** (30 camera, ~1245 học sinh, 30-60 bản ghi/ngày) | Phù hợp khi mở rộng cụm hàng trăm trường học |
| **Tính toàn vẹn & Lưu trữ** | Gắn qua Docker volume `./database`, không mất dữ liệu | Gắn qua Docker volume `pgdata` |
| **Sao lưu Google Drive 1-click** | **Tương thích hoàn hảo 100%**: dùng SQLite Backup API nén `.zip` gửi Drive tự động | Cần viết thêm kịch bản `pg_dump` riêng |
| **Độ phức tạp vận hành** | Zero configuration, không cần quản lý port, password DB | Cần quản trị mạng container, user/pass, connection pool |

> **Kết luận:**
> Đối với quy mô trường THPT Điều Cải, **SQLite là giải pháp tối ưu nhất** về hiệu năng, độ ổn định và chi phí vận hành phần cứng.
> Tuy nhiên, hệ thống đã được thiết kế **sẵn sàng 100% cho PostgreSQL** nếu sau này cần tích hợp vào CSDL tập trung của Sở GD&ĐT.

---

## 3. Các Lệnh Khởi Chạy Nhanh

### Cách 1: Sử dụng Batch Script 1-Click (Dành cho Windows)
- **Khởi động hệ thống:** Chạy file [scripts/docker_start.bat](file:///d:/Projects/diemdanhdieucai/scripts/docker_start.bat)
- **Dừng hệ thống:** Chạy file [scripts/docker_stop.bat](file:///d:/Projects/diemdanhdieucai/scripts/docker_stop.bat)

### Cách 2: Sử dụng Lệnh Docker Compose (Khuyên dùng)

#### 1. Khởi chạy chế độ Tiêu chuẩn (Frontend + Backend + SQLite):
```bash
# Build và khởi chạy ngầm
docker compose up -d --build
```
Sau khi khởi chạy thành công:
* **Giao diện người dùng (Frontend):** [http://localhost:3000](http://localhost:3000)
* **Backend REST API:** [http://localhost:8000](http://localhost:8000)
* **Tài liệu Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

#### 2. Khởi chạy chế độ Nâng cao (Bật thêm PostgreSQL):
```bash
docker compose --profile postgres up -d --build
```
Và trong tệp `.env`, chỉ cần đổi biến:
```env
DATABASE_URL=postgresql://postgres:dieucai_secure_pass_2026@db:5432/attendance_db
```

#### 3. Dừng hệ thống:
```bash
docker compose down
```

---

## 4. Quản Lý Dữ Liệu Bền Vững (Data Persistence)

Toàn bộ dữ liệu quan trọng đều được ánh xạ (Volume Mount) ra ngoài thư mục máy chủ thực tế, do đó **không bao giờ bị mất** khi container khởi động lại hoặc build phiên bản mới:

* `./database`: Chứa tệp CSDL SQLite `attendance.db`.
* `./storage/captures`: Lưu ảnh chụp gốc từ 30 camera RTSP lúc 6h45 & 12h45.
* `./storage/annotated`: Lưu ảnh có bounding box nhận diện học sinh.
* `./storage/reports`: Lưu file báo cáo điểm danh Excel xuất tự động.
* `./storage/backups`: Lưu các file nén sao lưu hệ thống `.zip`.
* `./models`: Lưu trọng số AI `yolo26m.pt` và `classroom_best.pt`.
* `./logs`: Lưu nhật ký hoạt động hệ thống.

---

## 5. Kích Hoạt GPU NVIDIA Trong Docker (Tùy chọn)

Nếu máy chủ trường học có trang bị Card đồ họa NVIDIA (ví dụ: RTX 3050, RTX 4060):
1. Cài đặt **NVIDIA Container Toolkit** trên hệ điều hành.
2. Mở tệp `docker-compose.yml`, bỏ dấu chú thích `#` tại khối:
   ```yaml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: all
             capabilities: [gpu]
   ```
3. Chạy lại: `docker compose up -d`
Mô hình AI YOLO26m sẽ tự động kích hoạt CUDA để tăng tốc độ nhận diện lên gấp 5-10 lần.
