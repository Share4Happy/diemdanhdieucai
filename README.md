# 🎓 HỆ THỐNG ĐIỂM DANH HỌC SINH TỰ ĐỘNG BẰNG AI CAMERA
### Trường THPT Điều Cải

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)
![YOLOv8](https://img.shields.io/badge/Ultralytics-YOLOv8-FF7F00?logo=yolo)
![PyTorch CUDA](https://img.shields.io/badge/PyTorch-CUDA%20Accelerated-EE4C2C?logo=pytorch)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?logo=opencv)
![Tests](https://img.shields.io/badge/Tests-13%20Passed-brightgreen)
![License](https://img.shields.io/badge/License-THPT%20Điều%20Cải-green)

Hệ thống điểm danh tự động toàn diện cho **30 lớp học** (tổng quy mô **1.246 học sinh**) tại **Trường THPT Điều Cải** ứng dụng thị giác máy tính AI (**YOLOv8 Custom Fine-tuned**), thuật toán phân vùng không gian đa giác ROI (**Red Zone** - khu vực bàn học / **Green Zone** - khu vực bục giảng giáo viên), kiến trúc phân tầng độc lập (**Frontend Glassmorphism + FastAPI RESTful Backend + SQLite/PostgreSQL Database + AI Training Subsystem**), tích hợp điều khiển Relay đèn LED báo hiệu phần cứng, lập lịch quét tự động lúc **06:45 AM** hàng ngày, tự động xuất báo cáo Excel chuẩn mẫu GD&ĐT và thông báo Zalo tức thời.

---

## 🌟 TÍNH NĂNG NỔI BẬT

1. **AI Đếm Sĩ Số Lớp Học Độ Chính Xác Cao (YOLOv8 Head & Upper Body Detection):**
   - Huấn luyện chuyên sâu để nhận diện đỉnh đầu và nửa thân trên học sinh từ camera góc cao lớp học.
   - Nhận diện chính xác học sinh ngồi cúi đầu đọc sách, viết bài hoặc bị bạn ngồi trước che khuất (*Occlusion*).
   - Tích hợp thuật toán **SAHI** (cắt lát ảnh đa tỷ lệ) và cân bằng sáng thích ứng cục bộ **CLAHE** (loại bỏ hoàn toàn hiện tượng ngược sáng và chói lóa từ dãy cửa sổ lớp học).

2. **Phân Vùng Không Gian Đa Giác Độc Lập (Spatial ROI Masking):**
   - **Red Zone (Khu vực bàn học sinh):** AI chỉ đếm và đánh số thứ tự `#01, #02, #03...` cho học sinh ngồi trong khu vực bàn học.
   - **Green Zone (Khu vực bục giảng):** Tự động loại trừ 100% người đứng hoặc ngồi tại bục giảng/bàn giáo viên, đảm bảo không bao giờ tính nhầm thầy/cô vào sĩ số học sinh.
   - Công cụ vẽ Canvas trực quan trên Web, hỗ trợ kéo thả đỉnh đa giác và lưu tọa độ riêng biệt cho từng phòng học.

3. **Kiến Trúc Tách Biệt 4 Phân Hệ Độc Lập:**
   - Phân chia module rõ ràng: `frontend/`, `backend/`, `database/`, `training/`.
   - Mỗi phân hệ có tài liệu quy chuẩn riêng, cho phép phân chia lập trình viên làm việc song song mà không gây xung đột mã nguồn.

4. **Trình Soi Chi Tiết AI Tracking (Interactive Lightbox Zoom & Pan):**
   - Bấm vào ảnh lớp học để mở trình xem ảnh toàn màn hình với hiệu ứng kính mờ (*Glassmorphism*).
   - Hỗ trợ cuộn chuột zoom từ 60% đến 500%, kéo chuột rê ảnh (*Pan*) để soi rõ từng vị trí học sinh.
   - Nút chuyển đổi nhanh đối chứng trực tiếp giữa **Ảnh AI phân tích** và **Ảnh gốc Camera**.

5. **Quản Lý Camera Toàn Diện & Live Snapshot / Webcam:**
   - Hỗ trợ đa dạng nguồn cấp: Camera IP RTSP (Hikvision, Dahua, Uniview,...), Webcam máy tính (DirectShow), File video/ảnh mô phỏng.
   - Kiểm tra kết nối mạng TCP nhanh và xem trước ảnh trực tiếp (*Live Snapshot*) tức thì trước khi lưu cấu hình.

6. **Tự Động Hóa Vận Hành & Báo Cáo Thông Minh:**
   - Lập lịch tự động quét lúc **06:45 AM** hàng ngày (Thứ 2 đến Thứ 7) qua **APScheduler**.
   - Tích hợp điều khiển mạch **Relay** đóng/ngắt đèn LED báo hiệu khi chu trình quét diễn ra.
   - Tự động xuất file báo cáo **Excel (.xlsx)** định dạng chuẩn của Sở GD&ĐT.
   - Gửi thông báo kết quả tức thời qua **Zalo Bot Gateway** (khuyến nghị) hoặc Zalo Official Account.

---

## 📂 CẤU TRÚC DỰ ÁN & PHÂN HỆ ĐỘC LẬP

Mã nguồn được cấu trúc khoa học theo mô hình đa tầng, thư mục gốc được tinh gọn tối đa chỉ còn **9 tệp tin điều khiển cốt lõi**:

```text
hethongdiemdanh Dieu Cai/
│
├── 🎨 frontend/                     # [PHÂN HỆ FRONTEND] Giao diện người dùng Web Dashboard
│   ├── index.html                  # Dashboard giám sát điểm danh thời gian thực 30 lớp
│   ├── cameras.html                # Quản lý danh sách & kiểm tra kết nối Camera/Webcam
│   ├── roi-config.html             # Công cụ vẽ phân vùng đa giác ROI (HTML5 Canvas)
│   ├── reports.html                # Bảng tra cứu lịch sử & xuất báo cáo Excel, gửi Zalo
│   ├── css/                        # Hệ thống CSS Glassmorphism & Responsive layout
│   ├── js/                         # API Client trung tâm (api.js) và logic các màn hình
│   └── README_FRONTEND.md          # Sổ tay quy chuẩn dành cho lập trình viên Frontend
│
├── ⚙️ backend/                      # [PHÂN HỆ BACKEND] Máy chủ REST API & Xử lý nghiệp vụ
│   ├── main.py                     # Khởi động FastAPI, cấu hình CORS, mount Static files
│   ├── system_check.py             # Script kiểm tra sức khỏe và tiến độ toàn hệ thống
│   ├── api/routers/                # Bộ định tuyến RESTful API:
│   │   ├── attendance.py           # /api/attendance: Quét điểm danh & phiên làm việc
│   │   ├── cameras.py              # /api/cameras: Quản lý Camera, snapshot live test
│   │   ├── roi.py                  # /api/roi: Tọa độ ROI đa giác, test nhận diện tức thì
│   │   ├── reports.py              # /api/reports: Lịch sử điểm danh, xuất báo cáo Excel
│   │   └── system.py               # /api/system: CSDL, HealthCheck, sample media
│   ├── schemas/                    # Pydantic Schemas xác thực dữ liệu đầu vào/ra
│   └── README_BACKEND.md           # Hướng dẫn phát triển API & Swagger Interactive Docs
│
├── 🗄️ database/                     # [PHÂN HỆ DATABASE] Cơ sở dữ liệu quan hệ
│   ├── models.py                   # SQLAlchemy ORM Models (Classroom, ROIPolygon, Camera,...)
│   ├── db_session.py               # Quản lý kết nối Session & Khởi tạo sẵn 30 lớp học
│   ├── attendance.db               # Tệp tin CSDL SQLite chính thức
│   └── README_DATABASE.md          # Sơ đồ thực thể quan hệ (ERD) & Quy chuẩn CSDL
│
├── 🧠 training/                     # [PHÂN HỆ AI TRAINING] Huấn luyện mô hình YOLOv8
│   ├── train_yolo.py               # Script huấn luyện YOLOv8 (GPU CUDA / CPU PyTorch)
│   ├── prepare_dataset.py          # Chuẩn hóa nhãn & phân bổ tập train/val
│   ├── sample_extractor.py         # Trích xuất khung hình từ video phục vụ gán nhãn
│   ├── generate_classrooms_media.py# Bộ sinh dữ liệu ảnh Full HD và video 15s cho 30 lớp
│   ├── train_gpu.bat               # Kịch bản 1-click huấn luyện GPU NVIDIA RTX
│   └── HUONG_DAN_TRAINING_AI.md    # Hướng dẫn chi tiết quy trình gán nhãn & huấn luyện AI
│
├── 🧱 core/                         # [CỐT LÕI HỆ THỐNG] Động cơ AI & Giao tiếp thiết bị
│   ├── detector.py                 # AI YOLOv8 nhận diện đỉnh đầu + SAHI + CLAHE
│   ├── attendance_engine.py        # Điều phối quét điểm danh đồng loạt 30 lớp học
│   ├── rtsp_client.py              # Thu nhận luồng hình ảnh đa luồng (RTSP/Webcam/File)
│   ├── roi_manager.py              # Thuật toán Point-in-Polygon lọc khu vực Red/Green Zone
│   ├── relay_service.py            # Điều khiển phần cứng Relay đèn LED báo hiệu
│   └── image_enhancer.py           # Bộ cân bằng sáng cục bộ CLAHE
│
├── 🔌 services/                     # [DỊCH VỤ NGOẠI VI] Tự động hóa & Báo cáo
│   ├── scheduler.py                # Lập lịch điểm danh tự động 06:45 AM (APScheduler)
│   ├── excel_exporter.py           # Xuất báo cáo Excel chuẩn hóa theo mẫu GD&ĐT
│   ├── zalo_service.py             # Tích hợp gửi tin nhắn Zalo Bot Gateway / OA (khuyến nghị Bot Gateway)
│   └── notification.py             # Quản lý kênh thông báo Email
│
├── 📁 dataset/                      # Kho dữ liệu hình ảnh, video & cấu hình huấn luyện
│   ├── classroom.yaml              # Cấu hình dataset cho YOLOv8
│   ├── classroom_data/             # Dữ liệu ảnh & nhãn YOLO phục vụ huấn luyện
│   └── classrooms_media/           # Bộ dữ liệu 30 lớp học (5 ảnh 1080p + 1 video 15s/lớp)
│       ├── danh_sach_si_so_toan_truong.xlsx # Bảng Excel tổng hợp sĩ số 30 lớp
│       ├── danh_sach_si_so_toan_truong.json # Dữ liệu JSON sĩ số toàn trường
│       ├── README.md               # Tài liệu chi tiết về bộ dữ liệu đa phương tiện
│       ├── Lop_10A1/ ... Lop_12A10/# 30 thư mục tương ứng 30 lớp học
│
├── 📦 models/                       # Trọng số mô hình AI
│   └── classroom_best.pt           # Model YOLOv8 Custom đã tinh chỉnh cho THPT Điều Cải
│
├── ⚙️ config/                       # Cấu hình tập trung (settings.py, logging_config.py)
├── 🧪 tests/                        # Bộ kiểm thử tự động Pytest (13 test cases passed)
│
├── 🚀 9 TỆP TIN ĐIỀU KHIỂN CỐT LÕI TẠI THƯ MỤC GỐC:
│   ├── run.bat                     # [Khởi động toàn diện] 1-click chạy cả Backend + Frontend
│   ├── run_backend.bat             # [Backend Dev] Khởi động riêng FastAPI Server (Cổng 8000)
│   ├── run_frontend.bat            # [Frontend Dev] Khởi động riêng Frontend độc lập (Cổng 3000)
│   ├── xem_tien_do.bat             # [Quản trị viên] Xem nhanh tiến độ & sức khỏe toàn hệ thống
│   ├── app.py                      # File thực thi Python trọn gói
│   ├── requirements.txt            # Danh sách thư viện phụ thuộc Python
│   ├── KIEN_TRUC_HE_THONG.md       # Tài liệu kiến trúc hệ thống & quy chuẩn phối hợp nhóm
│   ├── README.md                   # Tài liệu tổng quan dự án (Tệp này)
│   └── .gitignore                  # Cấu hình loại trừ Git chuẩn mực
```

---

## 👥 PHÂN CHIA VAI TRÒ & KỊCH BẢN CHẠY RIÊNG

Dự án được thiết kế giúp các thành viên trong nhóm làm việc độc lập:

| Vai Trò | Thư Mục Phụ Trách | Trách Nhiệm Chính | Lệnh Chạy Riêng |
| :--- | :--- | :--- | :--- |
| **Frontend Dev** | `frontend/` | Thiết kế giao diện Glassmorphism, đồ thị Chart.js, công cụ vẽ Canvas ROI, gọi REST API qua `api.js`. | `run_frontend.bat` (Cổng 3000) |
| **Backend Dev** | `backend/`, `core/`, `services/` | Xây dựng REST API FastAPI, tích hợp AI YOLOv8, Relay, Excel, Zalo Bot Gateway, APScheduler, viết Pytest. | `run_backend.bat` (Cổng 8000, Swagger `/docs`) |
| **Database Dev** | `database/` | Thiết kế mô hình ORM `models.py`, quản lý session `db_session.py`, nạp sẵn 30 lớp học và sao lưu. | `python -c "from database.db_session import init_db; init_db()"` |
| **AI Engineer** | `training/`, `dataset/` | Tiền xử lý dữ liệu, gán nhãn, fine-tuning YOLOv8 trên GPU RTX, đánh giá mAP và xuất mô hình. | `training\train_gpu.bat` |
| **Project Manager** | Toàn bộ dự án | Kiểm tra tiến độ phân hệ, tính toàn vẹn CSDL, trạng thái GPU và các kịch bản kiểm thử. | `xem_tien_do.bat` |

---

## 📊 BỘ DỮ LIỆU ĐA PHƯƠNG TIỆN 30 LỚP HỌC (`dataset/classrooms_media/`)

Dự án cung cấp sẵn bộ dữ liệu chuẩn mực cho toàn bộ **30 lớp học** của Trường THPT Điều Cải:
- **150 hình ảnh Full HD (1920x1080):** 5 ảnh/lớp thể hiện đầy đủ các tình huống: Đủ sĩ số 100%, Vắng 1 học sinh, Góc nhìn thực tế trong giờ học, Vắng 2 học sinh, Ảnh kiểm tra chốt buổi.
- **30 video chuẩn 15 giây (15fps, 225 frames/video):** Tỷ lệ khung hình chuẩn Full HD, có thể dùng trực tiếp làm nguồn cấp RTSP hoặc video mô phỏng camera thực tế.
- **Hồ sơ thông tin từng lớp:** Mỗi thư mục lớp có sẵn file siêu dữ liệu `info.json` và `thong_tin_lop.txt`.
- **Báo cáo sĩ số toàn trường:**
  - File Excel: `dataset/classrooms_media/danh_sach_si_so_toan_truong.xlsx`
  - File JSON: `dataset/classrooms_media/danh_sach_si_so_toan_truong.json`

### Bảng Thống Kê Sĩ Số 30 Lớp Học (Tổng: 1.246 Học Sinh)

| Khối | Số Lớp | Danh Sách Lớp Học | Phòng Học | Sĩ Số Mỗi Lớp | Tổng Học Sinh |
| :---: | :---: | :---| :---: | :---: | :---: |
| **Khối 10** | 10 lớp | 10A1 đến 10A10 | P.101 - P.110 | 39 - 43 HS/lớp | **410 học sinh** |
| **Khối 11** | 10 lớp | 11A1 đến 11A10 | P.111 - P.120 | 39 - 44 HS/lớp | **416 học sinh** |
| **Khối 12** | 10 lớp | 12A1 đến 12A10 | P.121 - P.130 | 40 - 45 HS/lớp | **420 học sinh** |
| **TOÀN TRƯỜNG** | **30 lớp** | **10A1 - 12A10** | **30 phòng** | **Trung bình 41.5** | **1.246 học sinh** |

*Xem tài liệu chi tiết tại: [dataset/classrooms_media/README.md](dataset/classrooms_media/README.md).*

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT VÀ KHỞI CHẠY

### 1. Yêu Cầu Hệ Thống:
- Hệ điều hành: Windows 10/11 hoặc Linux / macOS.
- Python: **Python 3.10** hoặc **Python 3.11** (khuyến nghị).
- GPU (tùy chọn): NVIDIA RTX series hỗ trợ CUDA 12.x giúp tăng tốc độ nhận diện lên đến 60+ FPS.

### 2. Cài Đặt Thư Viện:
```powershell
pip install -r requirements.txt
```
*(Nếu dùng GPU NVIDIA, cài PyTorch hỗ trợ CUDA tương ứng: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`).*

### 3. Các Phương Thức Khởi Chạy:

#### 🟢 Phương thức 1: Khởi động trọn gói 1-Click (Khuyến nghị)
Nhấp đúp vào tệp **`run.bat`**. Kịch bản sẽ tự động:
1. Phát hiện môi trường GPU NVIDIA (`venv_cuda`) để kích hoạt phần cứng.
2. Tự động kiểm tra và khởi tạo CSDL SQLite với đầy đủ 30 lớp học nếu chưa có.
3. Khởi động Web Server tại cổng `8000` và kích hoạt bộ lập lịch 06:45 AM.

#### 🔵 Phương thức 2: Khởi động riêng Backend REST API
Phù hợp cho lập trình viên Backend:
```powershell
run_backend.bat
```
Server sẽ chạy tại `http://localhost:8000`, cung cấp đầy đủ tài liệu API tương tác tại `http://localhost:8000/docs`.

#### 🟣 Phương thức 3: Khởi động riêng Frontend độc lập
Phù hợp cho lập trình viên Frontend muốn chỉnh sửa giao diện:
```powershell
run_frontend.bat
```
Giao diện chạy độc lập tại cổng `3000` (`http://localhost:3000`) và tự động kết nối tới API Backend ở cổng `8000`.

#### 🟡 Phương thức 4: Bảng kiểm tra tiến độ toàn hệ thống
Dành cho quản trị viên và trưởng dự án:
```powershell
xem_tien_do.bat
```
Hiển thị tức thì: Trạng thái 4 phân hệ, CSDL 30 lớp, bộ dữ liệu hình ảnh/video, GPU và kết quả kiểm thử.

---

## 🌐 DANH MỤC ĐỊA CHỈ TRUY CẬP

Sau khi khởi chạy hệ thống, mở trình duyệt tại:

| Giao diện / Chức năng | Địa chỉ (URL) | Mô tả chi tiết |
| :--- | :--- | :--- |
| **📊 Dashboard Điểm Danh** | [http://localhost:8000](http://localhost:8000) | Giám sát sĩ số thời gian thực 30 lớp, xem ảnh AI đối chứng, kích hoạt quét thủ công |
| **📷 Quản Lý Camera** | [http://localhost:8000/cameras](http://localhost:8000/cameras) | Thêm, sửa, kiểm tra kết nối RTSP/Webcam, xem trước Live Snapshot trực tiếp |
| **📐 Cấu Hình Vùng ROI** | [http://localhost:8000/roi-config](http://localhost:8000/roi-config) | Công cụ vẽ Canvas Red Zone (Bàn học) và Green Zone (Bục giảng giáo viên) |
| **📑 Báo Cáo & Dữ Liệu** | [http://localhost:8000/reports](http://localhost:8000/reports) | Tra cứu lịch sử theo ngày/lớp, tải file Excel chuẩn Sở GD&ĐT, gửi tin Zalo qua Bot Gateway |
| **📖 Swagger API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Tài liệu kỹ thuật OpenAPI/Swagger thử nghiệm trực tiếp các API RESTful |

---

## 🧠 QUY TRÌNH HUẤN LUYỆN MÔ HÌNH AI (TRAINING PIPELINE)

Toàn bộ công cụ phục vụ huấn luyện mô hình YOLOv8 được bố trí gọn gàng trong thư mục `training/`:

1. **Trích xuất khung hình từ video mẫu:**
   ```powershell
   python training/sample_extractor.py
   ```
2. **Chuẩn hóa nhãn & phân bổ tập train/val:**
   ```powershell
   python training/prepare_dataset.py
   ```
3. **Sinh lại bộ dữ liệu đa phương tiện cho 30 lớp học:**
   ```powershell
   python training/generate_classrooms_media.py
   ```
4. **Kích hoạt huấn luyện trên GPU NVIDIA RTX (1-Click):**
   ```powershell
   training\train_gpu.bat
   ```
   *Hoặc chạy trực tiếp qua CLI với các tham số tùy biến:*
   ```powershell
   python training/train_yolo.py --epochs 30 --imgsz 640 --batch 4 --device 0
   ```
   Sau khi huấn luyện hoàn tất, trọng số tối ưu nhất sẽ được tự động xuất bản vào `models/classroom_best.pt`.

*Xem sổ tay chi tiết tại: [training/HUONG_DAN_TRAINING_AI.md](training/HUONG_DAN_TRAINING_AI.md).*

---

## 🧪 KIỂM THỬ TỰ ĐỘNG (AUTOMATED TESTS)

Hệ thống đi kèm bộ kiểm thử tự động toàn diện đạt tỷ lệ vượt qua **13/13 test cases**:
```powershell
python -m pytest tests/ -v
```

Danh mục các bộ kiểm thử:
- `tests/test_attendance_engine.py`: Quy trình điều phối quét sĩ số học sinh và tính toán tỷ lệ vắng.
- `tests/test_camera_management.py`: Kiểm tra CRUD camera, phân loại RTSP/Webcam/File.
- `tests/test_roi_masking.py`: Kiểm tra thuật toán Point-in-Polygon lọc khu vực Red Zone và Green Zone.
- `tests/test_excel_export.py`: Kiểm tra cấu trúc file Excel xuất ra theo quy chuẩn mẫu của Sở GD&ĐT.
- `tests/test_zalo_service.py`: Kiểm tra định dạng webhook gửi cảnh báo qua Zalo.
- `tests/test_rtsp_mock.py`: Kiểm tra khả năng xử lý mất kết nối mạng và phục hồi luồng hình ảnh.

---

## 📚 TÀI LIỆU KỸ THUẬT ĐI KÈM

Để tìm hiểu chi tiết từng thành phần, vui lòng tham khảo các tài liệu chuyên sâu:

- 🏛️ **Kiến trúc tổng thể & Quy chuẩn cộng tác:** [KIEN_TRUC_HE_THONG.md](KIEN_TRUC_HE_THONG.md)
- 🎨 **Sổ tay phát triển Frontend:** [frontend/README_FRONTEND.md](frontend/README_FRONTEND.md)
- ⚙️ **Sổ tay phát triển Backend REST API:** [backend/README_BACKEND.md](backend/README_BACKEND.md)
- 🗄️ **Sổ tay phát triển Cơ sở dữ liệu:** [database/README_DATABASE.md](database/README_DATABASE.md)
- 🧠 **Sổ tay huấn luyện mô hình AI YOLOv8:** [training/HUONG_DAN_TRAINING_AI.md](training/HUONG_DAN_TRAINING_AI.md)
- 📁 **Thuyết minh bộ dữ liệu 30 lớp học:** [dataset/classrooms_media/README.md](dataset/classrooms_media/README.md)

---

## 📜 BẢN QUYỀN
Hệ thống được thiết kế, phát triển và chuyển giao phục vụ đề án chuyển đổi số giáo dục tại **Trường THPT Điều Cải**.
Mọi quyền sở hữu trí tuệ thuộc về nhóm tác giả và nhà trường.
