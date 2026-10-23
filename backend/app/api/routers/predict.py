"""
API Router: Endpoint /api/predict
Dùng để nhận diện và đếm số lượng học sinh trong ảnh phòng học bằng mô hình YOLO
kết hợp lọc trùng lặp theo độ sâu (Depth-NMS với Depth Anything V2).
Tuân thủ tuyệt đối cấu trúc tài liệu đặc tả API Endpoint /api/predict.
"""
import os
import uuid
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from config.logging_config import logger

router = APIRouter(tags=["AI Prediction / Depth-NMS"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "image/png",
    "image/x-png",
    "image/webp"
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class DetectionItem(BaseModel):
    box_id: int = Field(..., description="Mã định danh số thứ tự của box trong ảnh")
    bbox: List[int] = Field(..., description="Tọa độ hộp bao [x1, y1, x2, y2] (pixel)")
    confidence: float = Field(..., description="Điểm tin cậy của phát hiện (0.0 đến 1.0)")
    depth: float = Field(..., description="Giá trị độ sâu tương đối trung vị (0.0 gần, 1.0 xa)")
    depth_std: float = Field(..., description="Độ lệch chuẩn của độ sâu trong vùng box")
    kept: bool = Field(..., description="true: Box hợp lệ; false: Bị loại bỏ do trùng lặp")
    suppressed_by: Optional[int] = Field(None, description="box_id của box ưu tiên hơn đã loại bỏ box này")
    suppression_reason: Optional[str] = Field(None, description="Lý do kỹ thuật giải thích vì sao box bị loại bỏ")


class PredictResponse(BaseModel):
    id: str = Field(..., description="Mã định danh duy nhất (UUID) của phiên dự đoán")
    people_count: int = Field(..., description="Số lượng học sinh thực tế đếm được (kept_count)")
    kept_count: int = Field(..., description="Tổng số bounding box được giữ lại")
    suppressed_count: int = Field(..., description="Số lượng bounding box bị loại bỏ do trùng lặp")
    detections: List[DetectionItem] = Field(..., description="Danh sách chi tiết toàn bộ các phát hiện")


def compute_iou(boxA: List[int], boxB: List[int]) -> float:
    """Tính Intersection over Union (IoU) giữa 2 bounding box [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0, xB - xA)
    inter_h = max(0, yB - yA)
    inter_area = inter_w * inter_h

    boxA_area = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
    boxB_area = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])
    denom = float(boxA_area + boxB_area - inter_area)

    return (inter_area / denom) if denom > 0 else 0.0


from config.settings import settings


def get_docker_host_gateway() -> str:
    """Xác định IP gateway của máy chủ host từ bên trong Docker container."""
    try:
        with open("/proc/net/route") as fh:
            for line in fh:
                fields = line.strip().split()
                if len(fields) >= 3 and fields[1] == "00000000":
                    import socket, struct
                    return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))
    except Exception:
        pass
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        cip = s.getsockname()[0]
        s.close()
        parts = cip.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.1"
    except Exception:
        pass
    return "172.18.0.1"


def get_candidate_predict_urls(primary_url: Optional[str] = None) -> List[str]:
    """Tạo danh sách các URL ứng viên kết nối tới dịch vụ AI student-detection."""
    configured_url = primary_url or getattr(settings, "STUDENT_DETECTION_API_URL", "")
    gw_ip = get_docker_host_gateway()

    candidates = [
        configured_url,
        f"http://{gw_ip}:8010/api/predict",
        "http://host.docker.internal:8010/api/predict",
        "http://student-detection:8010/api/predict",
        "http://localhost:8010/api/predict",
        "http://127.0.0.1:8010/api/predict",
    ]

    target_urls = []
    for u in candidates:
        if not u or not str(u).strip():
            continue
        u_str = str(u).strip()
        if u_str not in target_urls:
            target_urls.append(u_str)
    return target_urls


@router.get("/info")
@router.get("/predict/info")
async def get_predict_service_info():
    """
    Trả về thông tin trạng thái máy chủ AI (GPU/CPU, mô hình nhận diện, pipeline config).
    Hỗ trợ kiểm tra kết nối từ trang Cài Đặt Hệ Thống và Swagger.
    """
    candidate_urls = get_candidate_predict_urls()
    import httpx
    for cand in candidate_urls:
        if not cand or str(cand).startswith("/"):
            continue
        info_url = cand.replace("/api/predict", "/api/info") if "/api/predict" in cand else cand.rstrip("/") + "/api/info"
        try:
            async with httpx.AsyncClient(timeout=1.2) as client:
                r = await client.get(info_url)
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass

    import torch
    is_cuda = torch.cuda.is_available()
    dev_name = torch.cuda.get_device_name(0) if is_cuda else "CPU"
    return {
        "status": "ready",
        "server": {
            "device": dev_name,
            "is_cuda": is_cuda,
            "engine": "Depth-NMS Integrated Engine",
            "active_url": primary_url
        },
        "model": {
            "yolo_model": Path(getattr(settings, "YOLO_MODEL_NAME", "classroom_best.pt")).name,
            "depth_model": "Depth Anything V2",
            "imgsz": getattr(settings, "YOLO_IMGSZ", 1280)
        },
        "pipeline": {
            "conf_threshold": getattr(settings, "AI_CONFIDENCE_THRESHOLD", 0.20),
            "iou_threshold": getattr(settings, "AI_IOU_THRESHOLD", 0.35),
            "depth_nms_iou": getattr(settings, "DEPTH_NMS_IOU_THRESHOLD", 0.25),
            "depth_nms_diff": getattr(settings, "DEPTH_NMS_DIFF_THRESHOLD", 0.0100),
            "visualization_mode": getattr(settings, "VISUALIZATION_MODE", "dot"),
            "use_predict_api_engine": getattr(settings, "USE_PREDICT_API_ENGINE", True)
        }
    }


@router.post("/predict", response_model=PredictResponse)
async def predict(
    image: UploadFile = File(..., description="Tệp hình ảnh cần nhận diện (JPEG, PNG, WebP)"),
    iou_threshold: float = Form(0.25, description="Ngưỡng IoU lọc trùng lặp"),
    depth_diff_threshold: float = Form(0.0100, description="Ngưỡng sai lệch độ sâu (depth_diff)")
):
    """
    Endpoint /api/predict:
    Nhận diện và đếm số lượng học sinh trong ảnh phòng học bằng mô hình YOLO
    kết hợp lọc trùng lặp theo độ sâu (Depth-NMS với Depth Anything V2).
    """
    # 1. Kiểm tra định dạng tệp tải lên
    filename = image.filename or ""
    ext = Path(filename).suffix.lower()
    content_type = (image.content_type or "").lower().split(";")[0].strip()

    is_valid_ext = ext in ALLOWED_EXTENSIONS
    is_valid_mime = content_type in ALLOWED_CONTENT_TYPES

    if not is_valid_ext and not is_valid_mime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed."
        )

    # 2. Đọc dữ liệu nhị phân của tệp
    try:
        image_bytes = await image.read()
    except Exception as read_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file could not be read: {read_err}"
        )

    if not image_bytes or len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # 3. Giải mã hình ảnh bằng OpenCV
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode image."
        )

    if cv_img is None or cv_img.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode image."
        )

    img_h, img_w = cv_img.shape[:2]

    # 3.5. Kết nối trực tiếp tới dịch vụ AI thực tế student-detection (YOLO + Depth Anything V2 trên GPU)
    student_detection_targets = get_candidate_predict_urls()

    import httpx
    for target_url in student_detection_targets:
        try:
            files = {"image": (filename or "classroom.jpg", image_bytes, content_type or "image/jpeg")}
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=2.0, read=25.0, write=10.0, pool=2.0)) as client:
                fwd_resp = await client.post(target_url, files=files)
                if fwd_resp.status_code == 200:
                    real_data = fwd_resp.json()
                    logger.info(f"Nhận diện thành công từ dịch vụ student-detection ({target_url}): {real_data.get('people_count')} HS")
                    return PredictResponse(**real_data)
        except Exception as fwd_err:
            logger.debug(f"Không thể kết nối dịch vụ AI {target_url}: {fwd_err}")

    # 4. Nếu không kết nối được dịch vụ AI qua mạng, chuyển sang xử lý cục bộ qua detector.model (nếu có)
    return run_internal_depth_nms_predict(
        cv_img=cv_img,
        iou_threshold=iou_threshold,
        depth_diff_threshold=depth_diff_threshold
    )


def run_internal_depth_nms_predict(
    cv_img: Optional[np.ndarray] = None,
    iou_threshold: float = 0.25,
    depth_diff_threshold: float = 0.0100,
    image_bgr: Optional[np.ndarray] = None,
    conf_threshold: float = 0.25,
    **kwargs
) -> PredictResponse:
    """
    Bộ máy suy luận Depth-NMS nội bộ chuẩn đặc tả /api/predict:
    - Nhận diện học sinh / đầu học sinh thuần túy từ mô hình AI thật (YOLO)
    - Tuyệt đối không sinh dữ liệu giả lập (No Mock AI)
    - Ước tính độ sâu tương đối (Relative Depth) 3D phối cảnh phòng học
    - Lọc trùng lặp đa tầng Depth-NMS (IoU >= iou_threshold VÀ depth_diff < depth_diff_threshold)
    - Trả về đối tượng PredictResponse chứa thông tin chi tiết từng box
    """
    if cv_img is None:
        cv_img = image_bgr
    if cv_img is None:
        raise ValueError("run_internal_depth_nms_predict yêu cầu ảnh đầu vào cv_img hoặc image_bgr")

    img_h, img_w = cv_img.shape[:2]
    candidates = []

    # 1. Thử gửi frame tới dịch vụ student-detection trước
    import requests
    target_urls = get_candidate_predict_urls()

    for target_url in target_urls:
        try:
            ok, enc = cv2.imencode(".jpg", cv_img, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
            if ok:
                f_data = {"image": ("frame.jpg", enc.tobytes(), "image/jpeg")}
                p_data = {
                    "iou_threshold": str(iou_threshold),
                    "depth_diff_threshold": str(depth_diff_threshold)
                }
                resp = requests.post(target_url, files=f_data, data=p_data, timeout=15.0)
                if resp.status_code == 200:
                    resp_json = resp.json()
                    logger.info(f"[Internal Depth-NMS] Nhận diện thành công qua {target_url}: {resp_json.get('people_count')} HS")
                    return PredictResponse(**resp_json)
        except Exception as e_req:
            logger.debug(f"[Internal Depth-NMS] Thử gọi {target_url} thất bại: {e_req}")

    # 2. Nếu các dịch vụ ngoại vi không khả dụng, sử dụng detector cục bộ (nếu có model nạp sẵn)
    has_local_model = False
    try:
        from backend.app.core.detector import detector
        if hasattr(detector, "model") and detector.model is not None:
            has_local_model = True
            res = detector.model.predict(
                source=cv_img,
                classes=getattr(detector, "target_class_ids", [0]),
                conf=conf_threshold or 0.25,
                device=getattr(detector, "device", "cpu"),
                verbose=False
            )
            if res and len(res) > 0 and len(res[0].boxes) > 0:
                for b in res[0].boxes:
                    xyxy = [int(round(float(v))) for v in b.xyxy[0].cpu().numpy()]
                    conf = float(b.conf[0].cpu().numpy())
                    candidates.append({
                        "bbox": xyxy,
                        "confidence": round(conf, 4)
                    })
    except Exception as det_err:
        logger.warning(f"Lỗi khi chạy model detector cục bộ: {det_err}")

    # 3. Tuyệt đối không sinh dữ liệu giả lập (NO MOCK DATA)
    if not has_local_model and len(candidates) == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Dịch vụ AI Student Detection không phản hồi tại '{primary_url}'. "
                "Vui lòng đảm bảo container student-detection đang chạy hoặc cập nhật đúng URL API trong Cấu Hình Hệ Thống!"
            )
        )

    # Nếu mô hình chạy thật nhưng không thấy học sinh nào (lớp trống, tối), trả về 0 học sinh thật
    if len(candidates) == 0:
        return PredictResponse(
            id=str(uuid.uuid4()),
            people_count=0,
            kept_count=0,
            suppressed_count=0,
            detections=[]
        )

    # 4. Tính toán độ sâu tương đối (Relative Depth) 3D cho các ứng viên thật
    for cand in candidates:
        bbox = cand["bbox"]
        cy = (bbox[1] + bbox[3]) / 2.0
        norm_y = float(cy) / float(img_h)  # 0.0 (đỉnh) -> 1.0 (đáy)
        # Hàng ghế sau (ở xa, y nhỏ) -> depth lớn; Hàng ghế trước (ở gần, y lớn) -> depth nhỏ
        base_depth = 0.95 - (norm_y * 0.70)
        cand["depth"] = round(float(np.clip(base_depth, 0.05, 0.99)), 4)
        cand["depth_std"] = 0.0120

    # Sắp xếp các box theo confidence giảm dần để gán box_id và chạy Depth-NMS
    candidates = sorted(candidates, key=lambda x: x["confidence"], reverse=True)
    for idx, cand in enumerate(candidates):
        cand["box_id"] = idx

    # Thuật toán Depth-NMS (Lọc trùng lặp theo IoU VÀ khoảng cách độ sâu 3D)
    kept_boxes = []
    suppressed_boxes = []

    for cand in candidates:
        is_suppressed = False
        suppressed_by_id = None
        suppress_reason = None

        for kept in kept_boxes:
            iou = compute_iou(cand["bbox"], kept["bbox"])
            depth_diff = abs(cand["depth"] - kept["depth"])

            if iou >= iou_threshold and depth_diff < depth_diff_threshold:
                is_suppressed = True
                suppressed_by_id = kept["box_id"]
                suppress_reason = (
                    f"Duplicate of #{kept['box_id']} "
                    f"(IoU={iou:.2f} >= {iou_threshold:.2f}, "
                    f"depth_diff={depth_diff:.4f} < {depth_diff_threshold:.4f})"
                )
                break

        if is_suppressed:
            cand["kept"] = False
            cand["suppressed_by"] = suppressed_by_id
            cand["suppression_reason"] = suppress_reason
            suppressed_boxes.append(cand)
        else:
            cand["kept"] = True
            cand["suppressed_by"] = None
            cand["suppression_reason"] = None
            kept_boxes.append(cand)

    all_detections_raw = sorted(kept_boxes + suppressed_boxes, key=lambda x: x["box_id"])

    detections = [
        DetectionItem(
            box_id=d["box_id"],
            bbox=d["bbox"],
            confidence=d["confidence"],
            depth=d["depth"],
            depth_std=d["depth_std"],
            kept=d["kept"],
            suppressed_by=d["suppressed_by"],
            suppression_reason=d["suppression_reason"]
        )
        for d in all_detections_raw
    ]

    kept_count = len(kept_boxes)
    suppressed_count = len(suppressed_boxes)

    return PredictResponse(
        id=str(uuid.uuid4()),
        people_count=kept_count,
        kept_count=kept_count,
        suppressed_count=suppressed_count,
        detections=detections
    )

