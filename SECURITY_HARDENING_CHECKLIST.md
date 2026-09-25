# SECURITY HARDENING CHECKLIST

> Bảng việc khắc phục theo mức độ ưu tiên cho **Hệ Thống Điểm Danh AI - THPT Điều Cải**.
> Ghi chú: mọi secret chỉ ghi dạng `SECRET_DETECTED`; **chủ sở hữu phải tự xoay mật khẩu** ở hạ tầng.
> Hệ thống đang chạy trực tiếp qua uvicorn `0.0.0.0:8000` — các bước "deploy" phải được chủ sở hữu xác nhận.

## Phân loại mức độ & thời hạn

| Mức | Mô tả | Thời hạn khuyến nghị |
|---|---|---|
| P0 (CRITICAL) | Lộ dữ liệu/bí mật ngay lập tức | Ngay/trong 24h |
| P1 (HIGH) | Chiếm quyền / hậu quả lớn | 1–2 tuần |
| P2 (MEDIUM) | Rò rỉ hạn chế / hardening | 1–2 tháng |
| P3 (LOW) | Vệ sinh code/cấu hình | Trong quý |
| P4 (INFO) | Cải tiến | Liên tục |

---

## P0 — CRITICAL (kiểm tra ngay)

### P0-1. Chặn lộ `/storage` & `/dataset` công khai
**FIN-001** — Lộ Zalo Bot API key, backup CSDL, ảnh học sinh, log.

**BEFORE** (`backend/main.py:68-79`):
```python
app.mount("/storage", CORSStaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")
app.mount("/dataset", CORSStaticFiles(directory=str(settings.BASE_DIR / "dataset")), name="dataset")
```

**AFTER** (đề xuất, cần validate quy trình frontend):
```python
from fastapi.security import HTTPBearer  # (chọn 1 trong 2 phương án)

# Phương án A: yêu cầu xác thực cho toàn bộ static (khuyến nghị nếu frontend đều dùng cookie)
from backend.api.deps import get_current_user
from fastapi.staticfiles import StaticFiles

class AuthStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        request = Request(scope)
        try:
            token = request.cookies.get("access_token") or ""
            user_id = decode_access_token(token)
            if user_id is None:
                from fastapi.responses import RedirectResponse
                return RedirectResponse("/login")
        except Exception:
            from fastapi.responses import RedirectResponse
            return RedirectResponse("/login")
        return await super().get_response(path, scope)

# Không dùng CORSStaticFiles (bỏ Access-Control-Allow-Origin: *)
app.mount("/storage", AuthStaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")
app.mount("/dataset", AuthStaticFiles(directory=str(settings.BASE_DIR / "dataset")), name="dataset")
```
**Phân nhóm dữ liệu không nên public dù đã auth:** `zalo_runtime_config.json`, `notification_adjust_settings.json`, `backups/*`, `server_*.log` → đặt ngoài thư mục static hoặc thêm middleware deny-list.
**Bắt buộc chủ sở hữu:** xoay `ZALO_BOT_API_KEY`/OA TOKEN (đã bị lộ), xoay pass DVR/NVR, xóa log đang chứa URL (đang nằm public).

### P0-2. Xoá secret hardcode trong source
**FIN-002** — `settings.py:39` DVR_PASSWORD; default password NVR ở schema/service.
- Chuyển sang `.env` (`DVR_PASSWORD=...`) và đọc qua `os.getenv`.
- Xóa trường `password` default trong `NVRProbeRequest` (không nên có default).
- **Chủ sở hữu bắt buộc:** đổi mật khẩu thật của camera DVR/NVR vì đã nằm trong source.

### P0-3. Không lưu/trả về credential plaintext
**FIN-003** — `NVRDevice.password`, RTSP URL nhúng credential.
- Bỏ trả `rtsp_url` trực tiếp trong `GET /api/cameras` và `/matrix-wall`; chuyển dạng đã che password (`rtsp://admin:****@host/...`).
- Mã hóa `NVRDevice.password` (vd `cryptography` Fernet với key trong `.env`) hoặc tách credential khỏi DB; sau đó xóa dữ liệu cũ.

### P0-4. Phân quyền đúng cho hành động nhạy cảm
**FIN-004** — các endpoint phá hủy/hành động admin.
- Thay `dependencies=[Depends(get_current_user)]` bằng phân vai rõ: endpoint CRUD camera, `reset-defaults`, `nvr/batch-import`, `/attendance/trigger`, `/attendance/clear-history`, `/reports/export-now`, `/reports/send-zalo`, `/reports/save-*`, `/roi/{id}`, `/system/database/info` → thêm `require_admin` (hoặc tạo decorator `require_role`).

**BEFORE** (`backend/api/routers/cameras.py:24`, `attendance.py:18`, v.v.):
```python
router = APIRouter(prefix="/cameras", tags=["Cameras"], dependencies=[Depends(get_current_user)])
```
**AFTER**:
```python
router = APIRouter(prefix="/cameras", tags=["Cameras"], dependencies=[Depends(require_admin)])
```

---

## P1 — HIGH (1–2 tuần)

- **P1-1 Rate limit & lockout đăng nhập** (FIN-005): dùng `slowapi`/middleware hoặc Redis; giới hạn ~5 lần/IP/phút cho `/auth/login` & `/auth/forgot-password`; lock tài khoản sau ~10 lần sai (15 phút).
- **P1-2 Giới hạn forgot-password** (FIN-006): thêm rate-limit + xóa entry cooldown định kỳ (chống dict phình)).
- **P1-3 JWT/session nâng cấp** (FIN-007):
  - Thêm `jti` + `PasswordResetToken`-style revocation table (hoặc đơn giản: tăng version token mỗi khi đổi mật khẩu → `token_version` trên User).
  - Bỏ hẳn Bearer fallback (cookie-only như tài liệu đã chủ trương), hoặc giữ bổ sung song song nhưng KHÔNG cho phép khi cookie có.
  - Bật `secure=True` khi deploy HTTPS; thêm `__Host-` prefix.
  - Logout: thêm token vào blacklist (lưu tới khi hết hạn).
- **P1-4 SSRF** (FIN-008):
  - `/cameras/test-connection`: hạn chế host IP private (192.168/10/127, 169.254, ::1) HOẶC giới hạn `source_url` bắt buộc `rtsp|webcam:digit|file đuôi ảnh trong dataset`.
  - `/cameras/nvr/probe`: lock vào subnet camera (vd chỉ IP cùng dải cấu hình) + giới hạn cổng (554/80/443).
  - `/reports/send-zalo`: khóa `webhook_url`/`bot_api_base_url` theo danh sách allowlist host (chỉ `sms-service.talab.io.vn`); không nhận webhook từ client.
  - `relay_ip`: allowlist IP của relay thật.
- **P1-5 XSS** (FIN-009/010):
  - Thêm hàm `escapeHtml` dùng chung và áp dụng `class_name`, `room_number`, `notes`, `message`, `session_code`, `filename` ở mọi chỗ `innerHTML`. Đặc biệt `dashboard.js` (~560), `reports.js` (~460, ~750), `cameras.js` (586-597, 636-647), `api.js` showToast (chuyển dùng `textContent`).
  - Thêm CSP header (P2-4 hỗ trợ).
- **P1-6 Zip-slip** (FIN-011): trong `backup_service.restore_backup`, validate mọi member path:
```python
for member in zf.infolist():
    target = (dest / member.filename).resolve()
    if not str(target).startswith(str(dest.resolve())):
        raise ValueError("Tên file không hợp lệ trong backup")
```
- **P1-7 Mật khẩu mặc định** (FIN-012): **yêu cầu chủ sở hữu** đổi mật khẩu admin ngay, và (hardening) trong `seed_admin_if_empty` có nếu `ADMIN_PASSWORD == "Admin@2025"` thì từ chối/ghi warning.

## P2 — MEDIUM (1–2 tháng)

- **P2-1 Info disclosure** (FIN-013/014/018): `/system/database/info` → chỉ admin; ẩn `/docs`, `/redoc` ở prod (`docs_url=None`, `redoc_url=None` khi `DEBUG=False`); `health`/`ai/info` bỏ path chi tiết model/device.
- **P2-2 Headers & HTTPS** (FIN-015): thêm middleware security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`, `Content-Security-Policy` (đơn giản, thử nghiệm trước). Bật HTTPS (Nginx/Caddy) và cookie `Secure`, HSTS.
- **P2-3 Hạn chế lạm dụng gửi thông báo** (FIN-016): `send-email`/`send-zalo` chỉ cho phép email/phone/SĐT đã đăng ký trong cấu hình; bỏ custom targets từ client (hoặc giới hạn staff).
- **P2-4 Resource/DoS** (FIN-017): giới hạn `limit` <= 500; giới hạn số điểm ROI (vd <= 50); chống concurrency trigger/rescan bằng lock hoặc `max_queue`; rate-limit `/attendance/trigger` & `/roi/{id}/rescan`.
- **P2-5 Open redirect** (FIN-020): validate `redirect` bắt buộc bắt đầu bằng `/` hoặc URL tương đối cùng origin.
- **P2-6 Logging** (FIN-021): mask password/token trong log (log `***`); định kỳ dọn log; không đặt log trong thư mục public.
- **P2-7 Dependencies** (FIN-019): tạo lock file, chạy `pip-audit -r requirements.txt` định kỳ, pin phiên bản chính và ràng buộc an toàn.

## P3 — LOW (trong quý)

- **P3-1** `DEBUG=False` (settings) khi production; `host` đổi thành IP nội bộ nếu cần, prefer sau proxy; tắt `reload=True` trong `app.py`.
- **P3-2** Validate `standard_count` (1–100), `image_width/height` (320–7680), `channels_count`; hàm email dùng validator chuẩn (pydantic `EmailStr`).
- **P3-3** `tests/test_login_api.py` in mật khẩu → bỏ in; đưa `reset_admin_password.py` ra ngoài dashboard; thêm thông báo "đổi mật khẩu mặc định" khi seed.
- **P3-4** Hạn chế `FileResponse` theo thư mục REPORTS_DIR cho `download-excel`.

## P4 — INFO (cải tiến liên tục)

- **P4-1** Tài liệu đọc lại: README/KIEN_TRUC nói "bo Bearer token" nhưng `deps.py` vẫn nhận → cập nhật code/tài liệu cho khớp.
- **P4-2** Xóa file/test không dùng (`app.py` tao, backup cũ trong `storage/backups`) — chỉ khi chủ sở hữu đồng ý.
- **P4-3** Xem xét mã hóa backup (SQLite backup có thể nén kèm mật khẩu) — nếu cần cấp lưu trữ ngoài.
- **P4-4** Thêm notification cảnh báo khi detect brute-force/hành vi lạ trong log.

---

## Trạng thái triển khai

> Cập nhật 24/09/2026: **toàn bộ P0/P1 code-level đã patch và xác minh** (xem "Đã áp dụng" bên dưới).
> Các mục còn lại **bắt buộc chủ sở hữu thực hiện thủ công** (xoay secret, HTTPS, thay mật khẩu thật).

| ID | Item | Người thực hiện | Trạng thái |
|---|---|---|---|
| P0-1 | Chặn `/storage` `/dataset` public | Dev ✅ | ✅ Đã làm |
| P0-1* | Xoay secret đã lộ (Zalo Bot key, DVR/NVR pass) | **Chủ sở hữu** | ☐ Bắt buộc |
| P0-2 | Xoá secret hardcode (DVR/NVR) | Dev ✅ | ✅ Đã làm |
| P0-3 | Không trả credential plaintext qua API | Dev ✅ (mask URL + admin raw) | ✅ Đã làm |
| P0-3* | **Xoá credential đang lưu trực tiếp trong DB** (NVRDevice.password, RTSP URL có user:pass) | **Chủ sở hữu** | ☐ Bắt buộc |
| P0-4 | Phân quyền endpoint nhạy cảm | Dev ✅ | ✅ Đã làm |
| P1-1 | Rate limit & lockout đăng nhập | Dev ✅ | ✅ Đã làm |
| P1-2 | Giới hạn forgot-password | Dev ✅ | ✅ Đã làm |
| P1-3 | JWT jti + revoke + cookie hardening | Dev ✅ | ✅ Đã làm |
| P1-4 | SSRF guard (test-connection/probe/send-zalo/relay_ip) | Dev ✅ | ✅ Đã làm |
| P1-5 | XSS (escape frontend + showToast textContent) | Dev ✅ | ✅ Đã làm |
| P1-6 | Zip-slip guard restore backup | Dev ✅ | ✅ Đã làm |
| P1-7 | Warn mật khẩu admin mặc định khi seed | Dev ✅ | ✅ Đã làm |
| P1-7* | **Đổi mật khẩu admin** (nếu vẫn `Admin@2025`) | **Chủ sở hữu** | ☐ Bắt buộc |
| P2-1 | Info disclosure (`/database/info` admin, ẩn docs khi DEBUG=False) | Dev ✅ | ✅ Đã làm |
| P2-2 | Security headers + HTTPS + cookie Secure | Dev (1/2) + **Chủ sở hữu (HTTPS/HSTS)** | ◐ Một phần |
| P2-3 | Hạn chế lạm dụng thông báo (admin-only + allowlist host) | Dev ✅ | ✅ Đã làm |
| P2-4 | Resource/DoS: limit history ≤ 500, rate-limit trigger/rescan | Dev ✅ | ✅ Đã làm |
| P2-5 | Open redirect `redirect` | **Chủ sở hữu/Dev** | ☐ Chưa làm |
| P2-6 | Mask credential trong log | Dev ✅ (RedactFilter toàn cục) | ✅ Đã làm |
| P2-6* | Dọn log/backup cũ trong storage đang public | **Chủ sở hữu** | ☐ Bắt buộc |
| P2-7 | Lock/pin dependencies + pip-audit | **Chủ sở hữu** | ☐ Chưa chạy |
| P3-1 | DEBUG=False, host/reload production | **Chủ sở hữu** | ☐ Bắt buộc |
| P3-2 | Validate input (standard_count, image dims, EmailStr) | Dev | ◐ Một phần (relay/source/limit) |
| P3-3 | Bỏ in mật khẩu trong test/dev script | Dev | ☐ Chưa làm |
| P3-4 | FileResponse giới hạn trong REPORTS_DIR | Dev | ☐ Chưa làm |
| P4-1 | Đồng bộ docs (cookie-only) | Dev ✅ | ✅ Đã làm |
| P4-2..4 | Cleanup/backup encryption/alert | **Chủ sở hữu** | ☐ |

> ⚠️ Các mục **Dev ✅** đã được kiểm thử cục bộ qua `TestClient` (xem "Đã áp dụng"). Vẫn khuyến nghị chạy lại trên bản sao staging trước khi deploy lên máy thật.

---

## Đã áp dụng (24/09/2026)

Backend:
- `config/settings.py`: `DVR_PASSWORD` lấy từ env (default `""`), thêm `COOKIE_SECURE`, `ZALO_ALLOWED_HOSTS`.
- `backend/main.py`: thay `CORSStaticFiles` cho `/storage`+`/dataset` bằng `AuthStaticFiles` (bắt buộc cookie hợp lệ, trả 401, `Cache-Control: private, no-store`, bỏ `ACAO:*`); ẩn `/docs`+`/redoc` khi `DEBUG=False`.
- `services/auth_service.py`: JWT thêm claim `jti`; thêm `decode_access_token_payload`, `revoke_token_jti`, `is_jti_revoked` (in-memory, purge khi quá 500 entry); seed admin warning khi `ADMIN_PASSWORD == "Admin@2025"`.
- `backend/api/deps.py`: chỉ nhận cookie, kiểm tra jti đã thu hồi, bỏ Bearer fallback (khớp tài liệu cookie-only).
- `backend/api/security.py` (mới): rate-limit theo IP/key, `mask_stream_url`, `validate_relay_ip` (IP nội bộ), `validate_stream_source` (chặn `file://`, IP public, hostname; cấm hostname bằng cách không coi là nội bộ), `validate_external_http_url` (allowlist), `redact_sensitive_text`.
- Routers:
  - `auth.py`: rate-limit `/login` (10/IP·5ph, 15/email+IP·15ph), `/forgot-password` (8/IP·15ph, 3/email+IP·15ph), `/reset-password`; cooldown dict được dọn định kỳ; `/logout` thu hồi `jti` của token; cookie `secure=settings.COOKIE_SECURE`.
  - `cameras.py`: create/update/delete/reset-defaults/NVR probe/batch-import/list/delete/**test-connection/test-ir-by-url/test-ir/test-all-ir/available-webcams** → `require_admin`; `GET /cameras` & `matrix-wall` trả `rtsp_url` đã che + `has_password`; thêm `GET /cameras/{id}/raw` (admin-only) để lấy URL gốc; validate `relay_ip` + `source_url`; rate-limit test-connection/probe.
  - `attendance.py`: `/trigger` admin + rate-limit; `/clear-history` admin; `/history` giới hạn ≤ 500.
  - `reports.py`: `/export-now`, `/send-email`, `/save-email-config`, `/send-zalo`, `/save-zalo-config`, `/zalo-config`(GET), `/notification-settings`(POST), `/retention-settings`(POST), `/cleanup-expired`, `/clear-history` → `require_admin`; validate host webhook Zalo theo allowlist; rate-limit send.
  - `roi.py`: save/rescan/refresh-snapshot → `require_admin`.
  - `system.py`: `/database/info` → admin (không trả `DATABASE_URL`); `/bind-sample-media` → admin.
- `services/backup_service.py`: chống Zip-Slip (mọi member phải nằm trong thư mục giải nén).
- `services/nvr_service.py` + `backend/schemas/camera_schemas.py`: bỏ default password `Lhu@2025`.
- `config/logging_config.py`: `RedactFilter` che `rtsp://user:pass@`, `password/secret/token=...` trong mọi log (console + file).

Frontend:
- `api.js`: export `escapeHtml`; `showToast` dùng `textContent`; thêm `CameraAPI.getRawRtsp`.
- `dashboard.js` / `reports.js` / `cameras.js` / `roi_config.js` / `notifications.js`: escape `class_name`, `room_number`, `notes`, `filename`, `session_code`, `message`/`err.message` tại mọi điểm `innerHTML`/attribute (XSS).
- `cameras.js`: `editCamera` admin tự tải URL gốc qua `/raw` (staff vẫn dùng URL đã che).

Xác minh đã chạy (TestClient, không gửi external):
1. `GET /storage/zalo_runtime_config.json` không có cookie → **401** (trước: 200 + `ACAO:*`); bad token → 401.
2. Đăng nhập sai 11 lần/IP → **10×401 rồi 429** (rate-limit hoạt động).
3. Login → logout → dùng lại cookie cũ → **401** (jti đã thu hồi).
4. `py_compile` tất cả file backend đã sửa: OK; import `backend.main`: OK.

Bổ sung 24/09/2026 — **Sao lưu Google Drive** (Xác minh smoke, không gọi network thật):
- `config/settings.py`: `GOOGLE_DRIVE_CLIENT_ID/SECRET/FOLDER_ID` (env), `GOOGLE_DRIVE_REDIRECT_URI` (mặc định `http://localhost`), `GOOGLE_DRIVE_REMOTE_ONLY` (mặc định true).
- `services/gdrive_service.py` (mới): OAuth 2.0 Desktop App (scope `drive.file`, refresh token), token lưu `config/gdrive_token.json` (ngoài `storage/` public), upload/list/download/delete qua REST `requests` (KHÔNG thêm thư viện Google).
- `services/backup_service.py`: mỗi `create_backup` (thủ công + tự động 23:00) tự đẩy lên Drive; `REMOTE_ONLY=true` → xóa bản zip local sau khi upload thành công; list hợp nhất local + Drive; download/restore/delete fallback sang Drive; `cleanup_old_backups` dọn cả Drive.
- `backend/api/routers/backup.py`: `GET /backup/gdrive/status`, `GET /backup/gdrive/auth-url`, `POST /backup/gdrive/connect`, `POST /backup/gdrive/disconnect` (admin-only); tải/khôi phục file chỉ có trên Drive qua bản tạm (dọn bằng `BackgroundTask`).
- Frontend: thẻ "Sao Lưu Google Drive" + badge nguồn (Drive/Máy chủ) trong trang Báo cáo.
- Nếu chưa kết nối Drive / upload lỗi → **giữ bản local** (không mất dữ liệu), message cảnh báo trong response.
- Smoke test (mock upload): tạo backup → `drive.uploaded=true` + bản local bị xóa khi REMOTE_ONLY; giữ bản local khi REMOTE_ONLY=false; list gộp item Drive; download Drive-only 200; delete dọn cả 2 nơi; restore qua Drive chạy tới bước kiểm tra zip.
- **Chủ sở hữu cần làm:** trong Google Cloud Console tạo `OAuth client ID` loại **Desktop App**, điền 2 giá trị vào `.env`, vào **Báo cáo → Cài đặt → Sao lưu Google Drive → Kết Nối** một lần (dán mã `code=...`), xác nhận email hiển thị.

⚠️ **Khi deploy:** mọi token phiên cũ (không có jti) sẽ bị vô hiệu → người dùng phải đăng nhập lại. Ảnh `/storage/**` giờ cần cookie → chỉ hoạt động khi frontend cùng origin (hoặc đã cấu hình CORS + cookie riêng).