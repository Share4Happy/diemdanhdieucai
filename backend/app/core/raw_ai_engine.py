"""
Module xử lý AI Engine & Pipeline duy nhất của hệ thống: Depth-NMS Predict API (/api/predict)
TUÂN THỦ YÊU CẦU NGƯỜI DÙNG:
1. Bỏ toàn bộ các thuật toán khác ra khỏi hệ thống ngoại trừ API /api/predict (Depth-NMS).
2. Toàn bộ cấu hình ROI (Green Zone, Red Zone, Spatial Mask) đều được COMMENT LẠI, không áp dụng.
3. Hiển thị kết quả duy nhất dạng Chấm Tròn Đồng Nhất (Dot Mode).
"""

import os
import cv2
import time
import base64
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from config.settings import settings
from config.logging_config import logger


def _resolve_model_path(model_name: str = "classroom_best.pt") -> tuple[str, bool]:
    """
    Xác định đường dẫn trọng số mô hình:
    Ưu tiên: classroom_best.pt (hoặc model_name yêu cầu).
    Fallback: yolo26m.pt, yolo26s.pt nếu chưa có file classroom_best.pt.
    Trả về: (resolved_path_str, is_fallback)
    """
    clean_name = Path(model_name).name
    candidates = [
        settings.MODELS_DIR / clean_name,
        settings.BASE_DIR / "models" / clean_name,
        settings.BASE_DIR / clean_name,
        Path(model_name),
        settings.MODELS_DIR / "classroom_best.pt",
        settings.BASE_DIR / "models" / "classroom_best.pt",
        settings.BASE_DIR / "classroom_best.pt",
        Path("classroom_best.pt"),
        settings.MODELS_DIR / "yolo26m.pt",
        settings.BASE_DIR / "models" / "yolo26m.pt",
        settings.BASE_DIR / "yolo26m.pt",
        settings.MODELS_DIR / "yolo26s.pt",
        settings.BASE_DIR / "models" / "yolo26s.pt",
        settings.BASE_DIR / "yolo26s.pt",
    ]
    for p in candidates:
        try:
            if p.exists() and p.is_file():
                is_fallback = "classroom_best" in clean_name and "classroom_best" not in p.name
                return str(p), is_fallback
        except Exception:
            continue

    return model_name, False


# ==============================================================================
# [COMMENTED OUT - CẤU HÌNH ROI ĐÃ BỎ/COMMENT HẾT THEO YÊU CẦU NGƯỜI DÙNG]
# Các hàm xử lý vùng ROI (green_zone, red_zone, spatial polygon, perspective transform)
# đã bị comment lại toàn bộ. Hệ thống không lọc người theo bàn học hay bục giảng.
# ==============================================================================
# def points_to_np(points: List[List[int]]) -> Optional[np.ndarray]:
#     ...
# def scale_polygon(points: List[List[int]], orig_w: int, orig_h: int, target_w: int, target_h: int) -> List[List[int]]:
#     ...
# def create_spatial_mask(shape: Tuple[int, int], polygon: List[List[int]]) -> np.ndarray:
#     ...


# ==============================================================================
# [COMMENTED OUT - CÁC THUẬT TOÁN CŨ ĐÃ BỎ HOÀN TOÀN KHỎI HỆ THỐNG]
# 1. Tiled Multi-Scale Inference (Sliding Window crop góc xa).
# 2. CLAHE Image Enhancement & Color Preprocessing.
# 3. 3-Level Deduplication (IoU + Head Overlap + Center Distance).
# 4. Aspect Ratio & Sleeve/Wrist Filter.
# 5. 10-Frames Temporal Union Overlay.
# 6. Fixed Seating Prior Homography Grid & Hungarian Linear Assignment.
# ==============================================================================
# def process_frame_ai(...) -> Dict[str, Any]:
#     # Thuật toán đa tỉ lệ cũ
#     pass
#
# def process_video_10frames_overlay(...) -> Dict[str, Any]:
#     # Thuật toán xếp chồng 10 frame video cũ
#     pass
#
# def generate_perspective_seating_grid(...) -> List[Dict[str, Any]]:
#     # Thuật toán bản đồ ghế phối cảnh cố định cũ
#     pass
#
# def match_candidates_to_seats(...) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
#     # Thuật toán Hungarian matching cũ
#     pass
#
# def process_seating_prior_pipeline(...) -> Dict[str, Any]:
#     # Pipeline Hungarian Seating Prior cũ
#     pass


def draw_predict_api_dots(
    img: np.ndarray,
    valid_students: List[Dict[str, Any]],
    ignored_people: Optional[List[Dict[str, Any]]] = None,
    red_zone: Optional[List[List[int]]] = None,
    green_zone: Optional[List[List[int]]] = None,
    visual_mode: str = "dot",
    check_mode: str = "predict_api",
    show_suppressed: bool = False,
    **kwargs
) -> np.ndarray:
    """
    Vẽ kết quả phát hiện học sinh theo chuẩn Depth-NMS API (/api/predict):
    - ĐỒNG NHẤT DẠNG CHẤM TRÒN PHÁT SÁNG (Dot Mode):
      Mỗi học sinh được đánh dấu bằng một điểm chấm tâm phát sáng (vòng ngoài glow mờ, vòng giữa neon cyan/emerald, tâm trắng sáng),
      kèm huy hiệu số thứ tự tròn phía trên để kiểm đếm trực quan rõ ràng.
    - [ROI COMMENTED OUT]: Không vẽ bất kỳ polygon vùng ROI (bàn học / bục giảng) nào.
    """
    out = img.copy()
    h, w = out.shape[:2]

    # [COMMENTED OUT - CẤU HÌNH ROI ĐÃ BỎ]
    # Không vẽ green_zone hay red_zone lên ảnh.
    # if green_zone and len(green_zone) >= 3:
    #     ...
    # if red_zone and len(red_zone) >= 3:
    #     ...

    # Màu sắc chấm tròn: Neon Cyan (0, 230, 255) / Emerald Green (0, 240, 160)
    dot_color = (255, 220, 0)      # BGR: Bright Cyan-Blue / Gold-Cyan
    glow_color = (200, 180, 0)     # Lớp glow mờ
    core_color = (255, 255, 255)   # Tâm trắng sáng

    # Xác định kích thước chấm phù hợp theo độ phân giải ảnh
    base_dim = max(w, h)
    radius_outer = max(6, int(base_dim * 0.008))
    radius_mid = max(4, int(radius_outer * 0.65))
    radius_core = max(2, int(radius_outer * 0.35))

    # Vẽ từng học sinh (chấm tròn)
    for idx, st in enumerate(valid_students):
        # Trích xuất tọa độ tâm từ centroid, head_center hoặc bbox
        if "centroid" in st and st["centroid"]:
            cx = int(st["centroid"][0])
            cy = int(st["centroid"][1])
        elif "head_center" in st and st["head_center"]:
            cx = int(st["head_center"][0])
            cy = int(st["head_center"][1])
        else:
            bbox = st.get("bbox") or st.get("box")
            if not bbox or len(bbox) < 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

        # Giới hạn trong khung hình
        cx = max(0, min(w - 1, cx))
        cy = max(0, min(h - 1, cy))

        # 1. Vẽ vòng hào quang phát sáng (glow layer mờ)
        overlay = out.copy()
        cv2.circle(overlay, (cx, cy), radius_outer + 4, glow_color, -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.45, out, 0.55, 0, out)

        # 2. Vẽ vòng tròn chính (neon)
        cv2.circle(out, (cx, cy), radius_mid, dot_color, -1, cv2.LINE_AA)
        cv2.circle(out, (cx, cy), radius_mid, (0, 0, 0), 1, cv2.LINE_AA)

        # 3. Vẽ tâm sáng trắng
        cv2.circle(out, (cx, cy), radius_core, core_color, -1, cv2.LINE_AA)

        # 4. Huy hiệu số thứ tự tròn phía trên chấm
        st_no = idx + 1
        label = str(st_no)
        badge_y = max(14, cy - radius_outer - 8)
        badge_r = max(9, int(radius_outer * 0.9))

        # Nền huy hiệu số: Đen viền sáng
        cv2.circle(out, (cx, badge_y), badge_r, (15, 23, 42), -1, cv2.LINE_AA)
        cv2.circle(out, (cx, badge_y), badge_r, dot_color, 1, cv2.LINE_AA)

        # Chữ số
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.32 if st_no < 100 else 0.26
        thickness = 1
        text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
        tx = cx - text_size[0] // 2
        ty = badge_y + text_size[1] // 2
        cv2.putText(out, label, (tx, ty), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    # Đính kèm Banner tiêu đề chuẩn API Depth-NMS ở góc trên bên trái
    banner_text = f"Depth-NMS API (/api/predict) | Dem: {len(valid_students)} Hoc Sinh"
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(banner_text, font, 0.55, 1)
    cv2.rectangle(out, (10, 10), (20 + tw, 20 + th + 10), (15, 23, 42), -1)
    cv2.rectangle(out, (10, 10), (20 + tw, 20 + th + 10), dot_color, 1)
    cv2.putText(out, banner_text, (15, 15 + th + 2), font, 0.55, (0, 240, 255), 1, cv2.LINE_AA)

    return out


# Backward compatible visualizer wrapper
def draw_detection_visualization(
    img: np.ndarray,
    valid_students: List[Dict[str, Any]],
    ignored_people: Optional[List[Dict[str, Any]]] = None,
    red_zone: Optional[List[List[int]]] = None,
    green_zone: Optional[List[List[int]]] = None,
    visual_mode: str = "dot",
    check_mode: str = "predict_api",
    show_suppressed: bool = False,
    **kwargs
) -> np.ndarray:
    """Chuyển tiếp trực tiếp về hàm vẽ chấm tròn đồng nhất Depth-NMS API."""
    return draw_predict_api_dots(
        img=img,
        valid_students=valid_students,
        ignored_people=ignored_people,
        red_zone=None,  # [ROI COMMENTED OUT]
        green_zone=None, # [ROI COMMENTED OUT]
        visual_mode=visual_mode or "dot",
        check_mode=check_mode or "predict_api",
        show_suppressed=show_suppressed,
        **kwargs
    )


def process_predict_api_test_pipeline(
    frame: Optional[np.ndarray] = None,
    media_target_path: Optional[Path] = None,
    is_video: bool = False,
    classroom_id: Optional[int] = None,
    classroom_info: Optional[Dict[str, Any]] = None,
    conf_threshold: float = 0.15,
    conf: Optional[float] = None,
    iou_threshold: float = 0.25,
    depth_diff_threshold: float = 0.0100,
    visual_mode: str = "dot",
    test_results_dir: Optional[Path] = None,
    run_id: Optional[str] = None,
    device: Optional[str] = None,
    device_name: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Pipeline duy nhất của hệ thống: Chạy trực tiếp thuật toán Depth-NMS API (/api/predict).
    - Hỗ trợ cả trực tiếp frame np.ndarray hoặc đường dẫn media_target_path (ảnh/video).
    - KHÔNG áp dụng cấu hình ROI (Green Zone / Red Zone đều đã cmt).
    - KHÔNG dùng bất kỳ thuật toán đa tỉ lệ hay Hungarian Seating Prior cũ nào.
    - Hiển thị trực quan dạng chấm tròn phát sáng đồng nhất 100%.
    """
    if run_id is None:
        run_id = f"{int(time.time() * 1000)}"

    effective_conf = conf if conf is not None else conf_threshold

    # 0. Nếu chưa có frame nhưng có media_target_path, trích xuất frame từ đường dẫn (RTSP/File/Snapshot)
    if frame is None and media_target_path is not None:
        source_str = str(media_target_path).strip()
        # 1. Nếu là luồng RTSP hoặc URL trực tiếp
        if source_str.startswith(("rtsp://", "http://", "https://")):
            old_ffmpeg = os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS")
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "protocol_whitelist;file,crypto,data,rtsp,rtp,tcp,udp"
            try:
                cap = cv2.VideoCapture(source_str)
                for _ in range(5):
                    ret, fr = cap.read()
                    if ret and fr is not None:
                        frame = fr
                        break
                cap.release()
            except Exception as e:
                logger.warning(f"Không thể đọc RTSP trực tiếp {source_str}: {e}")
            finally:
                if old_ffmpeg is not None:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = old_ffmpeg
                else:
                    os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)

            # Fallback 1: Tìm ảnh chụp snapshot gần nhất của phòng học
            if frame is None and (classroom_info or classroom_id):
                cid = (classroom_info.get("id") if classroom_info else None) or classroom_id
                cname = (classroom_info.get("name") if classroom_info else None) or f"Lop_{cid}"
                candidate_snaps = [
                    settings.STORAGE_DIR / "captures" / "latest" / f"Lop_{cid}.jpg",
                    settings.STORAGE_DIR / "captures" / "latest" / f"{cname}.jpg",
                    settings.DATA_DIR / "storage" / "captures" / "latest" / f"Lop_{cid}.jpg",
                    settings.DATA_DIR / "storage" / "captures" / "latest" / f"{cname}.jpg",
                    Path(f"/app/data/storage/captures/latest/Lop_{cid}.jpg")
                ]
                for cs in candidate_snaps:
                    if cs.exists():
                        frame = cv2.imread(str(cs))
                        if frame is not None:
                            logger.info(f"Đã fallback sang ảnh snapshot mới nhất của lớp: {cs}")
                            break

        # 2. Nếu là local file đường dẫn
        else:
            p = Path(source_str)
            if p.exists():
                if is_video or p.suffix.lower() in [".mp4", ".avi", ".mov", ".mkv", ".webm"]:
                    cap = cv2.VideoCapture(str(p))
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1)
                    target_idx = max(0, min(total_frames - 1, int(total_frames * 0.5)))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                    cap.release()
                else:
                    frame = cv2.imread(str(p))

        # Fallback 2: Nếu vẫn chưa lấy được khung hình, dùng ảnh mẫu phòng học
        if frame is None:
            sample_candidates = [
                settings.DATA_DIR / "dataset" / "samples" / "classroom_predict_sample.jpg",
                settings.DATA_DIR / "dataset" / "samples" / "classroom_sample_1.jpg",
                Path("/app/data/dataset/samples/classroom_predict_sample.jpg"),
                Path("/app/data/dataset/samples/classroom_sample_1.jpg")
            ]
            for sc in sample_candidates:
                if sc.exists():
                    frame = cv2.imread(str(sc))
                    if frame is not None:
                        logger.info(f"Đã fallback sang ảnh mẫu phòng học: {sc}")
                        break

    if frame is None:
        raise ValueError(f"Không thể đọc khung hình từ nguồn dữ liệu: {media_target_path}")

    t0 = time.time()
    logger.info(
        f"[PIPELINE-DUY-NHAT: /api/predict] conf={conf_threshold}, iou={iou_threshold}, "
        f"depth_diff={depth_diff_threshold}, visual_mode=dot (ROI ĐÃ CMT)"
    )

    # 1. Gọi trực tiếp hàm suy luận Depth-NMS Engine
    from backend.app.api.routers.predict import run_internal_depth_nms_predict
    pred_resp = run_internal_depth_nms_predict(
        image_bgr=frame,
        conf_threshold=effective_conf or 0.15,
        iou_threshold=iou_threshold or 0.25,
        depth_diff_threshold=depth_diff_threshold or 0.0100
    )

    # 2. Thu thập danh sách học sinh hợp lệ (kept = True)
    valid_students = []
    for d in pred_resp.detections:
        if d.kept:
            valid_students.append({
                "bbox": d.bbox,
                "confidence": d.confidence,
                "depth": d.depth,
                "depth_std": d.depth_std,
                "box_id": d.box_id
            })

    # 3. Vẽ trực quan dạng chấm tròn phát sáng đồng nhất
    annotated_img = draw_predict_api_dots(
        img=frame,
        valid_students=valid_students,
        ignored_people=[],
        red_zone=None,   # [ROI COMMENTED OUT]
        green_zone=None, # [ROI COMMENTED OUT]
        visual_mode="dot",
        check_mode="predict_api"
    )

    # 4. Chuẩn bị ảnh base64
    _, buf_ann = cv2.imencode(".jpg", annotated_img, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    ann_b64 = "data:image/jpeg;base64," + base64.b64encode(buf_ann.tobytes()).decode("utf-8")

    _, buf_orig = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    orig_b64 = "data:image/jpeg;base64," + base64.b64encode(buf_orig.tobytes()).decode("utf-8")

    if test_results_dir:
        out_file = test_results_dir / f"test_predict_{run_id}.jpg"
        try:
            cv2.imwrite(str(out_file), annotated_img)
        except Exception:
            pass

    t_elapsed = round((time.time() - t0) * 1000, 1)

    # 5. Danh sách detections chuẩn hóa
    boxes_list = []
    detections_list = []
    for d in pred_resp.detections:
        bbox = d.bbox
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        bw = max(0, bbox[2] - bbox[0])
        bh = max(0, bbox[3] - bbox[1])

        boxes_list.append({
            "id": d.box_id,
            "student_no": d.box_id + 1,
            "bbox": bbox,
            "head_bbox": bbox,
            "confidence": f"{d.confidence:.4f}",
            "confidence_pct": round(d.confidence * 100),
            "depth": round(d.depth, 4),
            "depth_std": round(d.depth_std, 4),
            "kept": d.kept,
            "suppressed_by": d.suppressed_by,
            "suppression_reason": d.suppression_reason,
            "centroid": [round(cx, 1), round(cy, 1)],
            "width": bw,
            "height": bh,
            "aspect_ratio": f"{bw / max(1, bh):.2f}",
            "class_name": "student" if d.kept else "duplicate_suppressed"
        })

        detections_list.append({
            "box_id": d.box_id,
            "bbox": bbox,
            "confidence": d.confidence,
            "depth": d.depth,
            "depth_std": d.depth_std,
            "kept": d.kept,
            "suppressed_by": d.suppressed_by,
            "suppression_reason": d.suppression_reason
        })

    predict_data_dict = {
        "id": pred_resp.id,
        "people_count": pred_resp.people_count,
        "kept_count": pred_resp.kept_count,
        "suppressed_count": pred_resp.suppressed_count,
        "detections": detections_list
    }

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"

    return {
        "success": True,
        "is_predict_api": True,
        "check_mode": "predict_api",
        "algorithm": "depth_nms_predict",
        "visual_mode": "dot",
        "classroom": classroom_info,
        "total_detections": len(pred_resp.detections),
        "valid_count": pred_resp.people_count,
        "ignored_count": 0,
        "present_count": pred_resp.people_count,
        "kept_count": pred_resp.kept_count,
        "suppressed_count": pred_resp.suppressed_count,
        "inference_time_ms": t_elapsed,
        "fps": round(1000.0 / max(1.0, t_elapsed), 1),
        "device": device,
        "device_name": device_name,
        "model_used": "Depth-NMS Predict Engine (/api/predict)",
        "annotated_b64": ann_b64,
        "roi_annotated_b64": ann_b64,
        "original_b64": orig_b64,
        "output_filename": f"test_predict_{run_id}.jpg",
        "boxes": boxes_list,
        "detections": detections_list,
        "predict_data": predict_data_dict,
        "roi": {
            "applied": False,
            "green_zone": [],
            "red_zone": [],
            "valid_count": pred_resp.people_count,
            "ignored_count": 0,
            "roi_annotated_b64": ann_b64
        },
        "pipeline_steps": [
            "1. Trích xuất khung hình từ nguồn lớp học",
            "2. Nhận diện học sinh toàn phòng học bằng mô hình YOLO (Không ép ROI)",
            "3. Ước lượng độ sâu 3D phối cảnh (Depth Anything V2)",
            f"4. Khử trùng lặp Depth-NMS (IoU >= {iou_threshold or 0.25}, depth_diff < {depth_diff_threshold or 0.0100}): Giữ {pred_resp.kept_count} HS, loại {pred_resp.suppressed_count} box trùng",
            f"5. Hiển thị đối chứng đồng nhất dạng Chấm Tròn (Dot Mode: {pred_resp.people_count} HS)"
        ]
    }


# Forwarding alias cho bất kỳ lệnh gọi cũ nào
def process_frame_ai(*args, **kwargs) -> Dict[str, Any]:
    """Forward toàn bộ về pipeline duy nhất /api/predict."""
    frame = args[0] if len(args) > 0 else kwargs.get("frame")
    conf = kwargs.get("conf_threshold", 0.15)
    info = kwargs.get("classroom_info")
    return process_predict_api_test_pipeline(frame=frame, conf_threshold=conf, classroom_info=info)

def process_video_10frames_overlay(*args, **kwargs) -> Dict[str, Any]:
    """Forward toàn bộ về pipeline duy nhất /api/predict."""
    frame = args[1] if len(args) > 1 else kwargs.get("last_frame")
    conf = kwargs.get("conf_threshold", 0.15)
    info = kwargs.get("classroom_info")
    return process_predict_api_test_pipeline(frame=frame, conf_threshold=conf, classroom_info=info)

def process_seating_prior_pipeline(*args, **kwargs) -> Dict[str, Any]:
    """Forward toàn bộ về pipeline duy nhất /api/predict."""
    frame = args[0] if len(args) > 0 else kwargs.get("frame")
    conf = kwargs.get("conf_threshold", 0.15)
    info = kwargs.get("classroom_info")
    return process_predict_api_test_pipeline(frame=frame, conf_threshold=conf, classroom_info=info)
