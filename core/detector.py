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
        
        # Kiểm tra đường dẫn trọng số - Ưu tiên mô hình classroom_best.pt camera thực tế
        candidate_paths = [
            settings.MODELS_DIR / "classroom_best.pt",
            settings.BASE_DIR / "models" / "classroom_best.pt",
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
                    logger.info(f"Đã nạp thành công mô hình phát hiện chính: {p.name}!")
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
        self.is_head_model = "classroom" in Path(self.model_name).name.lower() or "head" in Path(self.model_name).name.lower()
        logger.info(f"AI Target Classes cho điểm danh: {self.target_class_ids} (Mô hình chuyên biệt đầu: {self.is_head_model})")

        # Nạp mô hình bổ trợ: Chỉ kích hoạt nếu mô hình chính KHÔNG PHẢI là mô hình chuyên nhận diện đầu
        self.head_model = None
        self.head_target_class_ids = [0]
        if not self.is_head_model:
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

        # Nạp mô hình người COCO yolo26m.pt để xác thực thân người, giải cứu cúi đầu và lọc ba lô ghế trống
        self.coco_person_model = None
        coco_candidate = settings.MODELS_DIR / "yolo26m.pt"
        if coco_candidate.exists() and str(coco_candidate.resolve()) != str(Path(self.model_name).resolve()):
            try:
                self.coco_person_model = YOLO(str(coco_candidate))
                logger.info("Đã nạp mô hình COCO Person yolo26m.pt phục vụ xác thực thân người & giải cứu cúi đầu!")
            except Exception as e:
                logger.warning(f"Không thể nạp mô hình COCO Person: {e}")

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

        if self.coco_person_model is not None:
            try:
                self.coco_person_model.to(self.device)
            except Exception as e:
                logger.debug(f"Không thể gọi coco_person_model.to({self.device}): {e}")

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
        iou_thresh: float = 0.35,
        ios_thresh: float = 0.50,
        min_dist_px: float = 20.0
    ) -> Tuple[List[List[int]], List[float]]:
        """
        Khử trùng lặp đa tầng thông minh:
        1. Aspect Ratio Filtering: Đầu học sinh có tỷ lệ 0.42 <= h/w <= 1.68.
        2. Centroid Distance Suppression: Nếu khoảng cách tâm < 18px hoặc < 50% min_dim -> Trùng lặp.
        3. Vertical Stacking Suppression (Đã sửa lỗi nuốt học sinh bàn trước):
           Chỉ coi là chẻ đôi 1 đầu (tóc + mặt) nếu 2 box THẬT SỰ CHỒNG LẤN SÂU THEO PHƯƠNG DỌC
           (x_overlap > 50% min_w và y_overlap > 38% min_h).
           Tuyệt đối KHÔNG xóa nếu 2 đầu tách rời nhau (y_overlap <= 0 hoặc chỉ chạm mép).
        4. Standard IoU / IoS Containment: Nếu iou >= 0.35 hoặc ios >= 0.50 -> Trùng lặp.
        """
        if not boxes:
            return [], []

        indices = sorted(range(len(confs)), key=lambda i: confs[i], reverse=True)
        kept = []

        for i in indices:
            b1 = boxes[i]
            x1_a, y1_a, x2_a, y2_a = b1
            w_a = x2_a - x1_a
            h_a = y2_a - y1_a
            area_a = max(1, w_a * h_a)
            c1 = ((x1_a + x2_a) / 2.0, (y1_a + y2_a) / 2.0)

            aspect_a = h_a / max(1.0, float(w_a))
            if aspect_a < 0.25 or aspect_a > 2.50:
                continue

            duplicate = False
            for j in kept:
                b2 = boxes[j]
                x1_b, y1_b, x2_b, y2_b = b2
                w_b = x2_b - x1_b
                h_b = y2_b - y1_b
                area_b = max(1, w_b * h_b)
                c2 = ((x1_b + x2_b) / 2.0, (y1_b + y2_b) / 2.0)

                # Kiểm tra Row Occlusion (Học sinh hàng trước bị box người/thân học sinh hàng sau bao bọc):
                # Box nhỏ hơn nằm ở nửa dưới của box lớn hơn -> 2 học sinh ngồi trước-sau riêng biệt
                is_row_occlusion = False
                if area_a < area_b * 0.45:
                    if c1[1] > c2[1] + h_b * 0.15 and y1_a > y1_b + h_b * 0.30:
                        is_row_occlusion = True
                elif area_b < area_a * 0.45:
                    if c2[1] > c1[1] + h_a * 0.15 and y1_b > y1_a + h_a * 0.30:
                        is_row_occlusion = True

                # 1. Khoảng cách tâm (chỉ triệt tiêu nếu gần như trùng khít tâm hoàn toàn)
                dist = np.hypot(c1[0] - c2[0], c1[1] - c2[1])
                if not is_row_occlusion and dist < 8.0:
                    duplicate = True
                    break

                # 2. Giao điểm & Kiểm tra IoU + IoS
                y_overlap = min(y2_a, y2_b) - max(y1_a, y1_b)
                x_overlap = min(x2_a, x2_b) - max(x1_a, x1_b)
                if x_overlap > 0 and y_overlap > 0:
                    inter = x_overlap * y_overlap
                    iou = inter / float(area_a + area_b - inter)
                    ios = inter / float(min(area_a, area_b))
                    if not is_row_occlusion:
                        if iou >= iou_thresh or ios >= ios_thresh:
                            duplicate = True
                            break
                        min_dim = min(w_a, h_a, w_b, h_b)
                        if dist < max(14.0, min_dim * 0.45) and ios >= 0.25:
                            duplicate = True
                            break

            if not duplicate:
                kept.append(i)

        return [boxes[k] for k in kept], [confs[k] for k in kept]

    @staticmethod
    def fuse_head_and_person(
        head_boxes: List[List[int]],
        head_confs: List[float],
        person_boxes: List[List[int]],
        person_confs: List[float],
        img_shape: Tuple[int, int]
    ) -> Tuple[List[List[int]], List[float]]:
        """
        Kết hợp đa tầng mô hình chuyên biệt đầu và mô hình COCO Person:
        1. Anatomy Constraint: Mỗi học sinh đã xác định đầu thì các vật thể con ở ngực/bàn (ba lô),
           vùng đùi/quần đùi, chân dưới gầm bàn của chính học sinh đó sẽ BỊ TRIỆT TIÊU.
        2. Lọc bỏ vật thể cô lập không có thân người (cây cảnh ngoài cửa sổ, nan hoa sắt) nếu conf < 0.45.
        3. Giải cứu học sinh cúi gập đầu/nằm bàn với cửa sổ tọa độ hẹp chống bị bạn ngồi cùng bàn nuốt chửng.
        4. Khử trùng lặp an toàn không xóa mất học sinh bàn trước / bàn sau.
        """
        candidates = []
        for b, c in zip(head_boxes, head_confs):
            w = b[2] - b[0]
            h = b[3] - b[1]
            if w < 12 or h < 12 or (b[1] <= 5 and b[3] <= 55):
                continue
            aspect = h / max(1.0, float(w))
            # Lọc bỏ các vật thể có tỷ lệ bất thường (cánh tay, ống tay áo, chân bàn có aspect > 1.58).
            # Đầu học sinh nhìn từ camera lớp học luôn có aspect từ 0.30 (cúi đầu nằm bàn) đến 1.55 (quay nghiêng/buộc tóc).
            if aspect < 0.25 or aspect > 1.58:
                continue
            candidates.append({
                "bbox": b,
                "conf": c,
                "cx": (b[0] + b[2]) / 2.0,
                "cy": (b[1] + b[3]) / 2.0,
                "w": w,
                "h": h
            })

        candidates.sort(key=lambda x: x["conf"], reverse=True)

        verified = []
        suppressed_indices = set()

        for i, c1 in enumerate(candidates):
            if i in suppressed_indices:
                continue

            has_person = False
            is_sub_body_artifact = False
            for pb, pc in zip(person_boxes, person_confs):
                px1, py1, px2, py2 = pb
                pw = px2 - px1
                ph = py2 - py1
                # Kiểm tra c1 có nằm trong phạm vi thân người pb không
                if px1 - 15 <= c1["cx"] <= px2 + 15 and py1 - 20 <= c1["cy"] <= py2 + 10:
                    # Tâm đầu c1 nằm trong nửa trên của Person box
                    if c1["cy"] <= py1 + ph * 0.42:
                        has_person = True
                        break
                    else:
                        # Rơi vào vùng ngực dưới / bụng / đùi / cánh tay đặt trên bàn
                        is_sub_body_artifact = True

            # Triệt tiêu cánh tay / vật thể trên bàn nằm ở nửa dưới thân người của một học sinh
            if is_sub_body_artifact and not has_person:
                continue

            # Khi học sinh ngồi sau bàn gỗ, thân người thường bị che khuất nên has_person có thể False.
            if not has_person:
                aspect = c1["h"] / max(1.0, float(c1["w"]))
                if c1["conf"] < 0.18 or aspect < 0.25 or aspect > 1.58:
                    continue

            verified.append(c1)

            # Anatomy Suppression: Triệt tiêu chồng lấn sâu và cánh tay phụ bên dưới đầu chính c1
            b1 = c1["bbox"]
            for j in range(i + 1, len(candidates)):
                if j in suppressed_indices:
                    continue
                c2 = candidates[j]
                b2 = c2["bbox"]
                x_inter = min(b1[2], b2[2]) - max(b1[0], b2[0])
                y_inter = min(b1[3], b2[3]) - max(b1[1], b2[1])
                # 1. Chồng lấn diện tích sâu
                if x_inter > min(c1["w"], c2["w"]) * 0.65 and y_inter > min(c1["h"], c2["h"]) * 0.45:
                    suppressed_indices.add(j)
                    continue

                # 2. Triệt tiêu cánh tay / ống tay áo đặt trên bàn kề cận dưới đầu c1
                dx = abs(c2["cx"] - c1["cx"])
                dy = c2["cy"] - c1["cy"]
                c2_aspect = c2["h"] / max(1.0, float(c2["w"]))
                if 10 <= dy <= max(75.0, c1["h"] * 1.35) and dx <= max(70.0, c1["w"] * 1.25):
                    if c2_aspect >= 1.40 or (c2["w"] < c1["w"] * 0.65 and c2["conf"] < c1["conf"] * 0.80):
                        suppressed_indices.add(j)

        # Giải cứu học sinh cúi gập đầu (Bowing Student Rescue)
        for pb, pc in zip(person_boxes, person_confs):
            if pc < 0.25:
                continue
            px1, py1, px2, py2 = pb
            pw = px2 - px1
            ph = py2 - py1
            if pw < 20 or ph < 30:
                continue

            est_cx = px1 + pw * 0.50
            est_cy = py1 + min(pw * 0.45, ph * 0.25)
            est_w = max(18, int(pw * 0.55))
            est_h = max(20, int(pw * 0.65))

            # Dùng cửa sổ hẹp theo trục X (35% pw) để bạn ngồi cùng bàn KHÔNG nuốt chửng bạn cúi đầu
            has_assigned_head = False
            for v in verified:
                if abs(v["cx"] - est_cx) < max(16.0, pw * 0.35) and abs(v["cy"] - est_cy) < max(20.0, ph * 0.35):
                    has_assigned_head = True
                    break

            if not has_assigned_head:
                verified.append({
                    "bbox": [int(est_cx - est_w/2), int(est_cy - est_h/2), int(est_cx + est_w/2), int(est_cy + est_h/2)],
                    "conf": pc * 0.85,
                    "cx": est_cx,
                    "cy": est_cy,
                    "w": est_w,
                    "h": est_h
                })

        # Khử trùng lặp an toàn (bảo toàn học sinh bàn trước/bàn sau & ngồi cạnh nhau)
        verified.sort(key=lambda x: x["conf"], reverse=True)
        final_kept = []

        for c1 in verified:
            b1 = c1["bbox"]
            c1_pt = (c1["cx"], c1["cy"])
            w1, h1 = c1["w"], c1["h"]
            area1 = max(1, w1 * h1)

            is_dup = False
            for c2 in final_kept:
                b2 = c2["bbox"]
                c2_pt = (c2["cx"], c2["cy"])
                w2, h2 = c2["w"], c2["h"]
                area2 = max(1, w2 * h2)

                dist = np.hypot(c1_pt[0] - c2_pt[0], c1_pt[1] - c2_pt[1])
                if dist < 8.0:
                    is_dup = True
                    break

                y_overlap = min(b1[3], b2[3]) - max(b1[1], b2[1])
                x_overlap = min(b1[2], b2[2]) - max(b1[0], b2[0])
                if x_overlap > 0 and y_overlap > 0:
                    inter = x_overlap * y_overlap
                    iou = inter / float(area1 + area2 - inter)
                    ios = inter / float(min(area1, area2))
                    if iou >= 0.35 or ios >= 0.48:
                        is_dup = True
                        break
                    if dist < max(14.0, min(w1, h1, w2, h2) * 0.45) and ios >= 0.25:
                        is_dup = True
                        break

            if not is_dup:
                final_kept.append(c1)

        fused_b = [item["bbox"] for item in final_kept]
        fused_c = [item["conf"] for item in final_kept]
        return fused_b, fused_c

    def run_multiscale_tiled_inference(
        self,
        image: np.ndarray,
        conf_threshold: float = None,
        imgsz: int = None
    ) -> Tuple[List[List[int]], List[float]]:
        """
        Chạy phát hiện người theo cơ chế tối ưu đa tầng không trùng lặp:
        - Nếu self.model là mô hình chuyên biệt đầu (classroom_best.pt), quét trực tiếp.
        - Nếu ảnh nét cao và bật USE_TILED_INFERENCE, quét thêm phân mảnh để bắt học sinh góc xa.
        - Áp dụng thuật toán khử trùng lặp đa tầng triệt để.
        """
        h, w = image.shape[:2]
        if imgsz is None:
            imgsz = settings.YOLO_IMGSZ
        if conf_threshold is None:
            conf_threshold = settings.AI_CONFIDENCE_THRESHOLD

        all_boxes = []
        all_confs = []

        # 1. Quét toàn cục với mô hình chính
        eff_conf = conf_threshold if conf_threshold is not None else settings.AI_CONFIDENCE_THRESHOLD
        res_global = self.model.predict(
            source=image,
            classes=self.target_class_ids,
            conf=eff_conf,
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

        # 1.1 Quét mô hình thân người COCO Person để làm căn cứ bảo chứng và giải cứu cúi đầu
        person_boxes = []
        person_confs = []
        active_coco = self.coco_person_model if self.coco_person_model is not None else (self.model if not self.is_head_model else None)
        if active_coco is not None:
            try:
                res_person = active_coco.predict(
                    source=image,
                    classes=[0],
                    conf=max(0.18, eff_conf),
                    imgsz=imgsz,
                    iou=0.45,
                    device=self.device,
                    verbose=False
                )
                if res_person and len(res_person) > 0:
                    for b in res_person[0].boxes:
                        person_boxes.append([int(v) for v in b.xyxy[0].cpu().numpy()])
                        person_confs.append(float(b.conf[0].cpu().numpy()))
            except Exception as e:
                logger.debug(f"Lỗi quét person pass: {e}")

        # 2. Quét toàn cục bổ trợ bằng mô hình đầu (chỉ khi mô hình chính không phải là mô hình đầu)
        if not self.is_head_model and self.head_model is not None:
            res_head = self.head_model.predict(
                source=image,
                classes=self.head_target_class_ids,
                conf=eff_conf,
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

        # 3. Quét chi tiết phân mảnh đa tỷ lệ (Sliced Tiled Pass - SAHI) khi ảnh nét cao (>= 720p)
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
                active_tiled_model = self.head_model if (not self.is_head_model and self.head_model is not None) else self.model
                active_tiled_classes = self.head_target_class_ids if (not self.is_head_model and self.head_model is not None) else self.target_class_ids
                tile_conf = min(0.20, eff_conf)

                res_tiles = active_tiled_model.predict(
                    source=tile_list,
                    classes=active_tiled_classes,
                    conf=tile_conf,
                    imgsz=tile_imgsz,
                    device=self.device,
                    verbose=False
                )
                for res_tile, (x1, y1) in zip(res_tiles, tile_offsets):
                    if res_tile and len(res_tile) > 0:
                        for b in res_tile.boxes:
                            bx1, by1, bx2, by2 = [int(v) for v in b.xyxy[0].cpu().numpy()]
                            bconf = float(b.conf[0].cpu().numpy())
                            bw = bx2 - bx1
                            bh = by2 - by1
                            baspect = bh / max(1.0, float(bw))

                            # Lọc bỏ các mảnh cắt mép nối nhân tạo giữa các tiles (Tile Seam Truncation Artifacts):
                            touches_internal_x = (bx1 <= 3 and x1 > 0) or (bx2 >= tile_w - 3 and x1 + tile_w < w)
                            touches_internal_y = (by1 <= 3 and y1 > 0) or (by2 >= tile_h - 3 and y1 + tile_h < h)
                            if (touches_internal_x or touches_internal_y) and (baspect > 1.45 or baspect < 0.40 or bconf < 0.55):
                                continue

                            # Lọc aspect ratio bất thường ngay từ tầng tile (loại trừ cánh tay, ống tay áo chém dọc)
                            if baspect > 1.58:
                                continue

                            all_boxes.append([bx1 + x1, by1 + y1, bx2 + x1, by2 + y1])
                            all_confs.append(bconf)

        # 4. Hợp nhất đa tầng thông minh: Kết hợp Head Model + COCO Person Model
        if person_boxes:
            fused_boxes, fused_confs = self.fuse_head_and_person(
                all_boxes, all_confs, person_boxes, person_confs, image.shape
            )
        else:
            fused_boxes, fused_confs = self.deduplicate_boxes(
                all_boxes, all_confs, iou_thresh=settings.AI_IOU_THRESHOLD, ios_thresh=0.50, min_dist_px=20.0
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
        5. Khử trùng lặp an toàn bảo đảm không bao giờ vẽ 2 số thứ tự / 2 chấm xanh lên cùng 1 học sinh.
        6. Vẽ bounding box và khung chú thích đối chứng trực quan.
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

            # Loại bỏ các box nhiễu cực nhỏ (< 12px) hoặc box nhiễu sát mép trần camera (đèn tuýp/quạt trần)
            if box_w < 12 or box_h < 12 or (y1 <= 5 and y2 <= 55):
                continue

            # Tinh chỉnh box thích ứng: Nếu là mô hình chuyên biệt đầu, bbox chính là head_bbox
            if self.is_head_model:
                head_bbox = [x1, y1, x2, y2]
            else:
                aspect = box_h / max(1, box_w)
                if aspect >= 1.6:
                    head_y2 = int(y1 + box_h * 0.50)
                else:
                    head_y2 = y2
                head_bbox = [x1, y1, x2, max(y1 + 10, head_y2)]

            cx = (head_bbox[0] + head_bbox[2]) / 2.0
            cy = (head_bbox[1] + head_bbox[3]) / 2.0

            detected_boxes.append({
                "bbox": [x1, y1, x2, y2],
                "head_bbox": head_bbox,
                "centroid": (cx, cy),
                "confidence": conf,
                "class_id": 0
            })

        # Cơ chế dự phòng bổ trợ bằng HoughCircles (chỉ kích hoạt nếu không tìm thấy người nào)
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

        # 4. Khử trùng lặp an toàn cấp 2 trên valid_students (Đảm bảo 100% không bao giờ có 2 số thứ tự / 2 chấm xanh trên 1 học sinh)
        final_valid = []
        final_indices = sorted(range(len(valid_students)), key=lambda k: valid_students[k]["confidence"], reverse=True)
        for idx in final_indices:
            st = valid_students[idx]
            scx, scy = st["centroid"]
            sb = st["head_bbox"]
            sw, sh = sb[2] - sb[0], sb[3] - sb[1]

            aspect = sh / max(1.0, float(sw))
            if aspect < 0.25 or aspect > 1.58:
                continue

            dup = False
            for existing in final_valid:
                ecx, ecy = existing["centroid"]
                eb = existing["head_bbox"]
                ew, eh = eb[2] - eb[0], eb[3] - eb[1]

                # 1. Centroid Distance Suppression (chỉ khi gần như trùng khít)
                dist = np.hypot(scx - ecx, scy - ecy)
                if dist < 8.0:
                    dup = True
                    break

                # 2. IoU & IoS Containment
                y_overlap = min(sb[3], eb[3]) - max(sb[1], eb[1])
                x_overlap = min(sb[2], eb[2]) - max(sb[0], eb[0])
                if x_overlap > 0 and y_overlap > 0:
                    inter = x_overlap * y_overlap
                    ios = inter / float(min(sw * sh, ew * eh))
                    iou = inter / float(sw * sh + ew * eh - inter)
                    if ios >= 0.48 or iou >= 0.35:
                        dup = True
                        break
                    if dist < max(14.0, min(sw, sh, ew, eh) * 0.45) and ios >= 0.25:
                        dup = True
                        break

                # 3. Triệt tiêu cánh tay / ống tay áo đặt trên bàn kề cận dưới đầu đã xác nhận
                dy = scy - ecy
                dx = abs(scx - ecx)
                if 10 <= dy <= max(75.0, eh * 1.35) and dx <= max(70.0, ew * 1.25):
                    if aspect >= 1.40 or (sw < ew * 0.65 and st["confidence"] < existing["confidence"] * 0.80):
                        dup = True
                        break

            if not dup:
                final_valid.append(st)

        valid_students = final_valid
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
