# HƯỚNG DẪN VẬN HÀNH HỆ THỐNG ĐIỂM DANH TỰ ĐỘNG AI CAMERA (30 LỚP HỌC)
**Đơn vị sử dụng:** Trường THPT Điều Cải  
**Phiên bản:** 1.0.0

---

## 1. TỔNG QUAN HỆ THỐNG
Hệ thống sử dụng trí tuệ nhân tạo (Computer Vision & YOLO) kết hợp luồng camera RTSP từ 30 phòng học để thực hiện điểm danh tự động vào đầu giờ sáng (mặc định 06:45 AM).

### Điểm nổi bật:
- **Spatial ROI Masking**:
  - **Red Zone (Bàn học)**: Chỉ quét và đếm đầu người/nửa thân trên học sinh bên trong vùng này.
  - **Green Zone (Bục giảng)**: Tự động loại trừ 100% bục giảng, không bao giờ đếm nhầm thầy/cô giáo vào sĩ số.
- **Tự động hóa hoàn toàn**: Đúng 06:45 AM, máy chủ kích hoạt Relay bật đèn LED hồng ngoại báo hiệu, chụp đồng loạt 30 camera qua đa luồng, AI phân tích sĩ số, tự động lưu CSDL và xuất file Excel gửi Ban Giám hiệu.
- **Chống ngược sáng (WDR / CLAHE)**: Thuật toán tiền xử lý hình ảnh cân bằng sáng tự động, loại bỏ lóa sáng từ dãy cửa sổ bên phải.

---

## 2. CẤU TRÚC THƯ MỤC
```
hethongdiemdanh Dieu Cai/
├── backend/                 # Backend REST API (FastAPI, Routers, Schemas)
├── frontend/                # Giao diện Web Dashboard (HTML5, Canvas ROI, Glassmorphism CSS)
├── core/                    # AI Engine (YOLOv8, ROI Manager, RTSP Client, CLAHE Enhancer)
├── services/                # Dịch vụ nền (Lập lịch APScheduler, Xuất Excel, Thông báo Zalo)
├── config/                  # Cấu hình tập trung (Settings, Logging)
├── database/                # SQLite / SQLAlchemy & Seeder 30 lớp học
├── dataset/                 # Ảnh/video mẫu và khung hình trích xuất
├── models/                  # Trọng số mô hình AI (classroom_best.pt)
├── storage/                 # Ảnh chụp camera, ảnh đối chứng AI và báo cáo Excel
├── tests/                   # Bộ kiểm thử tự động
├── app.py                   # Điểm khởi chạy tương thích ngược
├── run.bat                  # File 1-click khởi chạy trên Windows (hỗ trợ NVIDIA CUDA)
├── train_gpu.bat            # File 1-click huấn luyện AI trên GPU
└── requirements.txt
```

---

## 3. CÁCH KHỞI CHẠY HỆ THỐNG

### Cách 1: Chạy trực tiếp trên máy chủ Windows (Khuyến nghị)
1. Nhấp đúp chuột vào file `run.bat`.
2. Hệ thống sẽ tự kiểm tra môi trường Python/CUDA, khởi tạo CSDL 30 lớp và mở server.
3. Mở trình duyệt Web (Chrome, Edge) truy cập:
   - **Bảng điều khiển điểm danh**: `http://localhost:8000`
   - **Quản lý Camera**: `http://localhost:8000/cameras`
   - **Công cụ vẽ không gian ROI**: `http://localhost:8000/roi-config`
   - **Báo cáo & Lịch sử**: `http://localhost:8000/reports`

### Cách 2: Chạy qua dòng lệnh
```powershell
python app.py
```

---

## 4. HƯỚNG DẪN THIẾT LẬP VÙNG ROI (RED ZONE & GREEN ZONE)
1. Truy cập đường dẫn: `http://localhost:8000/roi-config`
2. Tại thanh điều khiển trên cùng, chọn lớp học cần cấu hình (từ Lớp 10A1 đến 12A10).
3. **Vẽ Vùng Bàn Học (Red Zone)**:
   - Bấm nút **"Vẽ Red Zone (Bàn Học Sinh)"**.
   - Dùng chuột nhấp vào các góc xung quanh khu vực dãy bàn học sinh.
   - Kéo thả các chấm tròn để căn chỉnh sát mép bàn.
4. **Vẽ Vùng Bục Giảng (Green Zone)**:
   - Bấm nút **"Vẽ Green Zone (Bục Giảng - Loại Trừ)"**.
   - Nhấp chuột vẽ đa giác bao quanh bục giảng và bàn giáo viên.
5. Bấm nút **"Lưu Tọa Độ Vùng"**. Tọa độ sẽ được lưu vĩnh viễn vào CSDL của lớp đó.

---

## 5. KẾT NỐI CAMERA THẬT & ĐẦU THU RTSP
Trong file `config/settings.py` hoặc sửa trực tiếp trong CSDL bảng `classrooms`:
- **Đầu thu NVR Hikvision/Dahua**:
  `rtsp://admin:matkhau@IP_DAU_THU:554/Streaming/Channels/101` (Kênh 1), `201` (Kênh 2)...
- **Sub-stream (mượt hơn khi mạng yếu)**:
  `rtsp://admin:matkhau@IP_DAU_THU:554/Streaming/Channels/102`

---

## 6. XEM VÀ TẢI BÁO CÁO EXCEL
- Sau khi chu trình quét lúc 06:45 kết thúc, file Excel tự động được sinh tại:
  `storage/reports/YYYY-MM-DD/BaoCaoDiemDanh_YYYYMMDD_SESSION_*.xlsx`
- Bản sao mới nhất luôn có sẵn tại: `storage/reports/latest/BaoCaoDiemDanh_MoiNhat.xlsx`.
- Trên giao diện Web Dashboard, người dùng chỉ cần bấm nút **"Tải Báo Cáo Excel"** màu xanh lá ở góc phải để tải về máy.
- Bấm vào bất kỳ thẻ lớp học nào trên màn hình để mở cửa sổ đối chứng: **Ảnh gốc Camera** đặt cạnh **Ảnh AI đã vẽ Bounding Box** để kiểm tra tính xác thực.
