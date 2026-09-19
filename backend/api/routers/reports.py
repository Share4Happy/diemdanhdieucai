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
from backend.schemas.report_schemas import SendEmailRequest, ZaloTestRequest, ZaloConfigSaveRequest

router = APIRouter(prefix="/reports", tags=["Reports"])

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
        res = zalo_service.send_test_message(
            target_type=req.target_type or "WEBHOOK",
            webhook_url=req.webhook_url,
            access_token=req.access_token,
            user_id=req.user_id
        )
    return res

@router.get("/zalo-status")
async def get_zalo_status():
    """Lấy trạng thái cấu hình dịch vụ Zalo."""
    return zalo_service.get_status()

@router.post("/save-zalo-config")
async def save_zalo_config(req: ZaloConfigSaveRequest):
    """Lưu cấu hình Zalo vào bộ nhớ hệ thống."""
    settings.ENABLE_ZALO_NOTIFICATION = req.enabled
    settings.ZALO_NOTIFICATION_TYPE = req.notification_type
    if req.webhook_url is not None:
        settings.ZALO_WEBHOOK_URL = req.webhook_url.strip()
    if req.access_token is not None:
        settings.ZALO_OA_ACCESS_TOKEN = req.access_token.strip()
    if req.recipient_user_id is not None:
        settings.ZALO_RECIPIENT_USER_ID = req.recipient_user_id.strip()
    return {"success": True, "message": "Đã cập nhật cấu hình Zalo thành công!"}
