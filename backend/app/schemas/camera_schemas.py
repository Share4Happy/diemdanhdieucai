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
    ip_address: str = "192.168.1.200"
    rtsp_port: int = 554
    username: str = "admin"
    password: str = ""
    brand: str = "HIKVISION"
    channels_count: int = 30
    start_channel: int = 1
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
    nvr_name: Optional[str] = "Đầu Ghi NVR Hikvision THPT Điều Cải"
    ip_address: str = "192.168.1.200"
    rtsp_port: int = 554
    http_port: Optional[int] = 80
    username: str = "admin"
    password: str = ""
    brand: str = "HIKVISION"
    channels_count: int = 30
    start_channel: int = 1
    custom_pattern: Optional[str] = ""
    replace_existing: bool = True
    channels: list[NVRChannelItem]

class SwitchCameraSourceModeRequest(BaseModel):
    mode: str = "REAL_NVR"  # "REAL_NVR" or "MOCK_IMAGE"
    nvr_ip: str = "192.168.1.200"
    nvr_port: int = 554
    nvr_user: str = "admin"
    nvr_pass: str = "Lhu@2025"
    nvr_brand: str = "HIKVISION"
    channel_start: int = 1
    cleanup_mock_images: bool = False
    mock_folder: Optional[str] = "camera"

class InspectFolderRequest(BaseModel):
    folder_path: str = "camera"

class BatchStatusRequest(BaseModel):
    camera_ids: Optional[list[int]] = None
    is_active: bool = True

class ValidateNewCameraRequest(BaseModel):
    source_url: str
    relay_ip: Optional[str] = ""
    red_zone: Optional[list] = None
    green_zone: Optional[list] = None
    standard_count: Optional[int] = 40

class AutoScheduleRequest(BaseModel):
    auto_scan_enabled: Optional[bool] = True
    scan_time_morning: Optional[str] = "06:45"
    scan_time_afternoon: Optional[str] = "12:45"
    afternoon_enabled: Optional[bool] = True
    schedule_days: Optional[str] = "mon-sat"

class SwitchStreamRequest(BaseModel):
    stream_type: str = "main"  # "main" | "sub"

class BatchSwitchStreamRequest(BaseModel):
    stream_type: str = "main"  # "main" | "sub"
    classroom_ids: Optional[list[int]] = None

class StreamPolicyRequest(BaseModel):
    auto_fallback: bool = True
    timeout_seconds: float = 3.5

