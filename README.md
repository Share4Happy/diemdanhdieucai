# 🎓 HỆ THỐNG ĐIỂM DANH HỌC SINH TỰ ĐỘNG BẰNG AI CAMERA
### Trường THPT Điều Cải

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)
![YOLOv8](https://img.shields.io/badge/Ultralytics-YOLOv8-FF7F00?logo=yolo)
![PyTorch CUDA](https://img.shields.io/badge/PyTorch-CUDA%20Accelerated-EE4C2C?logo=pytorch)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?logo=opencv)
![License](https://img.shields.io/badge/License-THPT%20Điều%20Cải-green)

Hệ thống điểm danh tự động 30 lớp học bằng thị giác máy tính AI (**YOLOv8 Custom Fine-tuned**), tích hợp phân vùng không gian đa giác ROI (**Red Zone** - khu vực bàn học / **Green Zone** - khu vực bục giảng), kiến trúc phân tầng hiện đại (**FastAPI RESTful Backend + Vanilla Glassmorphism Frontend**), điều khiển Relay đèn LED báo hiệu phần cứng, tự động lập lịch quét đầu giờ 06:45 AM và xuất báo cáo Excel, thông báo Zalo tức thời.

---

## 🌟 TÍNH NĂNG NỔI BẬT

1. **AI Đếm Sĩ Số Lớp Học Độ Chính Xác Cao (YOLOv8 Head & Upper Body Detection):**
   - Huấn luyện chuyên biệt nhận diện đỉnh đầu và nửa thân trên học sinh từ camera góc cao trong lớp học thực tế.
   - Nhận diện chính xác học sinh ngồi cúi đầu đọc sách, viết bài hoặc bị bạn ngồi trước che khuất một phần (*Occlusion*).
   - Tích hợp thuật toán **SAHI** (cắt lát đa tỷ lệ) và cân bằng sáng thích nghi cục bộ **CLAHE** (loại bỏ hiện tượng ngược sáng và chói lóa từ dãy cửa sổ).

2. **Phân Vùng Không Gian Đa Giác Độc Lập (Spatial ROI Masking):**
   - **Red Zone (Khu vực bàn học sinh):** AI chỉ đếm và đánh số thứ tự cho học sinh ngồi trong khu vực bàn học.
   - **Green Zone (Khu vực bục giảng giáo viên):** Tự động loại trừ 100% người đứng hoặc ngồi tại bục giảng, bàn giáo viên để không bao giờ tính nhầm thầy/cô vào sĩ số.
   - Công cụ vẽ Canvas trực quan trên Web, hỗ trợ kéo thả đỉnh đa giác và lưu tọa độ riêng biệt cho từng phòng học.

3. **Kiến Trúc Tách Biệt Backend REST API & Frontend Hiện Đại:**
   - **Backend:** Xây dựng trên nền **FastAPI**, tách module theo chuẩn REST API (`/api/attendance`, `/api/cameras`, `/api/roi`, `/api/reports`, `/api/system`), tích hợp OpenAPI Swagger Docs (`/docs`).
   - **Frontend:** Thiết kế theo phong cách **Dark Glassmorphism**, tải trang siêu tốc với Vanilla HTML5/CSS3/JavaScript, không phụ thuộc framework nặng nề.

4. **Trình Soi Chi Tiết AI Tracking (Interactive Lightbox Zoom & Pan):**
   - Bấm vào bất kỳ ảnh lớp học nào để mở trình xem ảnh toàn màn hình với hiệu ứng kính mờ (*Glassmorphism*).
   - Hỗ trợ cuộn chuột zoom từ 60% đến 500%, kéo chuột rê ảnh (*Pan*) để soi rõ từng vị trí và số thứ tự `#01, #02...` của học sinh.
   - Nút chuyển đổi nhanh đối chứng trực tiếp giữa **Ảnh AI phân tích** và **Ảnh gốc Camera**.

5. **Quản Lý Camera Toàn Diện & Live Snapshot / Webcam:**
   - Hỗ trợ đa dạng nguồn cấp: Camera IP RTSP (Hikvision, Dahua, Uniview,...), Webcam máy tính (DirectShow), File video mô phỏng.
   - Kiểm tra kết nối TCP nhanh và xem trước ảnh trực tiếp (*Live Snapshot*) tức thì trước khi lưu cấu hình.

6. **Tự Động Hóa Vận Hành & Báo Cáo Thông Minh:**
   - Lập lịch tự động quét lúc **06:45 AM** hàng ngày (Thứ 2 đến Thứ 7) qua **APScheduler**.
   - Tích hợp điều khiển mạch **Relay** đóng/ngắt đèn LED báo hiệu khi chu trình quét diễn ra.
   - Tự động xuất file báo cáo **Excel (.xlsx)** định dạng chuẩn của Sở GD&ĐT.
   - Gửi thông báo kết quả tức thời qua **Zalo Webhook / Zalo Official Account**.

---

## 🛠️ CÔNG NGHỆ SỬ DỤNG

- **Backend:** Python 3.10+, FastAPI, Uvicorn, Pydantic v2
- **AI & Computer Vision:** Ultralytics YOLOv8, PyTorch CUDA 12.x (tăng tốc GPU NVIDIA), OpenCV, NumPy, Pillow, SAHI
- **Database:** SQLite / SQLAlchemy ORM (hỗ trợ mở rộng sang PostgreSQL)
- **Frontend:** HTML5 Canvas, Vanilla CSS3 (Custom Design System, Glassmorphism, Google Fonts Inter), Modern Vanilla JavaScript (ES6+, Fetch API)
- **Task Scheduling & Automation:** APScheduler
- **Hardware & Reporting:** RTSP Client (DirectShow / FFmpeg), Serial/HTTP Relay Service, OpenPyXL, Pandas, Zalo Webhook / OA
- **Testing:** Pytest

---

## 📂 CẤU TRÚC 4 PHÂN HỆ ĐỘC LẬP & PHÂN CHIA VAI TRÒ

Dự án được tổ chức thành **4 phân hệ độc lập** giúp dễ dàng phân chia nhân sự phụ trách từng phần mà không gây xung đột hay ảnh hưởng lẫn nhau:

```text
hethongdiemdanh Dieu Cai/
│
├── 🎨 frontend/                     # [TEAM FRONTEND] Giao diện người dùng Web Dashboard
│   ├── index.html                  # Dashboard giám sát điểm danh thời gian thực 30 lớp
│   ├── cameras.html                # Quản lý danh sách & kiểm tra kết nối Camera/Webcam
│   ├── roi-config.html             # Công cụ vẽ phân vùng đa giác ROI (HTML5 Canvas)
│   ├── reports.html                # Bảng tra cứu lịch sử & xuất báo cáo Excel, gửi Zalo
│   ├── css/                        # Stylesheet Glassmorphism & Responsive layout
│   ├── js/                         # API Client trung tâm (api.js) và logic các trang
│   └── README_FRONTEND.md          # Tài liệu quy chuẩn cho lập trình viên Frontend
│
├── ⚙️ backend/                      # [TEAM BACKEND] Máy chủ REST API & Xử lý nghiệp vụ
│   ├── main.py                     # Entry point khởi động FastAPI, CORS, Static Files
│   ├── api/routers/                # Router định tuyến theo chức năng:
│   │   ├── attendance.py           # /api/attendance: Quét điểm danh & phiên làm việc
│   │   ├── cameras.py              # /api/cameras: CRUD Camera, snapshot test
│   │   ├── roi.py                  # /api/roi: Tọa độ ROI đa giác, test nhận diện tức thì
│   │   ├── reports.py              # /api/reports: Lịch sử điểm danh, báo cáo Excel
│   │   └── system.py               # /api/system: CSDL, HealthCheck, sample media
│   ├── schemas/                    # Pydantic Schemas xác thực dữ liệu request/response
│   └── README_BACKEND.md           # Hướng dẫn phát triển API & Swagger Docs
│
├── 🧱 core/                         # [CỐT LÕI HỆ THỐNG] Động cơ AI & Giao tiếp phần cứng
│   ├── detector.py                 # AI YOLOv8 nhận diện học sinh + Tiled SAHI + CLAHE
│   ├── attendance_engine.py        # Điều phối quét điểm danh đồng loạt 30 lớp
│   ├── rtsp_client.py              # Thu nhận luồng hình ảnh đa luồng (RTSP/Webcam/File)
│   ├── roi_manager.py              # Thuật toán Point-in-Polygon lọc khu vực Red/Green zone
│   ├── relay_service.py            # Điều khiển phần cứng Relay đèn LED báo hiệu
│   └── image_enhancer.py           # Cân bằng sáng thích nghi CLAHE chống ngược sáng
│
├── 🔌 services/                     # [DỊCH VỤ MỞ RỘNG] Ngoại vi & Tự động hóa
│   ├── scheduler.py                # Lập lịch điểm danh tự động 06:45 AM (APScheduler)
│   ├── excel_exporter.py           # Xuất báo cáo Excel chuẩn hóa theo mẫu GD&ĐT
│   ├── zalo_service.py             # Tích hợp gửi tin nhắn Zalo Webhook / OA
│   └── notification.py             # Quản lý kênh thông báo Email Ban Giám Hiệu
│
├── 🗄️ database/                     # [TEAM DATABASE] Cơ sở dữ liệu quan hệ
│   ├── models.py                   # SQLAlchemy ORM Models (Classroom, ROIPolygon,...)
│   ├── db_session.py               # Quản lý Session & Hàm nạp sẵn 30 lớp học (init_db)
│   ├── attendance.db               # Tệp CSDL SQLite chính thức
│   └── README_DATABASE.md          # Sơ đồ thực thể quan hệ (ERD) & Quy chuẩn CSDL
│
├── 🧠 training/                     # [TEAM AI TRAINING] Huấn luyện mô hình YOLOv8
│   ├── train_yolo.py               # Huấn luyện YOLOv8 GPU CUDA PyTorch / CPU
│   ├── prepare_dataset.py          # Chuẩn hóa nhãn học sinh Điều Cải
│   ├── sample_extractor.py         # Trích xuất khung hình mẫu phục vụ gán nhãn
│   ├── generate_classrooms_media.py# Bộ sinh 150 ảnh 1080p và 30 video 15s cho 30 lớp
│   ├── train_gpu.bat               # File thực thi 1-click kích hoạt GPU NVIDIA RTX
│   └── README_TRAINING.md          # Quy chuẩn bộ dữ liệu & huấn luyện mô hình
│
├── 📁 dataset/                      # Dữ liệu hình ảnh, video & cấu hình huấn luyện
│   ├── classroom.yaml              # Cấu hình dataset cho YOLOv8
│   ├── classroom_data/             # Ảnh & nhãn đã gán phục vụ train/val
│   └── classrooms_media/           # Bộ dữ liệu 30 lớp học (5 ảnh Full HD + 1 video 15s)
│
├── 📦 models/                       # Trọng số mô hình AI chính thức
│   └── classroom_best.pt           # Model YOLOv8 Custom đã tinh chỉnh cho THPT Điều Cải
│
├── ⚙️ config/                       # Cấu hình tập trung (settings.py, logging_config.py)
├── 🧪 tests/                        # Bộ kiểm thử tự động Pytest (6 test suites)
│
├── 🚀 KỊCH BẢN CHẠY ĐỘC LẬP CHO TỪNG VAI TRÒ:
│   ├── run_backend.bat             # Chỉ chạy Backend FastAPI (Cổng 8000, Swagger /docs)
│   ├── run_frontend.bat            # Chỉ chạy Frontend độc lập (Cổng 3000, tự gọi API 8000)
│   ├── train_gpu.bat               # Huấn luyện AI với GPU NVIDIA RTX (chuyển tiếp tới training/)
│   ├── xem_tien_do.bat             # Bảng kiểm tra nhanh tiến độ & trạng thái các phân hệ
│   └── run.bat                     # Chạy trọn gói toàn bộ hệ thống (1-click)
│
└── 📖 TÀI LIỆU DỰ ÁN:
    ├── KIEN_TRUC_HE_THONG.md       # Sơ đồ kiến trúc & quy ước cộng tác nhóm
    └── training/HUONG_DAN_TRAINING_AI.md # Sổ tay hướng dẫn huấn luyện AI chi tiết
```

---

## 🚀 CÁCH CÀI ĐẶT VÀ KHỞI CHẠY

### 1. Chuẩn bị môi trường:
- Khuyến nghị **Python 3.10** hoặc **Python 3.11**.
- Cài đặt các thư viện cần thiết:
```powershell
pip install -r requirements.txt
```
*(Nếu sử dụng GPU NVIDIA, cài đặt PyTorch hỗ trợ CUDA phù hợp với phiên bản driver của máy).*

### 2. Khởi động hệ thống:

#### Cách 1: Khởi động 1-Click trên Windows (Khuyến nghị)
Nhấp đúp chuột vào file **`run.bat`**.  
File script sẽ tự động:
1. Phát hiện môi trường GPU NVIDIA (`venv_cuda`) nếu có để kích hoạt CUDA.
2. Kiểm tra và khởi tạo CSDL SQLite nếu chưa tồn tại.
3. Tự động sinh dữ liệu mô phỏng để sẵn sàng chạy thử nghiệm ngay lập tức.
4. Mở máy chủ Web và kích hoạt bộ lập lịch 06:45 AM.

#### Cách 2: Khởi động qua dòng lệnh
```powershell
python app.py
```
*Hoặc khởi chạy trực tiếp Backend FastAPI:*
```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌐 ĐỊA CHỈ TRUY CẬP HỆ THỐNG

Sau khi server khởi động thành công, truy cập trình duyệt tại:

| Giao diện / Chức năng | Đường dẫn (URL) | Mô tả |
| :--- | :--- | :--- |
| **📊 Dashboard Điểm Danh** | [http://localhost:8000](http://localhost:8000) | Giám sát sĩ số thời gian thực 30 lớp, xem ảnh AI đối chứng |
| **📷 Quản Lý Camera** | [http://localhost:8000/cameras](http://localhost:8000/cameras) | Thêm, sửa, kiểm tra kết nối RTSP/Webcam, Live Snapshot |
| **📐 Cấu Hình Vùng ROI** | [http://localhost:8000/roi-config](http://localhost:8000/roi-config) | Công cụ vẽ Red Zone (Bàn học) & Green Zone (Bục giảng) |
| **📑 Báo Cáo & Dữ Liệu** | [http://localhost:8000/reports](http://localhost:8000/reports) | Tra cứu lịch sử điểm danh và tải file Excel báo cáo |
| **📖 Tài Liệu Swagger API** | [http://localhost:8000/docs](http://localhost:8000/docs) | Tài liệu kỹ thuật tương tác trực tiếp REST API |

---

## 🎯 QUY TRÌNH HUẤN LUYỆN MÔ HÌNH AI (TRAINING PIPELINE)

Hệ thống cung cấp sẵn bộ công cụ huấn luyện lại mô hình YOLOv8 trên tập dữ liệu đặc thù của nhà trường:

1. **Chuẩn bị và trích xuất dữ liệu:**
   - Thả ảnh hoặc video mẫu vào thư mục `dataset/samples/`.
   - Chạy lệnh trích xuất khung hình:
     ```powershell
     python sample_extractor.py
     ```
   - Chuẩn bị và phân bổ tập train/val:
     ```powershell
     python prepare_dataset.py
     ```

2. **Huấn luyện mô hình:**
   - **Tự động trên GPU NVIDIA (RTX 3050):** Nhấp đúp file **`train_gpu.bat`**. File tự động kiểm tra và tiếp tục huấn luyện (*Resume*) nếu phiên trước bị gián đoạn.
   - **Huấn luyện thủ công qua CLI:**
     ```powershell
     python train_yolo.py --epochs 25 --imgsz 640 --batch 4 --device 0
     ```
   - Trọng số tối ưu nhất sẽ được tự động xuất bản vào `models/classroom_best.pt`.
   - Xem hướng dẫn gán nhãn chi tiết tại [HUONG_DAN_TRAINING_AI.md](file:///d:/Vibe%20Code/hethongdiemdanh%20Dieu%20Cai/HUONG_DAN_TRAINING_AI.md).

---

## 🧪 KIỂM THỬ HỆ THỐNG (AUTOMATED TESTS)

Hệ thống tích hợp đầy đủ bộ kiểm thử cho các thành phần cốt lõi:
```powershell
pytest -v
```
Các kịch bản kiểm thử bao gồm:
- Luồng điểm danh và đếm sĩ số học sinh (`test_attendance_engine.py`)
- Quản lý danh sách và kiểm tra camera (`test_camera_management.py`)
- Định dạng xuất báo cáo Excel (`test_excel_export.py`)
- Thuật toán xác định tọa độ mặt nạ ROI Red/Green Zone (`test_roi_masking.py`)
- Kết nối giả lập nguồn RTSP (`test_rtsp_mock.py`)
- Tích hợp dịch vụ tin nhắn Zalo (`test_zalo_service.py`)

---

## 📚 TÀI LIỆU HƯỚNG DẪN ĐI KÈM

- 📖 **Cẩm nang vận hành dành cho giám thị & kỹ thuật viên:** Xem [HDSD_VanHanh.md](file:///d:/Vibe%20Code/hethongdiemdanh%20Dieu%20Cai/HDSD_VanHanh.md)
- 🔬 **Quy trình gán nhãn & huấn luyện mô hình AI chuyên sâu:** Xem [HUONG_DAN_TRAINING_AI.md](file:///d:/Vibe%20Code/hethongdiemdanh%20Dieu%20Cai/HUONG_DAN_TRAINING_AI.md)

---

## 📜 BẢN QUYỀN
Hệ thống được thiết kế và phát triển phục vụ công tác quản lý trường học thông minh tại **Trường THPT Điều Cải**.
