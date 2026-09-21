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
    channel_number: Optional[int] = None

class TestCameraRequest(BaseModel):
    source_url: str
    trigger_signal: Optional[bool] = False
    relay_ip: Optional[str] = ""

class TestCameraIRRequest(BaseModel):
    mode: Optional[str] = "IR_ON"
    duration_seconds: Optional[int] = 4

class NVRProbeRequest(BaseModel):
    ip_address: str = "192.168.10.200"
    rtsp_port: int = 554
    username: str = "admin"
    password: str = "Lhu@2025"
    brand: str = "DAHUA"
    channels_count: int = 30
    naming_mode: str = "DEFAULT_30_CLASSES"
    custom_pattern: Optional[str] = ""

class NVRChannelItem(BaseModel):
    channel: int
    code: str
    name: str
    room_number: Optional[str] = ""
    standard_count: int = 40
    rtsp_url: str
    is_online: Optional[bool] = True
    is_selected: Optional[bool] = True
    thumbnail: Optional[str] = ""

class NVRBatchImportRequest(BaseModel):
    nvr_name: Optional[str] = "Đầu Ghi NVR Trường THPT Điều Cải"
    ip_address: str = "192.168.10.200"
    rtsp_port: int = 554
    http_port: Optional[int] = 80
    username: str = "admin"
    password: str = "Lhu@2025"
    brand: str = "DAHUA"
    channels_count: int = 30
    custom_pattern: Optional[str] = ""
    replace_existing: bool = True
    channels: list[NVRChannelItem]
