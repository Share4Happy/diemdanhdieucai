# 🎓 HỆ THỐNG ĐIỂM DANH HỌC SINH TỰ ĐỘNG BẰNG AI CAMERA
### Trường THPT Điều Cải

Hệ thống điểm danh tự động 30 lớp học bằng thị giác máy tính AI (YOLOv8 Fine-tuned), tích hợp phân vùng không gian ROI (Red Zone / Green Zone), điều khiển đèn LED báo hiệu qua Relay, tự động lập lịch quét đầu giờ sáng và xuất báo cáo Excel, thông báo Zalo.

---

## 🌟 TÍNH NĂNG NỔI BẬT

1. **AI Đếm Sĩ Số Lớp Học Chính Xác Cao (YOLOv8 Custom Head Detection):**
   - Huấn luyện chuyên biệt nhận diện đầu và nửa thân trên học sinh từ camera góc cao.
   - Nhận diện tốt học sinh ngồi cúi đầu đọc sách, viết bài hoặc bị bạn ngồi trước che khuất (*Occlusion*).
   - Áp dụng thuật toán SAHI (quét đa tỷ lệ phân mảnh) và chống ngược sáng CLAHE.

2. **Phân Vùng Không Gian Không Gian Đa Giác (Spatial Masking):**
   - **Red Zone (Khu vực bàn học):** AI chỉ đếm số lượng học sinh ngồi trong vùng bàn học.
   - **Green Zone (Khu vực bục giảng):** Tự động nhận diện và loại trừ thầy/cô giáo khỏi sĩ số học sinh.

3. **Trình Soi Chi Tiết AI Tracking (Interactive Lightbox):**
   - Bấm vào ảnh để mở trình phóng to toàn màn hình (*Dark Glassmorphism*).
   - Hỗ trợ lăn chuột zoom từ 60% đến 500%, kéo chuột rê ảnh (*Pan*) để soi rõ từng số thứ tự `#01, #02...` của từng bàn.
   - Nút chuyển đổi nhanh giữa **Ảnh AI phân tích** và **Ảnh gốc camera** để đối chứng trực tiếp.

4. **Quản Lý Camera & Kiểm Tra Trực Tiếp (Live Snapshot):**
   - Hỗ trợ đa dạng nguồn camera: Camera IP RTSP (Dahua, Hikvision...), Webcam máy tính, File video mẫu.
   - Kiểm tra kết nối TCP nhanh và xem trước ảnh trực tiếp (*Live Snapshot*) trước khi lưu.

5. **Tự Động Xuất Báo Cáo & Thông Báo:**
   - Lập lịch tự động quét lúc 06:45 AM hàng ngày (Thứ 2 đến Thứ 7).
   - Tự động xuất file báo cáo Excel chi tiết theo biểu mẫu chuẩn ngành giáo dục.
   - Tích hợp gửi thông báo sĩ số tức thì qua Zalo Webhook / Zalo OA.

---

## 🛠️ CÔNG NGHỆ SỬ DỤNG

- **Backend:** Python 3.10+, FastAPI, Uvicorn
- **AI / Computer Vision:** Ultralytics YOLOv8, OpenCV, PyTorch, SAHI
- **Database:** SQLite / SQLAlchemy ORM
- **Frontend:** HTML5, Vanilla CSS (Modern Dashboard), JavaScript (Canvas ROI Polygon, Interactive Lightbox)
- **Scheduler:** APScheduler
- **Hardware Integration:** RTSP Client (DirectShow / FFmpeg), Camera I/O Alarm Output Relay

---

## 🚀 CÁCH CÀI ĐẶT VÀ KHỞI CHẠY

### 1. Cài đặt thư viện:
```powershell
pip install -r requirements.txt
```

### 2. Khởi động hệ thống:
Cách 1: Nhấp đúp chuột vào file **`run.bat`** (Khuyến nghị cho Windows)  
Cách 2: Chạy lệnh dòng lệnh:
```powershell
python app.py
```

Sau khi khởi động, mở trình duyệt truy cập:
- **Dashboard Điểm Danh:** [http://localhost:8000](http://localhost:8000)
- **Quản Lý Camera:** [http://localhost:8000/cameras](http://localhost:8000/cameras)
- **Cấu Hình Vùng ROI:** [http://localhost:8000/roi-config](http://localhost:8000/roi-config)
- **Báo Cáo & Dữ Liệu:** [http://localhost:8000/reports](http://localhost:8000/reports)

---

## 📂 CẤU TRÚC DỰ ÁN

```text
hethongdiemdanh Dieu Cai/
├── app.py                     # Ứng dụng chính FastAPI & Web Routes
├── run.bat                    # Script 1-click khởi động hệ thống trên Windows
├── train_yolo.py              # Script huấn luyện AI YOLOv8 tự động
├── HUONG_DAN_TRAINING_AI.md   # Hướng dẫn chi tiết quy trình gán nhãn & train AI
├── config/                    # Cấu hình hệ thống (settings.py, logging_config.py)
├── core/                      # Các module lõi xử lý AI, Camera & Điểm danh
│   ├── detector.py            # AI Student Detection & Spatial Masking
│   ├── attendance_engine.py   # Quy trình điểm danh đồng loạt
│   ├── rtsp_client.py         # Kết nối đa luồng Camera RTSP / Webcam
│   ├── roi_manager.py         # Quản lý thuật toán vùng đa giác ROI
│   └── relay_service.py       # Điều khiển Relay đèn LED báo hiệu
├── database/                  # CSDL SQLite & Models SQLAlchemy
├── dataset/                   # Tập dữ liệu ảnh mẫu & file nhãn train AI
├── models/                    # Thư mục lưu trữ trọng số mô hình YOLO đã huấn luyện
├── storage/                   # Lưu trữ ảnh chụp camera, ảnh phân tích và báo cáo Excel
└── web/                       # Giao diện người dùng Web UI (HTML, CSS, JS)
```

---

## 📜 BẢN QUYỀN
Hệ thống được phát triển phục vụ công tác quản trị trường học thông minh tại Trường THPT Điều Cải.
