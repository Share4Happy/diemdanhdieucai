# Hướng Dẫn Dành Cho Lập Trình Viên Giao Diện (Frontend Team)

Thư mục `frontend/` chứa toàn bộ mã nguồn giao diện người dùng Web Dashboard của Hệ Thống Điểm Danh AI THPT Điều Cải.

---

## 1. Cấu Trúc Phân Hệ Frontend

```text
frontend/
├── index.html              # Trang chủ: Dashboard Giám Sát Điểm Danh 30 Lớp
├── login.html              # Màn hình Đăng nhập (JWT + Cookie)
├── forgot-password.html    # Màn hình Quên mật khẩu qua Email
├── reset-password.html     # Màn hình Đặt lại mật khẩu mới
├── users.html              # Màn hình Quản lý tài khoản & phân quyền (Admin)
├── cameras.html            # Trang Quản Lý Nguồn Camera & Lớp Học
├── roi-config.html         # Trang Cấu Hình Không Gian Tọa Độ ROI Đa Giác
├── reports.html            # Trang Thống Kê, Báo Cáo & Soi Ảnh Chi Tiết
├── notifications.html      # Trang Cấu Hình Kênh Thông Báo (Zalo & Email)
├── css/
│   ├── main.css            # Biến màu sắc CSS Variables, Typography, Layout chung
│   ├── auth.css            # Giao diện Glassmorphism cho Login, Forgot/Reset Password
│   ├── dashboard.css       # Style cho lưới 30 lớp học và Modal phóng to
│   ├── cameras.css         # Style cho trang quản lý camera và TV Wall
│   ├── roi_config.css      # Style cho bảng công cụ vẽ đa giác Canvas
│   ├── reports.css         # Style cho bộ lọc báo cáo, bảng biểu & Lightbox zoom/pan
│   ├── layout/             # Khung sườn bố cục giao diện (sidebar, header, app-shell)
│   └── components/         # Các thành phần giao diện tái sử dụng (button, card, modal, skeleton)
└── js/
    ├── api.js              # API Client trung tâm (fetchAPI, showToast, Token helpers)
    ├── login.js            # Logic đăng nhập & điều hướng
    ├── users.js            # Logic quản lý tài khoản người dùng
    ├── dashboard.js        # Logic trang giám sát điểm danh chính
    ├── cameras.js          # Logic trang thêm/sửa/xóa camera và test kết nối
    ├── roi_canvas.js       # Động cơ vẽ Canvas đa giác tương tác
    ├── roi_config.js       # Logic cấu hình tọa độ ROI đa giác
    ├── reports.js          # Logic xem lịch sử, phóng to ảnh, tải Excel, gửi Zalo
    ├── notifications.js    # Logic cấu hình Zalo Bot Gateway & SMTP Email
    └── shared/
        ├── app-shell.js    # Quản lý Sidebar, Header, Đăng xuất
        └── auth-guard.js   # Bảo vệ phiên làm việc JWT cho các trang chức năng
```

---

## 2. Thông Tin Đăng Nhập Mặc Định

- **Email Quản trị:** `admin@truongdieucai.edu.vn`
- **Mật khẩu:** `Admin@2025`
- **Vai trò:** `admin` (quản trị toàn diện, tạo user tại `/users.html`) hoặc `staff` (xem dashboard, báo cáo).

---

## 3. Quy Ước Màu Sắc ROI (Spatial Masking)

- 🟢 **Vùng Xanh (Green Zone) - Phần LẤY:** Khu vực bàn ghế học sinh. AI đếm sĩ số học sinh ngồi bên trong vùng này.
- 🔴 **Vùng Đỏ (Red Zone) - Phần BỎ ĐI:** Khu vực bục giảng / bàn giáo viên. Tự động loại trừ để không tính giáo viên vào sĩ số.

---

## 4. Cách Khởi Động & Phát Triển Độc Lập

Bạn có thể chạy độc lập Frontend mà không cần cài đặt các thư viện Python chuyên sâu:
1. Chạy file:
   ```cmd
   run_frontend.bat
   ```
   (Server giao diện sẽ mở tại `http://localhost:3000`).
2. Hoặc mở trực tiếp qua Backend FastAPI tại:
   ```cmd
   run.bat
   ```
   (Truy cập tại `http://localhost:8000`).

---

## 5. Quy Chuẩn Gọi API

Mọi tương tác dữ liệu với Backend đều thông qua `js/api.js`:
```javascript
import { AttendanceAPI, CameraAPI, AuthAPI, showToast } from './api.js';

// Kiểm tra thông tin người dùng đang đăng nhập:
const me = await AuthAPI.getMe();

// Kích hoạt quét điểm danh:
const result = await AttendanceAPI.triggerScan();

// Hiển thị thông báo Toast chuẩn UI:
showToast('Đã lưu cấu hình thành công!', 'success');
```
*Lưu ý: `api.js` tự động nhận diện nếu Frontend chạy ở port 3000 sẽ tự động kết nối sang Backend tại `http://localhost:8000` qua CORS.*
