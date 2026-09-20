# Hướng Dẫn Dành Cho Lập Trình Viên Giao Diện (Frontend Team)

Thư mục `frontend/` chứa toàn bộ mã nguồn giao diện người dùng của Hệ Thống Điểm Danh AI THPT Điều Cải.

---

## 1. Cấu Trúc Phân Hệ Frontend

```text
frontend/
├── css/
│   ├── main.css            # Biến màu sắc CSS Variables, Typography, Layout chung
│   ├── dashboard.css       # Style cho lưới 30 lớp học và Modal phóng to
│   ├── cameras.css         # Style cho trang quản lý camera và bảng trạng thái
│   ├── roi_config.css      # Style cho bảng công cụ vẽ đa giác Canvas
│   └── reports.css         # Style cho bộ lọc báo cáo và bảng biểu
├── js/
│   ├── api.js              # API Client trung tâm (fetchAPI, showToast, URL helpers)
│   ├── dashboard.js        # Logic trang giám sát điểm danh chính
│   ├── cameras.js          # Logic trang thêm/sửa/xóa camera và test kết nối
│   ├── roi_config.js       # Logic vẽ đa giác Canvas Red Zone / Green Zone
│   └── reports.js          # Logic xem lịch sử, tải Excel, gửi Zalo / Email
├── index.html              # Trang chủ: Dashboard Giám Sát Điểm Danh
├── cameras.html            # Trang: Quản Lý Nguồn Camera & Lớp Học
├── roi-config.html         # Trang: Cấu Hình Không Gian Tọa Độ ROI
└── reports.html            # Trang: Thống Kê & Báo Cáo Sĩ Số
```

---

## 2. Cách Khởi Động & Phát Triển Độc Lập

Bạn có thể chạy độc lập Frontend mà không cần cài đặt các thư viện Python chuyên sâu:
1. Chạy file:
   ```cmd
   run_frontend.bat
   ```
   (Server sẽ mở tại `http://localhost:3000/index.html`).
2. Hoặc sử dụng extension **Live Server** trong VSCode / Cursor / Antigravity mở trực tiếp `index.html`.

---

## 3. Quy Chuẩn Gọi API

Mọi tương tác dữ liệu với Backend đều thông qua `js/api.js`:
```javascript
import { AttendanceAPI, CameraAPI, showToast } from './api.js';

// Ví dụ kích hoạt quét điểm danh:
const result = await AttendanceAPI.triggerScan();

// Hiển thị thông báo Toast chuẩn UI:
showToast('Đã lưu cấu hình thành công!', 'success');
```
*Lưu ý: `api.js` đã được cấu hình tự động nhận diện nếu Frontend chạy ở port khác (ví dụ 3000) sẽ tự động gọi sang Backend tại `http://localhost:8000` qua CORS.*
