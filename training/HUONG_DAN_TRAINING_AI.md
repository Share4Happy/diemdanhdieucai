# HƯỚNG DẪN HUẤN LUYỆN AI, QUẢN LÝ CAMERA & GỬI THÔNG BÁO ZALO
**Dành riêng cho:** Hệ Thống Điểm Danh AI Camera - Trường THPT Điều Cải  
**Phiên bản:** 2.0.0

---

## MỤC LỤC
1. [Cơ chế AI hiện tại và vì sao cần huấn luyện (Training)?](#1-cơ-chế-ai-hiện-tại-và-vì-sao-cần-huấn-luyện-training)
2. [Quy trình 4 bước huấn luyện AI (Fine-tuning YOLOv8)](#2-quy-trình-4-bước-huấn-luyện-ai-fine-tuning-yolov8)
3. [Hướng dẫn Thêm - Sửa - Xóa - Test Camera tại chỗ](#3-hướng-dẫn-thêm---sửa---xóa---test-camera-tại-chỗ)
4. [Hướng dẫn Cấu hình & Nhận Báo Cáo Qua ZALO](#4-hướng-dẫn-cấu-hình--nhận-báo-cáo-qua-zalo)
5. [Mở rộng: Nhận diện danh tính từng học sinh (Face Recognition)](#5-mở-rộng-nhận-diện-danh-tính-từng-học-sinh-face-recognition)

---

## 1. CƠ CHẾ AI HIỆN TẠI VÀ VÌ SAO CẦN HUẤN LUYỆN (TRAINING)?

### 1.1 Cơ chế hiện tại của hệ thống:
- Hệ thống sử dụng mô hình thị giác máy tính **YOLOv8** (`yolov8s.pt`), kết hợp thuật toán **SAHI** (cắt ảnh phân mảnh độ phân giải cao 1280px) và **Mặt nạ không gian (Spatial ROI)**:
  - **Red Zone (Vùng Bàn Học)**: AI chỉ đếm người nằm trong khu vực này.
  - **Green Zone (Vùng Bục Giảng)**: Tự động loại trừ thầy/cô giáo khỏi sĩ số học sinh.

### 1.2 Vì sao cần Huấn Luyện (Training / Fine-tuning)?
- Mô hình YOLOv8 gốc được huấn luyện trên tập dữ liệu COCO quốc tế (chủ yếu là người đi lại ngang tầm mắt ngoài đường).
- Trong lớp học thực tế trường Điều Cải:
  - Camera lắp trên trần nhà nhìn xéo xuống góc nghiêng cao.
  - Học sinh ngồi bàn sau bị bàn trước che khuất thân dưới, cúi đầu viết bài chỉ thấy đỉnh đầu và vai.
  - Ánh sáng cửa sổ bên phải có thể gây lóa.
- **Khi bạn huấn luyện mô hình bằng dữ liệu thật của trường**, AI sẽ học được hình ảnh đặc trưng: *tóc đen, áo đồng phục, tư thế ngồi viết bài từ góc camera trên cao*, giúp độ chính xác đạt gần như **100%**, không bao giờ bị bỏ sót học sinh ngồi khuất.

---

## 2. QUY TRÌNH 4 BƯỚC HUẤN LUYỆN AI (FINE-TUNING YOLOV8)

### BƯỚC 1: Thu thập ảnh lớp học mẫu (50 - 100 ảnh)
1. Trên giao diện Web Dashboard, hệ thống tự động lưu các khung hình chụp thực tế mỗi ngày tại:
   `storage/captures/YYYY-MM-DD/`
2. Hoặc bạn có thể truy cập trang **Quản Lý Camera** (`http://localhost:8000/cameras`), bấm nút **"Test"** của các lớp để tải về 50 - 100 ảnh mẫu rõ nét ở các phòng học khác nhau.

### BƯỚC 2: Gán nhãn miễn phí trong 15 phút (Bằng Roboflow)
1. Truy cập trang web miễn phí: [https://roboflow.com](https://roboflow.com) và đăng ký tài khoản.
2. Bấm **"Create New Project"**:
   - Project Type: Chọn **Object Detection**
   - Tên: `DieuCai_Students`
3. Tải các ảnh bạn vừa thu thập ở Bước 1 lên.
4. Dùng chuột vẽ hộp bao (Bounding Box) quanh **đầu và vai của từng học sinh** và đặt tên nhãn duy nhất: `student_head`.
5. Bấm **"Generate Version"** -> Chọn **"Export Dataset"** -> Chọn định dạng **YOLOv8 PyTorch** -> Tải file zip về máy tính.
6. Giải nén vào thư mục dự án theo đường dẫn:
   ```
   dataset/classroom_data/
   ├── images/
   │   ├── train/   (chứa ảnh học)
   │   └── val/     (chứa ảnh kiểm thử)
   └── labels/
       ├── train/   (chứa file text nhãn .txt)
       └── val/     (chứa file text nhãn .txt)
   ```

### BƯỚC 3: Chạy lệnh huấn luyện tự động 1-click
Mở cửa sổ dòng lệnh PowerShell trong thư mục dự án và chạy:
```bash
python train_yolo.py --epochs 50 --imgsz 1280 --batch 8
```
*(Nếu máy tính của bạn không có GPU rời, hãy chạy: `python train_yolo.py --epochs 25 --batch 4 --imgsz 640`)*

Sau khi chạy xong, chương trình tự động tối ưu hóa và xuất file mô hình tốt nhất vào:
`models/classroom_best.pt`

### BƯỚC 4: Kích hoạt mô hình mới vào hệ thống
Mở file `config/settings.py` và sửa dòng sau:
```python
# Trước:
YOLO_MODEL_NAME: str = "yolov8s.pt"

# Sau khi train:
YOLO_MODEL_NAME: str = "models/classroom_best.pt"
```
Bây giờ khởi động lại hệ thống bằng file `run.bat` là hệ thống đã hoàn toàn "hiểu" lớp học Điều Cải!

---

## 3. HƯỚNG DẪN THÊM - SỬA - XÓA - TEST CAMERA TẠI CHỖ

Truy cập đường dẫn: `http://localhost:8000/cameras` trên trình duyệt.

### 3.1 Thêm Camera mới để kiểm thử:
1. Bấm nút **"Thêm Camera / Lớp Học Mới"**.
2. **Chọn mẫu nguồn nhanh** (nếu muốn test nhanh tại chỗ):
   - **Webcam Máy Tính (0)**: Dùng ngay camera laptop/PC của bạn để test AI nhận diện người trực tiếp!
   - **Video Mẫu (15s MP4)**: Dùng file `dataset/samples/classroom_sample_15s.mp4` để phát mô phỏng mà không cần mạng.
   - **Dahua / Hikvision**: Tự động điền chuỗi RTSP chuẩn trường học.
3. Điền Tên lớp, Phòng học, Sĩ số chuẩn (ví dụ: 40 em).
4. **Bấm "Kiểm Tra Kết Nối Ngay"**:
   - Hệ thống sẽ ping tới camera trong 1 giây, đo độ trễ mạng (latency ms) và **hiển thị ngay ảnh chụp xem trước (Live Snapshot)** trên màn hình để bạn xác nhận camera hoạt động tốt trước khi lưu.
5. Bấm **"Lưu Camera"**.

### 3.2 Chỉnh sửa hoặc Xóa camera:
- Bấm nút **Sửa** (cây bút) trên từng dòng để đổi luồng RTSP hoặc sĩ số.
- Bấm nút **Xóa** (thùng rác) để xóa bỏ lớp học thử nghiệm.
- Bất kỳ lúc nào bạn muốn quay về cấu hình 30 lớp học chuẩn của trường, chỉ cần bấm nút **"Khôi Phục 30 Lớp Chuẩn"** ở góc phải trên cùng.

---

## 4. HƯỚNG DẪN CẤU HÌNH & NHẬN BÁO CÁO QUA ZALO

Sau mỗi lần quét điểm danh lúc 06:45, hệ thống sẽ tự động gửi một bản tin tóm tắt chuyên nghiệp vào điện thoại Zalo của Ban Giám hiệu:
```text
🔔 [THPT ĐIỀU CẢI] BÁO CÁO ĐIỂM DANH SĨ SỐ ĐẦU GIỜ SÁNG
📅 Ngày quét: 18/09/2026 | Giờ: 06:45:00
🏫 Tổng số lớp: 30 lớp
👥 Sĩ số toàn trường: 1,230 / 1,245 học sinh
✅ Có mặt: 1,230 | ❌ Vắng mặt: 15 em (Tỷ lệ chuyên cần: 98.8%)

⚠️ CÁC LỚP CÓ HỌC SINH VẮNG:
• Lớp 10A1 (Phòng 101): Vắng 2 em (40/42)
• Lớp 11A4 (Phòng 114): Vắng 1 em (39/40)
• Lớp 12A2 (Phòng 122): Vắng 2 em (42/44)

📂 File báo cáo chi tiết Excel và ảnh đối chứng AI đã lưu trên hệ thống máy chủ.
```

### 4.1 Cách cấu hình nhận tin nhắn Zalo:
1. Mở trang **Quản Lý Báo Cáo** (`http://localhost:8000/reports`).
2. Kéo xuống mục **"3.2 Phân Phối Thông Báo Điểm Danh Qua ZALO"**:
   - **Cách 1 - Dùng Webhook (Đơn giản nhất)**: Dán URL Webhook của Zalo Bot hoặc dịch vụ trung gian vào ô *Zalo Webhook URL*.
   - **Cách 2 - Dùng Zalo Official Account (OA OpenAPI)**:
     + Chọn phương thức `Zalo Official Account`.
     + Nhập `Access Token` và `User ID` người nhận (từ trang Zalo for Developers).
3. Bấm nút **"Lưu Cấu Hình Zalo"**.
4. Bấm nút **"Gửi Thử Tin Nhắn Qua Zalo Ngay"** để kiểm tra tin nhắn có về điện thoại ngay lập tức hay không.

---

## 5. MỞ RỘNG: NHẬN DIỆN DANH TÍNH TỪNG HỌC SINH (FACE RECOGNITION)

Nếu trong tương lai nhà trường muốn điểm danh **đích danh từng em** (biết cụ thể em nào có mặt, em nào vắng tên gì):
1. **Đăng ký khuôn mặt (Face Enrollment)**:
   - Mỗi em học sinh chụp 2-3 ảnh chân dung góc thẳng, không đeo khẩu trang.
   - Dùng mạng nơ-ron trích xuất vector đặc trưng khuôn mặt 512 chiều (Face Embedding) và lưu vào bảng CSDL `students`.
2. **Quá trình điểm danh**:
   - Khi quét camera, AI cắt các khuôn mặt học sinh trong lớp -> So khớp khoảng cách Cosine với vector đã lưu để ra tên học sinh.
3. **Lưu ý thực tế**:
   - Đối với camera góc rộng bao quát cả phòng 45 em học sinh ngồi từ bàn đầu đến cuối lớp, khuôn mặt ở bàn cuối thường nhỏ (dưới 25x25 pixel). Do đó, giải pháp **Đếm sĩ số bằng YOLO Headcount** (hiện tại của trường Điều Cải) đang là giải pháp vận hành thực tế ổn định, nhanh và kinh tế nhất!
