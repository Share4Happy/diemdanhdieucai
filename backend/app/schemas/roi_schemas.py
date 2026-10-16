from pydantic import BaseModel
from typing import List, Optional

class ROISaveRequest(BaseModel):
    green_zone: Optional[List[List[int]]] = []
    red_zone: Optional[List[List[int]]] = []
    image_width: int = 1920
    image_height: int = 1080

class ROIApplyAllRequest(BaseModel):
    source_classroom_id: Optional[int] = None
    green_zone: Optional[List[List[int]]] = []
    red_zone: Optional[List[List[int]]] = []
    image_width: int = 1920
    image_height: int = 1080
    target_classroom_ids: Optional[List[int]] = None
