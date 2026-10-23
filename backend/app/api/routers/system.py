import os
import cv2
import time
import uuid
import base64
import shutil
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, Body, Request
from fastapi.responses import FileResponse, Response
from config.settings import settings
from config.logging_config import logger
from backend.app.api.deps import get_current_user, require_admin

router = APIRouter(tags=["System"])

@router.get("/database/info")
async def get_database_info(_admin=Depends(require_admin)):
    """Lấy thông tin cấu hình Cơ Sở Dữ Liệu hiện tại (PostgreSQL / MySQL / SQLite) — chỉ admin.
    Không trả về DATABASE_URL chi tiết để tránh lộ chuỗi kết nối chứa mật khẩu."""
    db_type = "SQLite"
    if "postgres" in settings.DATABASE_URL:
        db_type = "PostgreSQL"
    elif "mysql" in settings.DATABASE_URL:
        db_type = "MySQL"

    return {
        "database_url": None,  # Combo test: admin có thể lấy thật qua biến môi trường; không hiển thị trực tiếp
        "db_type": db_type,
        "status": "Kết nối thành công (Active)",
        "supported_drivers": ["sqlite3", "psycopg2 (PostgreSQL)", "pymysql (MySQL)"]
    }

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "architecture": "Decoupled Backend (FastAPI REST API)",
        "ai_model": {
            "family": getattr(settings, "YOLO_FAMILY", "YOLO26"),
            "variant": getattr(settings, "YOLO_VARIANT", "26m"),
            "model_name": settings.YOLO_MODEL_NAME,
            "imgsz": settings.YOLO_IMGSZ,
            "confidence_threshold": settings.AI_CONFIDENCE_THRESHOLD
        }
    }

@router.get("/ai/info")
@router.get("/system/ai/info")
async def get_ai_info():
    """Lấy thông tin chi tiết mô hình AI (YOLO26m), thiết bị tính toán (GPU/CPU) và tham số nhận diện."""
    from backend.app.core.detector import detector
    return {
        "success": True,
        "data": detector.get_model_info()
    }

@router.get("/system/classrooms-media")
async def get_classrooms_media(_user=Depends(get_current_user)):
    """Lấy danh mục dữ liệu 5 ảnh và 1 video 15s của 30 lớp học kèm thông tin sĩ số."""
    import json
    json_path = settings.CLASSROOMS_MEDIA_DIR / "danh_sach_si_so_toan_truong.json"
    if not json_path.exists():
        return {"success": False, "message": "Chưa khởi tạo bộ dữ liệu classrooms_media", "classes": []}

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"success": True, "data": data}

@router.post("/system/bind-sample-media")
async def bind_sample_media(media_type: str = "video", _admin=Depends(require_admin)):
    """
    Tùy chọn tự động gán nguồn rtsp_url của 30 lớp trong CSDL trỏ tới file video 15s hoặc ảnh mẫu
    để người dùng có thể chạy thử nghiệm tính năng điểm danh toàn diện ngay mà không cần camera vật lý.
    media_type: 'video' (mặc định video 15s) hoặc 'image' (ảnh 1)
    """
    from database.db_session import SessionLocal
    from database.models import Classroom
    db = SessionLocal()
    try:
        classrooms = db.query(Classroom).all()
        updated_count = 0
        for c in classrooms:
            clean_code = c.code.replace("LOP_", "")
            class_folder = settings.CLASSROOMS_MEDIA_DIR / f"Lop_{clean_code}"
            if class_folder.exists():
                if media_type == "image":
                    target_file = class_folder / "image_1.jpg"
                elif media_type == "camera":
                    ch_num = c.channel_number or 1
                    target_vid = settings.BASE_DIR / "camera" / f"{ch_num}.MP4"
                    target_cam = settings.BASE_DIR / "camera" / f"{ch_num}.JPG"
                    if target_vid.exists():
                        c.rtsp_url = f"camera/{ch_num}.MP4"
                        updated_count += 1
                        continue
                    elif target_cam.exists():
                        c.rtsp_url = f"camera/{ch_num}.JPG"
                        updated_count += 1
                        continue
                else:
                    target_file = class_folder / "video_15s.mp4"
                
                if target_file.exists():
                    rel_path = f"dataset/classrooms_media/Lop_{clean_code}/{target_file.name}"
                    c.rtsp_url = rel_path
                    updated_count += 1
        db.commit()
        return {
            "success": True, 
            "message": f"Đã liên kết thành công nguồn dữ liệu mẫu {media_type} cho {updated_count} lớp học!",
            "updated_count": updated_count
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Lỗi khi liên kết nguồn: {str(e)}"}
    finally:
        db.close()


@router.post("/system/reset-to-camera-photos")
async def reset_to_camera_photos(_user=Depends(get_current_user)):
    """Khởi tạo sạch 30 camera chuẩn của trường Điều Cải theo cấu hình hệ thống."""
    from database.db_session import SessionLocal, seed_default_classes
    from database.models import Classroom, ROIPolygon, AttendanceDetail

    db = SessionLocal()
    try:
        db.query(AttendanceDetail).delete()
        db.query(ROIPolygon).delete()
        db.query(Classroom).delete()
        db.commit()
        seed_default_classes(db)
        return {"success": True, "message": "Đã thiết lập thành công danh sách camera chuẩn trường THPT Điều Cải!"}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Lỗi: {str(e)}"}
    finally:
        db.close()


from backend.app.core.raw_ai_engine import (
    _resolve_model_path,
    # [COMMENTED OUT - ĐÃ BỎ CÁC THUẬT TOÁN CŨ, CHỈ DÙNG DUY NHẤT API /api/predict]
    # process_frame_ai,
    # process_video_10frames_overlay,
    # process_seating_prior_pipeline,
    process_predict_api_test_pipeline,
)


def prune_test_results_cache(test_dir: Path, max_age_seconds: int = 1800):
    """Tự động dọn dẹp các tệp video và frame test cũ, bảo vệ file kết quả mới nhất raw_conf005.jpg."""
    try:
        now_ts = time.time()
        for p in test_dir.iterdir():
            if not p.is_file():
                continue
            if p.name == "raw_conf005.jpg":
                continue
            if p.name.startswith(("test_input_", "frame_", "raw_conf", "roi_result_")):
                try:
                    if (now_ts - p.stat().st_mtime) > max_age_seconds:
                        p.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"Không thể dọn dẹp tệp test cũ: {e}")


@router.post("/system/test-raw-ai")
async def test_raw_ai(
    file: Optional[UploadFile] = File(None),
    sample_path: Optional[str] = Form(None),
    conf: float = Form(0.05),
    iou: float = Form(0.70),
    imgsz: int = Form(1280),
    max_det: int = Form(300),
    model_name: str = Form("classroom_best.pt"),
    apply_roi: bool = Form(True),
    classroom_id: Optional[int] = Form(None),
    green_zone_json: Optional[str] = Form(None),
    red_zone_json: Optional[str] = Form(None),
    check_mode: str = Form("raw"),             # 'raw', 'production', 'overlay_10frames', 'seating_prior'
    visual_mode: str = Form("dot"),             # 'dot', 'box', 'both'
    target_classes: Optional[str] = Form("0"),   # '0' (Chỉ học sinh/đầu), 'all' (Tất cả nhãn), hoặc '0,24,56'
    # Các tham số cấu hình tắt/mở từng chỉ số của Production Pipeline
    prod_clahe: bool = Form(True),
    prod_multiscale: bool = Form(True),
    prod_dedup: bool = Form(True),
    prod_sleeve_filter: bool = Form(True),
    prod_head_crop: bool = Form(True),
    prod_quality_check: bool = Form(True),
    prod_dedup_dist: float = Form(8.0),
    prod_ios_thresh: float = Form(0.48),
    prod_overlap_zone: bool = Form(True),
    prod_overlap_radius: float = Form(20.0),
    prod_show_overlap_zones: bool = Form(True),
    # Tham số cấu hình Số lượng Frame và Khoảng thời gian
    target_frames: int = Form(10),
    window_seconds: float = Form(60.0),
    # Tham số cấu hình Bản Đồ Ghế Ngồi Cố Định (Fixed Seating Prior)
    seat_map_mode: str = Form("grid_perspective"),
    seat_rows: int = Form(5),
    seat_cols: int = Form(8),
    seat_tolerance: float = Form(35.0),
    seat_strict_filter: bool = Form(True),
    show_vacant_seats: bool = Form(True),
    seat_layout_template: str = Form("2_aisle_center"),
    seat_aisle_ratio: float = Form(0.14),
    seat_column_groups: Optional[str] = Form("4,4"),
    # Tham số cấu hình Depth-NMS (/api/predict)
    iou_threshold: float = Form(0.25),
    depth_diff_threshold: float = Form(0.0100),
):
    """
    Điểm cuối kiểm thử AI đa năng:
    - Hỗ trợ tải lên CẢ ẢNH VÀ VIDEO (.mp4, .avi, .mov, .mkv, .webm) hoặc lấy trực tiếp từ Camera Lớp Học.
    - Hỗ trợ các chế độ kiểm tra:
        1. 'production': Chu trình kiểm tra sĩ số thực tế (CLAHE, Tiled Multi-Scale, Lọc độ nét/độ sáng, Khử trùng lặp 3 cấp, ROI).
        2. 'raw': Chạy mô hình YOLO nguyên bản không qua bất kỳ bộ lọc nào.
        3. 'overlay_10frames': Thuật toán xếp chồng đa khung hình theo số lượng và khoảng thời gian tùy chỉnh.
        4. 'seating_prior': Thuật toán Bản Đồ Ghế Ngồi Cố Định (Fixed Seating Prior, Homography 3D & Hungarian Matching).
    - Hỗ trợ lọc theo nhãn ('0' cho học sinh/đầu người, 'all', hoặc tùy chọn).
    - Hỗ trợ kiểu hiển thị: 'dot' (Chấm phát sáng không khoanh vuông), 'box' (Khoanh vuông), 'both' (Cả hai).
    """
    test_results_dir = settings.STORAGE_DIR / "test_results"
    test_results_dir.mkdir(parents=True, exist_ok=True)
    prune_test_results_cache(test_results_dir)

    run_id = uuid.uuid4().hex[:8]

    # Kiểm tra loại tệp tin (Ảnh hay Video)
    video_exts = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
    is_video = False
    file_ext = ".jpg"
    classroom_info = None

    if file and file.filename:
        filename_lower = file.filename.lower()
        if any(filename_lower.endswith(ext) for ext in video_exts):
            is_video = True
            file_ext = Path(file.filename).suffix.lower()
        elif any(filename_lower.endswith(ext) for ext in [".png", ".webp", ".bmp"]):
            file_ext = Path(file.filename).suffix.lower()
    elif sample_path:
        sample_lower = sample_path.lower()
        if any(sample_lower.endswith(ext) for ext in video_exts):
            is_video = True
            file_ext = Path(sample_path).suffix.lower()
        elif any(sample_lower.endswith(ext) for ext in [".png", ".webp", ".bmp"]):
            file_ext = Path(sample_path).suffix.lower()
    elif classroom_id:
        is_video = True

    media_target_path = test_results_dir / f"test_input_{run_id}{file_ext}"

    # 1. Thu nhận dữ liệu tệp tin từ UploadFile, Sample Path hoặc Camera Quản Lý Lớp Học
    if file and file.filename:
        with open(media_target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        if media_target_path.stat().st_size == 0:
            media_target_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Tệp tin tải lên rỗng")
    elif sample_path:
        clean_rel = sample_path.strip().lstrip("/")
        potential_sample_paths = [
            settings.BASE_DIR / clean_rel,
            settings.DATA_DIR / clean_rel,
            settings.STORAGE_DIR / clean_rel,
            Path(clean_rel)
        ]
        src_sample = next((p for p in potential_sample_paths if p.exists() and p.is_file()), None)
        if not src_sample:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp tin mẫu: {sample_path}")
        shutil.copy2(src_sample, media_target_path)
    elif classroom_id:
        from database.db_session import SessionLocal
        from database.models import Classroom
        db_cls = SessionLocal()
        try:
            cls_obj = db_cls.query(Classroom).filter(Classroom.id == classroom_id).first()
            if not cls_obj:
                raise HTTPException(status_code=404, detail=f"Không tìm thấy camera/lớp học với ID {classroom_id}")
            classroom_info = {
                "id": cls_obj.id,
                "name": cls_obj.name,
                "code": cls_obj.code,
                "room_number": cls_obj.room_number,
                "standard_count": cls_obj.standard_count,
                "rtsp_url": cls_obj.rtsp_url
            }
            source_url = (cls_obj.rtsp_url or "").strip()
        finally:
            db_cls.close()

        # Nguồn camera trực tiếp từ lớp học
        is_video = True
        media_target_path = source_url
    else:
        raise HTTPException(status_code=400, detail="Vui lòng tải lên một tệp tin, chọn mẫu hoặc chọn camera lớp học")

    # 2. Định vị mô hình AI
    resolved_model_path, is_fallback = _resolve_model_path(model_name)
    logger.info(f"[Test AI] Model: {resolved_model_path} | Check Mode: {check_mode} | Visual: {visual_mode} | Video: {is_video}")

    try:
        from ultralytics import YOLO
    except ImportError:
        raise HTTPException(status_code=500, detail="Môi trường chưa cài đặt 'ultralytics'")

    try:
        import torch
        device = "0" if torch.cuda.is_available() else "cpu"
        device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    except Exception:
        device = "cpu"
        device_name = "CPU"

    try:
        m = YOLO(resolved_model_path)
    except Exception as e_load:
        raise HTTPException(status_code=500, detail=f"Không thể nạp mô hình AI: {str(e_load)}")

    # 3. Phân giải cấu hình ROI
    import json
    from backend.app.core.roi_manager import ROIManager
    from database.db_session import SessionLocal
    from database.models import Classroom

    green_zone = []
    red_zone = []

    if classroom_id:
        db = SessionLocal()
        try:
            cls_obj = db.query(Classroom).filter(Classroom.id == classroom_id).first()
            if cls_obj and cls_obj.roi:
                green_zone = cls_obj.roi.green_zone or []
                red_zone = cls_obj.roi.red_zone or []
        finally:
            db.close()

    if green_zone_json:
        try:
            green_zone = json.loads(green_zone_json)
        except Exception:
            pass

    # =========================================================================
    # [CẤU HÌNH ROI ĐÃ ĐƯỢC COMMENT LẠI TOÀN BỘ THEO YÊU CẦU NGƯỜI DÙNG]
    # Không áp dụng Green Zone (bàn học), Red Zone (bục giảng) hay bất kỳ vùng giới hạn nào
    # =========================================================================
    # if green_zone_json:
    #     try:
    #         green_zone = json.loads(green_zone_json)
    #     except Exception:
    #         pass
    # if red_zone_json:
    #     try:
    #         red_zone = json.loads(red_zone_json)
    #     except Exception:
    #         pass
    green_zone = []
    red_zone = []
    apply_roi = False

    # =========================================================================
    # HỆ THỐNG DUY NHẤT: DEPTH-NMS PREDICT API (/api/predict)
    # Bỏ toàn bộ các thuật toán khác ra khỏi hệ thống, chạy thuần túy 100% qua API
    # =========================================================================
    return process_predict_api_test_pipeline(
        media_target_path=media_target_path,
        is_video=is_video,
        classroom_id=classroom_id,
        classroom_info=classroom_info,
        visual_mode=visual_mode or "dot",
        iou_threshold=iou_threshold or 0.25,
        depth_diff_threshold=depth_diff_threshold or 0.0100,
        conf=conf,
        test_results_dir=test_results_dir,
        run_id=run_id,
        device=device,
        device_name=device_name
    )

    # =========================================================================
    # [CÁC THUẬT TOÁN CŨ ĐÃ ĐƯỢC COMMENT LẠI HOÀN TOÀN THEO YÊU CẦU NGƯỜI DÙNG]
    # - Thuật toán Bản Đồ Ghế Ngồi Cố Định (Fixed Seating Prior) -> [COMMENTED OUT]
    # - Thuật toán Xếp Chồng 10 Frame (Temporal Union Overlay) -> [COMMENTED OUT]
    # - Thuật toán Production Pipeline cũ (Tiled Multi-Scale, CLAHE, Dedup 3 cấp) -> [COMMENTED OUT]
    # - Thuật toán Mô Hình Thô (Raw YOLO Predict) -> [COMMENTED OUT]
    # =========================================================================
    if is_video:
        # 1. Kích hoạt Thuật toán Xếp Chồng Khung Hình theo cấu hình (target_frames & window_seconds)
        if check_mode == "overlay_10frames" or classroom_id is not None or str(media_target_path).startswith("rtsp://"):
            return process_video_10frames_overlay(
                media_target_path=media_target_path,
                model_inst=m,
                conf=conf,
                iou=iou,
                imgsz=imgsz,
                max_det=max_det,
                device=device,
                target_classes=target_classes,
                green_zone=green_zone,
                red_zone=red_zone,
                apply_roi=apply_roi,
                visual_mode=visual_mode,
                test_results_dir=test_results_dir,
                run_id=run_id,
                resolved_model_path=resolved_model_path,
                device_name=device_name,
                prod_clahe=prod_clahe,
                prod_multiscale=prod_multiscale,
                prod_dedup=prod_dedup,
                prod_sleeve_filter=prod_sleeve_filter,
                prod_head_crop=prod_head_crop,
                prod_quality_check=prod_quality_check,
                prod_dedup_dist=prod_dedup_dist,
                prod_ios_thresh=prod_ios_thresh,
                prod_overlap_zone=prod_overlap_zone,
                prod_overlap_radius=prod_overlap_radius,
                prod_show_overlap_zones=prod_show_overlap_zones,
                target_frames=target_frames,
                window_seconds=window_seconds,
                classroom_info=classroom_info
            )

        old_ffmpeg_opts = os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS")
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "protocol_whitelist;file,crypto,data,rtsp,rtp,tcp,udp"
        try:
            cap = cv2.VideoCapture(str(media_target_path))
        finally:
            if old_ffmpeg_opts is not None:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = old_ffmpeg_opts
            else:
                os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)

        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Không thể mở hoặc đọc dữ liệu video này")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        duration_sec = round(total_frames / max(1.0, fps), 1)
        v_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        v_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Tuyệt đối không tự sinh ROI giả định
        if not green_zone or len(green_zone) < 3:
            green_zone = []
        if not red_zone or len(red_zone) < 3:
            red_zone = []
        if not green_zone and not red_zone:
            apply_roi = False

        # Lấy 6 - 8 khung hình rải đều theo thời gian để phân tích
        sample_count = min(8, max(4, total_frames // max(1, int(fps))))
        step = max(1, total_frames // sample_count)
        frame_indices = [min(total_frames - 1, i * step) for i in range(sample_count)]

        video_frames = []
        all_counts = []
        start_time = time.time()

        for f_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            frame_res = process_frame_ai(
                frame=frame,
                check_mode=check_mode,
                visual_mode=visual_mode,
                target_classes=target_classes,
                conf=conf,
                iou=iou,
                imgsz=imgsz,
                max_det=max_det,
                green_zone=green_zone,
                red_zone=red_zone,
                apply_roi=apply_roi,
                model_inst=m,
                resolved_model_path=resolved_model_path,
                device=device,
                prod_clahe=prod_clahe,
                prod_multiscale=prod_multiscale,
                prod_dedup=prod_dedup,
                prod_sleeve_filter=prod_sleeve_filter,
                prod_head_crop=prod_head_crop,
                prod_quality_check=prod_quality_check,
                prod_dedup_dist=prod_dedup_dist,
                prod_ios_thresh=prod_ios_thresh
            )

            _, buf_ann = cv2.imencode(".jpg", frame_res["annotated_img"])
            f_b64 = "data:image/jpeg;base64," + base64.b64encode(buf_ann.tobytes()).decode("utf-8")

            _, buf_orig = cv2.imencode(".jpg", frame)
            orig_b64 = "data:image/jpeg;base64," + base64.b64encode(buf_orig.tobytes()).decode("utf-8")

            ts = round(f_idx / max(1.0, fps), 1)
            all_counts.append(frame_res["valid_count"])

            video_frames.append({
                "frame_index": f_idx,
                "timestamp_sec": ts,
                "present_count": frame_res["valid_count"],
                "ignored_count": frame_res["ignored_count"],
                "total_detections": frame_res["total_detections"],
                "annotated_b64": f_b64,
                "original_b64": orig_b64,
                "boxes": frame_res["boxes"],
                "quality": {
                    "brightness": frame_res["brightness"],
                    "sharpness": frame_res["sharpness"],
                    "status": frame_res["quality_status"]
                }
            })

        cap.release()
        total_time_ms = round((time.time() - start_time) * 1000, 1)

        median_count = int(np.median(all_counts)) if all_counts else 0
        min_count = min(all_counts) if all_counts else 0
        max_count = max(all_counts) if all_counts else 0
        # Độ ổn định: tỷ lệ khung hình có sĩ số nằm trong biên độ ±1 so với trung vị
        stability_pct = round(sum(1 for c in all_counts if abs(c - median_count) <= 1) / max(1, len(all_counts)) * 100, 1)

        # Lưu ảnh frame 0 làm ảnh mặc định
        primary_frame = video_frames[0] if video_frames else None
        if primary_frame:
            first_frame_bytes = base64.b64decode(primary_frame["annotated_b64"].split(",", 1)[1])
            target_raw_conf005 = test_results_dir / "raw_conf005.jpg"
            root_raw_conf005 = settings.BASE_DIR / "raw_conf005.jpg"
            with open(target_raw_conf005, "wb") as f_out:
                f_out.write(first_frame_bytes)
            try:
                shutil.copy2(str(target_raw_conf005), str(root_raw_conf005))
            except Exception:
                pass

        return {
            "success": True,
            "is_video": True,
            "video_info": {
                "total_frames": total_frames,
                "fps": round(fps, 1),
                "duration_sec": duration_sec,
                "resolution": f"{v_w}x{v_h}",
                "sampled_count": len(video_frames),
                "stabilized_count": median_count,
                "min_count": min_count,
                "max_count": max_count,
                "stability_pct": stability_pct
            },
            "total_detections": primary_frame["total_detections"] if primary_frame else 0,
            "valid_count": median_count,
            "ignored_count": primary_frame["ignored_count"] if primary_frame else 0,
            "inference_time_ms": total_time_ms,
            "fps": round(1000.0 / max(1.0, total_time_ms / max(1, len(video_frames))), 1),
            "device": device,
            "device_name": device_name,
            "model_used": Path(resolved_model_path).name,
            "check_mode": check_mode,
            "visual_mode": visual_mode,
            "target_classes": target_classes,
            "annotated_b64": primary_frame["annotated_b64"] if primary_frame else None,
            "roi_annotated_b64": primary_frame["annotated_b64"] if primary_frame else None,
            "original_b64": primary_frame["original_b64"] if primary_frame else None,
            "output_filename": "raw_conf005.jpg",
            "video_frames": video_frames,
            "boxes": primary_frame["boxes"] if primary_frame else [],
            "pipeline_steps": frame_res.get("pipeline_steps", []) if 'frame_res' in locals() else [],
            "prod_config": {
                "clahe": prod_clahe,
                "multiscale": prod_multiscale,
                "dedup": prod_dedup,
                "sleeve_filter": prod_sleeve_filter,
                "head_crop": prod_head_crop,
                "quality_check": prod_quality_check,
                "dedup_dist": prod_dedup_dist,
                "ios_thresh": prod_ios_thresh
            },
            "roi": {
                "applied": apply_roi,
                "green_zone": green_zone,
                "red_zone": red_zone,
                "valid_count": median_count,
                "ignored_count": primary_frame["ignored_count"] if primary_frame else 0,
                "roi_annotated_b64": primary_frame["annotated_b64"] if primary_frame else None
            }
        }

    # =========================================================================
    # KỊCH BẢN B: XỬ LÝ ẢNH TĨNH (.jpg, .png, ...)
    # =========================================================================
    orig_img = cv2.imread(str(media_target_path))
    if orig_img is None:
        raise HTTPException(status_code=400, detail="Tệp tin không phải là hình ảnh hợp lệ hoặc bị hỏng")
    img_h, img_w = orig_img.shape[:2]

    # Lưu thêm frame.png chuẩn như cú pháp người dùng
    try:
        shutil.copy2(media_target_path, test_results_dir / "frame.png")
        shutil.copy2(media_target_path, settings.BASE_DIR / "frame.png")
    except Exception:
        pass

    # Tuyệt đối không tự sinh ROI giả định cho ảnh tĩnh
    if not green_zone or len(green_zone) < 3:
        green_zone = []
    if not red_zone or len(red_zone) < 3:
        red_zone = []
    if not green_zone and not red_zone:
        apply_roi = False

    start_time = time.time()
    res = process_frame_ai(
        frame=orig_img,
        check_mode=check_mode,
        visual_mode=visual_mode,
        target_classes=target_classes,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        max_det=max_det,
        green_zone=green_zone,
        red_zone=red_zone,
        apply_roi=apply_roi,
        model_inst=m,
        resolved_model_path=resolved_model_path,
        device=device,
        prod_clahe=prod_clahe,
        prod_multiscale=prod_multiscale,
        prod_dedup=prod_dedup,
        prod_sleeve_filter=prod_sleeve_filter,
        prod_head_crop=prod_head_crop,
        prod_quality_check=prod_quality_check,
        prod_dedup_dist=prod_dedup_dist,
        prod_ios_thresh=prod_ios_thresh
    )
    inference_time_ms = round((time.time() - start_time) * 1000, 1)

    # Lưu kết quả ra file raw_conf005.jpg
    raw_save_path = test_results_dir / f"raw_conf{str(conf).replace('.', '')}_{run_id}.jpg"
    cv2.imwrite(str(raw_save_path), res["annotated_img"])

    target_raw_conf005 = test_results_dir / "raw_conf005.jpg"
    root_raw_conf005 = settings.BASE_DIR / "raw_conf005.jpg"
    try:
        shutil.copy2(str(raw_save_path), str(target_raw_conf005))
        shutil.copy2(str(raw_save_path), str(root_raw_conf005))
    except Exception:
        pass

    with open(raw_save_path, "rb") as f_ann:
        annotated_b64 = "data:image/jpeg;base64," + base64.b64encode(f_ann.read()).decode("utf-8")
    with open(media_target_path, "rb") as f_orig:
        original_b64 = "data:image/jpeg;base64," + base64.b64encode(f_orig.read()).decode("utf-8")

    avg_conf = round(sum(b["confidence"] for b in res["boxes"]) / len(res["boxes"]), 4) if res["boxes"] else 0.0

    return {
        "success": True,
        "is_video": False,
        "total_detections": res["total_detections"],
        "valid_count": res["valid_count"],
        "ignored_count": res["ignored_count"],
        "average_confidence": avg_conf,
        "inference_time_ms": inference_time_ms,
        "fps": round(1000.0 / max(1.0, inference_time_ms), 1),
        "device": device,
        "device_name": device_name,
        "model_used": Path(resolved_model_path).name,
        "model_full_path": resolved_model_path,
        "is_fallback": is_fallback,
        "image_resolution": f"{img_w}x{img_h}",
        "check_mode": check_mode,
        "visual_mode": visual_mode,
        "target_classes": target_classes,
        "quality": {
            "brightness": res["brightness"],
            "sharpness": res["sharpness"],
            "status": res["quality_status"]
        },
        "pipeline_steps": res["pipeline_steps"],
        "prod_config": {
            "clahe": prod_clahe,
            "multiscale": prod_multiscale,
            "dedup": prod_dedup,
            "sleeve_filter": prod_sleeve_filter,
            "head_crop": prod_head_crop,
            "quality_check": prod_quality_check,
            "dedup_dist": prod_dedup_dist,
            "ios_thresh": prod_ios_thresh
        },
        "params": {
            "conf": conf,
            "iou": iou,
            "imgsz": imgsz,
            "max_det": max_det
        },
        "annotated_b64": annotated_b64,
        "roi_annotated_b64": annotated_b64,
        "original_b64": original_b64,
        "output_filename": "raw_conf005.jpg",
        "roi": {
            "applied": apply_roi,
            "green_zone": green_zone,
            "red_zone": red_zone,
            "valid_count": res["valid_count"],
            "ignored_count": res["ignored_count"],
            "roi_annotated_b64": annotated_b64
        },
        "boxes": res["boxes"]
    }


@router.get("/system/classrooms-roi")
async def get_classrooms_roi():
    """
    Lấy danh sách các lớp học cùng cấu hình ROI (Green Zone & Red Zone)
    để người dùng có thể nạp nhanh ROI của bất kỳ lớp học nào vào công cụ kiểm thử.
    """
    from database.db_session import SessionLocal
    from database.models import Classroom
    db = SessionLocal()
    try:
        classrooms = db.query(Classroom).order_by(Classroom.id).all()
        result = []
        for c in classrooms:
            roi = c.roi
            result.append({
                "id": c.id,
                "name": c.name,
                "code": c.code,
                "standard_count": c.standard_count,
                "green_zone": roi.green_zone if roi else [],
                "red_zone": roi.red_zone if roi else [],
                "image_width": roi.image_width if roi and roi.image_width else 1920,
                "image_height": roi.image_height if roi and roi.image_height else 1080,
                "rtsp_url": c.rtsp_url,
                "room_number": c.room_number,
                "is_active": c.is_active
            })
        return {"success": True, "classrooms": result}
    except Exception as e:
        logger.error(f"Lỗi lấy classrooms-roi: {e}")
        return {"success": False, "classrooms": []}
    finally:
        db.close()


@router.get("/system/sample-frames")
async def get_sample_frames():
    """
    Trả về danh sách các ảnh mẫu có sẵn trong hệ thống (camera, dataset/samples)
    để người dùng có thể thử nghiệm AI với 1 cú click.
    """
    samples = []
    
    # 1. Quét thư mục camera/
    camera_dir = settings.BASE_DIR / "camera"
    if camera_dir.exists():
        for f in sorted(camera_dir.glob("*.JPG")):
            samples.append({
                "name": f"Camera {f.stem}",
                "path": f"camera/{f.name}",
                "category": "Camera Thực Tế"
            })
            if len(samples) >= 10:
                break

    # 2. Quét thư mục samples/ (Cả ảnh và video)
    samples_dir = settings.BASE_DIR / "dataset" / "samples"
    if samples_dir.exists():
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.PNG"]:
            for f in sorted(samples_dir.glob(ext)):
                samples.append({
                    "name": f.stem,
                    "path": f"dataset/samples/{f.name}",
                    "category": "Ảnh Mẫu Dataset",
                    "type": "image"
                })
        for f in sorted(samples_dir.glob("*.[mM][pP]4")):
            samples.append({
                "name": f"Video 15s Thực Tế ({f.name})",
                "path": f"dataset/samples/{f.name}",
                "category": "Video Camera Thực Tế",
                "type": "video"
            })

    # 3. Quét latest captures
    latest_dir = settings.STORAGE_DIR / "captures" / "latest"
    if latest_dir.exists():
        for f in sorted(latest_dir.glob("*.jpg"))[:5]:
            samples.append({
                "name": f"Chụp Gần Nhất - {f.stem}",
                "path": f"storage/captures/latest/{f.name}",
                "category": "Ảnh Capture Gần Nhất",
                "type": "image"
            })

    return {"success": True, "samples": samples}


@router.get("/system/sample-frame-preview")
async def get_sample_frame_preview(path: str = Query(...)):
    """Trả về file ảnh mẫu để xem trước trên giao diện (Hỗ trợ trích frame 0 nếu là Video)."""
    clean_path = path.lstrip("/").replace("\\", "/")
    if ".." in clean_path:
        raise HTTPException(status_code=400, detail="Invalid path")
    target = settings.BASE_DIR / clean_path
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Sample image not found")

    # Nếu là tệp tin video, đọc frame đầu tiên và trả về dạng ảnh JPEG
    video_exts = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
    if any(clean_path.lower().endswith(ext) for ext in video_exts):
        cap = cv2.VideoCapture(str(target))
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            _, buf = cv2.imencode(".jpg", frame)
            return Response(content=buf.tobytes(), media_type="image/jpeg")

    return FileResponse(target, media_type="image/jpeg")


@router.get("/system/download-raw-result")
async def download_raw_result():
    """Tải tệp tin ảnh kết quả raw_conf005.jpg về máy tính."""
    candidates = [
        settings.STORAGE_DIR / "test_results" / "raw_conf005.jpg",
        settings.BASE_DIR / "raw_conf005.jpg"
    ]
    target_file = next((p for p in candidates if p.exists() and p.is_file()), None)
    if not target_file:
        raise HTTPException(status_code=404, detail="Chưa có kết quả kiểm thử nào. Vui lòng chạy kiểm thử trước.")

    return FileResponse(
        path=str(target_file),
        filename="raw_conf005.jpg",
        media_type="image/jpeg"
    )


def _normalize_ai_target_urls(url_str: Optional[str]) -> Tuple[str, str]:
    """
    Chuẩn hóa URL của dịch vụ AI và URL /api/info.
    Hỗ trợ cả URL tương đối ('/api/predict') và URL tuyệt đối ('http://...').
    """
    raw = (url_str or "").strip()
    if not raw:
        raw = getattr(settings, "STUDENT_DETECTION_API_URL", "http://student-detection:8010/api/predict")

    if raw.startswith("/"):
        predict_url = f"http://127.0.0.1:8000{raw}"
    elif not raw.startswith("http://") and not raw.startswith("https://"):
        predict_url = f"http://{raw}"
    else:
        predict_url = raw

    if "/api/predict" in predict_url:
        info_url = predict_url.replace("/api/predict", "/api/info")
    elif "/predict" in predict_url:
        info_url = predict_url.replace("/predict", "/info")
    else:
        info_url = predict_url.rstrip("/") + "/api/info"

    return predict_url, info_url


@router.get("/system/ai-endpoint")
async def get_ai_endpoint():
    """Lấy cấu hình đường dẫn API AI Student Detection hiện tại và kiểm tra kết nối thời gian thực."""
    import httpx
    current_url = getattr(settings, "STUDENT_DETECTION_API_URL", "http://student-detection:8010/api/predict")

    is_connected = False
    server_info = None
    latency_ms = None

    predict_url, info_url = _normalize_ai_target_urls(current_url)

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(info_url)
            if resp.status_code == 200:
                is_connected = True
                server_info = resp.json()
                latency_ms = round((time.time() - t0) * 1000, 1)
    except Exception:
        pass

    # Nếu không kết nối được qua URL riêng, thử kiểm tra endpoint nội bộ
    if not is_connected and not current_url.startswith("/"):
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                resp = await client.get("http://127.0.0.1:8000/api/info")
                if resp.status_code == 200:
                    local_info = resp.json()
                    if not server_info:
                        server_info = local_info
        except Exception:
            pass

    # Đảm bảo luôn có thông tin thiết bị phần cứng từ detector
    if not server_info:
        try:
            from backend.app.core.detector import detector
            m_info = detector.get_model_info()
            server_info = {
                "status": "ready" if is_connected else "local_standby",
                "server": {
                    "device": m_info.get("device", "CPU"),
                    "is_cuda": m_info.get("is_cuda", False),
                    "engine": "Depth-NMS Integrated Engine"
                },
                "model": {
                    "yolo_model": m_info.get("model_name", "classroom_best.pt"),
                    "depth_model": "Depth Anything V2",
                    "imgsz": settings.YOLO_IMGSZ
                }
            }
        except Exception:
            pass

    return {
        "success": True,
        "current_url": current_url,
        "default_docker_url": "http://student-detection:8010/api/predict",
        "default_host_url": "http://localhost:8010/api/predict",
        "is_connected": is_connected,
        "latency_ms": latency_ms,
        "server_info": server_info,
        "num_passes": getattr(settings, "ATTENDANCE_NUM_PASSES", 10),
        "delay_seconds": getattr(settings, "ATTENDANCE_PASS_DELAY_SECONDS", 10.0),
        "scan_mode": getattr(settings, "ATTENDANCE_SCAN_MODE", "round_robin"),
        "config": {
            "api_url": current_url,
            "use_predict_api_engine": getattr(settings, "USE_PREDICT_API_ENGINE", True),
            "num_passes": getattr(settings, "ATTENDANCE_NUM_PASSES", 10),
            "delay_seconds": getattr(settings, "ATTENDANCE_PASS_DELAY_SECONDS", 10.0),
            "scan_mode": getattr(settings, "ATTENDANCE_SCAN_MODE", "round_robin")
        }
    }


@router.post("/system/ai-ping")
async def ping_ai_endpoint(request: Request):
    """Kiểm tra kết nối tức thì tới một AI endpoint mà không lưu cấu hình."""
    import httpx
    target_url = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            target_url = body.get("api_url")
    except Exception:
        pass

    if not target_url:
        target_url = settings.STUDENT_DETECTION_API_URL

    target_url = str(target_url).strip()
    predict_url, info_url = _normalize_ai_target_urls(target_url)

    is_connected = False
    server_info = None
    latency_ms = None
    error_msg = None

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(info_url)
            latency_ms = round((time.time() - t0) * 1000, 1)
            if resp.status_code == 200:
                is_connected = True
                server_info = resp.json()
            else:
                error_msg = f"HTTP {resp.status_code}"
    except Exception as e:
        error_msg = str(e)

    # Đảm bảo bổ sung server_info nếu chưa có
    if not server_info:
        try:
            from backend.app.core.detector import detector
            m_info = detector.get_model_info()
            server_info = {
                "server": {
                    "device": m_info.get("device", "CPU"),
                    "is_cuda": m_info.get("is_cuda", False)
                },
                "model": {
                    "yolo_model": m_info.get("model_name", "classroom_best.pt")
                }
            }
        except Exception:
            pass

    return {
        "success": True,
        "target_url": target_url,
        "is_connected": is_connected,
        "latency_ms": latency_ms,
        "server_info": server_info,
        "num_passes": getattr(settings, "ATTENDANCE_NUM_PASSES", 10),
        "delay_seconds": getattr(settings, "ATTENDANCE_PASS_DELAY_SECONDS", 10.0),
        "scan_mode": getattr(settings, "ATTENDANCE_SCAN_MODE", "round_robin"),
        "error": error_msg
    }


@router.post("/system/ai-endpoint")
async def update_ai_endpoint(request: Request):
    """Cập nhật và lưu vĩnh viễn đường dẫn API AI Student Detection và tham số vào hệ thống và .env."""
    import httpx
    from config.ai_runtime_store import save_runtime_ai

    target_url = None
    params = {}
    c_type = request.headers.get("content-type", "")
    if "application/json" in c_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                target_url = body.get("api_url")
                params = body
        except Exception:
            pass
    elif "form" in c_type:
        try:
            form = await request.form()
            target_url = form.get("api_url")
            params = dict(form)
        except Exception:
            pass

    if not target_url:
        try:
            body = await request.json()
            if isinstance(body, dict):
                target_url = body.get("api_url")
                params = body
        except Exception:
            pass

    if not target_url:
        target_url = request.query_params.get("api_url")

    if not target_url:
        target_url = settings.STUDENT_DETECTION_API_URL

    target_url = str(target_url).strip()
    predict_url, info_url = _normalize_ai_target_urls(target_url)

    is_connected = False
    server_info = None
    latency_ms = None

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(info_url)
            if resp.status_code == 200:
                is_connected = True
                server_info = resp.json()
                latency_ms = round((time.time() - t0) * 1000, 1)
    except Exception as e:
        logger.warning(f"Kiểm tra ping tới {info_url} thất bại: {e}")

    save_runtime_ai(settings, target_url, params)
    logger.info(f"Đã cập nhật STUDENT_DETECTION_API_URL = {target_url} (Kết nối: {is_connected})")

    # Bổ sung server_info từ detector nếu microservice chưa bật
    if not server_info:
        try:
            from backend.app.core.detector import detector
            m_info = detector.get_model_info()
            server_info = {
                "server": {
                    "device": m_info.get("device", "CPU"),
                    "is_cuda": m_info.get("is_cuda", False)
                },
                "model": {
                    "yolo_model": m_info.get("model_name", "classroom_best.pt")
                }
            }
        except Exception:
            pass

    return {
        "success": True,
        "message": f"Đã lưu cấu hình AI vào hệ thống: {target_url}",
        "current_url": settings.STUDENT_DETECTION_API_URL,
        "is_connected": is_connected,
        "latency_ms": latency_ms,
        "server_info": server_info,
        "config": {
            "api_url": settings.STUDENT_DETECTION_API_URL,
            "use_predict_api_engine": getattr(settings, "USE_PREDICT_API_ENGINE", True),
            "num_passes": getattr(settings, "ATTENDANCE_NUM_PASSES", 10),
            "delay_seconds": getattr(settings, "ATTENDANCE_PASS_DELAY_SECONDS", 10.0),
            "scan_mode": getattr(settings, "ATTENDANCE_SCAN_MODE", "round_robin")
        }
    }


# =============================================================================
# BATCH TEST RUNS & EXPORT (XUẤT TRỌN GÓI ZIP: EXCEL + ẢNH GỐC + ẢNH CHẤM)
# =============================================================================

@router.post("/system/test-batches/save")
async def api_save_batch_test(request: Request):
    """Lưu kết quả kiểm thử số lượng lớn lớp học (batch test run)."""
    from backend.app.services.batch_test_service import save_batch_test
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Dữ liệu payload không đúng định dạng JSON")

    if not payload or not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload phải là JSON object")

    result = save_batch_test(payload)
    return result


@router.get("/system/test-batches")
async def api_list_batch_tests():
    """Lấy danh sách các đợt kiểm thử hàng loạt đã lưu."""
    from backend.app.services.batch_test_service import list_batch_tests
    runs = list_batch_tests()
    return {"success": True, "batches": runs}


@router.get("/system/test-batches/{batch_id}")
async def api_get_batch_test(batch_id: str):
    """Lấy chi tiết và bảng thống kê của một đợt kiểm thử."""
    from backend.app.services.batch_test_service import get_batch_test
    data = get_batch_test(batch_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đợt test {batch_id}")
    return {"success": True, "batch": data}


@router.get("/system/test-batches/{batch_id}/export-zip")
async def api_export_batch_zip(batch_id: str):
    """Xuất trọn gói 1-Click ZIP gồm: File Excel thống kê + Thư mục ảnh gốc + Thư mục ảnh chấm tròn."""
    from backend.app.services.batch_test_service import create_batch_zip
    try:
        zip_path = create_batch_zip(batch_id)
        if not zip_path.exists():
            raise HTTPException(status_code=404, detail="Không thể tạo gói tệp ZIP")
        return FileResponse(
            path=str(zip_path),
            filename=f"Bao_Cao_AI_Test_Hang_Loat_{batch_id}.zip",
            media_type="application/zip"
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đợt test {batch_id}")
    except Exception as e:
        logger.error(f"Lỗi khi xuất gói ZIP {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo gói ZIP: {str(e)}")


@router.get("/system/test-batches/{batch_id}/export-excel")
async def api_export_batch_excel(batch_id: str):
    """Tải riêng file Excel (.xlsx) bảng thống kê sĩ số của đợt test."""
    from backend.app.services.batch_test_service import _get_base_dir
    excel_path = _get_base_dir() / batch_id / f"thong_ke_si_so_{batch_id}.xlsx"
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail="Chưa có file Excel cho đợt test này")
    return FileResponse(
        path=str(excel_path),
        filename=f"Thong_Ke_Si_So_{batch_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/system/test-batches/{batch_id}/image/{img_type}/{filename}")
async def api_get_batch_image(batch_id: str, img_type: str, filename: str):
    """Xem trực tiếp ảnh gốc hoặc ảnh chấm trong đợt test."""
    from backend.app.services.batch_test_service import _get_base_dir
    if img_type not in ("orig", "original", "dot", "annotated", "anh_goc", "anh_ket_qua_cham"):
        raise HTTPException(status_code=400, detail="img_type không hợp lệ")

    sub_dir = "anh_goc" if img_type in ("orig", "original", "anh_goc") else "anh_ket_qua_cham"
    clean_fn = Path(filename).name
    img_path = _get_base_dir() / batch_id / sub_dir / clean_fn
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Ảnh không tồn tại")
    return FileResponse(img_path, media_type="image/jpeg")


