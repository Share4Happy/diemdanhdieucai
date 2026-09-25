# HƯỚNG DẪN BẢO TRÌ & BÀN GIAO HỆ THỐNG ĐIỂM DANH AI
**Trường THPT Điều Cải — AI Camera Attendance System**

---

## 1. Cấu Trúc Thư Mục Chuẩn Hóa Toàn Hệ Thống

Để đảm bảo việc bảo trì, nâng cấp và bàn giao diễn ra thuận tiện, toàn bộ dự án đã được phân bổ thành từng module chức năng độc lập:

```text
hethongdiemdanh Dieu Cai/
│
├── run.bat                          # [QUAN TRỌNG] File khởi động 1-Click toàn bộ hệ thống (Web + AI + Database)
├── train_real_camera.bat            # Script huấn luyện AI Fine-tuning với dữ liệu camera thực tế Điều Cải
├── app.py                           # Điểm khởi chạy máy chủ backend (Uvicorn ASGI)
├── requirements.txt                 # Danh sách thư viện Python cần thiết
├── .env                             # Cấu hình môi trường (IP NVR, Port, Mật khẩu, Database)
│
├── core/                            # TẦNG LÕI NGHIỆP VỤ & AI
│   ├── attendance_engine.py         # Động cơ điều phối điểm danh tự động 30 lớp học
│   ├── camera_source_manager.py     # [MỚI] Bộ chuyển đổi linh hoạt: Ảnh Test (Offline) <-> Đầu Ghi NVR Thật
│   ├── detector.py                  # Mô hình phát hiện học sinh YOLO26m + AI nhận diện đầu
│   ├── rtsp_client.py               # Kết nối đa luồng RTSP / Webcam / Ảnh file (Có chế độ Fallback an toàn)
│   ├── relay_service.py             # Điều khiển đèn hồng ngoại camera báo hiệu 3s trước khi chụp
│   ├── scheduler.py                 # Lập lịch tự động điểm danh ca sáng (06:45) & ca chiều (12:45)
│   └── timezone_utils.py            # Tiện ích múi giờ chuẩn Việt Nam (Asia/Ho_Chi_Minh)
│
├── backend/                         # TẦNG API REST (FastAPI)
│   ├── main.py                      # Khởi tạo FastAPI App, CORS, Static Files, Router Mounts
│   ├── api/routers/                 # Các API Endpoint theo nghiệp vụ:
│   │   ├── attendance.py            # API quét điểm danh, lịch sử, chi tiết từng phiên
│   │   ├── cameras.py               # API quản lý camera, chuyển đổi nguồn, cấu hình NVR
│   │   ├── reports.py               # API xuất Excel, biểu đồ chuyên cần, dọn dẹp dữ liệu
│   │   ├── roi.py                   # API vẽ vùng ROI lớp học, loại trừ khu vực ngoài hành lang
│   │   ├── auth.py & users.py       # API xác thực, phân quyền quản trị viên / giáo viên
│   │   └── system.py                # API giám sát tài nguyên GPU/CPU, kiểm tra sức khỏe hệ thống
│   └── schemas/                     # Pydantic Schemas xác thực dữ liệu đầu vào / đầu ra
│
├── database/                        # CƠ SỞ DỮ LIỆU
│   ├── attendance.db                # File CSDL SQLite chính thức
│   ├── models.py                    # Khai báo cấu trúc bảng (Classroom, Attendance, ROI, User, NVR)
│   └── db_session.py                # Quản lý kết nối DB Session và khởi tạo dữ liệu mặc định
│
├── frontend/                        # GIAO DIỆN NGƯỜI DÙNG (HTML / CSS / JS)
│   ├── index.html                   # Bảng điều khiển trung tâm (Dashboard & TV-Wall ma trận camera)
│   ├── cameras.html                 # Quản lý 30 camera, nút Bàn Giao Đầu Ghi & Ảnh Test
│   ├── roi.html                     # Giao diện thiết lập vùng vẽ ROI cho từng phòng học
│   ├── reports.html                 # Báo cáo chuyên cần, xuất file Excel, xem ảnh đối chứng AI
│   ├── notifications.html           # Cấu hình gửi thông báo Zalo / Email tự động
│   ├── users.html                   # Quản lý danh sách người dùng và phân quyền
│   ├── css/                         # Giao diện thiết kế theo Design System hiện đại
│   └── js/                          # Logic JavaScript tách module sạch sẽ
│
├── models/                          # TRỌNG SỐ MÔ HÌNH TRÍ TUỆ NHÂN TẠO (AI WEIGHTS)
│   ├── yolo26m.pt                   # Mô hình YOLO26m phát hiện người tổng thể
│   ├── classroom_best.pt            # Mô hình chuyên sâu nhận diện học sinh trong lớp học
│   └── classroom_real_camera_best.pt# Mô hình đã huấn luyện trực tiếp từ camera thật của trường
│
├── storage/                         # DỮ LIỆU LƯU TRỮ ĐỘNG (Sinh ra trong quá trình vận hành)
│   ├── captures/                    # Ảnh gốc camera chụp theo từng ngày và từng phiên độc lập
│   ├── annotated/                   # Ảnh AI đã khoanh vùng bounding box đối chứng
│   ├── reports/                     # Các file Excel báo cáo sĩ số đã xuất
│   └── backups/                     # Các bản sao lưu tự động của CSDL hàng ngày lúc 23:00
│
├── scripts/                         # CÔNG CỤ VẬN HÀNH & BẢO TRÌ BỔ TRỢ
│   ├── train_real_camera.bat        # Huấn luyện AI với camera trường
│   ├── xem_tien_do.bat              # Kiểm tra tình trạng hoạt động và tài nguyên hệ thống
│   ├── run_backend.bat              # Chạy riêng máy chủ backend
│   ├── run_frontend.bat             # Chạy riêng giao diện frontend
│   └── tools/                       # Các script sửa lỗi nhanh (Reset mật khẩu, cài đặt thư viện)
│
├── camera/                          # [THƯ MỤC ẢNH TEST TẠM THỜI]
│   └── 1.JPG ... 30.JPG             # 30 ảnh dùng để giả lập camera khi chạy thử nghiệm offline
│                                    # (Có thể XÓA BỎ hoàn toàn khi bàn giao cho trường học)
│
└── dataset/ & training/             # Dữ liệu ảnh mẫu và kịch bản huấn luyện mô hình YOLO
```

---

## 2. Hướng Dẫn Bàn Giao Khách Hàng (Chuyển Sang Đầu Ghi NVR Thật)

Khi bạn mang hệ thống đến lắp đặt và bàn giao tại trường học, bạn không cần phải sửa code hay thao tác thủ công phức tạp. Hệ thống đã tích hợp sẵn tính năng **1-Click Bàn Giao**:

### Bước 1: Kết Nối Mạng Đầu Ghi
1. Cắm dây mạng LAN của máy tính chủ (Server) và Đầu ghi NVR vào cùng mạng nội bộ của trường (ví dụ dải IP `192.168.10.x`).
2. Đảm bảo máy chủ ping thấy IP đầu ghi NVR (mặc định: `192.168.10.200`).

### Bước 2: Kích Hoạt Chế Độ Đầu Ghi Trên Giao Diện Web
1. Mở trình duyệt truy cập: `http://localhost:8000/cameras.html`.
2. Tại thanh công cụ phía trên, bấm nút: **"Chế Độ Camera & Bàn Giao"**.
3. Trong hộp thoại hiển thị, tại tab **"1. Bàn Giao Đầu Ghi NVR Thật"**:
   * **Địa chỉ IP Đầu Ghi:** Điền IP đầu ghi (VD: `192.168.10.200`).
   * **Cổng RTSP:** `554`.
   * **Tài khoản & Mật khẩu:** Điền thông tin đăng nhập đầu ghi (VD: `admin` / `DieuCai@2026`).
   * **Hãng Đầu Ghi:** Chọn `Dahua` (mặc định cho trường THPT Điều Cải) hoặc `Hikvision` / `KBVision`.
   * **Tùy chọn dọn dẹp:** Tích chọn ô:
     > ☑️ **"Xóa sạch thư mục ảnh test giả lập (camera/) sau khi chuyển đổi"**
4. Bấm nút: **"ÁP DỤNG ĐẦU GHI NVR & BÀN GIAO TOÀN BỘ 30 CAMERA"**.
5. Hệ thống sẽ tự động:
   * Ánh xạ toàn bộ 30 camera sang các luồng RTSP tương ứng (`channel=1` đến `channel=30`).
   * Cập nhật IP điều khiển đèn hồng ngoại LED.
   * Xóa sạch thư mục ảnh test `camera/` để giải phóng dung lượng ổ cứng.
   * Trạng thái góc trên chuyển sang: `🟢 NVR Thật (30 Cam)`.

---

## 3. Nếu Sau Này Cần Test Lại Mà Không Có Đầu Ghi Thì Sao?

Hệ thống được thiết kế hoàn toàn linh hoạt:
1. Bạn chỉ cần vào lại trang `Quản Lý Camera` -> bấm nút **"Chế Độ Camera & Bàn Giao"**.
2. Chọn tab **"2. Chế Độ Ảnh Mẫu (Test)"** -> bấm **"Kích Hoạt Chế Độ Ảnh Test (Camera 1 - 30)"**.
3. Bạn có thể copy ảnh mới vào thư mục `camera/` (đặt tên `1.JPG` đến `30.JPG`) hoặc để hệ thống tự động sinh khung hình test.
4. **Cơ chế an toàn 100%:** Dù thư mục `camera/` có bị xóa hay camera RTSP bị mất điện, hệ thống **không bao giờ bị dừng (crash)**, mà sẽ tạo ảnh thông báo trạng thái trực quan để người quản trị dễ dàng nhận biết.

---

## 4. Quy Trình Vận Hành & Khởi Động Hàng Ngày

* **Khởi động hệ thống:** Chỉ cần nhấp đúp chuột vào file:
  ```bash
  run.bat
  ```
  File này sẽ tự động:
  1. Kiểm tra môi trường GPU CUDA NVIDIA (RTX 3050).
  2. Khởi tạo và kiểm tra toàn vẹn CSDL SQLite.
  3. Giải phóng cổng 8000 nếu bị chiếm dụng.
  4. Khởi động Web Server FastAPI và Bộ lập lịch điểm danh tự động (06:45 ca sáng & 12:45 ca chiều).

---

## 5. Hướng Dẫn Bảo Trì Định Kỳ

### 5.1. Sao Lưu & Phục Hồi Dữ Liệu
* Hệ thống tự động sao lưu file `database/attendance.db` vào thư mục `storage/backups/` mỗi ngày vào lúc 23:00.
* Khi cần phục hồi, chỉ cần copy file backup mới nhất đè lại vào `database/attendance.db`.

### 5.2. Quản Lý Dung Lượng Ảnh Lưu Trữ
* Ảnh điểm danh được lưu trữ độc lập theo ngày tại `storage/captures/{YYYY-MM-DD}/{MÃ_PHIÊN}/`.
* Hệ thống có sẵn dịch vụ dọn dẹp định kỳ (Retention Service) trong trang **Báo Cáo & Dữ Liệu**, cho phép tự động xóa ảnh cũ quá 30 hoặc 60 ngày để tránh đầy bộ nhớ máy chủ.

### 5.3. Huấn Luyện Lại AI (Fine-tuning)
* Nếu nhà trường thay đổi góc lắp đặt camera hoặc ánh sáng phòng học, chỉ cần chạy script:
  ```bash
  train_real_camera.bat
  ```
  để AI tự động học lại đặc trưng khuôn mặt/đầu học sinh với camera mới.
