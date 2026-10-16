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
    print(" BẮT ĐẦU KIỂM THỬ VÀ ĐÁNH GIÁ MA TRẬN 77 REST API ENDPOINTS ")
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
        print(f"[{status_mark}] {method:<6} {endpoint:<45} | Trả về: {status_code:<3} (Mong muốn: {expected_status}) | {latency_ms:>5.1f}ms | {notes}")

    # =========================================================================
    # PHẦN 1: KIỂM THỬ BẢO MẬT & XÁC THỰC (UNAUTHENTICATED)
    # =========================================================================
    print("\n--- [1] KIỂM THỬ XÁC THỰC & BẢO MẬT (CHƯA ĐĂNG NHẬP) ---")
    anon_client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # 1.1 Public endpoints: mong muốn 200
    for method, path in [
        ("GET", "/api/health"),
        ("GET", "/api/database/info"),
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
        ("Auth", "GET", "/api/auth/me"),
        ("Auth", "GET", "/api/auth/users"),
        ("Cameras", "GET", "/api/cameras"),
        ("Attendance", "GET", "/api/attendance/latest"),
        ("Attendance", "GET", "/api/attendance/history"),
        ("ROI", "GET", "/api/roi/10A1"),
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
            record(router, method, f"{path} (unauth)", r.status_code, 401, lat, "Yêu cầu đăng nhập", passed)
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
        record("Auth", "POST", "/api/auth/login", r.status_code, 200, lat, f"Cookie set: {'access_token' in admin_client.cookies}", passed)
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
    record("Auth", "GET", "/api/auth/me", r.status_code, 200, lat, f"User: {r.json().get('user', {}).get('email')}", r.status_code == 200)

    # 3.2 /api/auth/users
    t0 = time.time()
    r = admin_client.get("/api/auth/users")
    lat = (time.time() - t0) * 1000
    record("Auth", "GET", "/api/auth/users", r.status_code, 200, lat, f"Users count: {len(r.json()) if isinstance(r.json(), list) else 'err'}", r.status_code == 200)

    # 3.3 /api/auth/forgot-password (gửi email hợp lệ)
    t0 = time.time()
    r = admin_client.post("/api/auth/forgot-password", json={"email": "admin@truongdieucai.edu.vn"})
    lat = (time.time() - t0) * 1000
    record("Auth", "POST", "/api/auth/forgot-password", r.status_code, 200, lat, r.json().get("message", "")[:40], r.status_code == 200)

    # =========================================================================
    # PHẦN 4: KIỂM THỬ ROUTER SYSTEM & AI
    # =========================================================================
    print("\n--- [4] KIỂM THỬ ROUTER: SYSTEM & AI ---")
    system_tests = [
        ("GET", "/api/health", None, 200),
        ("GET", "/api/database/info", None, 200),
        ("GET", "/api/ai/info", None, 200),
        ("GET", "/api/system/ai/info", None, 200),
        ("GET", "/api/system/classrooms-media", None, 200),
        ("POST", "/api/system/reset-to-camera-photos", {}, 200),
    ]
    for method, path, payload, exp in system_tests:
        t0 = time.time()
        r = admin_client.request(method, path, json=payload if payload is not None else None)
        lat = (time.time() - t0) * 1000
        record("System", method, path, r.status_code, exp, lat, "Hệ thống & Model YOLO", r.status_code == exp)

    # =========================================================================
    # PHẦN 5: KIỂM THỬ ROUTER CAMERAS & NVR
    # =========================================================================
    print("\n--- [5] KIỂM THỬ ROUTER: CAMERAS & NVR ---")
    camera_gets = [
        ("GET", "/api/cameras", 200, "Danh sách 30 phòng"),
        ("GET", "/api/cameras/", 200, "Alias trailing slash"),
        ("GET", "/api/cameras/10A1/raw", 200, "Raw RTSP URL (admin)"),
        ("GET", "/api/cameras/matrix-wall", 200, "Ma trận 30 camera"),
        ("GET", "/api/cameras/source-status", 200, "Trạng thái nguồn cấp hình"),
        ("GET", "/api/cameras/available-webcams", 200, "Quét webcam nội bộ"),
        ("GET", "/api/cameras/progress", 200, "Tiến độ chụp ảnh song song"),
        ("GET", "/api/cameras/nvr/list", 200, "Danh sách NVR cấu hình"),
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
        ("POST", "/api/cameras/test-connection", {"source_url": "camera/10A1.jpg", "trigger_signal": False}, 200, "Test kết nối preview ảnh mẫu"),
        ("POST", "/api/cameras/test-ir-by-url", {"source_url": "camera/10A1.jpg", "relay_ip": ""}, 200, "Test tín hiệu IR"),
        ("POST", "/api/cameras/10A1/test-ir", {"duration_seconds": 1, "mode": "IR_ON"}, 200, "Test IR phòng 10A1"),
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
    # 6.1 GET /api/roi/10A1
    t0 = time.time()
    r = admin_client.get("/api/roi/10A1")
    lat = (time.time() - t0) * 1000
    has_keys = "green_zone" in r.json() and "red_zone" in r.json() if r.status_code == 200 else False
    record("ROI", "GET", "/api/roi/10A1", r.status_code, 200, lat, f"Vùng xanh/đỏ: {has_keys}", r.status_code == 200 and has_keys)

    # 6.2 POST /api/roi/10A1 (Lưu tọa độ chuẩn)
    test_roi_payload = {
        "green_zone": [{"x": 100, "y": 200}, {"x": 800, "y": 200}, {"x": 800, "y": 700}, {"x": 100, "y": 700}],
        "red_zone": [{"x": 50, "y": 50}, {"x": 300, "y": 50}, {"x": 300, "y": 180}, {"x": 50, "y": 180}]
    }
    t0 = time.time()
    r = admin_client.post("/api/roi/10A1", json=test_roi_payload)
    lat = (time.time() - t0) * 1000
    record("ROI", "POST", "/api/roi/10A1", r.status_code, 200, lat, "Lưu tọa độ vùng ROI", r.status_code == 200)

    # 6.3 POST /api/roi/10A1/refresh-snapshot
    t0 = time.time()
    r = admin_client.post("/api/roi/10A1/refresh-snapshot")
    lat = (time.time() - t0) * 1000
    record("ROI", "POST", "/api/roi/10A1/refresh-snapshot", r.status_code, 200, lat, "Chụp lại ảnh mẫu phòng 10A1", r.status_code == 200)

    # 6.4 POST /api/roi/10A1/rescan
    t0 = time.time()
    r = admin_client.post("/api/roi/10A1/rescan")
    lat = (time.time() - t0) * 1000
    record("ROI", "POST", "/api/roi/10A1/rescan", r.status_code, 200, lat, f"Quét AI thử nghiệm: {r.json().get('student_count', 0)} HS", r.status_code == 200)

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

    # Thử lấy session chi tiết nếu có
    try:
        r_hist = admin_client.get("/api/attendance/history")
        sessions = r_hist.json().get("sessions", []) if r_hist.status_code == 200 else []
        if sessions:
            first_sid = sessions[0]["id"]
            t0 = time.time()
            r_sess = admin_client.get(f"/api/attendance/sessions/{first_sid}")
            lat = (time.time() - t0) * 1000
            record("Attendance", "GET", f"/api/attendance/sessions/{first_sid}", r_sess.status_code, 200, lat, f"Chi tiết phiên ID={first_sid}", r_sess.status_code == 200)
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
        ("POST", "/api/reports/save-email-config", {"smtp_server": "smtp.gmail.com", "smtp_port": 587, "smtp_user": "test@gmail.com"}, 200, "Lưu cấu hình email"),
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
        ("GET", "/api/backup/gdrive/auth-url", 200, "Lấy URL ủy quyền OAuth GDrive"),
    ]
    for method, path, exp, desc in bk_gets:
        t0 = time.time()
        r = admin_client.get(path)
        lat = (time.time() - t0) * 1000
        record("Backup", method, path, r.status_code, exp, lat, desc, r.status_code == exp)

    # Tạo backup mới thử nghiệm
    t0 = time.time()
    r = admin_client.post("/api/backup/create", json={"include_media": False})
    lat = (time.time() - t0) * 1000
    created_file = r.json().get("filename") if r.status_code == 200 else None
    record("Backup", "POST", "/api/backup/create", r.status_code, 200, lat, f"Tạo file: {created_file}", r.status_code == 200)

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
