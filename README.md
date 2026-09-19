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

## 📂 CẤU TRÚC DỰ ÁN CHI TIẾT

```text
hethongdiemdanh Dieu Cai/
├── backend/                       # Máy chủ Backend REST API (FastAPI)
│   ├── main.py                    # Điểm khởi chạy server chính, CORS, Static Files & Web Routes
│   ├── api/
│   │   ├── __init__.py
│   │   └── routers/               # Các Router định tuyến phân hệ nghiệp vụ
│   │       ├── attendance.py      # API quét điểm danh, đối chứng AI, kích hoạt thủ công
│   │       ├── cameras.py         # API CRUD camera, snapshot test, quét kiểm tra kết nối
│   │       ├── roi.py             # API tọa độ ROI đa giác, tải frame mẫu, reset vùng
│   │       ├── reports.py         # API lịch sử điểm danh, tải file Excel báo cáo
│   │       └── system.py          # API trạng thái hệ thống, GPU CUDA, bộ nhớ
│   └── schemas/                   # Khung dữ liệu Pydantic v2 xác thực request/response
│       ├── camera_schemas.py      # Data schemas cho Quản lý Camera
│       ├── report_schemas.py      # Data schemas cho Báo cáo & Lịch sử
│       └── roi_schemas.py         # Data schemas cho Tọa độ ROI đa giác
│
├── frontend/                      # Giao diện người dùng Web Dashboard (HTML5 / Vanilla CSS & JS)
│   ├── index.html                 # Trang Dashboard giám sát điểm danh thời gian thực 30 lớp
│   ├── cameras.html               # Trang quản lý danh sách & kiểm tra kết nối Camera/Webcam
│   ├── roi-config.html            # Công cụ trực quan vẽ phân vùng đa giác ROI (HTML5 Canvas)
│   ├── reports.html               # Bảng tra cứu lịch sử & tải báo cáo Excel
│   ├── css/                       # Thiết kế giao diện hiện đại Glassmorphism & Dark mode
│   │   ├── main.css               # Hệ thống design tokens, bố cục chung, thanh điều hướng
│   │   ├── dashboard.css          # Giao diện thẻ lớp học, lightbox zoom/pan, thanh thống kê
│   │   ├── cameras.css            # Giao diện lưới camera, video stream, form thêm/sửa
│   │   ├── roi_config.css         # Giao diện khung vẽ canvas, bảng điều khiển tọa độ
│   │   └── reports.css            # Giao diện bộ lọc ngày tháng và bảng dữ liệu báo cáo
│   └── js/                        # Logic tương tác phía Client & gọi REST API
│       ├── api.js                 # Wrapper HTTP Client chuẩn hóa các lời gọi API backend
│       ├── dashboard.js           # Xử lý dữ liệu dashboard, quét tự động/thủ công, lightbox
│       ├── cameras.js             # Xử lý danh sách camera, live snapshot, modal form
│       ├── roi_canvas.js          # Thuật toán vẽ đa giác Canvas (Red Zone & Green Zone)
│       ├── roi_config.js          # Điều phối chọn lớp học, tải/lưu tọa độ ROI
│       └── reports.js             # Tra cứu lịch sử, xuất báo cáo Excel
│
├── core/                          # Các module lõi xử lý AI & Thị giác máy tính
│   ├── detector.py                # AI YOLOv8 nhận diện học sinh & bộ lọc không gian ROI
│   ├── attendance_engine.py       # Bộ máy điều phối quét điểm danh đồng loạt 30 lớp
│   ├── rtsp_client.py             # Kết nối đa luồng Camera RTSP, Webcam, Video file
│   ├── roi_manager.py             # Thuật toán kiểm tra điểm trong đa giác (Ray-casting)
│   ├── relay_service.py           # Module điều khiển phần cứng Relay đèn LED báo hiệu
│   └── image_enhancer.py          # Thuật toán cân bằng sáng CLAHE & khử lóa ngược sáng
│
├── services/                      # Các dịch vụ nền & Tích hợp ngoại vi
│   ├── scheduler.py               # Lập lịch điểm danh tự động 06:45 AM (APScheduler)
│   ├── excel_exporter.py          # Xuất file Excel báo cáo chuẩn hóa theo mẫu GD&ĐT
│   ├── notification.py            # Quản lý kênh thông báo (Zalo / Email)
│   └── zalo_service.py            # Tích hợp gửi tin nhắn báo cáo qua Zalo Webhook / OA
│
├── config/                        # Cấu hình tập trung toàn hệ thống
│   ├── settings.py                # Biến môi trường, cổng mạng, đường dẫn, ngưỡng AI
│   └── logging_config.py          # Cấu hình ghi log màu Console & File log xoay vòng
│
├── database/                      # Cơ sở dữ liệu SQLite & ORM
│   ├── models.py                  # Định nghĩa Models (Classroom, AttendanceSession, ROIConfig)
│   ├── db_session.py              # Phiên kết nối SQLAlchemy & hàm tự động khởi tạo Seeder
│   └── attendance.db              # Tệp CSDL SQLite chính thức
│
├── dataset/                       # Dữ liệu phục vụ nghiên cứu & huấn luyện AI
│   ├── samples/                   # Ảnh chụp & video mẫu thực tế tại trường Điều Cải
│   ├── extracted_frames/          # Khung hình trích xuất phục vụ gán nhãn
│   └── classroom.yaml             # Cấu hình tập dữ liệu YOLOv8 (classes, train/val path)
│
├── models/                        # Trọng số mô hình AI chính thức
│   └── classroom_best.pt          # Model YOLOv8 Custom đã huấn luyện tối ưu cho THPT Điều Cải
│
├── weights/                       # Trọng số tiền huấn luyện cơ sở
│   └── yolo26n.pt                 # Mô hình base
│
├── storage/                       # Lưu trữ tệp tin vận hành (tự động quản lý theo ngày)
│   ├── captures/                  # Ảnh gốc chụp từ camera theo định dạng YYYY-MM-DD
│   ├── annotated/                 # Ảnh đối chứng AI đã vẽ bounding box và số thứ tự
│   └── reports/                   # Báo cáo điểm danh Excel (.xlsx) xuất theo phiên quét
│
├── tests/                         # Bộ kiểm thử tự động (Unit / Integration Tests)
│   ├── test_attendance_engine.py  # Kiểm thử luồng điểm danh
│   ├── test_camera_management.py  # Kiểm thử API & quản lý camera
│   ├── test_excel_export.py       # Kiểm thử định dạng file báo cáo Excel
│   ├── test_roi_masking.py        # Kiểm thử thuật toán mặt nạ đa giác ROI
│   ├── test_rtsp_mock.py          # Kiểm thử chụp ảnh RTSP giả lập
│   └── test_zalo_service.py       # Kiểm thử tạo payload thông báo Zalo
│
├── logs/                          # Nhật ký hoạt động hệ thống
│   └── attendance_system.log      # File ghi nhật ký chi tiết
│
├── app.py                         # Điểm kích hoạt tương thích ngược (chuyển tiếp backend.main)
├── run.bat                        # Script 1-click khởi chạy toàn bộ hệ thống trên Windows
├── train_gpu.bat                  # Script 1-click huấn luyện AI trên GPU NVIDIA RTX 3050
├── train_yolo.py                  # Script huấn luyện AI YOLOv8 hỗ trợ tiếp tục checkpoint (Resume)
├── prepare_dataset.py             # Script chuẩn bị & phân chia dữ liệu huấn luyện
├── sample_extractor.py            # Script trích xuất khung hình hoặc tạo dữ liệu lớp học giả lập
├── requirements.txt               # Danh mục thư viện Python phụ thuộc
├── HDSD_VanHanh.md                # Sổ tay hướng dẫn vận hành hệ thống chi tiết
└── HUONG_DAN_TRAINING_AI.md       # Sổ tay hướng dẫn gán nhãn và huấn luyện AI chi tiết
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
