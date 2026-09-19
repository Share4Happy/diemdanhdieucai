from pydantic import BaseModel
from typing import Optional

class SendEmailRequest(BaseModel):
    email: Optional[str] = None

class ZaloTestRequest(BaseModel):
    target_type: Optional[str] = "WEBHOOK"
    webhook_url: Optional[str] = None
    access_token: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[int] = None

class ZaloConfigSaveRequest(BaseModel):
    enabled: bool
    notification_type: str
    webhook_url: Optional[str] = ""
    access_token: Optional[str] = ""
    recipient_user_id: Optional[str] = ""
