import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from ultralytics import YOLO

from config.settings import settings
from config.logging_config import logger

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

    def detect_via_predict_api(
        self,
        image: np.ndarray,
        api_url: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        depth_diff_threshold: Optional[float] = None,
        timeout: float = 10.0
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Gọi Endpoint /api/predict (mô hình student-detection AI thật) để nhận diện và lọc trùng lặp Depth-NMS.
        Hỗ trợ gọi trực tiếp tới container student-detection, proxy backend hoặc máy chủ GPU ngoại vi.
        """
        if not getattr(settings, "USE_PREDICT_API_ENGINE", True):
            logger.info("[Detector] USE_PREDICT_API_ENGINE=False, chuyển sang xử lý qua mô hình cục bộ")
            return None

        if api_url is None:
            api_url = getattr(settings, "STUDENT_DETECTION_API_URL", "")

        from backend.app.api.routers.predict import get_candidate_predict_urls
        target_urls = get_candidate_predict_urls(api_url)
        if "http://127.0.0.1:8000/api/predict" not in target_urls:
            target_urls.append("http://127.0.0.1:8000/api/predict")

        eff_iou = str(iou_threshold if iou_threshold is not None else getattr(settings, "DEPTH_NMS_IOU_THRESHOLD", 0.25))
        eff_depth = str(depth_diff_threshold if depth_diff_threshold is not None else getattr(settings, "DEPTH_NMS_DIFF_THRESHOLD", 0.0100))
        eff_conf = str(conf_threshold if conf_threshold is not None else getattr(settings, "AI_CONFIDENCE_THRESHOLD", 0.20))

        # 1. Gửi tệp ảnh thuần túy sang Service AI API (student-detection service)
        for target_url in target_urls:
            import requests
            try:
                success, encoded_img = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                if success:
                    files = {"image": ("frame.jpg", encoded_img.tobytes(), "image/jpeg")}
                    resp = requests.post(target_url, files=files, timeout=timeout)
                    if resp.status_code == 200:
                        res_json = resp.json()
                        detections = res_json.get("detections", [])
                        detected_boxes = []
                        for d in detections:
                            if not d.get("kept", True):
                                continue
                            bbox = d.get("bbox")
                            if not bbox or len(bbox) != 4:
                                continue
                            x1, y1, x2, y2 = bbox
                            conf = float(d.get("confidence", 0.85))
                            depth = float(d.get("depth", 0.5))
                            box_w = x2 - x1
                            box_h = y2 - y1

                            aspect = box_h / max(1, box_w)
                            head_y2 = int(y1 + box_h * 0.50) if aspect >= 1.6 else y2
                            head_bbox = [x1, y1, x2, max(y1 + 10, head_y2)]
                            cx = (head_bbox[0] + head_bbox[2]) / 2.0
                            cy = (head_bbox[1] + head_bbox[3]) / 2.0

                            detected_boxes.append({
                                "bbox": [x1, y1, x2, y2],
                                "head_bbox": head_bbox,
                                "centroid": (cx, cy),
                                "confidence": conf,
                                "depth": depth,
                                "class_id": 0,
                                "box_id": d.get("box_id", len(detected_boxes))
                            })
                        logger.info(f"[Hệ Thống Điểm Danh Chính - /api/predict] Đã nhận diện thành công {len(detected_boxes)} học sinh qua {target_url}")
                        return detected_boxes
            except Exception as e_ext:
                logger.debug(f"[Predict API Engine] Thử gọi {target_url} thất bại: {e_ext}")

        # 2. Xử lý trực tiếp siêu tốc qua Depth-NMS Engine nội bộ
        try:
            from backend.app.api.routers.predict import run_internal_depth_nms_predict
            pred_resp = run_internal_depth_nms_predict(
                image,
                conf_threshold=float(eff_conf),
                iou_threshold=float(eff_iou),
                depth_diff_threshold=float(eff_depth)
            )
            detected_boxes = []
            for d in pred_resp.detections:
                if not d.kept:
                    continue
                bbox = d.bbox
                if not bbox or len(bbox) != 4:
                    continue
                x1, y1, x2, y2 = bbox
                conf = float(d.confidence or 0.85)
                depth = float(d.depth or 0.5)
                box_w = x2 - x1
                box_h = y2 - y1

                aspect = box_h / max(1, box_w)
                head_y2 = int(y1 + box_h * 0.50) if aspect >= 1.6 else y2
                head_bbox = [x1, y1, x2, max(y1 + 10, head_y2)]
                cx = (head_bbox[0] + head_bbox[2]) / 2.0
                cy = (head_bbox[1] + head_bbox[3]) / 2.0

                detected_boxes.append({
                    "bbox": [x1, y1, x2, y2],
                    "head_bbox": head_bbox,
                    "centroid": (cx, cy),
                    "confidence": conf,
                    "depth": depth,
                    "class_id": 0,
                    "box_id": d.box_id
                })
            return detected_boxes
        except Exception as e_internal:
            logger.warning(f"[Predict API Engine] Chạy nội bộ thất bại: {e_internal}")
            return None

    def detect_students_in_classroom(
        self,
        image: np.ndarray,
        red_zone: Optional[List[List[int]]] = None,
        green_zone: Optional[List[List[int]]] = None,
        conf_threshold: float = None,
        classroom_name: str = "Lớp Học",
        standard_count: int = 40,
        apply_clahe: bool = True,
        roi_dims: Optional[Tuple[int, int]] = None,
        visual_mode: Optional[str] = None
    ) -> Tuple[int, List[Dict[str, Any]], np.ndarray]:
        """
        Quy trình nhận diện và đếm học sinh DUY NHẤT của hệ thống:
        - Sử dụng thuần túy 100% Endpoint /api/predict (Depth-NMS với Depth Anything V2).
        - Bỏ toàn bộ các thuật toán khác ra khỏi hệ thống.
        - Toàn bộ cấu hình ROI (Green Zone, Red Zone) đã được COMMENT LẠI hoàn toàn.
        - Hiển thị đối chứng đồng nhất dạng Chấm Tròn phát sáng (Dot Mode).
        """
        if image is None:
            return 0, [], None

        # 1. Chạy nhận diện DUY NHẤT qua Depth-NMS Predict API (/api/predict)
        detected_boxes = self.detect_via_predict_api(
            image=image,
            conf_threshold=conf_threshold
        )

        # Fallback an toàn trực tiếp qua engine nội bộ nếu có gián đoạn kết nối
        if detected_boxes is None:
            from backend.app.api.routers.predict import run_internal_depth_nms_predict
            pred_resp = run_internal_depth_nms_predict(
                image,
                iou_threshold=getattr(settings, "DEPTH_NMS_IOU_THRESHOLD", 0.25),
                depth_diff_threshold=getattr(settings, "DEPTH_NMS_DIFF_THRESHOLD", 0.0100)
            )
            detected_boxes = []
            for d in pred_resp.detections:
                if not d.kept:
                    continue
                bbox = d.bbox
                if not bbox or len(bbox) != 4:
                    continue
                x1, y1, x2, y2 = bbox
                conf = float(d.confidence or 0.85)
                depth = float(d.depth or 0.5)
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                detected_boxes.append({
                    "bbox": [x1, y1, x2, y2],
                    "head_bbox": [x1, y1, x2, y2],
                    "centroid": (cx, cy),
                    "confidence": conf,
                    "depth": depth,
                    "class_id": 0,
                    "box_id": d.box_id
                })

        logger.info(f"[Hệ Thống AI Điều Cải - /api/predict] Đã nhận diện thuần túy {len(detected_boxes)} học sinh cho {classroom_name}")

        valid_students = detected_boxes
        for idx, st in enumerate(valid_students, 1):
            st["student_no"] = idx

        present_count = len(valid_students)

        # 2. Tạo ảnh đối chứng trực quan DẠNG CHẤM TRÒN ĐỒNG NHẤT (Dot Mode)
        from backend.app.core.raw_ai_engine import draw_predict_api_dots
        effective_visual_mode = visual_mode or getattr(settings, "VISUALIZATION_MODE", "dot")
        annotated_img = draw_predict_api_dots(
            image,
            valid_students,
            visual_mode=effective_visual_mode,
            show_suppressed=False
        )

        return present_count, valid_students, annotated_img

detector = StudentDetector()
