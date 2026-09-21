# 🎨 PHÂN HỆ FRONTEND - HỆ THỐNG ĐIỂM DANH AI THPT ĐIỀU CẢI

![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white)
![CSS3 Glassmorphism](https://img.shields.io/badge/CSS3-Glassmorphism%20Design-1572B6?logo=css3)
![JavaScript ES6+](https://img.shields.io/badge/JavaScript-ES6%2B%20Modular-F7DF1E?logo=javascript&logoColor=black)
![JWT Auth](https://img.shields.io/badge/Auth-JWT%20Guard-FF6F00)
![Responsive](https://img.shields.io/badge/Responsive-Desktop%20%7C%20Tablet%20%7C%20Mobile-brightgreen)

Thư mục `frontend/` chứa toàn bộ mã nguồn giao diện Web Dashboard của Hệ Thống Điểm Danh Học Sinh Tự Động Bằng AI Camera tại **Trường THPT Điều Cải**.

---

## 🌟 TRIẾT LÝ THIẾT KẾ & TÍNH NĂNG NỔI BẬT

1. **Phong cách Glassmorphism Cao Cấp:**
   - Sử dụng hiệu ứng kính mờ (*Backdrop Blur*), độ tương phản cao, bảng màu HSL hiện đại với nền tối Dark Modern Theme.
   - Micro-animations mượt mà, Skeleton Loaders tối ưu trải nghiệm khi tải dữ liệu lớn từ 30 camera.
2. **Bảo Mật Xác Thực & Phân Quyền (JWT Auth Guard):**
   - Kiểm soát truy cập phân tầng thông qua `js/shared/auth-guard.js`.
   - Tự động kiểm tra phiên làm việc và chuyển hướng người dùng chưa đăng nhập về trang `/login.html`.
   - Phân quyền theo vai trò: **Quản trị viên (Admin)** và **Nhân viên (Staff)**.
3. **Phân Vùng Không Gian Đa Giác ROI Trực Quan (HTML5 Canvas):**
   - 🟢 **Vùng Xanh (Green Zone) - Phần LẤY:** Khu vực bàn học sinh. AI chỉ đếm và đánh số thứ tự `#01, #02, #03...` cho học sinh ngồi trong vùng này.
   - 🔴 **Vùng Đỏ (Red Zone) - Phần BỎ ĐI:** Khu vực bục giảng / bàn giáo viên. Tự động loại trừ 100% người đứng hoặc ngồi tại khu vực này để không tính nhầm vào sĩ số học sinh.
4. **Trình Soi Chi Tiết AI Tracking (Interactive Lightbox Zoom & Pan):**
   - Bấm vào bất kỳ ảnh kết quả nào để mở Lightbox phóng to toàn màn hình.
   - Hỗ trợ cuộn chuột thu phóng từ 60% đến 500%, kéo chuột rê ảnh (*Pan*) để kiểm tra từng góc lớp.
   - Nút chuyển đổi tức thì giữa **Ảnh AI phân tích** và **Ảnh gốc Camera**.
   - Hỗ trợ đóng modal linh hoạt bằng nút X, phím `Escape` hoặc click vào nền kính mờ.
5. **Giám Sát Camera & Ma Trận TV Wall:**
   - Quản lý danh mục 30 lớp học và luồng Camera IP RTSP / Webcam máy tính / File mô phỏng.
   - Xem trước Live Snapshot tức thì, kiểm tra kết nối mạng và hiển thị ma trận camera trực quan.
6. **Báo Cáo Thông Minh & Cấu Hình Thông Báo:**
   - Tra cứu lịch sử điểm danh theo ngày và khối lớp, lọc nhanh danh sách vắng.
   - Xuất file Excel (.xlsx) chuẩn biểu mẫu quy định của Sở GD&ĐT.
   - Cấu hình gửi thông báo thời gian thực qua **Zalo Bot Gateway** và **Email SMTP**.

---

## 🔑 THÔNG TIN TÀI KHOẢN MẶC ĐỊNH

Khi hệ thống khởi chạy lần đầu tiên, tài khoản quản trị mặc định sẽ được nạp tự động vào cơ sở dữ liệu:

| Thuộc tính | Giá trị mặc định | Ghi chú |
| :--- | :--- | :--- |
| **Email đăng nhập** | `admin@truongdieucai.edu.vn` | Định cấu hình trong `.env` (`ADMIN_EMAIL`) |
| **Mật khẩu mặc định** | `Admin@2025` | Định cấu hình trong `.env` (`ADMIN_PASSWORD`) |
| **Vai trò (Role)** | `admin` | Toàn quyền cấu hình camera, ROI, thông báo và quản lý tài khoản |

> [!TIP]
> Quản trị viên có thể truy cập trang **Quản lý tài khoản** (`/users.html`) để đổi mật khẩu, thêm tài khoản mới cho cán bộ giáo viên (`staff`) hoặc thu hồi quyền truy cập khi cần thiết.

---

## 📁 CẤU TRÚC PHÂN HỆ FRONTEND

```text
frontend/
│
├── 📄 CÁC TRANG MÀN HÌNH CHÍNH (HTML):
│   ├── index.html                  # Dashboard giám sát thời gian thực 30 lớp học & kích hoạt quét
│   ├── login.html                  # Màn hình đăng nhập hệ thống bảo mật bằng JWT
│   ├── forgot-password.html        # Màn hình yêu cầu cấp lại mật khẩu qua Email SMTP
│   ├── reset-password.html         # Màn hình đặt lại mật khẩu mới với mã xác thực Token
│   ├── users.html                  # Quản lý danh sách tài khoản, thêm người dùng & phân quyền (Admin)
│   ├── cameras.html                # Quản lý danh mục Camera 30 lớp, xem Live Snapshot & TV Wall
│   ├── roi-config.html             # Công cụ vẽ phân vùng không gian đa giác ROI (Green Zone & Red Zone)
│   ├── reports.html                # Tra cứu lịch sử, soi ảnh đối chứng, xuất Excel & gửi Zalo
│   └── notifications.html          # Cấu hình kênh thông báo Zalo Bot Gateway & Email SMTP
│
├── 🎨 HỆ THỐNG GIAO DIỆN (CSS):
│   ├── auth.css                    # Phong cách Glassmorphism cho Login, Quên mật khẩu & Đặt lại mật khẩu
│   ├── main.css                    # Biến màu sắc CSS Variables, Typography, thanh cuộn tùy biến
│   ├── dashboard.css               # Phong cách lưới 30 lớp học, thẻ chỉ số KPI & thanh tiến độ
│   ├── cameras.css                 # Bảng cấu hình Camera, thẻ Camera Card & Live Preview
│   ├── roi_config.css              # Bảng công cụ vẽ Canvas, bảng nút chức năng phân vùng
│   ├── reports.css                 # Bộ lọc dữ liệu báo cáo, bảng tổng hợp sĩ số & Modal Soi ảnh
│   ├── layout/
│   │   ├── app-shell.css           # Bố cục khung sườn chung: Sidebar điều hướng, Header, User Menu
│   │   ├── sidebar.css             # Thanh điều hướng bên trái
│   │   └── header.css              # Thanh tiêu đề, thông tin đăng nhập & nút Đăng xuất
│   └── components/
│       ├── buttons.css             # Các kiểu nút bấm bấm gradient, icon button
│       ├── cards.css               # Thẻ kính mờ Glassmorphism
│       ├── tables.css              # Bảng biểu hiển thị dữ liệu chuẩn
│       ├── modal-system.css        # Hệ thống hộp thoại Modal và Popup xác nhận
│       └── skeleton-loader.css     # Hiệu ứng nạp dữ liệu chờ (Skeleton Shimmer)
│
├── ⚡ LOGIC XỬ LÝ & TƯƠNG TÁC (JAVASCRIPT):
│   ├── api.js                      # API Client trung tâm (fetchAPI, Token handling, Toast notifications)
│   ├── dashboard.js                # Logic nạp sĩ số 30 lớp, kích hoạt quét điểm danh thủ công
│   ├── login.js                    # Logic đăng nhập, lưu trữ JWT và điều hướng Dashboard
│   ├── users.js                    # Logic tải danh sách user, tạo mới user, phân quyền Admin/Staff
│   ├── cameras.js                  # Logic thêm/sửa/xóa camera, kiểm tra kết nối RTSP & chụp Snapshot
│   ├── roi_canvas.js               # Động cơ vẽ Canvas đa giác, kéo thả đỉnh, hiển thị Green/Red Zone
│   ├── roi_config.js               # Logic điều khiển trang ROI, chọn lớp, lưu tọa độ lên máy chủ
│   ├── reports.js                  # Logic tra cứu lịch sử, phóng to ảnh AI (Zoom/Pan), xuất Excel, gửi Zalo
│   ├── notifications.js            # Logic lưu và kiểm tra kết nối Zalo Bot Gateway / Email SMTP
│   ├── shared/
│   │   ├── app-shell.js            # Quản lý Sidebar, hiển thị tên người dùng và sự kiện Đăng xuất
│   │   └── auth-guard.js           # Bộ gác cổng bảo vệ định danh JWT trên mọi trang chức năng
│   └── components/
│       └── skeleton-templates.js   # Khung xương hiển thị tạm thời khi hệ thống đang nạp dữ liệu
│
└── 📖 TÀI LIỆU HƯỚNG DẪN:
    ├── README.md                   # Tài liệu tổng quan phân hệ Frontend (Tệp này)
    └── README_FRONTEND.md          # Sổ tay ngắn gọn dành cho lập trình viên giao diện
```

---

## 🎯 QUY ƯỚC PHÂN VÙNG ROI TRÊN CANVAS (`roi-config.html`)

Khi thiết lập vùng nhận diện cho từng phòng học, công cụ Canvas sử dụng quy chuẩn màu sắc phân định rõ ràng:

```text
 ┌─────────────────────────────────────────────────────────────┐
 │                      KHUNG HÌNH CAMERA                      │
 │                                                             │
 │   ┌───────────────────────┐                                 │
 │   │  🔴 VÙNG ĐỎ           │  <-- BỤC GIẢNG / BÀN GIÁO VIÊN  │
 │   │  (RED ZONE - BỎ ĐI)   │      (Loại trừ 100% giáo viên)  │
 │   └───────────────────────┘                                 │
 │                                                             │
 │   ┌─────────────────────────────────────────────────────┐   │
 │   │  🟢 VÙNG XANH                                       │   │
 │   │  (GREEN ZONE - PHẦN LẤY)                            │   │
 │   │                                                     │   │
 │   │  #01 👤    #02 👤    #03 👤    #04 👤               │   │
 │   │  #05 👤    #06 👤    #07 👤    #08 👤               │   │
 │   │                                                     │   │
 │   │  <-- KHU VỰC BÀN HỌC SINH (AI tính sĩ số tại đây)   │   │
 │   └─────────────────────────────────────────────────────┘   │
 └─────────────────────────────────────────────────────────────┘
```

- 🟢 **Vùng Xanh Lá (Green Zone) - Phần LẤY (Bàn học sinh):**
  - Bao quanh toàn bộ các dãy bàn ghế học sinh.
  - AI YOLOv8 chỉ đếm và vẽ bounding box, đánh số thứ tự `#01, #02...` cho người có đỉnh đầu/thân trên nằm bên trong vùng này.
  - Giá trị mặt nạ nhị phân trên Backend: `mask = 255` (Khu vực giữ lại).
- 🔴 **Vùng Đỏ (Red Zone) - Phần BỎ ĐI (Bục giảng / Bàn giáo viên):**
  - Bao quanh bục giảng, bàn giáo viên và cửa ra vào lớp học.
  - Bất kỳ ai xuất hiện trong khu vực này sẽ bị thuật toán loại trừ tức thì, đảm bảo thầy cô đứng lớp không bị tính vào sĩ số học sinh.
  - Giá trị mặt nạ nhị phân trên Backend: `mask = 0` (Khu vực loại bỏ).

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY & PHÁT TRIỂN

### Cách 1: Khởi động tích hợp cùng Backend (Khuyến nghị)
Toàn bộ mã nguồn thư mục `frontend/` đã được cấu hình phục vụ trực tiếp qua FastAPI static files. Khi khởi chạy Backend:
```powershell
run.bat
# hoặc
python app.py
```
Mở trình duyệt truy cập: **`http://localhost:8000`**.

### Cách 2: Khởi động riêng Frontend độc lập (Cổng 3000)
Dành cho lập trình viên chuyên trách giao diện muốn tinh chỉnh CSS/JS mà không cần khởi động AI hoặc GPU:
```powershell
run_frontend.bat
```
Giao diện sẽ chạy tại `http://localhost:3000`. Mô-đun `js/api.js` đã được lập trình sẵn để tự động phát hiện và chuyển tiếp tất cả các yêu cầu REST API sang Backend tại cổng `8000` thông qua giao thức CORS.

---

## 🔌 QUY CHUẨN TƯƠNG TÁC API QUA `api.js`

Mọi thao tác đọc/ghi dữ liệu đều tập trung thông qua `frontend/js/api.js`:

```javascript
import { AttendanceAPI, CameraAPI, AuthAPI, showToast } from './api.js';

// 1. Kiểm tra trạng thái phiên làm việc hiện tại:
const currentUser = await AuthAPI.getMe();
console.log('Xin chào:', currentUser.full_name);

// 2. Kích hoạt chu trình quét sĩ số 30 lớp học:
try {
    const scanResult = await AttendanceAPI.triggerScan();
    showToast('Đã kích hoạt quét điểm danh thành công!', 'success');
} catch (error) {
    showToast(error.message, 'error');
}

// 3. Tải danh sách cấu hình Camera:
const cameras = await CameraAPI.getAll();
```

### Các tính năng tự động tích hợp trong `api.js`:
- **Đính kèm Token:** Tự động gửi Cookie và Header xác thực `Authorization: Bearer <token>` trong từng request.
- **Xử lý 401 Unauthorized:** Khi phiên làm việc hết hạn hoặc token không hợp lệ, hệ thống tự động lưu vị trí hiện tại và điều hướng về `/login.html`.
- **Toast Notifications:** Hàm `showToast(msg, type)` cung cấp thông báo popup đẹp mắt với các kiểu `'success'`, `'error'`, `'warning'`, `'info'`.
