"""Quản lý lưu / đọc cấu hình điều chỉnh thông báo (mẫu tin nhắn, quy tắc gửi, lịch trình) ra file JSON."""
import json
from pathlib import Path
from typing import Dict, Any

NOTIFICATION_SETTINGS_FILE = "notification_adjust_settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "ENABLE_ZALO_NOTIFICATION": True,
    "ENABLE_EMAIL_NOTIFICATION": False,
    "NOTIFICATION_SEND_CONDITION": "always",  # "always" | "has_absent"
    "NOTIFICATION_ALERT_THRESHOLD_PERCENT": 10.0,
    "NOTIFICATION_ALERT_CLASS_ABSENT": 3,
    "SCAN_TIME_MORNING": "06:45",
    "SCAN_TIME_AFTERNOON": "12:45",
    "SCHEDULE_DAYS": "mon-sat",
    "AUTO_SCAN_ENABLED": True,
    "DATA_RETENTION_DAYS": 90,
    "DATA_AUTO_CLEANUP_ENABLED": True,
    "DATA_CLEANUP_EXCEL_ENABLED": True,
    "ZALO_SCHOOL_TEMPLATE": """🔔 [THPT ĐIỀU CẢI] BÁO CÁO ĐIỂM DANH SĨ SỐ ĐẦU GIỜ
📅 Ngày quét: {ngay} | Giờ: {gio}
🏫 Tổng số lớp: {tong_lop} lớp
👥 Sĩ số toàn trường: {si_so} học sinh
✅ Có mặt: {co_mat} | ❌ Vắng mặt: {vang_mat}
📊 Tỷ lệ chuyên cần: {ty_le}

{danh_sach_vang}

📂 File báo cáo Excel & ảnh đối chứng AI đã lưu trên hệ thống máy chủ.""",
    "ZALO_CLASS_TEMPLATE": """🔔 [THPT ĐIỀU CẢI] BÁO CÁO ĐIỂM DANH LỚP {lop}
📅 Ngày quét: {ngay} | Giờ: {gio}
🏫 Lớp: {lop} {phong}
👥 Sĩ số: {co_mat}/{si_so} học sinh
✅ Có mặt: {co_mat} | ❌ Vắng: {vang_mat} em
📊 Tỷ lệ chuyên cần: {ty_le}""",
    "EMAIL_SUBJECT_TEMPLATE": "[ĐIỂM DANH SĨ SỐ] Báo cáo ngày {ngay} lúc {gio} - THPT Điều Cải",
    "EMAIL_BODY_TEMPLATE": """Kính gửi Ban Giám hiệu Trường THPT Điều Cải,

Hệ thống Camera AI đã hoàn tất quy trình quét điểm danh tự động lúc {gio} ngày {ngay}.

THỐNG KÊ TỔNG QUAN:
- Tổng số lớp học: {tong_lop} lớp
- Sĩ số toàn trường: {si_so} học sinh
- Có mặt: {co_mat} học sinh | Vắng mặt: {vang_mat} học sinh
- Tỷ lệ chuyên cần: {ty_le}

Chi tiết sĩ số của từng lớp và ảnh chụp đối chứng được đính kèm trong file Excel bên dưới.

Trân trọng,
Hệ Thống Điểm Danh Tự Động AI"""
}

def load_notification_settings(settings) -> Dict[str, Any]:
    """Nạp cấu hình điều chỉnh thông báo vào đối tượng settings."""
    path = settings.BASE_DIR / "storage" / NOTIFICATION_SETTINGS_FILE
    data = dict(DEFAULT_SETTINGS)
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                data.update(saved)
        except Exception:
            pass

    for k, v in data.items():
        setattr(settings, k, v)
    return data

def save_notification_settings(settings, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ghi cấu hình điều chỉnh thông báo ra file JSON và cập nhật runtime settings."""
    path = settings.BASE_DIR / "storage" / NOTIFICATION_SETTINGS_FILE
    current = dict(DEFAULT_SETTINGS)
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                current.update(saved)
        except Exception:
            pass

    current.update(payload)
    for k, v in current.items():
        setattr(settings, k, v)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current
