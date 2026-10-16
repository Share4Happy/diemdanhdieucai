"""
Script đánh giá và kiểm thử ma trận toàn bộ 77 REST API endpoints của hệ thống.
Chạy trực tiếp qua HTTP client tới backend.
"""
import sys
import time
import json
from pathlib import Path
import httpx

BASE_URL = "http://127.0.0.1:8000"

def run_audit():
    print("=" * 80)
    print(" BẮT ĐẦU KIỂM THỬ VÀ ĐÁNH GIÁ MA TRẬN TOÀN BỘ REST API ENDPOINTS ")
    print("=" * 80)

    results = []

    def record(router, method, endpoint, status_code, expected_status, latency_ms, notes="", passed=True):
        status_mark = "✅ PASS" if passed else "❌ FAIL"
        results.append({
            "router": router,
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "expected_status": expected_status,
            "latency_ms": round(latency_ms, 1),
            "passed": passed,
            "notes": notes
        })
        print(f"[{status_mark}] {method:<6} {endpoint:<45} | Trả về: {status_code:<3} (Kỳ vọng: {str(expected_status):<3}) | {latency_ms:>5.1f}ms | {notes}")

    # =========================================================================
    # PHẦN 1: KIỂM THỬ BẢO MẬT & XÁC THỰC (UNAUTHENTICATED)
    # =========================================================================
    print("\n--- [1] KIỂM THỬ XÁC THỰC & BẢO MẬT (CHƯA ĐĂNG NHẬP) ---")
    anon_client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # 1.1 Public endpoints: mong muốn 200
    for method, path in [
        ("GET", "/api/health"),
    ]:
        t0 = time.time()
        try:
            r = anon_client.request(method, path)
            lat = (time.time() - t0) * 1000
            passed = r.status_code == 200
            record("System", method, path, r.status_code, 200, lat, "Công khai (Public)", passed)
        except Exception as e:
            record("System", method, path, 0, 200, 0, f"Lỗi kết nối: {e}", False)

    # 1.2 Protected endpoints: mong muốn 401 khi chưa đăng nhập
    protected_samples = [
        ("System", "GET", "/api/database/info"),
        ("Auth", "GET", "/api/auth/me"),
        ("Auth", "GET", "/api/auth/users"),
        ("Cameras", "GET", "/api/cameras"),
        ("Attendance", "GET", "/api/attendance/latest"),
        ("Attendance", "GET", "/api/attendance/history"),
        ("ROI", "GET", "/api/roi/1"),
        ("Reports", "GET", "/api/reports/list"),
        ("Reports", "GET", "/api/reports/distribution-status"),
        ("Backup", "GET", "/api/backup/list"),
    ]
    for router, method, path in protected_samples:
        t0 = time.time()
        try:
            r = anon_client.request(method, path)
            lat = (time.time() - t0) * 1000
            passed = r.status_code == 401
            record(router, method, f"{path} (unauth)", r.status_code, 401, lat, "Chặn 401 an toàn", passed)
        except Exception as e:
            record(router, method, f"{path} (unauth)", 0, 401, 0, f"Lỗi: {e}", False)

    # =========================================================================
    # PHẦN 2: ĐĂNG NHẬP ADMIN & LẤY COOKIE
    # =========================================================================
    print("\n--- [2] ĐĂNG NHẬP QUẢN TRỊ VIÊN ---")
    admin_client = httpx.Client(base_url=BASE_URL, timeout=15.0)
    t0 = time.time()
    try:
        r = admin_client.post("/api/auth/login", json={
            "email": "admin@truongdieucai.edu.vn",
            "password": "Admin@2025"
        })
        lat = (time.time() - t0) * 1000
        passed = r.status_code == 200 and "access_token" in admin_client.cookies
        record("Auth", "POST", "/api/auth/login", r.status_code, 200, lat, f"Đăng nhập thành công, cookie: {'access_token' in admin_client.cookies}", passed)
    except Exception as e:
        record("Auth", "POST", "/api/auth/login", 0, 200, 0, f"Lỗi: {e}", False)
        print("KHÔNG THỂ TIẾP TỤC NẾU KHÔNG ĐĂNG NHẬP ĐƯỢC ADMIN!")
        return

    # =========================================================================
    # PHẦN 3: KIỂM THỬ ROUTER AUTH (VỚI QUYỀN ADMIN)
    # =========================================================================
    print("\n--- [3] KIỂM THỬ ROUTER: AUTH & USERS ---")
    # 3.1 /api/auth/me
    t0 = time.time()
    r = admin_client.get("/api/auth/me")
    lat = (time.time() - t0) * 1000
    user_data = r.json().get("user", {}) if r.status_code == 200 else {}
    record("Auth", "GET", "/api/auth/me", r.status_code, 200, lat, f"Email: {user_data.get('email')}, Role: {user_data.get('role')}", r.status_code == 200)

    # 3.2 /api/auth/users
    t0 = time.time()
    r = admin_client.get("/api/auth/users")
    lat = (time.time() - t0) * 1000
    users_list = r.json() if isinstance(r.json(), list) else []
    record("Auth", "GET", "/api/auth/users", r.status_code, 200, lat, f"Số tài khoản: {len(users_list)}", r.status_code == 200)

    # 3.3 /api/auth/forgot-password (gửi email hợp lệ)
    t0 = time.time()
    r = admin_client.post("/api/auth/forgot-password", json={"email": "admin@truongdieucai.edu.vn"})
    lat = (time.time() - t0) * 1000
    record("Auth", "POST", "/api/auth/forgot-password", r.status_code, 200, lat, r.json().get("message", "")[:45], r.status_code == 200)

    # =========================================================================
    # PHẦN 4: KIỂM THỬ ROUTER SYSTEM & AI
    # =========================================================================
    print("\n--- [4] KIỂM THỬ ROUTER: SYSTEM & AI ---")
    system_tests = [
        ("GET", "/api/health", None, 200, "Sức khỏe hệ thống & AI Engine"),
        ("GET", "/api/database/info", None, 200, "Thông tin CSDL SQLite"),
        ("GET", "/api/ai/info", None, 200, "Thông tin YOLO26 Engine"),
        ("GET", "/api/system/ai/info", None, 200, "Alias YOLO26 Engine"),
        ("GET", "/api/system/classrooms-media", None, 200, "Danh sách media mẫu phòng học"),
        ("POST", "/api/system/reset-to-camera-photos", {}, 200, "Reset về ảnh mẫu camera"),
    ]
    for method, path, payload, exp, desc in system_tests:
        t0 = time.time()
        r = admin_client.request(method, path, json=payload if payload is not None else None)
        lat = (time.time() - t0) * 1000
        record("System", method, path, r.status_code, exp, lat, desc, r.status_code == exp)

    # =========================================================================
    # PHẦN 5: KIỂM THỬ ROUTER CAMERAS & NVR
    # =========================================================================
    print("\n--- [5] KIỂM THỬ ROUTER: CAMERAS & NVR ---")
    camera_gets = [
        ("GET", "/api/cameras", 200, "Danh sách 30 camera kèm has_roi"),
        ("GET", "/api/cameras/", 200, "Trailing slash alias"),
        ("GET", "/api/cameras/1/raw", 200, "Raw RTSP URL (admin ID=1)"),
        ("GET", "/api/cameras/matrix-wall", 200, "Ma trận 30 camera trực tiếp"),
        ("GET", "/api/cameras/source-status", 200, "Trạng thái nguồn cấp hình"),
        ("GET", "/api/cameras/available-webcams", 200, "Quét webcam nội bộ"),
        ("GET", "/api/cameras/progress", 200, "Tiến độ chụp ảnh song song"),
        ("GET", "/api/cameras/nvr/list", 200, "Danh sách cấu hình NVR"),
    ]
    for method, path, exp, desc in camera_gets:
        t0 = time.time()
        r = admin_client.get(path)
        lat = (time.time() - t0) * 1000
        record("Cameras", method, path, r.status_code, exp, lat, desc, r.status_code == exp)

    camera_posts = [
        ("POST", "/api/cameras/batch-status", {"classroom_ids": ["10A1", "10A2"]}, 200, "Batch status ping"),
        ("POST", "/api/cameras/inspect-folder", {"folder_path": "dataset"}, 200, "Kiểm tra thư mục media"),
        ("POST", "/api/cameras/cleanup-test-images", None, 200, "Dọn dẹp ảnh wizard"),
        ("POST", "/api/cameras/test-connection", {"source_url": "camera/10A1.jpg", "trigger_signal": False}, 200, "Test preview ảnh mẫu"),
        ("POST", "/api/cameras/test-ir-by-url", {"source_url": "camera/10A1.jpg", "relay_ip": ""}, 200, "Test tín hiệu IR"),
        ("POST", "/api/cameras/1/test-ir", {"duration_seconds": 1, "mode": "IR_ON"}, 200, "Test IR phòng ID=1"),
        ("POST", "/api/cameras/validate-new-camera", {"source_url": "camera/10A1.jpg", "standard_count": 40}, 200, "Validate Wizard camera"),
    ]
    for method, path, payload, exp, desc in camera_posts:
        t0 = time.time()
        r = admin_client.post(path, json=payload if payload is not None else None)
        lat = (time.time() - t0) * 1000
        record("Cameras", method, path, r.status_code, exp, lat, desc, r.status_code == exp)

    # =========================================================================
    # PHẦN 6: KIỂM THỬ ROUTER ROI
    # =========================================================================
    print("\n--- [6] KIỂM THỬ ROUTER: ROI CONFIGURATION ---")
    # 6.1 GET /api/roi/1 (Phòng 10A1 có ID=1)
    t0 = time.time()
    r = admin_client.get("/api/roi/1")
    lat = (time.time() - t0) * 1000
    has_keys = "green_zone" in r.json() and "red_zone" in r.json() if r.status_code == 200 else False
    record("ROI", "GET", "/api/roi/1", r.status_code, 200, lat, f"Đã có green/red zone: {has_keys}", r.status_code == 200 and has_keys)

    # 6.2 POST /api/roi/1 (Lưu tọa độ chuẩn định dạng [[x, y], ...])
    test_roi_payload = {
        "green_zone": [[100, 200], [800, 200], [800, 700], [100, 700]],
        "red_zone": [[50, 50], [300, 50], [300, 180], [50, 180]],
        "image_width": 1280,
        "image_height": 720
    }
    t0 = time.time()
    r = admin_client.post("/api/roi/1", json=test_roi_payload)
    lat = (time.time() - t0) * 1000
    record("ROI", "POST", "/api/roi/1", r.status_code, 200, lat, "Lưu tọa độ vùng ROI & sync AI", r.status_code == 200)

    # 6.3 POST /api/roi/1/refresh-snapshot
    t0 = time.time()
    r = admin_client.post("/api/roi/1/refresh-snapshot")
    lat = (time.time() - t0) * 1000
    record("ROI", "POST", "/api/roi/1/refresh-snapshot", r.status_code, 200, lat, "Chụp lại ảnh mẫu phòng ID=1", r.status_code == 200)

    # 6.4 POST /api/roi/1/rescan
    t0 = time.time()
    r = admin_client.post("/api/roi/1/rescan")
    lat = (time.time() - t0) * 1000
    scanned_count = r.json().get("student_count", 0) if r.status_code == 200 else 0
    record("ROI", "POST", "/api/roi/1/rescan", r.status_code, 200, lat, f"AI phát hiện: {scanned_count} học sinh", r.status_code == 200)

    # =========================================================================
    # PHẦN 7: KIỂM THỬ ROUTER ATTENDANCE
    # =========================================================================
    print("\n--- [7] KIỂM THỬ ROUTER: ATTENDANCE ---")
    att_tests = [
        ("GET", "/api/attendance/latest", 200, "Phiên điểm danh mới nhất"),
        ("GET", "/api/attendance/today-sessions", 200, "Danh sách phiên hôm nay"),
        ("GET", "/api/attendance/trend-7days", 200, "Xu hướng sĩ số 7 ngày qua"),
        ("GET", "/api/attendance/history", 200, "Lịch sử điểm danh"),
        ("GET", "/api/attendance/progress", 200, "Tiến độ quét điểm danh"),
        ("GET", "/api/attendance/download-excel", 200, "Tải file Excel mẫu"),
    ]
    for method, path, exp, desc in att_tests:
        t0 = time.time()
        r = admin_client.get(path)
        lat = (time.time() - t0) * 1000
        record("Attendance", method, path, r.status_code, exp, lat, desc, r.status_code == exp)

    # Chi tiết phiên điểm danh & Sửa sĩ số (override)
    try:
        r_hist = admin_client.get("/api/attendance/history")
        sessions = r_hist.json().get("sessions", []) if r_hist.status_code == 200 else []
        if sessions:
            first_sid = sessions[0]["id"]
            t0 = time.time()
            r_sess = admin_client.get(f"/api/attendance/sessions/{first_sid}")
            lat = (time.time() - t0) * 1000
            record("Attendance", "GET", f"/api/attendance/sessions/{first_sid}", r_sess.status_code, 200, lat, f"Chi tiết phiên ID={first_sid}", r_sess.status_code == 200)

            # Test override sĩ số chi tiết
            details = r_sess.json().get("details", []) if r_sess.status_code == 200 else []
            if details:
                first_det_id = details[0]["id"]
                t0 = time.time()
                r_over = admin_client.put(f"/api/attendance/details/{first_det_id}/override", json={
                    "actual_count": 38,
                    "reason": "Điều chỉnh sĩ số kiểm thử hệ thống"
                })
                lat = (time.time() - t0) * 1000
                record("Attendance", "PUT", f"/api/attendance/details/{first_det_id}/override", r_over.status_code, 200, lat, "Sửa sĩ số thủ công kèm lý do", r_over.status_code == 200)
    except Exception as e:
        record("Attendance", "GET", "/api/attendance/sessions/{id}", 0, 200, 0, f"Lỗi: {e}", False)

    # =========================================================================
    # PHẦN 8: KIỂM THỬ ROUTER REPORTS & NOTIFICATIONS
    # =========================================================================
    print("\n--- [8] KIỂM THỬ ROUTER: REPORTS & NOTIFICATIONS ---")
    rep_gets = [
        ("GET", "/api/reports/list", 200, "Danh sách báo cáo"),
        ("GET", "/api/reports/latest-summary", 200, "Tổng hợp số liệu mới nhất"),
        ("GET", "/api/reports/distribution-status", 200, "Trạng thái cấu hình gửi"),
        ("GET", "/api/reports/zalo-status", 200, "Trạng thái kết nối Zalo OA"),
        ("GET", "/api/reports/zalo-config", 200, "Cấu hình Zalo"),
        ("GET", "/api/reports/notification-settings", 200, "Cấu hình gửi thông báo"),
        ("GET", "/api/reports/retention-settings", 200, "Chính sách lưu trữ dữ liệu"),
    ]
    for method, path, exp, desc in rep_gets:
        t0 = time.time()
        r = admin_client.get(path)
        lat = (time.time() - t0) * 1000
        record("Reports", method, path, r.status_code, exp, lat, desc, r.status_code == exp)

    # Test POST cấu hình reports
    rep_posts = [
        ("POST", "/api/reports/export-now", None, 200, "Xuất báo cáo ngay lập tức"),
        ("POST", "/api/reports/save-email-config", {"principal_email": "admin@truongdieucai.edu.vn"}, 200, "Lưu cấu hình email Hiệu Trưởng"),
        ("POST", "/api/reports/save-zalo-config", {"enabled": False, "notification_type": "BOT_API"}, 200, "Lưu cấu hình Zalo"),
        ("POST", "/api/reports/notification-settings", {"enable_zalo": False, "enable_email": False}, 200, "Cập nhật ngưỡng thông báo"),
        ("POST", "/api/reports/retention-settings", {"days_to_keep": 30, "auto_delete_images": False}, 200, "Cập nhật chính sách lưu trữ"),
        ("POST", "/api/reports/cleanup-expired", {"days": 90}, 200, "Dọn dẹp báo cáo quá hạn"),
    ]
    for method, path, payload, exp, desc in rep_posts:
        t0 = time.time()
        r = admin_client.post(path, json=payload if payload is not None else None)
        lat = (time.time() - t0) * 1000
        record("Reports", method, path, r.status_code, exp, lat, desc, r.status_code == exp)

    # =========================================================================
    # PHẦN 9: KIỂM THỬ ROUTER BACKUP & RESTORE
    # =========================================================================
    print("\n--- [9] KIỂM THỬ ROUTER: BACKUP & RESTORE ---")
    bk_gets = [
        ("GET", "/api/backup/list", 200, "Danh sách bản sao lưu"),
        ("GET", "/api/backup/gdrive/status", 200, "Trạng thái Google Drive"),
    ]
    for method, path, exp, desc in bk_gets:
        t0 = time.time()
        r = admin_client.get(path)
        lat = (time.time() - t0) * 1000
        record("Backup", method, path, r.status_code, exp, lat, desc, r.status_code == exp)

    # GDrive auth-url: nếu chưa có Client ID trong .env thì trả về 400 kèm thông báo cấu hình
    t0 = time.time()
    r_gdrive_auth = admin_client.get("/api/backup/gdrive/auth-url")
    lat = (time.time() - t0) * 1000
    gdrive_passed = r_gdrive_auth.status_code in (200, 400)
    gdrive_note = "URL ủy quyền OAuth" if r_gdrive_auth.status_code == 200 else f"Chưa cấu hình .env: {r_gdrive_auth.json().get('detail')}"
    record("Backup", "GET", "/api/backup/gdrive/auth-url", r_gdrive_auth.status_code, "200/400", lat, gdrive_note, gdrive_passed)

    # Tạo backup mới thử nghiệm
    t0 = time.time()
    r_bk = admin_client.post("/api/backup/create", json={"include_media": False})
    lat = (time.time() - t0) * 1000
    created_file = r_bk.json().get("data", {}).get("backup_name") if r_bk.status_code == 200 else None
    record("Backup", "POST", "/api/backup/create", r_bk.status_code, 200, lat, f"Tạo file backup: {created_file}", r_bk.status_code == 200 and bool(created_file))

    if created_file:
        # Tải file vừa tạo
        t0 = time.time()
        r_dl = admin_client.get(f"/api/backup/download/{created_file}")
        lat = (time.time() - t0) * 1000
        record("Backup", "GET", f"/api/backup/download/{created_file}", r_dl.status_code, 200, lat, f"Kích thước: {len(r_dl.content)} bytes", r_dl.status_code == 200)

        # Xóa file vừa tạo để hoàn trả dung lượng
        t0 = time.time()
        r_del = admin_client.delete(f"/api/backup/{created_file}")
        lat = (time.time() - t0) * 1000
        record("Backup", "DELETE", f"/api/backup/{created_file}", r_del.status_code, 200, lat, "Dọn dẹp file backup mẫu", r_del.status_code == 200)

    # =========================================================================
    # PHẦN 10: ĐĂNG XUẤT (REVOKE JTI)
    # =========================================================================
    print("\n--- [10] KIỂM THỬ ĐĂNG XUẤT (REVOKE JTI) ---")
    t0 = time.time()
    r_logout = admin_client.post("/api/auth/logout")
    lat = (time.time() - t0) * 1000
    record("Auth", "POST", "/api/auth/logout", r_logout.status_code, 200, lat, "Thu hồi JTI và xoá cookie", r_logout.status_code == 200)

    # Kiểm tra gọi lại /api/auth/me sau khi đăng xuất -> phải trả về 401
    t0 = time.time()
    r_me_after = admin_client.get("/api/auth/me")
    lat = (time.time() - t0) * 1000
    record("Auth", "GET", "/api/auth/me (sau logout)", r_me_after.status_code, 401, lat, "Phiên JWT đã bị vô hiệu hoá thành công", r_me_after.status_code == 401)

    # =========================================================================
    # TỔNG KẾT MA TRẬN
    # =========================================================================
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["passed"])
    failed_tests = total_tests - passed_tests
    avg_latency = sum(r["latency_ms"] for r in results) / max(1, total_tests)

    print("\n" + "=" * 80)
    print(" KẾT QUẢ TỔNG HỢP KIỂM THỬ MA TRẬN REST API ")
    print("=" * 80)
    print(f"Tổng số ca kiểm thử (Test Cases): {total_tests}")
    print(f"Số ca THÀNH CÔNG (PASS):        {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"Số ca THẤT BẠI (FAIL):          {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
    print(f"Thời gian phản hồi trung bình:   {avg_latency:.1f} ms")
    print("=" * 80)

    # Lưu kết quả ra file JSON
    out_path = Path("/app/data/api_audit_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "avg_latency_ms": round(avg_latency, 1),
            "results": results
        }, f, ensure_ascii=False, indent=2)
    print(f"Đã lưu kết quả chi tiết vào: {out_path}")

if __name__ == "__main__":
    run_audit()
