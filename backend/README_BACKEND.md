# Hướng Dẫn Dành Cho Lập Trình Viên Backend (Backend Team)

Phân hệ Backend chịu trách nhiệm cung cấp REST API, xử lý nghiệp vụ điểm danh, điều phối phần cứng và giao tiếp cơ sở dữ liệu.

---

## 1. Cấu Trúc Phân Hệ Backend & Modules Nghiệp Vụ

```text
backend/
├── api/
│   └── routers/
│       ├── attendance.py   # /api/attendance: Kích hoạt quét & lấy dữ liệu phiên
│       ├── cameras.py      # /api/cameras: Thêm, sửa, xóa camera, test nguồn
│       ├── roi.py          # /api/roi: Lưu tọa độ ROI, test nhận diện AI tức thì
│       ├── reports.py      # /api/reports: Lấy danh sách báo cáo, tải Excel, gửi Zalo
│       └── system.py       # /api/system: Thông tin DB, HealthCheck, sample media
├── schemas/                # Pydantic Models kiểm tra tính hợp lệ dữ liệu đầu vào
└── main.py                 # FastAPI Application & Cấu hình CORS, Lifespan

core/                       # Động cơ nghiệp vụ cốt lõi
├── attendance_engine.py    # Điều phối quét 30 camera song song & tính sĩ số
├── detector.py             # Xử lý ảnh bằng mô hình YOLOv8 + Tiled Inference
├── roi_manager.py          # Thuật toán Point-in-Polygon lọc người ngoài vùng
├── rtsp_client.py          # Đa luồng bắt frame từ camera RTSP / Webcam / File
├── relay_service.py        # Kích hoạt đèn LED báo hiệu
└── image_enhancer.py       # Tăng cường độ nét ảnh & chống ngược sáng (CLAHE)

services/                   # Dịch vụ mở rộng
├── excel_exporter.py       # Tạo tệp Excel báo cáo chuẩn
├── zalo_service.py         # Gửi thông báo qua Zalo Webhook / OA API
├── notification.py         # Gửi email báo cáo cho Ban Giám Hiệu
└── scheduler.py            # Hẹn giờ tự động điểm danh lúc 06:45 AM
```

---

## 2. Cách Khởi Động & Phát Triển

1. Khởi động máy chủ phát triển với chế độ tự động reload khi sửa code:
   ```cmd
   run_backend.bat
   ```
2. Tra cứu tài liệu API tự động (Swagger UI):
   - **Swagger UI**: `http://localhost:8000/docs`
   - **ReDoc**: `http://localhost:8000/redoc`

---

## 3. Quy Chuẩn Bổ Sung API Mới

- Định nghĩa Schema dữ liệu đầu vào tại `backend/schemas/`.
- Tạo hoặc bổ sung router tại `backend/api/routers/`.
- Đăng ký router vào `backend/main.py` với tiền tố `/api`.
- Viết Unit Test tương ứng trong `tests/` để đảm bảo độ tin cậy.
