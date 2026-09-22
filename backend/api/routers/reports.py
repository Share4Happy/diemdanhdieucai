
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db
from database.models import AttendanceSession
from core.attendance_engine import attendance_engine
from services.excel_exporter import excel_exporter
from services.notification import notification_service
from services.zalo_service import zalo_service
from config.zalo_runtime_store import save_runtime_zalo
from config.notification_settings_store import save_notification_settings, DEFAULT_SETTINGS
from services.scheduler import attendance_scheduler
from backend.schemas.report_schemas import (
    SendEmailRequest,
    EmailConfigSaveRequest,
    ZaloTestRequest,
    ZaloConfigSaveRequest,
    NotificationAdjustRequest
)
from backend.api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"], dependencies=[Depends(get_current_user)])

@router.get("/list")
async def list_reports():
    """Lấy danh sách tất cả các file Excel đã xuất trong hệ thống."""
    reports = excel_exporter.list_all_reports()
    return {"reports": reports}

@router.post("/export-now")
async def export_excel_now(db: Session = Depends(get_db)):
    """Xuất file Excel tổng hợp 30 lớp học ngay lập tức bằng pandas & openpyxl."""
    session = db.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()
    if not session:
        result = attendance_engine.run_daily_attendance(trigger_led=False)
        session_id = result.get("session_id")
    else:
        session_id = session.id

    path = excel_exporter.generate_daily_report(session_id)
    if not path or not os.path.exists(str(path)):
        raise HTTPException(status_code=500, detail="Không thể tạo file Excel báo cáo.")

    rel_path = path.relative_to(settings.REPORTS_DIR)
    rel_str = str(rel_path).replace("\\", "/")
    download_url = f"/storage/reports/{rel_str}"
    return {
        "success": True,
        "filename": path.name,
        "download_url": download_url
    }

@router.post("/send-email")
async def send_report_email(req: SendEmailRequest):
    """Gửi email báo cáo điểm danh trực tiếp tới Hiệu trưởng."""
    res = notification_service.send_test_email(req.email)
    return res

@router.post("/save-email-config")
async def save_email_config(req: EmailConfigSaveRequest):
    """Lưu cấu hình email Hiệu Trưởng vào hệ thống."""
    if req.principal_email:
        settings.PRINCIPAL_EMAIL = req.principal_email.strip()
        payload = {"PRINCIPAL_EMAIL": settings.PRINCIPAL_EMAIL}
        save_notification_settings(settings, payload)
    return {"success": True, "message": f"Đã lưu email Hiệu Trưởng: {settings.PRINCIPAL_EMAIL}"}

@router.get("/distribution-status")
async def get_distribution_status():
    """Lấy thông tin trạng thái phân phối báo cáo nội bộ và email."""
    return notification_service.get_status()

@router.post("/send-zalo")
async def send_zalo_report(req: ZaloTestRequest):
    """Gửi tin nhắn báo cáo điểm danh hoặc tin thử nghiệm qua Zalo."""
    if req.session_id:
        res = zalo_service.send_attendance_summary(req.session_id)
    else:
        # Nhận diện đầy đủ cả 2 chuẩn đặt tên field từ frontend / API client
        target_type = req.notification_type or req.target_type or settings.ZALO_NOTIFICATION_TYPE or "BOT_API"
        bot_key = req.bot_api_key or req.api_key or settings.ZALO_BOT_API_KEY
        bot_id = req.bot_id or settings.ZALO_BOT_ID
        bot_url = req.bot_api_base_url or req.api_base_url or settings.ZALO_BOT_API_BASE_URL
        phone = req.test_phone or req.phone
        user_id = req.recipient_user_id or req.user_id or settings.ZALO_RECIPIENT_USER_ID
        access_token = req.access_token or settings.ZALO_OA_ACCESS_TOKEN
        webhook_url = req.webhook_url or settings.ZALO_WEBHOOK_URL

        # Nếu có cấu hình bot_id hoặc bot_key và target_type là WEBHOOK nhưng không có webhook_url -> Tự động chuyển qua BOT_API
        if (bot_id or bot_key) and (target_type.upper() == "WEBHOOK" and not webhook_url):
            target_type = "BOT_API"

        res = zalo_service.send_test_message(
            target_type=target_type,
            webhook_url=webhook_url,
            access_token=access_token,
            user_id=user_id,
            phone=phone,
            bot_id=bot_id,
            api_key=bot_key,
            api_base_url=bot_url,
            recipients=req.recipients
        )
    return res

@router.get("/zalo-status")
async def get_zalo_status():
    """Lấy trạng thái cấu hình dịch vụ Zalo."""
    return zalo_service.get_status()

@router.get("/zalo-config")
async def get_zalo_config():
    """Lấy toàn bộ cấu hình Zalo để nạp lên giao diện quản trị."""
    return {
        "success": True,
        "config": {
            "enabled": settings.ENABLE_ZALO_NOTIFICATION,
            "notification_type": settings.ZALO_NOTIFICATION_TYPE,
            "webhook_url": settings.ZALO_WEBHOOK_URL,
            "access_token": settings.ZALO_OA_ACCESS_TOKEN,
            "recipient_user_id": settings.ZALO_RECIPIENT_USER_ID,
            "bot_api_base_url": settings.ZALO_BOT_API_BASE_URL,
            "bot_id": settings.ZALO_BOT_ID,
            "bot_api_key": settings.ZALO_BOT_API_KEY,
            "recipient_phones": settings.ZALO_RECIPIENT_PHONES,
            "recipients_json": settings.ZALO_RECIPIENTS_JSON
        }
    }

@router.post("/save-zalo-config")
async def save_zalo_config(req: ZaloConfigSaveRequest):
    """Lưu cấu hình Zalo vào bộ nhớ hệ thống và ghi ra file để giữ qua các lần khởi động."""
    settings.ENABLE_ZALO_NOTIFICATION = req.enabled
    settings.ZALO_NOTIFICATION_TYPE = req.notification_type
    if req.webhook_url not in (None, ""):
        settings.ZALO_WEBHOOK_URL = req.webhook_url.strip()
    if req.access_token not in (None, ""):
        settings.ZALO_OA_ACCESS_TOKEN = req.access_token.strip()
    if req.recipient_user_id not in (None, ""):
        settings.ZALO_RECIPIENT_USER_ID = req.recipient_user_id.strip()
    if req.bot_api_base_url not in (None, ""):
        settings.ZALO_BOT_API_BASE_URL = req.bot_api_base_url.strip()
    if req.bot_id not in (None, ""):
        settings.ZALO_BOT_ID = req.bot_id.strip()
    if req.bot_api_key not in (None, ""):
        settings.ZALO_BOT_API_KEY = req.bot_api_key.strip()
    if req.recipient_phones not in (None, ""):
        settings.ZALO_RECIPIENT_PHONES = req.recipient_phones.strip()
    if req.recipients_json not in (None, ""):
        settings.ZALO_RECIPIENTS_JSON = req.recipients_json.strip()
    save_runtime_zalo(settings)
    return {"success": True, "message": "Đã cập nhật cấu hình Zalo thành công!"}

@router.get("/notification-settings")
async def get_notification_settings():
    """Lấy cấu hình điều chỉnh thông báo hiện tại (quy tắc, ngưỡng cảnh báo, lịch trình, mẫu tin nhắn)."""
    return {
        "enable_zalo": getattr(settings, "ENABLE_ZALO_NOTIFICATION", True),
        "enable_email": getattr(settings, "ENABLE_EMAIL_NOTIFICATION", False),
        "send_condition": getattr(settings, "NOTIFICATION_SEND_CONDITION", "always"),
        "alert_threshold_percent": getattr(settings, "NOTIFICATION_ALERT_THRESHOLD_PERCENT", 10.0),
        "alert_class_absent_count": getattr(settings, "NOTIFICATION_ALERT_CLASS_ABSENT", 3),
        "scan_time_morning": getattr(settings, "SCAN_TIME_MORNING", "06:45"),
        "scan_time_afternoon": getattr(settings, "SCAN_TIME_AFTERNOON", "12:45"),
        "auto_scan_enabled": getattr(settings, "AUTO_SCAN_ENABLED", True),
        "zalo_school_template": getattr(settings, "ZALO_SCHOOL_TEMPLATE", "") or DEFAULT_SETTINGS["ZALO_SCHOOL_TEMPLATE"],
        "zalo_class_template": getattr(settings, "ZALO_CLASS_TEMPLATE", "") or DEFAULT_SETTINGS["ZALO_CLASS_TEMPLATE"],
        "email_subject_template": getattr(settings, "EMAIL_SUBJECT_TEMPLATE", "") or DEFAULT_SETTINGS["EMAIL_SUBJECT_TEMPLATE"],
        "email_body_template": getattr(settings, "EMAIL_BODY_TEMPLATE", "") or DEFAULT_SETTINGS["EMAIL_BODY_TEMPLATE"],
        "defaults": DEFAULT_SETTINGS
    }

@router.post("/notification-settings")
async def update_notification_settings(req: NotificationAdjustRequest):
    """Cập nhật cấu hình điều chỉnh thông báo (quy tắc, ngưỡng cảnh báo, lịch trình, mẫu tin nhắn)."""
    payload = {
        "ENABLE_ZALO_NOTIFICATION": req.enable_zalo,
        "ENABLE_EMAIL_NOTIFICATION": req.enable_email,
        "NOTIFICATION_SEND_CONDITION": req.send_condition,
        "NOTIFICATION_ALERT_THRESHOLD_PERCENT": req.alert_threshold_percent,
        "NOTIFICATION_ALERT_CLASS_ABSENT": req.alert_class_absent_count,
        "SCAN_TIME_MORNING": req.scan_time_morning,
        "SCAN_TIME_AFTERNOON": req.scan_time_afternoon,
        "AUTO_SCAN_ENABLED": req.auto_scan_enabled,
        "ZALO_SCHOOL_TEMPLATE": req.zalo_school_template,
        "ZALO_CLASS_TEMPLATE": req.zalo_class_template,
        "EMAIL_SUBJECT_TEMPLATE": req.email_subject_template,
        "EMAIL_BODY_TEMPLATE": req.email_body_template,
    }
    save_notification_settings(settings, payload)
    try:
        attendance_scheduler.update_schedule(
            morning_time=req.scan_time_morning,
            afternoon_time=req.scan_time_afternoon,
            enabled=bool(req.auto_scan_enabled)
        )
    except Exception as e:
        logger.warning(f"Lỗi cập nhật lịch trình quét nền: {e}")
    return {"success": True, "message": "Đã lưu cài đặt điều chỉnh thông báo thành công!"}

@router.post("/clear-history")
@router.delete("/clear-history")
async def clear_reports_history(db: Session = Depends(get_db)):
    """Xóa toàn bộ lịch sử điểm danh để làm mới hệ thống (Endpoint dự phòng cho Reports)."""
    from backend.api.routers.attendance import clear_attendance_history
    return await clear_attendance_history(db)

