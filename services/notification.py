import os
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional

from config.settings import settings
from config.logging_config import logger
from database.db_session import SessionLocal
from database.models import AttendanceSession
from services.zalo_service import zalo_service

class NotificationService:
    """
    Module phân phối báo cáo:
    1. Tự động lưu file Excel vào thư mục dùng chung nội bộ.
    2. Tự động gửi thông báo tóm tắt sĩ số qua ZALO cho BGH.
    3. Gửi email trực tiếp kèm file Excel cho Hiệu trưởng ngay sau khi hoàn tất điểm danh.
    """

    def send_attendance_report(self, session_id: int, excel_path: Path) -> bool:
        """Thực hiện lưu trữ nội bộ, gửi Zalo và gửi email cho Ban Giám hiệu."""
        db = SessionLocal()
        session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
        db.close()

        if not session or not excel_path or not excel_path.exists():
            logger.warning("Không đủ thông tin để gửi báo cáo!")
            return False

        # 1. Lưu bản sao vào thư mục nội bộ cố định "Báo cáo mới nhất"
        try:
            latest_dir = settings.REPORTS_DIR / "latest"
            latest_dir.mkdir(parents=True, exist_ok=True)
            latest_copy = latest_dir / "BaoCaoDiemDanh_MoiNhat.xlsx"
            shutil.copy2(str(excel_path), str(latest_copy))
            logger.info(f"Đã lưu bản sao báo cáo nội bộ tại: {latest_copy}")
        except Exception as e:
            logger.error(f"Lỗi sao chép báo cáo nội bộ: {e}")

        # 2. Tự động gửi thông báo sĩ số tức thì qua Zalo
        try:
            zalo_res = zalo_service.send_attendance_summary(session_id)
            logger.info(f"Kết quả gửi tin nhắn Zalo: {zalo_res.get('message')}")
        except Exception as e:
            logger.error(f"Lỗi gửi thông báo Zalo: {e}")

        # 3. Gửi email trực tiếp đến Hiệu trưởng
        if not settings.ENABLE_EMAIL_NOTIFICATION or not settings.SMTP_PASSWORD:
            logger.info(
                f"[NOTIFICATION-LOG]: File Excel đã sẵn sàng tại {excel_path.name}. "
                f"(Email tự động đang ở chế độ chờ cấu hình SMTP mật khẩu ứng dụng)."
            )
            return True

        try:
            logger.info(f"Đang gửi email báo cáo điểm danh tới Hiệu trưởng ({settings.PRINCIPAL_EMAIL})...")
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USER
            msg["To"] = settings.PRINCIPAL_EMAIL
            msg["Subject"] = f"[ĐIỂM DANH SĨ SỐ] Báo cáo ngày {session.scan_date} - THPT Điều Cải"

            body = f"""
Kính gửi Ban Giám hiệu Trường THPT Điều Cải,

Hệ thống Camera AI đã hoàn tất quy trình quét điểm danh tự động lúc {session.scan_time} ngày {session.scan_date}.

THỐNG KÊ TỔNG QUAN:
- Tổng số lớp học: {session.total_classes} lớp
- Tổng sĩ số toàn trường: {session.total_standard} học sinh
- Số học sinh hiện diện: {session.total_present} học sinh
- Số học sinh vắng mặt: {session.total_absent} học sinh
- Tỷ lệ chuyên cần: {(session.total_present / session.total_standard * 100):.1f}%

Chi tiết sĩ số của từng lớp và ảnh chụp đối chứng được đính kèm trong file Excel bên dưới.

Trân trọng,
Hệ Thống Điểm Danh Tự Động AI
            """
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Đính kèm file Excel
            with open(str(excel_path), "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={excel_path.name}",
            )
            msg.attach(part)

            # Kết nối SMTP
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()

            logger.info(f"Đã gửi thành công email báo cáo tới {settings.PRINCIPAL_EMAIL}")
            return True

        except Exception as e:
            logger.error(f"Lỗi khi gửi email báo cáo: {e}")
            return False

    def send_test_email(self, to_email: str = None) -> dict:
        """Gửi email thử nghiệm kèm file báo cáo mới nhất."""
        if not to_email:
            to_email = settings.PRINCIPAL_EMAIL

        latest_report = settings.REPORTS_DIR / "latest" / "BaoCaoDiemDanh_MoiNhat.xlsx"
        if not latest_report.exists():
            # Thử tìm file bất kỳ trong storage/reports
            existing = list(settings.REPORTS_DIR.glob("**/*.xlsx"))
            if existing:
                latest_report = existing[0]

        if not settings.SMTP_PASSWORD:
            return {
                "success": False,
                "message": "Chưa cấu hình Mật khẩu Ứng dụng SMTP trong cài đặt hệ thống."
            }

        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USER
            msg["To"] = to_email
            msg["Subject"] = "[TEST] Thử nghiệm hệ thống gửi email báo cáo điểm danh - THPT Điều Cải"
            body = f"Kính gửi Ban Giám hiệu,\n\nĐây là email kiểm tra tính năng tự động gửi báo cáo điểm danh từ Hệ Thống AI Camera.\n\nNgười nhận: {to_email}\nTrạng thái: Hoạt động tốt."
            msg.attach(MIMEText(body, "plain", "utf-8"))

            if latest_report.exists():
                with open(str(latest_report), "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={latest_report.name}")
                msg.attach(part)

            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            return {"success": True, "message": f"Đã gửi email thử nghiệm thành công tới {to_email}"}
        except Exception as e:
            return {"success": False, "message": f"Lỗi gửi email: {str(e)}"}

    def get_status(self) -> dict:
        latest_file = settings.REPORTS_DIR / "latest" / "BaoCaoDiemDanh_MoiNhat.xlsx"
        return {
            "internal_folder": str(settings.REPORTS_DIR),
            "latest_copy_exists": latest_file.exists(),
            "latest_copy_path": str(latest_file) if latest_file.exists() else "",
            "principal_email": settings.PRINCIPAL_EMAIL,
            "smtp_configured": bool(settings.SMTP_PASSWORD),
            "email_enabled": settings.ENABLE_EMAIL_NOTIFICATION
        }

notification_service = NotificationService()

