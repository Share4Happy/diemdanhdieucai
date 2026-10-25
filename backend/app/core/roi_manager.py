import cv2
import numpy as np
from typing import List, Tuple, Dict, Any

class ROIManager:
    """
    Bộ tương thích ngược cho cấu hình ROI (Spatial ROI):
    Hệ thống điểm danh hiện tại sử dụng thuần túy 100% mô hình AI qua /api/predict (Depth-NMS).
    Mọi vị trí trong phòng học đều được quét toàn diện, không áp dụng cắt xén mặt nạ.
    """

    @staticmethod
    def points_to_np(points: List[List[int]]) -> np.ndarray:
        if not points:
            return np.array([], dtype=np.int32)
        return np.array(points, dtype=np.int32).reshape((-1, 1, 2))

    @staticmethod
    def scale_polygon(points: List[List[int]], from_w: int, from_h: int, to_w: int, to_h: int) -> List[List[int]]:
        return points or []

    @classmethod
    def create_spatial_mask(
        cls,
        image_shape: Tuple[int, int],
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> np.ndarray:
        h, w = image_shape[:2]
        return np.full((h, w), 255, dtype=np.uint8)

    @classmethod
    def apply_spatial_mask(
        cls,
        image: np.ndarray,
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> np.ndarray:
        return image

    @classmethod
    def is_point_in_roi(
        cls,
        point: Tuple[float, float],
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> bool:
        return True

    @classmethod
    def filter_detections(
        cls,
        boxes: List[Dict[str, Any]],
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        for b in boxes:
            if "centroid" not in b or b["centroid"] is None:
                x1, y1, x2, y2 = b["bbox"]
                b["centroid"] = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        return boxes, []

    @classmethod
    def draw_roi_overlays(
        cls,
        image: np.ndarray,
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None,
        alpha: float = 0.22
    ) -> np.ndarray:
        return image

roi_manager = ROIManager()
