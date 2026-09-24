from pydantic import BaseModel
from typing import List, Optional

class ROISaveRequest(BaseModel):
    green_zone: Optional[List[List[int]]] = []
    red_zone: Optional[List[List[int]]] = []
    image_width: int = 1080
    image_height: int = 1024
