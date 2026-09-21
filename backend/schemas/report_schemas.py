from pydantic import BaseModel
from typing import Optional

class SendEmailRequest(BaseModel):
    email: Optional[str] = None

class ZaloTestRequest(BaseModel):
    target_type: Optional[str] = "WEBHOOK"
    webhook_url: Optional[str] = None
    access_token: Optional[str] = None
    user_id: Optional[str] = None
    phone: Optional[str] = None
    bot_id: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    session_id: Optional[int] = None

class ZaloConfigSaveRequest(BaseModel):
    enabled: bool
    notification_type: str
    webhook_url: Optional[str] = ""
    access_token: Optional[str] = ""
    recipient_user_id: Optional[str] = ""
    bot_api_base_url: Optional[str] = ""
    bot_id: Optional[str] = ""
    bot_api_key: Optional[str] = ""
    recipient_phones: Optional[str] = ""       # Legacy: chỉ dành cho nhóm Ban Giám Hiệu
    recipients_json: Optional[str] = ""        # [{"phone","role","class_code"}]: người nhận theo vai trò
