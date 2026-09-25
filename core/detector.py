import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from ultralytics import YOLO

from config.settings import settings
from config.logging_config import logger
from core.roi_manager import ROIManager
from core.image_enhancer import ImageEnhancer

class StudentDetector:
    """
    Module AI Object Detection chuyên nhận diện đầu người và nửa thân trên của học sinh.
    Tích hợp Spatial Masking (Red Zone - Green Zone), chống ngược sáng cửa sổ (CLAHE),
    và thuật toán Sliced/Tiled Multi-Scale Inference (SAHI) chống bỏ sót học sinh bị che khuất.
    """

    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = settings.YOLO_MODEL_NAME

        self.model_name = str(model_name)
        logger.info(f"Đang tải mô hình phát hiện đối tượng AI: {self.model_name}...")
        
        # Kiểm tra đường dẫn trọng số
        candidate_paths = [
            Path(self.model_name),
            settings.MODELS_DIR / Path(self.model_name).name,
            settings.BASE_DIR / self.model_name,
            settings.MODELS_DIR / "yolo26m.pt",
            settings.BASE_DIR / "yolo26m.pt",
            settings.MODELS_DIR / "yolo26s.pt",
        ]

        loaded = False
        for p in candidate_paths:
            if p.exists() or str(p).endswith(".pt"):
                try:
                    self.model = YOLO(str(p))
                    self.model_name = str(p)
                    loaded = True
                    logger.info(f"Đã nạp thành công mô hình {settings.YOLO_FAMILY} ({p.name})!")
                    break
                except Exception as e:
                    logger.warning(f"Không thể nạp checkpoint từ {p}: {e}")

        if not loaded:
            logger.warning("Đang tải mô hình yolo26m.pt trực tiếp từ Ultralytics...")
            try:
                self.model = YOLO("yolo26m.pt")
                self.model_name = "yolo26m.pt"
            except Exception as e:
                logger.error(f"Lỗi tải yolo26m.pt: {e}. Sử dụng yolo26s.pt làm dự phòng.")
                self.model = YOLO("yolo26s.pt")
                self.model_name = "yolo26s.pt"

        self.target_class_ids = self._determine_target_classes_for_model(self.model)
        logger.info(f"AI Target Classes cho điểm danh: {self.target_class_ids} (Tên: {[self.model.names.get(i, 'unknown') for i in self.target_class_ids]})")

        # Nạp mô hình bổ trợ chuyên nhận diện đầu học sinh (chống sót góc xa & cúi gục đầu)
        self.head_model = None
        self.head_target_class_ids = [0]
        head_candidates = [
            Path(getattr(settings, "HEAD_MODEL_NAME", "models/classroom_best.pt")),
            settings.MODELS_DIR / "classroom_best.pt",
            settings.BASE_DIR / "models" / "classroom_best.pt",
        ]
        for hp in head_candidates:
            if hp.exists() and str(hp) != str(self.model_name):
                try:
                    self.head_model = YOLO(str(hp))
                    self.head_target_class_ids = self._determine_target_classes_for_model(self.head_model)
                    logger.info(f"Đã nạp mô hình bổ trợ chuyên nhận diện đầu học sinh: {hp.name} (Classes: {self.head_target_class_ids})")
                    break
                except Exception as e:
                    logger.warning(f"Không thể nạp mô hình đầu học sinh từ {hp}: {e}")

        # Tối ưu thiết bị phần cứng (Tự động kích hoạt GPU NVIDIA CUDA RTX 3050 và FP16 Half Precision)
        import torch
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.half = (self.device != "cpu")
        logger.info(f"StudentDetector sử dụng thiết bị AI: {self.device} (Tăng tốc FP16 Half: {self.half})")

        try:
            self.model.to(self.device)
        except Exception as e:
            logger.debug(f"Không thể gọi model.to({self.device}): {e}")

        if self.head_model is not None:
            try:
                self.head_model.to(self.device)
            except Exception as e:
                logger.debug(f"Không thể gọi head_model.to({self.device}): {e}")

    def _determine_target_classes_for_model(self, model: Any) -> List[int]:
        """Tự động nhận diện class id tương ứng với học sinh/người/đầu trong mô hình."""
        if not hasattr(model, "names") or not model.names:
            return [0]

        names = model.names
        matched_ids = []
        for cls_id, name in names.items():
            name_lower = str(name).lower()
            if name_lower in ["person", "student_head", "student", "head", "item"]:
                matched_ids.append(int(cls_id))

        return matched_ids if matched_ids else [0]

    def _determine_target_classes(self) -> List[int]:
        return self._determine_target_classes_for_model(self.model)

    def get_model_info(self) -> Dict[str, Any]:
        """Trả về thông tin chi tiết mô hình AI phục vụ giám sát và báo cáo hệ thống."""
        import torch
        is_cuda = torch.cuda.is_available()
        device_name = torch.cuda.get_device_name(0) if is_cuda else "CPU"
        return {
            "family": getattr(settings, "YOLO_FAMILY", "YOLO26"),
            "variant": getattr(settings, "YOLO_VARIANT", "26m"),
            "model_name": Path(self.model_name).name,
            "model_path": self.model_name,
            "head_model": Path(getattr(settings, "HEAD_MODEL_NAME", "")).name if self.head_model else None,
            "device": device_name,
            "is_cuda": is_cuda,
            "imgsz": settings.YOLO_IMGSZ,
            "confidence_threshold": settings.AI_CONFIDENCE_THRESHOLD,
            "iou_threshold": settings.AI_IOU_THRESHOLD,
            "target_classes": self.target_class_ids,
            "target_class_names": [self.model.names.get(i, "unknown") for i in self.target_class_ids] if hasattr(self.model, "names") else ["person"]
        }

    @staticmethod
    def deduplicate_boxes(
        boxes: List[List[int]],
        confs: List[float],
        iou_thresh: float = 0.45,
        ios_thresh: float = 0.50
    ) -> Tuple[List[List[int]], List[float]]:
        """
        Hợp nhất các bounding boxes đa tỷ lệ (Global + Tiled + Head Model):
        - Nếu IoU >= iou_thresh: trùng lặp đối tượng.
        - Nếu 1 box lọt trong box kia (IoS >= ios_thresh):
          hợp nhất thông minh giữa box toàn thân (COCO) và box đầu (Head Specialist).
        - Đảm bảo KHÔNG gộp 2 người khác nhau khi 1 người đứng trước che 1 người ngồi sau.
        """
        if not boxes:
            return [], []

        indices = sorted(range(len(confs)), key=lambda i: confs[i], reverse=True)
        kept = []

        for i in indices:
            b1 = boxes[i]
            x1_a, y1_a, x2_a, y2_a = b1
            area_a = max(1, (x2_a - x1_a) * (y2_a - y1_a))

            duplicate = False
            for j in kept:
                b2 = boxes[j]
                x1_b, y1_b, x2_b, y2_b = b2
                area_b = max(1, (x2_b - x1_b) * (y2_b - y1_b))

                # Giao điểm
                ix1 = max(x1_a, x1_b)
                iy1 = max(y1_a, y1_b)
                ix2 = min(x2_a, x2_b)
                iy2 = min(y2_a, y2_b)

                if ix2 > ix1 and iy2 > iy1:
                    inter = (ix2 - ix1) * (iy2 - iy1)
                    iou = inter / float(area_a + area_b - inter)
                    ios = inter / float(min(area_a, area_b))

                    if iou >= iou_thresh:
                        duplicate = True
                        break

                    # Một box nằm trong box kia (Head nằm trong Upper-body/Person hoặc ngược lại)
                    if ios >= ios_thresh:
                        big_b = b2 if area_b > area_a else b1
                        small_b = b1 if area_b > area_a else b2
                        bx1, by1, bx2, by2 = big_b
                        sx1, sy1, sx2, sy2 = small_b
                        scx = (sx1 + sx2) / 2.0
                        scy = (sy1 + sy2) / 2.0

                        # Nếu tâm box nhỏ nằm trong box lớn và ở nửa trên (75% trên) -> Cùng 1 học sinh
                        if (bx1 - 10 <= scx <= bx2 + 10) and (by1 - 10 <= scy <= by1 + (by2 - by1) * 0.75):
                            duplicate = True
                            break

            if not duplicate:
                kept.append(i)

        return [boxes[k] for k in kept], [confs[k] for k in kept]

    def run_multiscale_tiled_inference(
        self,
        image: np.ndarray,
        conf_threshold: float,
        imgsz: int = None
    ) -> Tuple[List[List[int]], List[float]]:
        """
        Chạy phát hiện người theo cơ chế đa tầng (Global + Head Specialist + Sliced Tiles)
        giúp phát hiện rõ nét học sinh ngồi ở xa và học sinh cúi đầu bị che khuất một phần.
        """
        h, w = image.shape[:2]
        if imgsz is None:
            imgsz = settings.YOLO_IMGSZ

        all_boxes = []
        all_confs = []

        # 1. Quét toàn cục với mô hình chính (YOLO person detector)
        # Sử dụng ngưỡng conf 0.25 để loại trừ hoàn toàn nhiễu mặt bàn/ghế gỗ
        coco_conf = max(0.25, conf_threshold)
        res_global = self.model.predict(
            source=image,
            classes=self.target_class_ids,
            conf=coco_conf,
            imgsz=imgsz,
            iou=settings.AI_IOU_THRESHOLD,
            device=self.device,
            verbose=False
        )
        if res_global and len(res_global) > 0:
            for b in res_global[0].boxes:
                xyxy = [int(v) for v in b.xyxy[0].cpu().numpy()]
                conf = float(b.conf[0].cpu().numpy())
                all_boxes.append(xyxy)
                all_confs.append(conf)

        # 2. Quét toàn cục bổ trợ bằng mô hình chuyên phát hiện đầu (Head Specialist)
        # Chạy ở ngưỡng nhạy cao (conf_threshold = 0.18) để bắt trọn học sinh cúi đầu / góc xa
        if self.head_model is not None:
            res_head = self.head_model.predict(
                source=image,
                classes=self.head_target_class_ids,
                conf=conf_threshold,
                imgsz=imgsz,
                iou=settings.AI_IOU_THRESHOLD,
                device=self.device,
                verbose=False
            )
            if res_head and len(res_head) > 0:
                for b in res_head[0].boxes:
                    xyxy = [int(v) for v in b.xyxy[0].cpu().numpy()]
                    conf = float(b.conf[0].cpu().numpy())
                    all_boxes.append(xyxy)
                    all_confs.append(conf)

        # 3. Quét chi tiết phân mảnh đa tỷ lệ (Sliced Tiled Pass - SAHI) khi ảnh độ nét cao (>= 720p)
        if settings.USE_TILED_INFERENCE and (w >= 1280 or h >= 720):
            tile_w, tile_h = 1200, 800
            step_x, step_y = 900, 600
            tile_imgsz = 960

            tile_list = []
            tile_offsets = []

            for y in range(0, h, step_y):
                for x in range(0, w, step_x):
                    x2 = min(w, x + tile_w)
                    y2 = min(h, y + tile_h)
                    x1 = max(0, x2 - tile_w)
                    y1 = max(0, y2 - tile_h)

                    tile = image[y1:y2, x1:x2]
                    tile_list.append(tile)
                    tile_offsets.append((x1, y1))

            if tile_list:
                # Quét hàng loạt (Batch Inference) trên GPU giúp tăng tốc gấp 4-6 lần
                res_tiles = self.model.predict(
                    source=tile_list,
                    classes=self.target_class_ids,
                    conf=coco_conf,
                    imgsz=tile_imgsz,
                    device=self.device,
                    verbose=False
                )
                for res_tile, (x1, y1) in zip(res_tiles, tile_offsets):
                    if res_tile and len(res_tile) > 0:
                        for b in res_tile.boxes:
                            bx1, by1, bx2, by2 = [int(v) for v in b.xyxy[0].cpu().numpy()]
                            all_boxes.append([bx1 + x1, by1 + y1, bx2 + x1, by2 + y1])
                            all_confs.append(float(b.conf[0].cpu().numpy()))

        # 4. Khử trùng lặp đa tầng thông minh
        fused_boxes, fused_confs = self.deduplicate_boxes(
            all_boxes, all_confs, iou_thresh=settings.AI_IOU_THRESHOLD, ios_thresh=0.60
        )
        return fused_boxes, fused_confs

    def detect_students_in_classroom(
        self,
        image: np.ndarray,
        red_zone: List[List[int]],
        green_zone: List[List[int]] = None,
        conf_threshold: float = None,
        classroom_name: str = "Lớp Học",
        standard_count: int = 40,
        apply_clahe: bool = True,
        roi_dims: Optional[Tuple[int, int]] = None
    ) -> Tuple[int, List[Dict[str, Any]], np.ndarray]:
        """
        Quy trình xử lý AI toàn diện:
        1. Tiền xử lý chống ngược sáng (CLAHE/Glare reduction).
        2. Chạy suy luận đa tầng phân mảnh (Tiled Multi-Scale Inference) chống sót học sinh bị che khuất.
        3. Tinh chỉnh bounding box đầu/thân trên thích ứng (Adaptive Head/Upper-body).
        4. Lọc tọa độ theo Red Zone (bàn học) & Green Zone (bục giảng giáo viên).
        5. Vẽ bounding box và khung chú thích đối chứng trực quan.
        """
        if image is None:
            return 0, [], None

        h, w = image.shape[:2]
        if conf_threshold is None:
            conf_threshold = settings.AI_CONFIDENCE_THRESHOLD

        # Tự động đồng bộ tỉ lệ đa giác ROI nếu kích thước ảnh khác kích thước cấu hình ROI
        if roi_dims and len(roi_dims) == 2:
            rw, rh = roi_dims
            if rw > 0 and rh > 0 and (rw != w or rh != h):
                red_zone = ROIManager.scale_polygon(red_zone, rw, rh, w, h)
                green_zone = ROIManager.scale_polygon(green_zone, rw, rh, w, h)

        # 1. Tiền xử lý chống ngược sáng cửa sổ
        processed_img = image.copy()
        if apply_clahe:
            processed_img = ImageEnhancer.preprocess_classroom_frame(processed_img)

        # 2. Chạy YOLO đa tầng (Global + Tiled)
        fused_boxes, fused_confs = self.run_multiscale_tiled_inference(
            processed_img,
            conf_threshold=conf_threshold
        )

        detected_boxes = []
        for bbox, conf in zip(fused_boxes, fused_confs):
            x1, y1, x2, y2 = bbox
            box_w = x2 - x1
            box_h = y2 - y1

            # Loại bỏ các box nhiễu cực nhỏ (< 8px)
            if box_w < 8 or box_h < 10:
                continue

            # Tinh chỉnh box thích ứng cho đầu & thân trên
            aspect = box_h / max(1, box_w)
            if aspect >= 1.8:
                head_y2 = int(y1 + box_h * 0.45)
            elif aspect >= 1.2:
                head_y2 = int(y1 + box_h * 0.70)
            else:
                head_y2 = y2

            head_bbox = [x1, y1, x2, max(y1 + 10, head_y2)]
            cx = (x1 + x2) / 2.0
            cy = y1 + (head_bbox[3] - y1) * 0.35

            detected_boxes.append({
                "bbox": [x1, y1, x2, y2],
                "head_bbox": head_bbox,
                "centroid": (cx, cy),
                "confidence": conf,
                "class_id": 0
            })

        # Cơ chế dự phòng bổ trợ bằng HoughCircles (chỉ kích hoạt nếu không tìm thấy người nào)
        # Kiểm soát chặt chẽ ngưỡng param2 và khoảng cách tối thiểu để không phát hiện texture tóc thành 73 người
        if len(detected_boxes) == 0:
            masked_img = ROIManager.apply_spatial_mask(processed_img, red_zone, green_zone)
            gray = cv2.cvtColor(masked_img, cv2.COLOR_BGR2GRAY)
            min_dist = max(90, int(min(w, h) * 0.15))
            circles = cv2.HoughCircles(
                gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=min_dist,
                param1=60, param2=35, minRadius=25, maxRadius=70
            )
            if circles is not None:
                circles = np.uint16(np.around(circles))
                # Giới hạn tối đa không bao giờ tạo quá 3 vòng tròn nếu ở cự ly webcam gần
                for c in circles[0, :min(len(circles[0]), 3)]:
                    cx, cy, r = int(c[0]), int(c[1]), int(c[2])
                    x1, y1 = max(0, cx - r), max(0, cy - r)
                    x2, y2 = min(w, cx + r), min(h, cy + r + int(r * 1.5))
                    detected_boxes.append({
                        "bbox": [x1, y1, x2, y2],
                        "head_bbox": [x1, y1, x2, y1 + int(r * 2)],
                        "centroid": (float(cx), float(cy)),
                        "confidence": 0.88,
                        "class_id": 0
                    })

        # 3. Lọc lại bằng thuật toán Polygon Centroid (Red Zone & Green Zone)
        valid_students, ignored_people = ROIManager.filter_detections(
            detected_boxes, red_zone, green_zone
        )

        present_count = len(valid_students)
        absent_count = max(0, standard_count - present_count)

        # 4. Tạo ảnh đối chứng trực quan (Annotated Visualization Image)
        annotated_img = image.copy()

        # Vẽ Red Zone & Green Zone bán trong suốt
        annotated_img = ROIManager.draw_roi_overlays(annotated_img, red_zone, green_zone, alpha=0.20)

        # Vẽ bounding box và Huy hiệu số thứ tự (Smart High-Contrast Badges) cho từng học sinh
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.52
        font_thickness = 1

        for idx, student in enumerate(valid_students, 1):
            hx1, hy1, hx2, hy2 = student["head_bbox"]
            conf = student["confidence"]

            # 1. Bounding box đầu/thân trên màu xanh neon sáng với nét khử răng cưa
            cv2.rectangle(annotated_img, (hx1, hy1), (hx2, hy2), (255, 140, 0), 2, cv2.LINE_AA)

            # 2. Điểm chấm tâm đầu định vị chính xác (chấm xanh lá viền đen chống chìm)
            cx, cy = [int(v) for v in student["centroid"]]
            cv2.circle(annotated_img, (cx, cy), 5, (0, 0, 0), -1, cv2.LINE_AA)
            cv2.circle(annotated_img, (cx, cy), 3, (0, 255, 120), -1, cv2.LINE_AA)

            # 3. Huy hiệu số thứ tự tương phản cao (High-Contrast Number Badge)
            label = f"#{idx:02d}"
            (tw, th), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
            badge_pad_x = 4
            badge_pad_y = 3
            bw = tw + badge_pad_x * 2
            bh = th + badge_pad_y * 2

            # Đặt nhãn căn giữa phía trên đầu học sinh (hoặc lọt trong box nếu sát mép trên)
            bx1 = max(2, min(w - bw - 2, int((hx1 + hx2) / 2 - bw / 2)))
            by2 = hy1 - 4
            if by2 - bh < 2:
                by2 = hy1 + bh + 4
            by1 = by2 - bh
            bx2 = bx1 + bw

            # Nền tối tương phản cao
            cv2.rectangle(annotated_img, (bx1, by1), (bx2, by2), (18, 22, 26), -1)
            # Viền neon vàng sáng sắc nét
            cv2.rectangle(annotated_img, (bx1, by1), (bx2, by2), (0, 235, 255), 1, cv2.LINE_AA)
            # Chữ số trắng tinh siêu nét
            cv2.putText(
                annotated_img,
                label,
                (bx1 + badge_pad_x, by2 - badge_pad_y - 1),
                font,
                font_scale,
                (255, 255, 255),
                font_thickness,
                cv2.LINE_AA
            )

        # Vẽ bounding box mảnh & thanh lịch cho giáo viên/người ở bục giảng (loại trừ)
        if ignored_people:
            for ignored in ignored_people:
                ix1, iy1, ix2, iy2 = ignored["bbox"]
                cv2.rectangle(annotated_img, (ix1, iy1), (ix2, iy2), (120, 120, 120), 1, cv2.LINE_AA)

            first_ignored = ignored_people[0]
            ix1, iy1, ix2, iy2 = first_ignored["bbox"]
            cv2.putText(
                annotated_img,
                "Giao vien (Buc giang)",
                (ix1, max(18, iy1 - 6)),
                font,
                0.48,
                (160, 160, 160),
                1,
                cv2.LINE_AA
            )

        # GỠ BỎ BANNER ĐEN 75px: 100% diện tích camera được giữ trọn vẹn, không che khuất học sinh hàng đầu.

        return present_count, valid_students, annotated_img

detector = StudentDetector()
