from pydantic import BaseModel
from typing import Optional

class SendEmailRequest(BaseModel):
    email: Optional[str] = None

class EmailConfigSaveRequest(BaseModel):
    principal_email: str

class ZaloTestRequest(BaseModel):
    target_type: Optional[str] = None
    notification_type: Optional[str] = None
    webhook_url: Optional[str] = None
    access_token: Optional[str] = None
    user_id: Optional[str] = None
    recipient_user_id: Optional[str] = None
    phone: Optional[str] = None
    test_phone: Optional[str] = None
    bot_id: Optional[str] = None
    api_key: Optional[str] = None
    bot_api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    bot_api_base_url: Optional[str] = None
    recipients: Optional[list] = None
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

class NotificationAdjustRequest(BaseModel):
    enable_zalo: Optional[bool] = True
    enable_email: Optional[bool] = False
    send_condition: Optional[str] = "always"  # "always" | "has_absent"
    alert_threshold_percent: Optional[float] = 10.0
    alert_class_absent_count: Optional[int] = 3
    scan_time_morning: Optional[str] = "06:45"
    scan_time_afternoon: Optional[str] = "12:45"
    auto_scan_enabled: Optional[bool] = True
    zalo_school_template: Optional[str] = ""
    zalo_class_template: Optional[str] = ""
    email_subject_template: Optional[str] = ""
    email_body_template: Optional[str] = ""

