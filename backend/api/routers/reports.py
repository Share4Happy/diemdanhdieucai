
from datetime import datetime, timedelta
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db
from database.models import AttendanceSession, AttendanceDetail, Classroom
from core.attendance_engine import attendance_engine
from core.timezone_utils import get_now
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
    NotificationAdjustRequest,
    RetentionSettingsRequest,
    CleanupExpiredRequest
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
async def send_zalo_report(req: ZaloTestRequest, db: Session = Depends(get_db)):
    """Gửi tin nhắn báo cáo điểm danh qua Zalo."""
    session_id = req.session_id
    if not session_id:
        latest = (
            db.query(AttendanceSession)
            .filter(~AttendanceSession.session_code.like("%TEST%"), AttendanceSession.total_standard > 0)
            .order_by(AttendanceSession.id.desc())
            .first()
        )
        if not latest:
            latest = (
                db.query(AttendanceSession)
                .filter(~AttendanceSession.session_code.like("%TEST%"))
                .order_by(AttendanceSession.id.desc())
                .first()
            )
        if latest:
            session_id = latest.id

    has_custom_target = bool(
        req.phone or req.test_phone or req.api_key or req.bot_api_key or
        req.bot_id or req.webhook_url or req.access_token
    )
    if session_id and not has_custom_target:
        res = zalo_service.send_attendance_summary(session_id)
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
            recipients=req.recipients,
            session_id=session_id
        )
    return res

@router.get("/latest-summary")
async def get_latest_summary(db: Session = Depends(get_db)):
    """Lấy dữ liệu thống kê của phiên điểm danh thực tế mới nhất cho xem trước tin nhắn."""
    session = (
        db.query(AttendanceSession)
        .filter(~AttendanceSession.session_code.like("%TEST%"), AttendanceSession.total_standard > 0)
        .order_by(AttendanceSession.id.desc())
        .first()
    )
    if not session:
        session = (
            db.query(AttendanceSession)
            .filter(~AttendanceSession.session_code.like("%TEST%"))
            .order_by(AttendanceSession.id.desc())
            .first()
        )
    if session:
        details = (
            db.query(AttendanceDetail)
            .filter(AttendanceDetail.session_id == session.id)
            .order_by(AttendanceDetail.absent_count.desc())
            .all()
        )
        data = zalo_service._collect_message_data(session, details)
        first_detail = details[0] if details else None
        if first_detail and first_detail.classroom:
            data["lop"] = first_detail.classroom.name
            data["phong"] = f"({first_detail.classroom.room_number})" if first_detail.classroom.room_number else ""
        return {"success": True, "data": data, "session_id": session.id}

    classrooms = db.query(Classroom).filter(Classroom.is_active == True).all()
    total_std = sum(c.standard_count for c in classrooms)
    now = get_now()
    first_c = classrooms[0] if classrooms else None
    return {
        "success": True,
        "data": {
            "ngay": now.strftime("%d/%m/%Y"),
            "gio": now.strftime("%H:%M:%S"),
            "tong_lop": str(len(classrooms)),
            "si_so": f"{total_std}/{total_std}",
            "co_mat": str(total_std),
            "vang_mat": "0",
            "ty_le": "100.0%",
            "danh_sach_vang": "🎉 XUẤT SẮC: 100% tất cả các lớp đi học đầy đủ!",
            "lop": first_c.name if first_c else "Lớp 10A1",
            "phong": f"({first_c.room_number})" if first_c and first_c.room_number else "",
        },
        "session_id": None
    }

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
        "schedule_days": getattr(settings, "SCHEDULE_DAYS", "mon-sat"),
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
    schedule_days = req.schedule_days or getattr(settings, "SCHEDULE_DAYS", "mon-sat")
    payload = {
        "ENABLE_ZALO_NOTIFICATION": req.enable_zalo,
        "ENABLE_EMAIL_NOTIFICATION": req.enable_email,
        "NOTIFICATION_SEND_CONDITION": req.send_condition,
        "NOTIFICATION_ALERT_THRESHOLD_PERCENT": req.alert_threshold_percent,
        "NOTIFICATION_ALERT_CLASS_ABSENT": req.alert_class_absent_count,
        "SCAN_TIME_MORNING": req.scan_time_morning,
        "SCAN_TIME_AFTERNOON": req.scan_time_afternoon,
        "SCHEDULE_DAYS": schedule_days,
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
            days=schedule_days,
            enabled=bool(req.auto_scan_enabled)
        )
    except Exception as e:
        logger.warning(f"Lỗi cập nhật lịch trình quét nền: {e}")
    return {"success": True, "message": "Đã lưu cài đặt điều chỉnh thông báo thành công!"}

@router.get("/retention-settings")
async def get_retention_settings(db: Session = Depends(get_db)):
    """Lấy cấu hình thời gian lưu trữ dữ liệu và thông số thống kê CSDL."""
    total_sessions = db.query(AttendanceSession).count()
    total_details = db.query(AttendanceDetail).count()

    excel_files = list(settings.REPORTS_DIR.glob("*.xlsx"))
    total_excel_files = len(excel_files)

    db_file = settings.BASE_DIR / "database" / "attendance.db"
    db_size_mb = 0.0
    if db_file.exists():
        db_size_mb = round(db_file.stat().st_size / (1024 * 1024), 2)

    oldest_session = db.query(AttendanceSession).order_by(AttendanceSession.id.asc()).first()
    newest_session = db.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()

    return {
        "success": True,
        "retention_days": getattr(settings, "DATA_RETENTION_DAYS", 90),
        "auto_cleanup_enabled": getattr(settings, "DATA_AUTO_CLEANUP_ENABLED", True),
        "cleanup_excel_enabled": getattr(settings, "DATA_CLEANUP_EXCEL_ENABLED", True),
        "stats": {
            "total_sessions": total_sessions,
            "total_details": total_details,
            "total_excel_files": total_excel_files,
            "db_size_mb": db_size_mb,
            "oldest_date": oldest_session.scan_date if oldest_session else None,
            "newest_date": newest_session.scan_date if newest_session else None,
        }
    }

@router.post("/retention-settings")
async def save_retention_settings_endpoint(req: RetentionSettingsRequest):
    """Lưu cấu hình thời gian lưu trữ dữ liệu."""
    if req.retention_days < 7:
        raise HTTPException(status_code=400, detail="Thời gian lưu trữ tối thiểu là 7 ngày.")
    if req.retention_days > 1000:
        raise HTTPException(status_code=400, detail="Thời gian lưu trữ tối đa là 1000 ngày.")

    payload = {
        "DATA_RETENTION_DAYS": int(req.retention_days),
        "DATA_AUTO_CLEANUP_ENABLED": bool(req.auto_cleanup_enabled),
        "DATA_CLEANUP_EXCEL_ENABLED": bool(req.cleanup_excel_enabled),
    }
    save_notification_settings(settings, payload)
    return {
        "success": True,
        "message": f"Đã cập nhật thời gian lưu trữ dữ liệu thành {req.retention_days} ngày.",
        "config": payload
    }

@router.post("/cleanup-expired")
async def cleanup_expired_data(req: CleanupExpiredRequest = None, db: Session = Depends(get_db)):
    """Chủ động dọn dẹp các bản ghi điểm danh và file Excel cũ hơn thời hạn quy định."""
    days = req.days if (req and req.days) else getattr(settings, "DATA_RETENTION_DAYS", 90)
    cutoff_date = (get_now() - timedelta(days=days)).strftime("%Y-%m-%d")

    expired_sessions = db.query(AttendanceSession).filter(AttendanceSession.scan_date < cutoff_date).all()
    deleted_sessions_count = len(expired_sessions)
    deleted_details_count = 0

    if expired_sessions:
        session_ids = [s.id for s in expired_sessions]
        for s in expired_sessions:
            for d in s.details:
                deleted_details_count += 1
                if d.raw_image_path and os.path.exists(d.raw_image_path):
                    try:
                        os.remove(d.raw_image_path)
                    except Exception:
                        pass
                if d.annotated_image_path and os.path.exists(d.annotated_image_path):
                    try:
                        os.remove(d.annotated_image_path)
                    except Exception:
                        pass

        db.query(AttendanceDetail).filter(AttendanceDetail.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(AttendanceSession).filter(AttendanceSession.id.in_(session_ids)).delete(synchronize_session=False)
        db.commit()

    deleted_files_count = 0
    if getattr(settings, "DATA_CLEANUP_EXCEL_ENABLED", True):
        cutoff_timestamp = (get_now() - timedelta(days=days)).timestamp()
        for f in settings.REPORTS_DIR.glob("*.xlsx"):
            try:
                if f.stat().st_mtime < cutoff_timestamp:
                    f.unlink(missing_ok=True)
                    deleted_files_count += 1
            except Exception:
                pass

    return {
        "success": True,
        "message": f"Đã dọn dẹp dữ liệu trước ngày {cutoff_date} ({days} ngày trước): {deleted_sessions_count} phiên ({deleted_details_count} bản ghi) và {deleted_files_count} file Excel.",
        "cutoff_date": cutoff_date,
        "deleted_sessions": deleted_sessions_count,
        "deleted_details": deleted_details_count,
        "deleted_excel_files": deleted_files_count
    }

@router.post("/clear-history")
@router.delete("/clear-history")
async def clear_reports_history(db: Session = Depends(get_db)):
    """Xóa toàn bộ lịch sử điểm danh để làm mới hệ thống (Endpoint dự phòng cho Reports)."""
    from backend.api.routers.attendance import clear_attendance_history
    return await clear_attendance_history(db)


