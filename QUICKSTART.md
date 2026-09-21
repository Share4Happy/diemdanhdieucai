# 🚀 Khởi Động Nhanh - Hệ Thống Điểm Danh AI

## Cài Đặt 3 Bước

### 1️⃣ Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2️⃣ Cấu hình admin (tạo file `.env`)
```bash
copy .env.example .env
```

Chỉnh sửa `.env`:
```env
ADMIN_EMAIL=admin@truongdieucai.edu.vn
ADMIN_PASSWORD=Admin@2025
JWT_SECRET=change-this-to-random-secret-key
```

### 3️⃣ Khởi động server
```bash
python app.py
```

Hoặc trên Windows:
```bash
run.bat
```

---

## 📱 Truy Cập

Mở trình duyệt: **http://localhost:8000**

### Đăng nhập lần đầu
- **Email**: `admin@truongdieucai.edu.vn`
- **Mật khẩu**: `Admin@2025` (hoặc giá trị bạn đặt trong .env)

---

## 🎯 Các Trang Chính

| Trang | URL | Mô tả |
|-------|-----|-------|
| Dashboard | `/` | Giám sát điểm danh 30 lớp |
| Camera | `/cameras` | Quản lý camera & lớp học |
| ROI | `/roi-config` | Vẽ vùng phân tích AI |
| Báo cáo | `/reports` | Xem lịch sử & xuất Excel |
| Tài khoản | `/users` | Quản lý user (admin) |

---

## 👥 Tạo Tài Khoản Mới

1. Đăng nhập với tài khoản **admin**
2. Vào **Hệ thống** → **Tài khoản**
3. Điền thông tin user mới
4. Chọn vai trò: **Nhân viên** hoặc **Quản trị**

---

## 🔑 Quên Mật Khẩu

Cần cấu hình SMTP trong `.env`:
```env
SMTP_USER=admin@truongdieucai.edu.vn
SMTP_PASSWORD=your-gmail-app-password
```

Với Gmail: Tạo App Password tại https://myaccount.google.com/apppasswords

---

## 📚 Tài Liệu Chi Tiết

- [Installation Guide](docs/INSTALLATION.md) - Hướng dẫn cài đặt chi tiết
- [Authentication Guide](docs/AUTHENTICATION_GUIDE.md) - Hệ thống xác thực
- [Backend README](backend/README_BACKEND.md) - API documentation
- [Database README](database/README_DATABASE.md) - Schema & ERD

---

## ⚠️ Lưu Ý

### Lần khởi động đầu tiên
- Hệ thống tự động tạo admin nếu DB trống
- Cần đặt `ADMIN_EMAIL` và `ADMIN_PASSWORD` trong `.env`

### Bảo mật
- Đổi `JWT_SECRET` thành chuỗi ngẫu nhiên
- Đổi `ADMIN_PASSWORD` thành mật khẩu mạnh
- SMTP không bắt buộc (chỉ cần cho reset password)

### Môi trường production
- Đổi `APP_PUBLIC_URL` thành domain thực
- Siết `CORS_ORIGINS` theo domain cụ thể

---

## 🐛 Xử Lý Lỗi

### Lỗi: No module named 'jwt'
```bash
pip install PyJWT bcrypt
```

### Lỗi: Address already in use
Đổi port trong `config/settings.py`:
```python
PORT: int = 8080
```

### Không đăng nhập được
- Xóa cookie browser
- Kiểm tra `CORS_ORIGINS` có chứa origin đang dùng không

---

**Hệ thống sẵn sàng! 🎉**

Xem [Authentication Guide](docs/AUTHENTICATION_GUIDE.md) để biết thêm chi tiết.
