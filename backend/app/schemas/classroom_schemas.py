from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ClassroomCreateRequest(BaseModel):
    name: str = Field(..., description="Tên lớp học, ví dụ: 10A1 hoặc Lớp 10A1")
    code: Optional[str] = Field(None, description="Mã lớp định danh duy nhất (tự sinh nếu để trống)")
    room_number: Optional[str] = Field("", description="Số phòng học, ví dụ: Phòng 21")
    standard_count: int = Field(40, ge=1, le=100, description="Sĩ số chuẩn của lớp")
    rtsp_url: Optional[str] = Field("", description="Luồng RTSP camera hoặc đường dẫn nguồn")
    channel_number: Optional[int] = Field(None, description="Kênh camera NVR (1-30)")
    nvr_id: Optional[int] = Field(None, description="ID của đầu ghi NVR liên kết")
    relay_ip: Optional[str] = Field("", description="Địa chỉ IP Relay đèn LED phòng học")
    is_active: bool = Field(True, description="Trạng thái hoạt động")

class ClassroomUpdateRequest(BaseModel):
    name: Optional[str] = None
    room_number: Optional[str] = None
    standard_count: Optional[int] = Field(None, ge=1, le=100)
    rtsp_url: Optional[str] = None
    channel_number: Optional[int] = None
    nvr_id: Optional[int] = None
    relay_ip: Optional[str] = None
    is_active: Optional[bool] = None

class ClassroomBatchItem(BaseModel):
    name: str
    code: Optional[str] = None
    room_number: Optional[str] = ""
    standard_count: int = 40
    channel_number: Optional[int] = None
    rtsp_url: Optional[str] = ""
    relay_ip: Optional[str] = ""
    is_active: bool = True

class ClassroomBatchImportRequest(BaseModel):
    items: List[ClassroomBatchItem]
    update_existing: bool = True

class ClassroomQuickUpdateCount(BaseModel):
    standard_count: int = Field(..., ge=1, le=100)
