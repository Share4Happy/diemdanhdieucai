from pydantic import BaseModel
from typing import List, Optional

class ROISaveRequest(BaseModel):
    red_zone: List[List[int]]
    green_zone: Optional[List[List[int]]] = []
    image_width: int = 1080
    image_height: int = 1024
