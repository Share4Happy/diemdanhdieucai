import json
import requests
from typing import Dict, Any, Optional
from pathlib import Path

from config.settings import settings
from config.logging_config import logger
from database.db_session import SessionLocal
from database.models import AttendanceSession, AttendanceDetail, Classroom

class ZaloNotificationService:
    """
    Module phân phối thông báo điểm danh qua ứng dụng ZALO:
    1. Hỗ trợ gửi tin nhắn tóm tắt qua Zalo Webhook (Zalo Bot / Nhóm Zalo BGH)
    2. Hỗ trợ gửi tin nhắn qua Zalo Official Account (OA) OpenAPI (CS/ZNS) tới số điện thoại / User ID
    """

    def __init__(self):
        self.timeout = 8

    def format_attendance_message(self, session_id: int) -> str:
        """Định dạng bản tin tóm tắt kết quả điểm danh cho tin nhắn Zalo."""
        db = SessionLocal()
        try:
            session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
            if not session:
                return "Không tìm thấy thông tin phiên điểm danh."

            details = (
                db.query(AttendanceDetail)
                .filter(AttendanceDetail.session_id == session.id)
                .order_by(AttendanceDetail.absent_count.desc())
                .all()
            )

            total_std = session.total_standard or sum(d.standard_count for d in details)
            total_pre = session.total_present or sum(d.present_count for d in details)
            total_abs = session.total_absent or sum(d.absent_count for d in details)
            rate = (total_pre / total_std * 100) if total_std > 0 else 0.0

            lines = [
                "🔔 [THPT ĐIỀU CẢI] BÁO CÁO ĐIỂM DANH SĨ SỐ ĐẦU GIỜ SÁNG",
                f"📅 Ngày quét: {session.scan_date} | Giờ: {session.scan_time}",
                f"🏫 Tổng số lớp: {session.total_classes} lớp",
                f"👥 Sĩ số toàn trường: {total_pre}/{total_std} học sinh",
                f"✅ Có mặt: {total_pre} | ❌ Vắng mặt: {total_abs}",
                f"📊 Tỷ lệ chuyên cần: {rate:.1f}%",
                ""
            ]

            absent_classes = [d for d in details if d.absent_count > 0]
            if absent_classes:
                lines.append("⚠️ DANH SÁCH LỚP CÓ HỌC SINH VẮNG:")
                for d in absent_classes:
                    cname = d.classroom.name if d.classroom else f"Lớp {d.classroom_id}"
                    room = f" ({d.classroom.room_number})" if d.classroom and d.classroom.room_number else ""
                    lines.append(f"• {cname}{room}: Vắng {d.absent_count} em (Hiện diện: {d.present_count}/{d.standard_count})")
            else:
                lines.append("🎉 XUẤT SẮC: 100% tất cả các lớp đi học đầy đủ!")

            lines.append("")
            lines.append("📂 File báo cáo Excel & ảnh đối chứng AI đã lưu trên hệ thống máy chủ.")
            return "\n".join(lines)
        finally:
            db.close()

    def send_via_webhook(self, message: str, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """Gửi tin nhắn qua Webhook URL của Zalo Bot hoặc dịch vụ webhook trung gian."""
        url = webhook_url or settings.ZALO_WEBHOOK_URL
        if not url:
            return {"success": False, "message": "Chưa cấu hình ZALO_WEBHOOK_URL."}

        try:
            payload = {
                "text": message,
                "msg_type": "text",
                "sender": "AI Camera THPT Điều Cải"
            }
            res = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            if res.status_code in [200, 201, 204]:
                logger.info(f"Đã gửi thành công tin nhắn Zalo qua Webhook!")
                return {"success": True, "message": "Đã gửi tin nhắn Zalo qua Webhook thành công!"}
            else:
                return {
                    "success": False,
                    "message": f"Webhook trả về lỗi HTTP {res.status_code}: {res.text[:120]}"
                }
        except Exception as e:
            logger.error(f"Lỗi gửi Zalo Webhook: {e}")
            return {"success": False, "message": f"Lỗi kết nối Webhook: {str(e)}"}

    def send_via_oa_api(
        self,
        message: str,
        access_token: Optional[str] = None,
        recipient_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Gửi tin nhắn qua Zalo Official Account OpenAPI (CS/Chăm sóc khách hàng)."""
        token = access_token or settings.ZALO_OA_ACCESS_TOKEN
        uid = recipient_user_id or settings.ZALO_RECIPIENT_USER_ID

        if not token or not uid:
            return {"success": False, "message": "Chưa cấu hình Access Token hoặc Recipient User ID của Zalo OA."}

        try:
            url = "https://openapi.zalo.me/v3.0/oa/message/cs"
            headers = {
                "access_token": token,
                "Content-Type": "application/json"
            }
            payload = {
                "recipient": {"user_id": uid},
                "message": {"text": message}
            }
            res = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            data = res.json() if res.content else {}
            if data.get("error") == 0:
                logger.info(f"Đã gửi thành công tin nhắn Zalo OA tới user {uid}!")
                return {"success": True, "message": f"Đã gửi tin nhắn Zalo OA thành công tới User ID: {uid}"}
            else:
                return {
                    "success": False,
                    "message": f"Zalo OA API trả về lỗi: {data.get('message', 'Unknown error')} (Mã: {data.get('error')})"
                }
        except Exception as e:
            logger.error(f"Lỗi gửi Zalo OA API: {e}")
            return {"success": False, "message": f"Lỗi kết nối Zalo OA API: {str(e)}"}

    def send_attendance_summary(self, session_id: int) -> Dict[str, Any]:
        """Tự động tổng hợp và gửi tin nhắn điểm danh sau khi quét hoàn tất."""
        if not settings.ENABLE_ZALO_NOTIFICATION:
            logger.info("[ZALO-LOG] Tính năng gửi Zalo đang tắt trong cấu hình.")
            return {"success": False, "message": "Tính năng gửi Zalo đang tắt."}

        message = self.format_attendance_message(session_id)
        
        # Kiểm tra chế độ gửi
        if settings.ZALO_NOTIFICATION_TYPE.upper() == "OA_API" and settings.ZALO_OA_ACCESS_TOKEN:
            return self.send_via_oa_api(message)
        elif settings.ZALO_WEBHOOK_URL:
            return self.send_via_webhook(message)
        else:
            logger.info(
                f"[ZALO-LOG-SIMULATION]: Tin nhắn Zalo đã sẵn sàng:\n{message}\n"
                f"(Chưa cấu hình Webhook URL hoặc OA Token, đã ghi vào log hệ thống)."
            )
            return {
                "success": True,
                "message": "Đã tạo nội dung tin nhắn Zalo (Chế độ mô phỏng / Chờ cấu hình Webhook URL).",
                "preview_text": message
            }

    def send_test_message(
        self,
        target_type: str = "WEBHOOK",
        webhook_url: Optional[str] = None,
        access_token: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Gửi tin nhắn thử nghiệm để kiểm tra thông kết nối Zalo."""
        test_msg = (
            "🔔 [TEST] THỬ NGHIỆM KẾT NỐI HỆ THỐNG ĐIỂM DANH AI - THPT ĐIỀU CẢI\n"
            "Tin nhắn này xác nhận tính năng gửi thông báo tự động qua Zalo đang hoạt động tốt!\n"
            "Hệ thống sẽ tự động gửi báo cáo sĩ số 30 lớp học vào 06:48 mỗi sáng."
        )

        if target_type.upper() == "OA_API":
            return self.send_via_oa_api(test_msg, access_token=access_token, recipient_user_id=user_id)
        else:
            return self.send_via_webhook(test_msg, webhook_url=webhook_url)

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": settings.ENABLE_ZALO_NOTIFICATION,
            "notification_type": settings.ZALO_NOTIFICATION_TYPE,
            "webhook_configured": bool(settings.ZALO_WEBHOOK_URL),
            "oa_configured": bool(settings.ZALO_OA_ACCESS_TOKEN and settings.ZALO_RECIPIENT_USER_ID),
            "recipient_user_id": settings.ZALO_RECIPIENT_USER_ID,
            "webhook_url_masked": (
                settings.ZALO_WEBHOOK_URL[:18] + "..." + settings.ZALO_WEBHOOK_URL[-8:]
                if len(settings.ZALO_WEBHOOK_URL) > 26 else settings.ZALO_WEBHOOK_URL
            )
        }

zalo_service = ZaloNotificationService()
