import cv2
import numpy as np
from typing import List, Tuple, Dict, Any

# =============================================================================
# [CẤU HÌNH ROI ĐÃ ĐƯỢC COMMENT LẠI TOÀN BỘ THEO YÊU CẦU NGƯỜI DÙNG]
# Hệ thống chuyển sang dùng thuần túy 100% Endpoint /api/predict (Depth-NMS).
# Không áp dụng Green Zone (bàn học), Red Zone (bục giảng) hay bất kỳ vùng giới hạn nào.
# =============================================================================

class ROIManager:
    """
    [COMMENTED OUT] Quản lý vùng không gian (Spatial ROI) cho lớp học:
    Toàn bộ các quy tắc cắt xén theo Green Zone / Red Zone đã được vô hiệu hóa.
    """

    @staticmethod
    def points_to_np(points: List[List[int]]) -> np.ndarray:
        # if not points:
        #     return np.array([], dtype=np.int32)
        # return np.array(points, dtype=np.int32).reshape((-1, 1, 2))
        return np.array([], dtype=np.int32)

    @staticmethod
    def scale_polygon(points: List[List[int]], from_w: int, from_h: int, to_w: int, to_h: int) -> List[List[int]]:
        # [COMMENTED OUT - Không co dãn hay áp dụng ROI]
        # if not points or not from_w or not from_h or (from_w == to_w and from_h == to_h):
        #     return points
        # sx = to_w / float(from_w)
        # sy = to_h / float(from_h)
        # return [[int(round(p[0] * sx)), int(round(p[1] * sy))] for p in points]
        return points or []

    @classmethod
    def create_spatial_mask(
        cls,
        image_shape: Tuple[int, int],
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> np.ndarray:
        # [COMMENTED OUT - Không che mask, quét toàn bộ bức ảnh]
        # h, w = image_shape[:2]
        # mask = np.zeros((h, w), dtype=np.uint8)
        # if green_zone and len(green_zone) >= 3:
        #     green_poly = cls.points_to_np(green_zone)
        #     cv2.fillPoly(mask, [green_poly], 255)
        # else:
        #     mask[:] = 255
        # return mask
        h, w = image_shape[:2]
        return np.full((h, w), 255, dtype=np.uint8)

    @classmethod
    def apply_spatial_mask(
        cls,
        image: np.ndarray,
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> np.ndarray:
        # [COMMENTED OUT - Giữ nguyên hình ảnh gốc, không che vùng nào]
        # mask = cls.create_spatial_mask(image.shape[:2], red_zone, green_zone)
        # mask_3ch = cv2.merge([mask, mask, mask])
        # masked_image = cv2.bitwise_and(image, mask_3ch)
        # return masked_image
        return image

    @classmethod
    def is_point_in_roi(
        cls,
        point: Tuple[float, float],
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> bool:
        # [COMMENTED OUT - Mọi vị trí trong phòng học đều hợp lệ theo /api/predict]
        # px, py = float(point[0]), float(point[1])
        # if green_zone and len(green_zone) >= 3:
        #     green_poly = cls.points_to_np(green_zone)
        #     dist_green = cv2.pointPolygonTest(green_poly, (px, py), True)
        #     if dist_green < -25.0:
        #         return False
        return True

    @classmethod
    def filter_detections(
        cls,
        boxes: List[Dict[str, Any]],
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        # [COMMENTED OUT - Giữ lại 100% các học sinh được nhận diện, không loại ai]
        # valid_boxes = []
        # ignored_boxes = []
        # for box in boxes:
        #     if "centroid" in box and box["centroid"] is not None:
        #         cx, cy = box["centroid"]
        #     else:
        #         x1, y1, x2, y2 = box["bbox"]
        #         cx = (x1 + x2) / 2.0
        #         cy = y1 + (y2 - y1) * 0.35
        #     if cls.is_point_in_roi((cx, cy), red_zone, green_zone):
        #         box["centroid"] = (cx, cy)
        #         valid_boxes.append(box)
        #     else:
        #         box["centroid"] = (cx, cy)
        #         ignored_boxes.append(box)
        # return valid_boxes, ignored_boxes
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
        # [COMMENTED OUT - Không vẽ đa giác Green Zone hay Red Zone đè lên ảnh]
        # overlay = image.copy()
        # output = image.copy()
        # if green_zone and len(green_zone) >= 3:
        #     green_poly = cls.points_to_np(green_zone)
        #     cv2.fillPoly(overlay, [green_poly], (40, 180, 40))
        #     cv2.polylines(output, [green_poly], True, (0, 215, 0), 2, cv2.LINE_AA)
        # if red_zone and len(red_zone) >= 3:
        #     red_poly = cls.points_to_np(red_zone)
        #     cv2.fillPoly(overlay, [red_poly], (30, 30, 200))
        #     cv2.polylines(output, [red_poly], True, (0, 0, 235), 2, cv2.LINE_AA)
        # cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)
        # return output
        return image

roi_manager = ROIManager()
