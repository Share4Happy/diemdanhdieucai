from pydantic import BaseModel
from typing import Optional

class CameraCreateRequest(BaseModel):
    code: str
    name: str
    room_number: Optional[str] = ""
    standard_count: int = 40
    rtsp_url: str
    relay_ip: Optional[str] = ""
    is_active: bool = True

class CameraUpdateRequest(BaseModel):
    name: Optional[str] = None
    room_number: Optional[str] = None
    standard_count: Optional[int] = None
    rtsp_url: Optional[str] = None
    relay_ip: Optional[str] = None
    is_active: Optional[bool] = None

class TestCameraRequest(BaseModel):
    source_url: str
