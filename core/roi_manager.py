import cv2
import numpy as np
from typing import List, Tuple, Dict, Any

class ROIManager:
    """
    Quản lý vùng không gian (Spatial ROI) cho lớp học:
    - Green Zone: Vùng đa giác bao quanh bàn học sinh (Khu vực nhận diện).
    - Mặc định: Mọi khu vực nằm ngoài Green Zone (bục giảng, ngoài phòng...) tự động bị bỏ qua.
    """

    @staticmethod
    def points_to_np(points: List[List[int]]) -> np.ndarray:
        """Chuyển đổi danh sách tọa độ [[x, y], ...] thành np.int32 array cho OpenCV."""
        if not points:
            return np.array([], dtype=np.int32)
        return np.array(points, dtype=np.int32).reshape((-1, 1, 2))

    @staticmethod
    def scale_polygon(points: List[List[int]], from_w: int, from_h: int, to_w: int, to_h: int) -> List[List[int]]:
        """Tự động co dãn tỉ lệ tọa độ đa giác từ độ phân giải cũ sang độ phân giải mới."""
        if not points or not from_w or not from_h or (from_w == to_w and from_h == to_h):
            return points
        sx = to_w / float(from_w)
        sy = to_h / float(from_h)
        return [[int(round(p[0] * sx)), int(round(p[1] * sy))] for p in points]

    @classmethod
    def create_spatial_mask(
        cls,
        image_shape: Tuple[int, int],
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> np.ndarray:
        """
        Tạo mặt nạ nhị phân (Binary Mask) kích thước (H, W):
        - Giá trị 255 (Trắng): Khu vực bên trong Green Zone (Bàn học sinh / Cần đếm).
        - Giá trị 0 (Đen): Mọi khu vực nằm ngoài Green Zone mặc định bị loại trừ / bỏ qua.
        """
        h, w = image_shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        # 1. Bật vùng Green Zone (Khu vực nhận diện / Bàn học sinh)
        if green_zone and len(green_zone) >= 3:
            green_poly = cls.points_to_np(green_zone)
            cv2.fillPoly(mask, [green_poly], 255)
        else:
            # Nếu chưa vẽ Green Zone, mặc định quét toàn bộ ảnh
            mask[:] = 255

        return mask

    @classmethod
    def apply_spatial_mask(
        cls,
        image: np.ndarray,
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> np.ndarray:
        """
        Bôi đen toàn bộ các khu vực nằm ngoài đa giác Green Zone.
        AI sẽ chỉ quét và đếm số lượng xuất hiện trong vùng sáng còn lại.
        """
        mask = cls.create_spatial_mask(image.shape[:2], red_zone, green_zone)
        # Tạo ảnh 3 kênh từ mask
        mask_3ch = cv2.merge([mask, mask, mask])
        # Áp dụng toán tử AND
        masked_image = cv2.bitwise_and(image, mask_3ch)
        return masked_image

    @classmethod
    def is_point_in_roi(
        cls,
        point: Tuple[float, float],
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> bool:
        """
        Kiểm tra tọa độ tâm điểm (x, y) của đầu người:
        - Phải nằm TRONG Green Zone (Phần LẤY - có dung sai sát mép viền 10px).
        - Mọi điểm nằm ngoài Green Zone mặc định bị bỏ qua (False).
        """
        px, py = float(point[0]), float(point[1])

        # Kiểm tra Green Zone (Khu vực nhận diện / Bàn học sinh): Phải nằm bên trong hoặc sát viền mép (dung sai 10px)
        if green_zone and len(green_zone) >= 3:
            green_poly = cls.points_to_np(green_zone)
            dist_green = cv2.pointPolygonTest(green_poly, (px, py), True)
            if dist_green < -10.0:
                # Nằm ngoài vùng xanh -> Tự động bỏ qua
                return False

        return True

    @classmethod
    def filter_detections(
        cls,
        boxes: List[Dict[str, Any]],
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Phân loại danh sách bounding boxes:
        - valid_boxes: Bounding boxes hợp lệ trong vùng bàn học sinh (Green Zone).
        - ignored_boxes: Bounding boxes nằm ngoài Green Zone (mặc định tự động bỏ qua).
        """
        valid_boxes = []
        ignored_boxes = []

        for box in boxes:
            # Ưu tiên sử dụng centroid đã tính chính xác từ StudentDetector (tâm đầu học sinh)
            if "centroid" in box and box["centroid"] is not None:
                cx, cy = box["centroid"]
            else:
                x1, y1, x2, y2 = box["bbox"]
                cx = (x1 + x2) / 2.0
                cy = y1 + (y2 - y1) * 0.35 # Trọng tâm đầu

            if cls.is_point_in_roi((cx, cy), red_zone, green_zone):
                box["centroid"] = (cx, cy)
                valid_boxes.append(box)
            else:
                box["centroid"] = (cx, cy)
                ignored_boxes.append(box)

        return valid_boxes, ignored_boxes

    @classmethod
    def draw_roi_overlays(
        cls,
        image: np.ndarray,
        red_zone: List[List[int]] = None,
        green_zone: List[List[int]] = None,
        alpha: float = 0.22
    ) -> np.ndarray:
        """Vẽ lớp phủ mờ trực quan hiển thị Vùng Xanh (Green Zone) nhận diện bàn học sinh."""
        overlay = image.copy()
        output = image.copy()

        # Vẽ Green Zone (Khu vực nhận diện - Bàn học - Đường viền xanh lá tinh tế + phủ màu mờ nhẹ)
        if green_zone and len(green_zone) >= 3:
            green_poly = cls.points_to_np(green_zone)
            cv2.fillPoly(overlay, [green_poly], (40, 180, 40))
            cv2.polylines(output, [green_poly], True, (0, 215, 0), 2, cv2.LINE_AA)

        # Trộn mờ tinh tế
        cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)
        return output
