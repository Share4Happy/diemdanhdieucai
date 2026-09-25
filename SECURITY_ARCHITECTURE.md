# SECURITY ARCHITECTURE

> Tài liệu kiến trúc bảo mật của **Hệ Thống Điểm Danh Tự Động AI - THPT Điều Cải**.
> Được lập trong khuôn khổ audit bảo mật (đã được chủ sở hữu ủy quyền). Không tiết lộ bất kỳ secret nào (ghi ký hiệu `SECRET_DETECTED`).

---

## 1. Tổng quan hệ thống

- **Loại ứng dụng:** Web Dashboard đơn khối (monolith) kết hợp Frontend tĩnh + Backend REST API + máy học (YOLO26m/STAL).
- **Backend:** Python FastAPI + Uvicorn, chạy trực tiếp (không reverse proxy, không HTTPS trong cấu hình hiện tại).
- **Frontend:** HTML/CSS/JS tĩnh (vanilla), được phục vụ trực tiếp bởi cùng backend (No build step).
- **Database:** SQLite (`database/attendance.db`) qua SQLAlchemy ORM.
- **AI/Hardware:** OpenCV, Ultralytics YOLO, giao thức RTSP (Hikvision/Dahua), điều khiển đèn Relay qua HTTP/ONVIF/CGI, gửi báo cáo qua Zalo Bot Gateway & SMTP.
- **Môi trường triển khai:** Windows (máy chủ của trường), entry point `app.py` / `backend/main.py`, bind `0.0.0.0:8000`, `DEBUG=True`.

## 2. Data Flow tổng quan

```
[Admin/Staff - Browser]
        │  (HTTP, cookie HTTP-only 'access_token' + [Bearer token fallback])
        ▼
[FastAPI Backend 0.0.0.0:8000]
   ├── /api/auth/*        → bcrypt verify → JWT HS256 (PyJWT) → set cookie
   ├── /api/*.            → get_current_user (JWT decode → DB User) → require_admin (role check)
   ├── /storage, /dataset → StaticFiles KHÔNG xác thực + header CORS Access-Control-Allow-Origin: *
   ├── /docs, /redoc      → OpenAPI công khai
   │
   ├── APScheduler (BackgroundScheduler, múi giờ VN)
   │     ├── Quét điểm danh sáng/chiều (06:45, 12:45, thứ 2-thứ 7)
   │     └── Sao lưu CSDL hàng ngày 23:00 → storage/backups/*.zip
   │
   ├── AttendanceEngine → detector (YOLO26m + head-model) → ROI masking
   ├── RTSPClient / NVRService / RelayService
   │     └── kết nối camera NVR (RTSP Digest), Relay đèn (HTTP/ONVIF), probe kênh
   ├── NotificationService (SMTP) / ZaloService (Bot Gateway / OA / Webhook)
   └── SQLite attendance.db
        ├── User (password_hash bcrypt, role admin/staff)
        ├── PasswordResetToken (sha256(token))
        ├── Classroom (rtsp_url kèm credential nhúng, relay_ip)
        ├── NVRDevice (username, password PLAINTEXT)
        ├── ROIPolygon, AttendanceSession, AttendanceDetail
```

## 3. Biên giới tin cậy (Trust Boundaries)

| Biên giới | Mô tả | Ghi chú bảo mật |
|---|---|---|
| Browser ↔ Backend | Không TLS (HTTP), cookie `secure=False` | Nhiễu mạng LAN/HTT cũng đọc session |
| Staff/Admin role | Phân vai nhưng nhiều endpoint nhạy cảm chỉ yêu cầu **đã đăng nhập** | Thiếu phân quyền thực thi ở nhiều chỗ |
| Backend ↔ Camera/NVR/Relay (LAN 192.168.x.x) | RTSP, Digest HTTP, probe TCP | Nguồn người dùng cấp → nguy cơ SSRF |
| Backend ↔ External (Zalo Gateway `sms-service.talab.io.vn`, SMTP) | API key do runtime cấu hình | secret lưu plaintext trong `storage/zalo_runtime_config.json` (bị lộ công khai) |
| Static mount `/storage` `/dataset` | Không qua auth | **Toàn bộ dữ liệu ảnh/báo cáo/backup/log công khai** |

## 4. Attack Surface chính

1. **Endpoints chưa xác thực (public):**
   - `GET /login, /forgot-password, /reset-password, /users, /cameras, /roi-config, /reports, /notifications, /` (trang tĩnh)
   - `POST /api/auth/login`, `POST /api/auth/forgot-password`, `POST /api/auth/reset-password`
   - `GET /api/system/health`, `GET /api/system/ai/info`
   - `GET /docs`, `/redoc`, `/openapi.json`
   - **`GET /storage/**` và `GET /dataset/**`** — mất. <= XEM FIN-001
2. **Endpoints có xác thực (bất kỳ user):** toàn bộ `/cameras`, `/attendance`, `/reports`, `/roi`, `/system`, `/backup` (một phần).
3. **Endpoints chỉ admin:** `/auth/users*`, `/backup/*` (create/download/upload-restore), `/system/database/info` (xem FIN-013, nằm nhầm quyền).

## 5. Bề mặt quản lý secret

| Secret | Nơi lưu | Bị lộ? |
|---|---|---|
| `DVR_PASSWORD` | Hardcode `config/settings.py:39` | ✅ Có — trong source (SECRET_DETECTED) |
| `JWT_SECRET` | `.env` (64 ký tự, đã set) + fallback cứng trong source | Fallback yếu nếu `.env` thiếu |
| `ADMIN_PASSWORD` | `.env` + default mặc định trong source `.env.example` | Khả năng cao vẫn là default |
| `NVRDevice.password` | DB plaintext `models.py` | ✅ Có (nội bộ DB/API) |
| RTSP URL credential | `Classroom.rtsp_url` nhúng `user:pass@` | ✅ Có — trả về qua `/api/cameras` |
| `ZALO_BOT_API_KEY`, OA access token | `storage/zalo_runtime_config.json` | ✅ **Có — công khai qua `/storage/`** |
| `SMTP_USER/PASSWORD`, Zalo keys | `.env` (một số trống) | Quản lý bằng dotenv (đúng) |

## 6. Models/Data được xác thực (perimeter cần bảo vệ)

- RTSP URL nhúng credential; `source_url` người dùng → cv2/requests (SSRF + đọc file cục bộ).
- `relay_ip`, `ip_address` → relay_service phát request HTTP đến host tùy ý.
- `webhook_url`, `bot_api_base_url`, `access_token`, `phone` → gửi nội dung/tin nhắn/HTTP ra mạng tùy ý.
- File zip khôi phục backup → `zipfile.extractall` (nguy cơ zip-slip).
- `class_name`, `room_number`, `notes`, `message`, `template` chuỗi kiểu HTML → DOM/stored XSS khi render frontend.

## 7. Chuỗi bảo vệ hiện tại & lỗ hổng nổi bật

1. Mật khẩu: bcrypt (tốt) ✅ | JWT: HS256, không blacklist/refresh/jti (kém) ⚠️
2. Cookie: HTTP-only + SameSite=Lax (tốt một phần) ❌ `Secure` chưa bật, còn Bearer fallback.
3. ROLE check: chỉ dùng ở `/auth/users` + `/backup` và `/system` một phần ❌ — phần lớn endpoint điều hành/cam nằm dưới `get_current_user`.
4. Static mount: **không xác thực + CORS `*`** ❌ — lộ Zalo API key, backup CSDL, ảnh học sinh.
5. SSRF: `test-connection` (đọc cả file cục bộ), `nvr/probe`, `send-zalo` (webhook tùy ý) ⚠️
6. XSS: khá nhiều điểm `innerHTML` không escape, dữ liệu từ DB (`class_name/notes`) được render trực tiếp ⚠️

Chi tiết từng lỗ hổng, mức độ ảnh hưởng và phương án khắc phục: xem **SECURITY_AUDIT_REPORT.md** và **SECURITY_HARDENING_CHECKLIST.md**.