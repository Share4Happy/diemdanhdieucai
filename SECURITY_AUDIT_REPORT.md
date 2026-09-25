# SECURITY AUDIT REPORT

## Hệ Thống Điểm Danh Tự Động AI - THPT Điều Cải

| | |
|---|---|
| **Đối tượng audit** | Toàn bộ mã nguồn + cấu hình triển khai `D:\Projects\diemdanhdieucai` |
| **Ngày thực hiện** | 2026-09-24 |
| **Phạm vi** | Backend FastAPI, Frontend tĩnh, SQLite, AI pipeline, tích hợp NVR/Relay/Zalo/SMTP |
| **Ủy quyền** | Có (chủ sở hữu hệ thống) |
| **Hạn chế** | Không tấn công production, không xóa dữ liệu, không gửi dữ liệu ra external, không in secret. Các kiểm tra động chỉ dùng instance thử nghiệm cục bộ chế độ read-only trên port riêng (8099) |

---

## 1. Executive Summary

Hệ thống có kiến trúc phân lớp rõ ràng, mật khẩu người dùng được hash bcrypt, kiểm soát phân quyền cơ bản (admin/staff), cookie HTTP-only + SameSite, token reset dùng SHA-256, và `.env` được gitignore đúng cách. Tuy nhiên **tồn tại một lỗ hổng CRITICAL bị phát hiện và xác minh động**: toàn bộ thư mục `storage/` (và `dataset/`) được phục vụ **công khai, không xác thực, kèm CORS `*`**, dẫn đến lộ:
- Khóa Zalo Bot (`ZALO_BOT_API_KEY`) — xác minh: `GET /storage/zalo_runtime_config.json → HTTP 200`, file chứa `ZALO_BOT_API_KEY`.
- Bản sao lưu CSDL (`GET /storage/backups/backup_THPTDieuCai_20260923_140721.zip → HTTP 200`) chứa toàn bộ hash mật khẩu người dùng.
- Ảnh gương mặt học sinh (`/storage/captures/**`, `/storage/annotated/**`), báo cáo Excel, và log server (64 KB) có thể chứa RTSP URL kèm credential.

Cùng với đó là **thất bại phân quyền trên diện rộng** (nhiều hành động phá hủy/admin chỉ cần "đã đăng nhập"), **secret hardcode trong source**, **lưu plaintext mật khẩu NVR/RTSP**, **không rate limit đăng nhập**, và **SSRF/XSS** trên một số endpoint. Tổng cộng: **4 CRITICAL, 8 HIGH, 11 MEDIUM, 4 LOW, 3 INFO**.

| Mức độ | Số lượng | Uớc tính ưu tiên xử lý |
|---|---|---|
| CRITICAL | 4 | Ngay lập tức (P0) |
| HIGH | 8 | Trong 1–2 tuần (P1) |
| MEDIUM | 11 | Trong 1–2 tháng (P2) |
| LOW | 4 | Trong quý (P3) |
| INFO | 3 | Cải tiến liên tục (P4) |

> ⚠️ **Hành động khẩn cấp đề nghị (chỉ là đề xuất, xin chủ sở hữu xác nhận trước khi thực hiện):**
> 1. Gỡ/quản lý lại mount công khai `/storage` + `/dataset` (yêu cầu xác thực hoặc chặn các nhóm file nhạy cảm).
> 2. Xoay toàn bộ secret bị nghi lộ (Pass camera DVR/NVR, `ZALO_BOT_API_KEY`, xem `SECRET_DETECTED`).
> 3. Đổi mật khẩu tài khoản admin khỏi giá trị mặc định.
> 4. Bật rate-limit cho `/auth/login` và `/auth/forgot-password`.

## 2. Phương pháp luận

- Audit mã nguồn thủ công (Python backend, JS frontend, schema, settings).
- Phân tích tĩnh chữ ký bảo mật: grep `innerHTML`, `eval`, `subprocess`, `shell=True`, `password`, `secret`, `token`, `extractall`, `FileResponse`, `requests.`, `cv2`, `os.system`.
- Xác minh động an toàn: dựng **instance thử nghiệm cục bộ** (port 8099, chỉ mount static giống production, KHÔNG khởi động scheduler/model/notifier) để xác nhận hành vi `/storage`.
- Không thực hiện: tấn công brute-force dữ liệu, quét mạng, khai thác thật, thay đổi production.

## 3. Kiến trúc bảo mật tóm tắt

Tham khảo chi tiết: **`SECURITY_ARCHITECTURE.md`**.

- User Flow: Browser → cookie/Bearer → Auth → JWT → DB User (role).
- Static: `/storage`, `/dataset` tự do (KHÔNG qua auth) — điểm chết.
- Ngoại vi: RTSP/NVR/Relay (LAN) + Zalo Gateway + SMTP (Internet).

## 4. Tài sản & exposure

| Tài sản | Vị trí | Bị lộ hiện tại |
|---|---|---|
| Hash mật khẩu người dùng (bcrypt) | `database/attendance.db`, bản sao lưu | Backup public qua `/storage/backups/*.zip` |
| Khóa Zalo Bot / OA access token | `storage/zalo_runtime_config.json` | **Public qua `/storage/zalo_runtime_config.json`** |
| Ảnh học sinh (raw + annotated) | `storage/captures`, `storage/annotated` | Public |
| Báo cáo sĩ số Excel | `storage/reports` | Public |
| Log server | `storage/server_*.log` | Public |
| Credential NVR (username/password) | DB `NVRDevice.password` plaintext | Nội bộ DB; RTSP URL kèm pass trả về qua API |
| Credential DVR (camera trường) | Hardcode `config/settings.py` | Trong source (SECRET_DETECTED) |
| Cấu hình Zalo/SMTP/email Hiệu trưởng | `.env`, `storage/notification_adjust_settings.json` | Một phần public |

## 5. Bảng tổng hợp findings

| ID | Mức độ | Hạng mục | Vị trí | Trạng thái |
|---|---|---|---|---|
| FIN-001 | **CRITICAL** | Static/Privilege | `backend/main.py:68-79`, mount `/storage`, `/dataset` (không auth, CORS `*`) | ✅ **Xác minh động (read-only, port 8099)** |
| FIN-002 | **CRITICAL** | Secrets | `config/settings.py:39` (DVR_PASSWORD hardcode), `backend/schemas/camera_schemas.py` (default `password`), `services/nvr_service.py` | ✅ Confirmed (source) |
| FIN-003 | **CRITICAL** | Secrets tại-rest | `database/models.py` (NVRDevice.password plaintext), `Classroom.rtsp_url` nhúng credential, trả về qua `GET /api/cameras` & `/matrix-wall` | ✅ Confirmed |
| FIN-004 | **CRITICAL** | Authorization | Routers `/cameras`, `/attendance`, `/reports`, `/roi` chỉ dùng `get_current_user`; hành động phá hủy (delete/reset-defaults/clear-history/batch-import replace) | ✅ Confirmed |
| FIN-005 | HIGH | Authentication/DoS | `POST /api/auth/login` không rate-limit; không lockout; password policy yếu | ✅ Confirmed |
| FIN-006 | HIGH | Authentication/Abuse | `/api/auth/forgot-password` cooldown in-memory (`_forgot_last_sent`), không giới hạn kích thước dict | ✅ Confirmed |
| FIN-007 | HIGH | Session/JWT | Cookie `secure=False`, không revocation/blacklist/jti; Bearer fallback vẫn tồn tại (`backend/api/deps.py:12-13`); logout không vô hiệu token | ✅ Confirmed |
| FIN-008 | HIGH | SSRF | `POST /api/cameras/test-connection` (đọc file cục bộ qua cv2), `POST /api/cameras/nvr/probe` (TCP scan tùy ý), `POST /api/reports/send-zalo` (webhook/base URL tùy ý), `relay_ip` tùy ý | ✅ Confirmed |
| FIN-009 | HIGH | Stored XSS | `frontend/js/dashboard.js` (~line 560 render class_name/room_number; ~574 notes), `frontend/js/reports.js` history rows; sau `/api/cameras` có thể ghi tên lớp | ✅ Confirmed |
| FIN-010 | HIGH | Reflected/DOM XSS | `frontend/js/cameras.js:586-597,636-647` (message chứa `source_url`), `frontend/js/api.js:237` showToast, `frontend/js/reports.js` error paths, `roi_canvas.js` mode | ✅ Confirmed |
| FIN-011 | HIGH | Zip-slip | `services/backup_service.py` restore_backup → `zipfile.extractall` / `upload-restore` | ✅ Confirmed (admin-only) |
| FIN-012 | HIGH | Default creds | `.env.example`/`settings.py` ADMIN_PASSWORD default; khả năng cao production giữ default (độ dài trùng khớp `Admin@2025` = 10 ký tự) | 🔍 Potential |
| FIN-013 | MEDIUM | Info disclosure | `GET /api/system/database/info` trả `DATABASE_URL`; `excel_report_path`, `rel_ip` chuỗi path đầy đủ ở `/attendance/latest`, `today-sessions` | ✅ Confirmed |
| FIN-014 | MEDIUM | Info disclosure | `/docs`, `/redoc`, `/openapi.json` public (FastAPI default) | ✅ Confirmed |
| FIN-015 | MEDIUM | Headers/clickjacking | Không CSP, X-Frame-Options, HSTS, nosniff; không HTTPS; cookie `secure=False` | ✅ Confirmed |
| FIN-016 | MEDIUM | Message abuse | `POST /api/reports/send-email` gửi tới email tùy ý; `send-zalo` cho phép target tùy ý (phone/webhook) → spam/phishing danh nghĩa nhà trường | ✅ Confirmed |
| FIN-017 | MEDIUM | DoS/Resource | `/attendance/history` limit không chặn trên; ROI polygon không giới hạn số điểm/kích thước; trigger-scant liên tục gánh nặng AI | ✅ Confirmed |
| FIN-018 | MEDIUM | Info disclosure | `GET /api/system/health`, `/ai/info` public (lộ đường dẫn model, GPU, cấu hình) | ✅ Confirmed |
| FIN-019 | MEDIUM | Dependencies | `requirements.txt` chỉ `>=` không chặn trên; chưa chạy `pip-audit` | ⏳ UNVERIFIED (môi trường) |
| FIN-020 | MEDIUM | Open redirect | `frontend/js/login.js` `getRedirectTarget(redirect=...)` cho phép điều hướng `https://evil.com` | ✅ Confirmed |
| FIN-021 | MEDIUM | Logging | Log INFO/DEBUG ghi RTSP URL kèm credential (`cameras.py:96,126,153`, `roi.py:89`); log nằm trong `/storage` công khai | ✅ Confirmed |
| FIN-022 | LOW | Hardening | `DEBUG=True`, `HOST=0.0.0.0`, `app.py` `reload=True`, chạy uvicorn không proxy | ✅ Confirmed |
| FIN-023 | LOW | Input validation | `standard_count`, `image_width/height`, `channels_count` không chặn giá trị bất thường; email check sơ sài | ✅ Confirmed |
| FIN-024 | LOW | Dev secrets | `tests/test_login_api.py` in mật khẩu; `reset_admin_password.py`, `create_admin_fresh.py` trong repo; README hiển thị test | 🔍 Potential |
| FIN-025 | INFO | Good practice | `.env` gitignore; `.gitignore` đủ (db/storage/log/docs) | ✅ Confirmed (giữ nguyên) |
| FIN-026 | INFO | Documentation | README/KIEN_TRUC mô tả Bearer đã gỡ nhưng `deps.py` vẫn nhận Bearer | ✅ Confirmed |
| FIN-027 | INFO | Ops | Scheduler backup 23:00 & cleanup 90 ngày cấu hình đúng; tuy nhiên backup public | ✅ Confirmed |

## 6. Xác thực (Authentication)

- bcrypt cost mặc định (`bcrypt.gensalt()`); so sánh an toàn. ✅
- Thông báo lỗi đăng nhập generic ("Email hoặc mật khẩu không đúng"): chống user enumeration. ✅
- **Không có rate-limit, không lockout, không CAPTCHA, không brute-force protection** cho `/auth/login` (FIN-005).
- Forgot-password: token thần kỳ, có cooldown 5 phút **per-process memory**, không chia sẻ giữa worker, dict không giới hạn (FIN-006); token 256-bit (tốt).
- Reset token được hash SHA-256 lưu DB, đánh dấu `used_at` (1 lần dùng). ✅
- `test_login_api.py` in admin password ra console (dev risk nhỏ; FIN-024).

## 7. Phân quyền (Authorization)

- Role admin/staff, chỉ admin mở `/auth/users*` & `/backup*` phần lớn. (tốt phần đó)
- **KHÔNG áp dụng cho**: mọi endpoint `/cameras/**` (gồm `reset-defaults`, `delete/{id}`, `nvr/batch-import` với `replace_existing`, `test-all-ir`), `/attendance/trigger`, `/attendance/clear-history`, `/reports/export-now`, `/reports/send-zalo`, `/reports/save-*`, `/roi/{id}` save/rescan, `/system/database/info`. → FIN-004.
- Hậu quả: một tài khoản staff (hoặc account bị chiếm) có thể xóa toàn bộ cấu hình camera, xóa lịch sử điểm danh, điểm danh liên tục (hao AI), gửi Zalo/email giả danh nhà trường, đọc full DB info.

## 8. Phiên & JWT

- JWT HS256 secret từ `.env` (64 ký tự — OK), fallback trong source yếu nếu thiếu `.env` (FIN-002).
- Payload chỉ `sub` + `exp`: không `jti`, không `iss/aud`, không version/blacklist → **không thể thu hồi token**, đổi mật khẩu không invalidate phiên cũ (FIN-007).
- Cookie: `HttpOnly`, `SameSite=Lax`, **`Secure` chưa bật**, không `__Host-` prefix. Kiểu `max_age` 12h.
- Vẫn nhận `Authorization: Bearer` — trung lập việc "cookie-only" đã tuyên bố; Bearer không dính SameSite/CSRF nhưng dễ bị exfil qua XSS/localStorage (`currentUser`/`currentUserRole` lưu localStorage).
- Logout chỉ xóa cookie; token còn hiệu lực nếu bị đánh cắp.

## 9. Input Validation & Injection

- SQLAlchemy ORM: tránh SQLi thủ công. ✅
- `source_url` (RTSP/file): chấp nhận bất cứ thứ gì, từ đó cv2/requests đọc → SSRF + đọc file cục bộ (FIN-008).
- `webhook_url`, `bot_api_base_url`: không validate scheme/host → SSRF + lạm dụng webhook (FIN-008/FIN-016).
- ROI: không giới hạn số điểm đa giác/kích thước chuỗi (FIN-017).
- Email: chỉ kiểm tra chứa `@` (FIN-023).
- Không có giới hạn kích thước request body (FastAPI mặc định).

## 10. Bảo mật cơ sở dữ liệu

- SQLite file `database/attendance.db`; không có quyền system hạn chế đáng kể trên Windows, không mã hóa.
- Backup schema: có (21:00/23:00) — tốt, nhưng **backup được phục vụ công khai** → phá hủy tính toàn vẹn/quyền riêng tư (FIN-001).
- `NVRDevice.password` lưu **plaintext** (FIN-003); RTSP URL kèm credential lưu plaintext trong `Classroom.rtsp_url`.

## 11. Dữ liệu cá nhân & quyền riêng tư (PII)

- Ảnh gương mặt học sinh (raw + bounding box) lưu `storage/captures|annotated` và **public not auth** (FIN-001). Cần cân nhắc: ảnh khuôn mặt = dữ liệu nhạy cảm theo quy định VN (Nghị định 13/2023/NĐ-CP về dữ liệu cá nhân).
- Báo cáo sĩ số (tên lớp, phòng, số lượng) public.
- Không thấy cơ chế xóa (right to erasure) tự động cho ảnh học sinh ngoài retention 90 ngày (có sẵn, chạy được — các khối làm đúng nhưng mounted công khai).

## 12. Upload & File

- Backup download dùng `Path(...).name` → thường sánh path traversal ✅.
- `download-excel` dùng `excel_report_path` từ DB (không kiểm tra nằm trong REPORTS_DIR) — nếu DB bị ghi thì FileResponse trả file tùy ý. LOW.
- **Restore backup: unzip dùng `extractall` với tên entry không được validate → Zip-slip** (nhưng chỉ admin) (FIN-011).

## 13. API Security & Rate limiting

- Không global rate-limit middleware; không per-IP; cache-control không set cho API.
- `/api/auth/login`, `/forgot-password` dễ brute-force → FIN-005/006.
- `/attendance/trigger` có thể bị gọi liên tục → hao CPU AI (FIN-017).
- CORS: danh sách cho phép (KHÔNG `*` cho API) nhưng `allow_methods=["*"]`/`allow_headers=["*"]`; static mount lại `*` (FIN-001/015).

## 14. XSS

- `showToast` (`api.js:237`) nhét message server → DOM XSS nếu server message chứa HTML do user kiểm soát.
- Bảng điểm danh `dashboard.js` (~560) + lịch sử `reports.js` (~460): render `class_name`, `room_number`, `notes` **không escape** → stored XSS (payload `<img onerror=...>` hoặc attr injection qua `title`). FIN-009.
- Test camera `cameras.js:586-597` viết `data.message` (chứa `source_url` user nhập) vào `innerHTML` → reflected DOM XSS; các nhánh IR test (~636-647) tương tự. FIN-010.
- `roi_canvas.js` ~line 102 và các nhánh lỗi khác trong `cameras.js`, `reports.js` dùng innerHTML với dữ liệu dịch.
- **Không có CSP** để giảm thiểu.

## 15. CSRF

- Cookie `SameSite=Lax` → chặn phần lớn POST CSRF cross-site ✅ (tốt).
- Nhưng không có CSRF token, `SameSite` không đủ khi: (a) cookie có `secure=False` trên HTTP; (b) CORS `allow_origins` cấu hình rộng; (c) một số hành động nhạy cảm được trigger qua query GET? (chưa thấy GET ghi dữ liệu — kiểm tra lại cần thận trọng, hiện chưa phát hiện GET mutate).
- Tuy nhiên mọi attack xuyên site cần token; vì token Bearer fallback có thể được gửi qua `Authorization` từ JS, attacker trên cùng origin/subdomain CORS có thể giả. Xem như hụt giảm thiểu cơ bản (FIN-007/015).

## 16. SSRF & hạ tầng mạng

- `POST /api/cameras/test-connection`: `source_url` bất kỳ → `rtsp_client` mở URL (RTSP) hoặc **file cục bộ** (cv2) → SSRF, đọc file ảnh/tệp nội bộ, ngược lại scan mạng nội bộ (FIN-008).
- `POST /api/cameras/nvr/probe`: `ip_address` + `rtsp_port` tùy ý → quét cổng TCP LAN (mặc IP 192.168.10.* nhưng không khóa).
- `POST /api/reports/send-zalo`: cho `webhook_url`, `bot_api_base_url` tùy ý → gọi GET/POST đến server tùy ý + kèm nội dung báo cáo → SSRF + exfil.
- `relay_ip` từ form → relay_service HTTP/ONVIF đến host tùy ý (kèm mặc định password) → SSRF/brute-force nghịch.

## 17. Secrets & cấu hình

- `DVR_PASSWORD` hardcode trong `settings.py` (SECRET_DETECTED) — FIN-002.
- `camera_schemas.py` NVRProbeRequest có `password` default hardcoded của camera trường (SECRET_DETECTED) — FIN-002.
- `nvr_service.probe_all_nvr_channels(..., password="...")` default (SECRET_DETECTED) — FIN-002.
- `JWT_SECRET` fallback trong source (yếu) — FIN-002 (nhưng .env prod có secret 64 ký tự).
- Zalo OA access token & Bot API key lưu plaintext `storage/zalo_runtime_config.json`, **public qua `/storage`** — FIN-001.
- `.env` đúng chuẩn (gitignore, không commit) ✅ FIN-025.
- `ADMIN_PASSWORD`: `.env.example` mang default `Admin@2025`; settings cũng có default → nguy cơ giữ default (FIN-012).

## 18. Dependencies

- `requirements.txt` dùng phạm vi chỉ `>=` (vd `fastapi>=0.110.0`, không chặn trên), không lock file, không hash.
- Không rảnh chạy `pip-audit`/`safety` (thiếu venv xác định trên máy audit) → FIN-019 đánh `UNVERIFIED`.
- Nên tạo `requirements.lock` (pip-tools / uv lock) và cài `pip-audit` vào quy trình CI/định kỳ.

## 19. Docker & Server

- **Không có Docker/Kubernetes/reverse proxy** trong repo; uvicorn chạy trực tiếp trên `0.0.0.0:8000` (run.bat/app.py).
- Không HTTPS/TLS termination; cookie `secure=False`; không HSTS.
- `DEBUG=True`; `host=0.0.0.0` mặc định → bind mọi NIC (gồm mạng LAN trường).
- Đề nghị: đưa sau Nginx/Caddy (TLS, gzip, security headers, static serve có auth), chặn `/docs` ở prod, đổi `DEBUG=False`, `SERVER_NAME`/trusted hosts.

## 20. Logging & xử lý lỗi

- File logs `storage/server_out/err/reload.log` (INFO) — nằm trong `/storage` public (FIN-021).
- `logger.info` ghi RTSP URL kèm pass (`cameras.py:96`, `roi.py:89`, `cameras.py:126/153`) → lộ credential vào log.
- Xử lý lỗi: trả về `detail=str(e)` cho exception (vd `clear_attendance_history`, `download-excel`) → leak stack/chi tiết nội bộ trong resp API (mức độ thấp).
- Chưa thấy log an toàn (mask secret), chưa cảnh báo/notification khi có tấn công.

## 21. DoS, lạm dụng & logic nghiệp vụ

- `/attendance/trigger`, `/roi/{id}/rescan`, `/reports/export-now` gọi pipeline AI nặng, không giới hạn tần suất → DoS CPU (FIN-017).
- `/attendance/history?limit=` không chặn trên → JOINS lớn.
- `/forgot-password`: gửi mail spam thoải mái nhưng nghiệp vụ "không lộ mail tồn tại" tốt ✅.
- `send-zalo` cho phép nội dung/target tùy ý → spam/phishing danh nghĩa nhà trường (FIN-016).
- `test-all-ir`, `nvr/probe` kích hoạt phần cứng/scan nhiều kênh — có thể làm ảnh hưởng vận hành camera.

## 22. Kế hoạch kiểm thử bảo mật (Security Test Plan)

> Trạng thái: vì ràng buộc "không tấn công production", các kiểm thử xâm nhập động thực tế đánh dấu `NOT RUN`; kiểm thử chứng minh lộ gateway `/storage` đã **chạy xác minh động trên môi trường thử nghiệm cục bộ read-only (port 8099)**.

| ID | Nội dung | Cách kiểm thử đề xuất | Kết quả của buổi audit |
|---|---|---|---|
| SEC-EXPOSURE-001 | Truy cập `/storage/zalo_runtime_config.json` không cần token | GET (instance thử nghiệm) | ✅ VERIFIED — HTTP 200, có `ZALO_BOT_API_KEY` |
| SEC-EXPOSURE-002 | Tải backup CSDL public | GET `/storage/backups/backup_*.zip` | ✅ VERIFIED — HTTP 200, 11,159 bytes |
| SEC-EXPOSURE-003 | Đọc log server public | GET `/storage/server_out.log` | ✅ VERIFIED — HTTP 200, 64 KB |
| SEC-EXPOSURE-004 | Ảnh học sinh public | GET `/storage/captures/latest/Lop_1.jpg` (path biết trước) | Potential — file tồn tại, mount công khai; NOT RUN toàn cục |
| SEC-AUTH-001 | Brute-force `/api/auth/login` | gửi loạt login sai; đo lockout/rate-limit | NOT RUN (hạn chế) — code cho thấy không có |
| SEC-AUTH-002 | Staff → `/api/cameras/reset-defaults` | login staff, POST reset | NOT RUN — code cho thấy chỉ cần `get_current_user` |
| SEC-AUTH-003 | Staff → `/api/attendance/clear-history` | login staff, POST clear | NOT RUN — code cho thấy chỉ cần `get_current_user` |
| SEC-AUTH-004 | HS256 token hết hạn/không hợp lệ | decode token fake | NOT RUN — decode trả None (code nhìn thấy đúng) |
| SEC-SSRF-001 | `/cameras/test-connection` với `file://`/local path | gửi `source_url` đường dẫn ảnh nội bộ | NOT RUN — code `cv2` nhận path bất kỳ |
| SEC-SSRF-002 | `/cameras/nvr/probe` scan cổng LAN | đổi `ip_address` nội bộ khác | NOT RUN — code probe TCP tùy ý |
| SEC-SSRF-003 | `/reports/send-zalo` với webhook nội bộ | đổi `webhook_url` = http://127.0.0.1 | NOT RUN — code cho phép |
| SEC-XSS-001 | Stored XSS qua `class_name` | tạo camera tên `<img src=x onerror=alert(1)>` rồi xem dashboard | NOT RUN — code `innerHTML` không escape (dashboard.js ~560) |
| SEC-XSS-002 | Reflected DOM XSS qua message test camera | nhập `source_url` chứa `<script>`, test kết nối | NOT RUN — cameras.js:586-597 |
| SEC-ZIP-001 | Zip-slip restore gói zip có `../` | chuẩn bị zip độc, tải lên upload-restore | NOT RUN — code `extractall` |
| SEC-CONF-001 | OpenAPI/docs public | GET /docs, /redoc | NOT RUN — FastAPI mở sẵn |
| SEC-DEP-001 | pip-audit trên venv | chạy `pip-audit -r requirements.txt` | NOT RUN (môi trường chưa rõ) |

## Phụ lục A — Phân loại mức độ

- **CRITICAL:** Lộ dữ liệu nhạy cảm/bí mật hoặc khả năng chiếm quyền toàn cục khi bị khai thác, không cần điều kiện đặc biệt.
- **HIGH:** Chiếm quyền một tài khoản/quyền staff hoặc gây hậu quả lớn cục bộ.
- **MEDIUM:** Rò rỉ thông tin giới hạn, hardening, lạm dụng hạn chế.
- **LOW:** Cải tiến vệ sinh mã/cấu hình.
- **INFO:** Khuyến nghị.



## Phụ lục B — Danh mục nguồn tham khảo

- `SECURITY_ARCHITECTURE.md` — mô tả kiến trúc & attack surface.
- GitHub Advisory / OWASP:
  - OWASP Top 10 2021 (A01 Broken Access Control, A03 Injection, A05 Misconfiguration, A06 Vulnerable Components, A07 XSS, A08 SSRF, A09 Logging, A10 SSRF & Supply chain).
  - OWASP ASVS v4.
- CVEs liên quan: không có CVE cụ thể áp cho các phụ thuộc được audit (chưa chạy scanner).