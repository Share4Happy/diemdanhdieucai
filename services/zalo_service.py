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
    3. Hỗ trợ gửi tin nhắn batch tới nhiều người lạ qua Zalo Bot Gateway (API Key + Bot ID, resolve SĐT -> UID)
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

    def _parse_bot_recipients(self, recipients=None) -> list:
        """Chuyển danh sách người nhận về dạng [{'phone': '...'}] cho API batch."""
        if recipients is None:
            items = [p.strip() for p in (settings.ZALO_RECIPIENT_PHONES or "").split(",") if p.strip()]
        else:
            items = recipients

        parsed = []
        for r in items:
            if isinstance(r, dict):
                phone = str(r.get("phone", "")).strip()
            else:
                phone = str(r).strip()
            if phone:
                parsed.append({"phone": phone})
        return parsed

    def send_via_bot_api(
        self,
        message: str,
        recipients: Optional[list] = None,
        api_base_url: Optional[str] = None,
        bot_id: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Gửi tin nhắn tới nhiều người lạ qua Zalo Bot Gateway.

        Endpoint: POST /bots/{bot_id}/messages/send-batch (tối đa 10 recipients/lần gọi).
        Nếu danh sách SĐT nhiều hơn 10, hệ thống tự động chia đợt (<=10/lần) và gửi tuần tự cho tới hết.
        - Đợt <= 5 SĐT: gateway xử lý đồng bộ, trả kết quả chi tiết từng recipient
        - Đợt 6-10 SĐT: gateway trả campaign_id (HTTP 202), xử lý nền
        """
        base_url = (api_base_url or settings.ZALO_BOT_API_BASE_URL or "").rstrip("/")
        bot = bot_id or settings.ZALO_BOT_ID
        key = api_key or settings.ZALO_BOT_API_KEY

        if not base_url or not bot or not key:
            return {"success": False, "message": "Chưa cấu hình đầy đủ Zalo Bot API (API Base URL / Bot ID / API Key)."}

        all_recips = self._parse_bot_recipients(recipients)
        if not all_recips:
            return {"success": False, "message": "Chưa có số điện thoại người nhận (ZALO_RECIPIENT_PHONES)."}

        url = f"{base_url}/bots/{bot}/messages/send-batch"
        headers = {"x-api-key": key, "Content-Type": "application/json"}
        logger.info(f"[ZALO-BOT] Gửi batch tin nhắn tới {len(all_recips)} số điện thoại qua Zalo Bot Gateway...")

        # API giới hạn 10 recipient/lần gọi -> tự động chia nhỏ đợt, gửi tuần tự cho tới hết
        chunks = [all_recips[i:i + 10] for i in range(0, len(all_recips), 10)]
        synced_results = []   # kết quả chi tiết từ các đợt đồng bộ (<= 5 SĐT)
        campaign_ids = []     # campaign chạy nền từ các đợt bất đồng bộ (6-10 SĐT)
        errors = []
        accepted_total = 0

        for chunk in chunks:
            payload = {
                "recipients": chunk,
                "content": {"type": "text", "data": {"text": message}},
                "mode": "safe"
            }
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            except requests.exceptions.Timeout:
                errors.append(f"Đợt {len(chunk)} SĐT: timeout sau {self.timeout}s.")
                continue
            except requests.exceptions.ConnectionError as e:
                errors.append(f"Đợt {len(chunk)} SĐT: mất kết nối ({e}).")
                continue
            except requests.exceptions.RequestException as e:
                errors.append(f"Đợt {len(chunk)} SĐT: {e}")
                continue

            try:
                data = res.json() if res.content else {}
            except Exception:
                data = {}

            if res.status_code in [200, 201, 204]:
                chunk_res = self._bot_success_response(data)
                synced_results.append(chunk_res)
                accepted_total += chunk_res.get("accepted", 0)
            elif res.status_code == 202:
                # Batch 6-10 chạy nền: gateway trả campaign_id để poll tiến độ
                cid = data.get("campaign_id") or ""
                campaign_ids.append(cid)
                logger.info(f"[ZALO-BOT] Campaign {cid} đang xử lý nền ({len(chunk)} SĐT).")
            else:
                errors.append(f"Đợt {len(chunk)} SĐT: HTTP {res.status_code} {data.get('message', res.text[:200])}")

        if not synced_results and not campaign_ids:
            return {"success": False, "message": "Không gửi được tin nhắn Zalo Bot: " + "; ".join(errors) or "Lỗi không xác định."}

        # Tổng hợp kết quả toàn bộ danh sách SĐT đã chia đợt
        merged_results = []
        for r in synced_results:
            merged_results.extend(r.get("results") or [])

        msg_parts = [f"Đã gọi Zalo Bot API {len(chunks)} đợt cho {len(all_recips)} SĐT"]
        if merged_results or accepted_total:
            msg_parts.append(f"gửi thành công đồng bộ {accepted_total} SĐT")
        if campaign_ids:
            msg_parts.append(f"{len(campaign_ids)} campaign chạy nền (ID: {', '.join(campaign_ids)})")
        if errors:
            msg_parts.append(f"{len(errors)} đợt lỗi: {'; '.join(errors)}")

        return {
            "success": True,
            "message": ". ".join(msg_parts) + ".",
            "accepted": accepted_total,
            "results": merged_results,
            "campaign_ids": campaign_ids,
            "async": bool(campaign_ids),
            "errors": errors,
            "chunks": len(chunks)
        }

    @staticmethod
    def _bot_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Tổng hợp kết quả phản hồi thành công từ Zalo Bot Gateway."""
        if data.get("success") is False:
            return {"success": False, "message": data.get("message", "Zalo Bot API báo lỗi khi gửi tin nhắn.")}

        results = data.get("results") or []
        accepted = data.get("accepted", len(results))
        failed = [r for r in results if r.get("status") != "success"]
        msg = f"Đã gửi tin nhắn Zalo Bot thành công tới {accepted} số điện thoại."
        if failed:
            msg += f" ({len(failed)} recipient thất bại.)"
        return {
            "success": True,
            "message": msg,
            "accepted": accepted,
            "results": results,
            "status": data.get("status", "completed")
        }

    def send_attendance_summary(self, session_id: int) -> Dict[str, Any]:
        """Tự động tổng hợp và gửi tin nhắn điểm danh sau khi quét hoàn tất."""
        if not settings.ENABLE_ZALO_NOTIFICATION:
            logger.info("[ZALO-LOG] Tính năng gửi Zalo đang tắt trong cấu hình.")
            return {"success": False, "message": "Tính năng gửi Zalo đang tắt."}

        message = self.format_attendance_message(session_id)
        
        # Kiểm tra chế độ gửi
        if settings.ZALO_NOTIFICATION_TYPE.upper() == "BOT_API":
            return self.send_via_bot_api(message)
        elif settings.ZALO_NOTIFICATION_TYPE.upper() == "OA_API" and settings.ZALO_OA_ACCESS_TOKEN:
            return self.send_via_oa_api(message)
        elif settings.ZALO_WEBHOOK_URL:
            return self.send_via_webhook(message)
        else:
            logger.info(
                f"[ZALO-LOG-SIMULATION]: Tin nhắn Zalo đã sẵn sàng:\n{message}\n"
                f"(Chưa cấu hình Webhook URL, OA Token hoặc Zalo Bot Gateway, đã ghi vào log hệ thống)."
            )
            return {
                "success": True,
                "message": "Đã tạo nội dung tin nhắn Zalo (Chế độ mô phỏng / Chờ cấu hình kênh gửi).",
                "preview_text": message
            }

    def send_test_message(
        self,
        target_type: str = "WEBHOOK",
        webhook_url: Optional[str] = None,
        access_token: Optional[str] = None,
        user_id: Optional[str] = None,
        phone: Optional[str] = None,
        bot_id: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Gửi tin nhắn thử nghiệm để kiểm tra thông kết nối Zalo."""
        test_msg = (
            "🔔 [TEST] THỬ NGHIỆM KẾT NỐI HỆ THỐNG ĐIỂM DANH AI - THPT ĐIỀU CẢI\n"
            "Tin nhắn này xác nhận tính năng gửi thông báo tự động qua Zalo đang hoạt động tốt!\n"
            "Hệ thống sẽ tự động gửi báo cáo sĩ số 30 lớp học vào 06:48 mỗi sáng."
        )

        if target_type.upper() == "BOT_API":
            recipients = [{"phone": phone}] if phone else None
            return self.send_via_bot_api(test_msg, recipients=recipients, api_base_url=api_base_url, bot_id=bot_id, api_key=api_key)
        elif target_type.upper() == "OA_API":
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
            ),
            "bot_configured": bool(settings.ZALO_BOT_ID and settings.ZALO_BOT_API_KEY and settings.ZALO_BOT_API_BASE_URL),
            "bot_id": settings.ZALO_BOT_ID,
            "bot_api_base_url": settings.ZALO_BOT_API_BASE_URL,
            "bot_api_key_masked": (
                settings.ZALO_BOT_API_KEY[:4] + "..." + settings.ZALO_BOT_API_KEY[-4:]
                if len(settings.ZALO_BOT_API_KEY) > 8 else settings.ZALO_BOT_API_KEY
            ),
            "recipient_phones": settings.ZALO_RECIPIENT_PHONES
        }

zalo_service = ZaloNotificationService()
