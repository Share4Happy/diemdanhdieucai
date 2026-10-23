import os
import cv2
import time
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import SessionLocal
from database.models import Classroom, ROIPolygon, AttendanceSession, AttendanceDetail
from backend.app.core.rtsp_client import rtsp_client, is_valid_frame
from backend.app.core.relay_service import relay_service
from backend.app.core.detector import detector
from backend.app.core.timezone_utils import get_now
from services.progress_service import progress_tracker
from collections import defaultdict


def compute_weighted_attendance_result(
    samples: List[Dict[str, Any]],
    standard_count: int = 40
) -> Dict[str, Any]:
    """
    Thuật toán Phương án 1: Tần số có trọng số tin cậy (Confidence-Weighted Frequency Mode)
    Áp dụng cho 8 lần quét liên tiếp:
    1. Nhóm các lần quét theo sĩ số (present_count).
    2. Với mỗi mức sĩ số C, tính tổng trọng số Score(C) = sum(confidence_avg) * sharpness_boost.
    3. Chọn mức sĩ số có Score cao nhất.
       - Tie-break: Nếu có 2 mức sĩ số có điểm bằng nhau, ưu tiên sĩ số LỚN HƠN.
    4. Trong các lần quét đạt mức sĩ số chiến thắng đó, chọn lần có chất lượng cao nhất
       (confidence cao nhất, nét nhất) làm ảnh đối chứng lưu CSDL.
    """
    valid_samples = [s for s in samples if s.get("is_valid", True) and s.get("present_count") is not None]

    if not valid_samples:
        return {
            "success": False,
            "present_count": 0,
            "absent_count": standard_count,
            "status": "NO_SIGNAL",
            "confidence_avg": 0.0,
            "best_frame": None,
            "best_annotated_img": None,
            "detected_students": [],
            "counts_history": [],
            "audit_notes": "⚠️ Mất tín hiệu camera sau các lần quét (Không có hình ảnh hợp lệ)"
        }

    counts_history = [s["present_count"] for s in valid_samples]

    grouped = defaultdict(list)
    for s in valid_samples:
        grouped[s["present_count"]].append(s)

    scored_candidates = []
    for count, sample_list in grouped.items():
        freq = len(sample_list)
        total_conf = sum(s.get("confidence_avg", 0.85) for s in sample_list)
        avg_sharpness = sum(s.get("laplacian_sharpness", 20.0) for s in sample_list) / max(1, freq)
        sharpness_boost = 1.0 + min(0.15, max(0.0, (avg_sharpness - 10.0) / 200.0))
        final_score = total_conf * sharpness_boost

        scored_candidates.append({
            "count": count,
            "frequency": freq,
            "total_score": round(final_score, 3),
            "samples": sample_list
        })

    # Sắp xếp: Tiêu chí 1: Score cao nhất; Tiêu chí 2 (Tie-break): Count lớn hơn
    scored_candidates.sort(key=lambda x: (x["total_score"], x["count"]), reverse=True)
    winner = scored_candidates[0]

    winning_count = winner["count"]
    winning_freq = winner["frequency"]
    winning_score = winner["total_score"]
    winning_samples = winner["samples"]

    # Chọn lần quét có độ tin cậy và độ nét tốt nhất trong nhóm winning
    best_sample = max(
        winning_samples,
        key=lambda s: (s.get("confidence_avg", 0.0), s.get("laplacian_sharpness", 0.0))
    )

    total_passes = len(samples)
    audit_notes = (
        f"Quét {total_passes} lần: {counts_history} -> Chốt {winning_count} HS "
        f"(Tần suất {winning_freq}/{len(valid_samples)}, Trọng số: {winning_score:.2f})"
    )

    absent_count = max(0, standard_count - winning_count)
    conf_avg = round(best_sample.get("confidence_avg", 0.85), 2)

    return {
        "success": True,
        "present_count": winning_count,
        "absent_count": absent_count,
        "status": "OK",
        "confidence_avg": conf_avg,
        "best_frame": best_sample.get("frame"),
        "best_annotated_img": best_sample.get("annotated_img"),
        "detected_students": best_sample.get("detected_students", []),
        "counts_history": counts_history,
        "winning_freq": winning_freq,
        "total_valid": len(valid_samples),
        "audit_notes": audit_notes,
        "best_pass_index": best_sample.get("pass_index", 1)
    }


class AttendanceEngine:
    """
    Quy trình tính toán điểm danh sĩ số:
    Kết hợp luồng Camera RTSP, điều khiển đèn LED, xử lý AI và cập nhật Database.
    """

    def __init__(self):
        pass

    def run_daily_attendance(
        self,
        date_str: Optional[str] = None,
        trigger_led: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Quy trình điểm danh đồng loạt 30 lớp:
        1. Chụp ảnh đồng loạt 30 camera qua đa luồng RTSP (đèn hồng ngoại mặc định tắt).
        2. Áp dụng Masking & AI YOLO đếm đầu người.
        3. Tính toán số học sinh hiện diện, số học sinh vắng.
        4. Lưu kết quả và đường dẫn file ảnh đối chứng vào CSDL.
        """
        if trigger_led is None:
            trigger_led = getattr(settings, "ENABLE_CAMERA_SIGNAL", False)

        start_scan_time = time.time()
        now = get_now()
        if not date_str:
            date_str = now.strftime("%Y-%m-%d")
        scan_time_str = now.strftime("%H:%M:%S")

        session_code = f"SESSION_{now.strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"=== BẮT ĐẦU PHIÊN ĐIỂM DANH: {session_code} ===")

        db: Session = SessionLocal()
        try:
            # Lấy danh sách lớp học đang kích hoạt và cấu hình ROI
            classrooms = db.query(Classroom).filter(Classroom.is_active == True).order_by(Classroom.id).all()
            if not classrooms:
                logger.warning("Không tìm thấy lớp học nào đang kích hoạt trong CSDL!")
                progress_tracker.finish(False, "Không tìm thấy lớp học nào đang kích hoạt trong CSDL!")
                return {"success": False, "message": "Không có lớp học"}

            total_cams = len(classrooms)
            progress_tracker.start(
                action="ATTENDANCE_SCAN",
                title=f"Quét Điểm Danh Toàn Trường ({total_cams} Lớp)",
                total_steps=3,
                total_items=total_cams
            )
            progress_tracker.update(
                step=1,
                step_title="1/3: Kết Nối & Chụp Ảnh Camera NVR",
                percent=8,
                log_text=f"Khởi tạo phiên điểm danh cho {total_cams} phòng học trường Điều Cải"
            )

            # 1. Bật đèn hồng ngoại camera báo hiệu giờ điểm danh (trước khi chụp)
            if trigger_led:
                progress_tracker.update(
                    current_item="Bật đèn hồng ngoại camera báo hiệu...",
                    log_text="Kích hoạt tín hiệu đèn hồng ngoại camera 3s..."
                )
                relay_service.signal_classrooms_before_capture(
                    classrooms=classrooms,
                    signal_seconds=3,
                    capture_color=True
                )

            # Tạo bản ghi Session mới
            new_session = AttendanceSession(
                session_code=session_code,
                scan_date=date_str,
                scan_time=scan_time_str,
                total_classes=len(classrooms),
                status="PROCESSING"
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            # 2. Tạo thư mục lưu trữ độc lập cho phiên điểm danh này (chống ghi đè giữa các phiên trong ngày)
            session_captures_folder = settings.CAPTURES_DIR / date_str / session_code
            session_captures_folder.mkdir(parents=True, exist_ok=True)

            session_annotated_folder = settings.ANNOTATED_DIR / date_str / session_code
            session_annotated_folder.mkdir(parents=True, exist_ok=True)

            cls_data_list = [
                {
                    "id": c.id,
                    "name": c.name,
                    "rtsp_url": c.rtsp_url
                } for c in classrooms
            ]

            def on_camera_captured(cur_done, total_done, cls_info, success):
                status_str = "thành công" if success else "thử lại / kiểm tra"
                log_t = "success" if success else "warning"
                # Map 10% -> 48%
                pct = int(10 + (cur_done / max(1, total_done)) * 38)
                progress_tracker.update(
                    step=1,
                    step_title="1/3: Kết Nối & Chụp Ảnh Camera NVR",
                    current=cur_done,
                    total=total_done,
                    current_item=f"{cls_info['name']} (CH{cls_info['id']:02d})",
                    percent=pct,
                    log_text=f"Camera CH{cls_info['id']:02d} ({cls_info['name']}): Bắt hình {status_str}",
                    log_type=log_t
                )

            capture_results = rtsp_client.capture_all_classrooms(
                cls_data_list,
                date_str=date_str,
                target_folder=session_captures_folder,
                progress_callback=on_camera_captured
            )

            # 3. Tự động trả các camera về chế độ Tự Động (Auto) sau khi đã chụp xong
            if trigger_led:
                relay_service.restore_classrooms_auto(classrooms)

            total_standard = 0
            total_present = 0
            total_absent = 0
            details_list = []

            num_passes = getattr(settings, "ATTENDANCE_NUM_PASSES", 10)
            delay_sec = getattr(settings, "ATTENDANCE_PASS_DELAY_SECONDS", 10.0)
            scan_mode = getattr(settings, "ATTENDANCE_SCAN_MODE", "round_robin")

            if scan_mode == "round_robin" and total_cams > 1:
                # =========================================================================
                # PHƯƠNG ÁN B: QUÉT XOAY VÒNG TOÀN TRƯỜNG (ROUND-ROBIN BATCHES)
                # Mỗi vòng quét 1 lượt cả 30 camera, sau đó nghỉ delay_sec (10s) rồi quét vòng tiếp theo.
                # Đảm bảo mỗi lớp đủ num_passes lần quét ở các thời điểm cách biệt nhau.
                # Tổng thời gian cho 30 lớp chỉ mất ~4-5 phút thay vì 50 phút!
                # =========================================================================
                progress_tracker.update(
                    step=2,
                    step_title=f"2/3: Quét AI {num_passes} Vòng Xoay Vòng Toàn Trường",
                    percent=50,
                    log_text=f"Bắt đầu quy trình quét AI xoay vòng {num_passes} lượt cho {total_cams} phòng học..."
                )

                classroom_samples = {c.id: [] for c in classrooms}

                for pass_round in range(1, num_passes + 1):
                    for idx, cls in enumerate(classrooms, start=1):
                        c_id = cls.id
                        c_name = cls.name

                        cur_global_item = (pass_round - 1) * total_cams + idx
                        total_global_items = num_passes * total_cams
                        sub_pct = int(50 + (cur_global_item / total_global_items) * 38)

                        frame = None
                        is_ok = False

                        # Vòng 1: ưu tiên dùng initial_frame đã bắt ở Bước 1
                        if pass_round == 1:
                            cap_info = capture_results.get(c_id)
                            init_frame = cap_info.get("frame") if cap_info else None
                            if init_frame is not None and is_valid_frame(init_frame):
                                frame = init_frame
                                is_ok = True

                        # Các vòng tiếp theo hoặc nếu vòng 1 chưa có: bắt khung hình tươi từ RTSP
                        if frame is None and cls.rtsp_url:
                            try:
                                fetch_ok, fetched, _, _ = rtsp_client._fetch_frame_from_source(cls.rtsp_url)
                                if fetch_ok and fetched is not None and is_valid_frame(fetched):
                                    frame = fetched
                                    is_ok = True
                            except Exception as e_fetch:
                                logger.debug(f"[RoundRobin] Lớp {c_name} vòng {pass_round}: Lỗi đọc camera: {e_fetch}")

                        # Fallback ảnh đĩa nếu không bắt được luồng trực tiếp
                        if frame is None:
                            latest_file = settings.CAPTURES_DIR / "latest" / f"Lop_{c_id}.jpg"
                            if latest_file.exists():
                                frame = cv2.imread(str(latest_file))
                                is_ok = (frame is not None)

                        if not is_ok or frame is None:
                            classroom_samples[c_id].append({
                                "pass_index": pass_round,
                                "frame": None,
                                "present_count": None,
                                "confidence_avg": 0.0,
                                "laplacian_sharpness": 0.0,
                                "brightness": 0.0,
                                "detected_students": [],
                                "annotated_img": None,
                                "is_valid": False
                            })
                            progress_tracker.update(
                                step=2,
                                step_title=f"2/3: Quét AI Vòng {pass_round}/{num_passes} (Xoay Vòng Toàn Trường)",
                                current=idx,
                                total=total_cams,
                                current_item=f"{c_name} (Vòng {pass_round}/{num_passes})",
                                percent=sub_pct,
                                log_text=f"⚠️ Vòng {pass_round}/{num_passes} - {c_name}: Không có tín hiệu camera sạch",
                                log_type="warning"
                            )
                            continue

                        # Thẩm định độ sáng & độ nét
                        try:
                            gray_chk = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            brightness = float(gray_chk.mean())
                            lap_sharpness = float(cv2.Laplacian(gray_chk, cv2.CV_64F).var())
                        except Exception:
                            brightness = 100.0
                            lap_sharpness = 20.0

                        min_lap = getattr(cls, 'laplacian_threshold', None) or 5.0
                        if brightness < 15.0 or lap_sharpness < min_lap:
                            classroom_samples[c_id].append({
                                "pass_index": pass_round,
                                "frame": frame,
                                "present_count": None,
                                "confidence_avg": 0.0,
                                "laplacian_sharpness": lap_sharpness,
                                "brightness": brightness,
                                "detected_students": [],
                                "annotated_img": None,
                                "is_valid": False
                            })
                            progress_tracker.update(
                                step=2,
                                step_title=f"2/3: Quét AI Vòng {pass_round}/{num_passes} (Xoay Vòng Toàn Trường)",
                                current=idx,
                                total=total_cams,
                                current_item=f"{c_name} (Vòng {pass_round}/{num_passes})",
                                percent=sub_pct,
                                log_text=f"⚠️ Vòng {pass_round}/{num_passes} - {c_name}: Ảnh mờ/tối (b={brightness:.1f}, lap={lap_sharpness:.1f})",
                                log_type="warning"
                            )
                            continue

                        # Gọi AI nhận diện
                        cam_conf = getattr(cls, 'conf_threshold', None)
                        p_cnt, detected_students, annotated_img = detector.detect_students_in_classroom(
                            image=frame,
                            conf_threshold=cam_conf,
                            classroom_name=cls.name,
                            standard_count=cls.standard_count,
                            apply_clahe=False
                        )
                        c_avg = (
                            sum(s.get("confidence", 0.85) for s in detected_students) / max(1, len(detected_students))
                            if detected_students else 0.85
                        )

                        classroom_samples[c_id].append({
                            "pass_index": pass_round,
                            "frame": frame,
                            "present_count": p_cnt,
                            "confidence_avg": c_avg,
                            "laplacian_sharpness": lap_sharpness,
                            "brightness": brightness,
                            "detected_students": detected_students,
                            "annotated_img": annotated_img,
                            "is_valid": True
                        })

                        progress_tracker.update(
                            step=2,
                            step_title=f"2/3: Quét AI Vòng {pass_round}/{num_passes} (Xoay Vòng Toàn Trường)",
                            current=idx,
                            total=total_cams,
                            current_item=f"{c_name} (Vòng {pass_round}/{num_passes})",
                            percent=sub_pct,
                            log_text=f"Vòng {pass_round}/{num_passes} - {c_name}: Đếm được {p_cnt} HS (conf: {c_avg:.1%})"
                        )

                    # Nghỉ delay_sec giữa các vòng quét toàn trường (có đếm ngược)
                    if pass_round < num_passes and delay_sec > 0:
                        sleep_int = int(delay_sec)
                        for sec_left in range(sleep_int, 0, -1):
                            progress_tracker.update(
                                step=2,
                                step_title=f"2/3: Quét AI Vòng {pass_round}/{num_passes} (Xoay Vòng Toàn Trường)",
                                percent=sub_pct,
                                current_item=f"Nghỉ giữa Vòng {pass_round} và Vòng {pass_round + 1}",
                                log_text=f"✅ Hoàn thành Vòng {pass_round}/{num_passes}. ⏱️ Đang chờ {sec_left}s trước khi quét Vòng {pass_round + 1}..."
                            )
                            time.sleep(1.0)
                        rem = delay_sec - sleep_int
                        if rem > 0:
                            time.sleep(rem)

                # Tổng kết trọng số cho cả 30 lớp
                for idx, cls in enumerate(classrooms, start=1):
                    c_id = cls.id
                    c_name = cls.name
                    std_count = cls.standard_count
                    total_standard += std_count

                    cap_info = capture_results.get(c_id)
                    raw_path = cap_info["image_path"] if cap_info else ""

                    samples = classroom_samples.get(c_id, [])
                    scan_res = compute_weighted_attendance_result(samples, standard_count=std_count)

                    present_count = scan_res["present_count"]
                    absent_count = scan_res["absent_count"]
                    status = scan_res["status"]
                    confidence_avg = scan_res["confidence_avg"]
                    notes = scan_res["audit_notes"]
                    annotated_path = raw_path

                    best_annotated = scan_res.get("best_annotated_img")
                    if best_annotated is not None:
                        annotated_filename = f"Lop_{c_id}_result.jpg"
                        annotated_filepath = session_annotated_folder / annotated_filename
                        cv2.imwrite(str(annotated_filepath), best_annotated)
                        annotated_path = str(annotated_filepath)

                    best_raw = scan_res.get("best_frame")
                    if best_raw is not None and raw_path:
                        cv2.imwrite(raw_path, best_raw)

                    total_present += present_count
                    total_absent += absent_count

                    detail = AttendanceDetail(
                        session_id=new_session.id,
                        classroom_id=c_id,
                        standard_count=std_count,
                        present_count=present_count,
                        absent_count=absent_count,
                        raw_image_path=raw_path,
                        annotated_image_path=annotated_path,
                        confidence_avg=round(confidence_avg, 2),
                        notes=notes,
                        status=status
                    )
                    db.add(detail)
                    details_list.append({
                        "class_name": c_name,
                        "standard": std_count,
                        "present": present_count,
                        "absent": absent_count,
                        "status": status,
                        "notes": notes,
                        "annotated_path": annotated_path
                    })

                    pct_ai = int(88 + (idx / total_cams) * 4)
                    progress_tracker.update(
                        step=2,
                        step_title=f"2/3: Tổng Kết {num_passes} Vòng Quét & Trọng Số",
                        current=idx,
                        total=total_cams,
                        current_item=f"{c_name}: Chốt {present_count}/{std_count} HS",
                        percent=pct_ai,
                        log_text=f"✅ {c_name}: {notes}",
                        log_type="info" if absent_count == 0 else "warning"
                    )

            else:
                # Chế độ tuần tự (Sequential) - chạy lần lượt từng lớp
                progress_tracker.update(
                    step=2,
                    step_title=f"2/3: Quét AI {num_passes} Lần & Thuật Toán Trọng Số",
                    percent=50,
                    log_text=f"Bắt đầu nhận diện AI {num_passes} lần cho từng lớp..."
                )

                for idx, cls in enumerate(classrooms, start=1):
                    c_id = cls.id
                    c_name = cls.name
                    std_count = cls.standard_count
                    total_standard += std_count

                    cap_info = capture_results.get(c_id)
                    raw_path = cap_info["image_path"] if cap_info else ""
                    frame = cap_info.get("frame") if cap_info else None
                    is_cam_ok = bool(cap_info and cap_info.get("success", False))

                    present_count = 0
                    absent_count = 0
                    annotated_path = raw_path
                    confidence_avg = 0.0
                    status = "OK" if is_cam_ok else "NO_SIGNAL"
                    notes = ""

                    if is_cam_ok and frame is not None:
                        def on_daily_pass(cur_pass, total_passes, count, conf, countdown_msg=""):
                            sub_pct = int(50 + ((idx - 1 + cur_pass / total_passes) / total_cams) * 40)
                            count_lbl = f"{count} HS" if count is not None else "đang bắt hình..."
                            log_extra = f" | ⏱️ {countdown_msg}" if countdown_msg else ""
                            progress_tracker.update(
                                step=2,
                                step_title=f"2/3: Quét AI {total_passes} Lần & Thuật Toán Trọng Số",
                                current=idx,
                                total=total_cams,
                                current_item=f"{c_name} (Lần quét {cur_pass}/{total_passes})",
                                percent=sub_pct,
                                log_text=f"{c_name} [Lần {cur_pass}/{total_passes}]: Đếm được {count_lbl} (conf: {conf:.1%}){log_extra}"
                            )

                        scan_res = self.scan_classroom_multi_pass(
                            cls=cls,
                            num_passes=num_passes,
                            delay_seconds=delay_sec,
                            initial_frame=frame,
                            progress_callback=on_daily_pass
                        )

                        present_count = scan_res["present_count"]
                        absent_count = scan_res["absent_count"]
                        status = scan_res["status"]
                        confidence_avg = scan_res["confidence_avg"]
                        notes = scan_res["audit_notes"]

                        best_annotated = scan_res.get("best_annotated_img")
                        if best_annotated is not None:
                            annotated_filename = f"Lop_{c_id}_result.jpg"
                            annotated_filepath = session_annotated_folder / annotated_filename
                            cv2.imwrite(str(annotated_filepath), best_annotated)
                            annotated_path = str(annotated_filepath)

                        best_raw = scan_res.get("best_frame")
                        if best_raw is not None and raw_path:
                            cv2.imwrite(raw_path, best_raw)

                        total_present += present_count
                        total_absent += absent_count
                    else:
                        notes = "⚠️ Mất tín hiệu Camera (Chờ kiểm tra thủ công)"
                        logger.warning(f"Lớp {c_name} (ID: {c_id}) mất tín hiệu camera. Đánh dấu NO_SIGNAL.")

                    detail = AttendanceDetail(
                        session_id=new_session.id,
                        classroom_id=c_id,
                        standard_count=std_count,
                        present_count=present_count,
                        absent_count=absent_count,
                        raw_image_path=raw_path,
                        annotated_image_path=annotated_path,
                        confidence_avg=round(confidence_avg, 2),
                        notes=notes,
                        status=status
                    )
                    db.add(detail)
                    details_list.append({
                        "class_name": c_name,
                        "standard": std_count,
                        "present": present_count,
                        "absent": absent_count,
                        "status": status,
                        "notes": notes,
                        "annotated_path": annotated_path
                    })

                    pct_ai = int(50 + (idx / total_cams) * 40)
                    progress_tracker.update(
                        step=2,
                        step_title=f"2/3: Quét AI {num_passes} Lần & Thuật Toán Trọng Số",
                        current=idx,
                        total=total_cams,
                        current_item=f"{c_name}: Chốt {present_count}/{std_count} HS",
                        percent=pct_ai,
                        log_text=f"✅ {c_name}: {notes}",
                        log_type="info" if absent_count == 0 else "warning"
                    )

            # Cập nhật kết quả tổng hợp vào Session
            no_signal_count = sum(1 for d in details_list if d.get("status") in ["NO_SIGNAL", "CAN_KIEM_TRA"])
            new_session.total_standard = total_standard
            new_session.total_present = total_present
            new_session.total_absent = total_absent
            if no_signal_count == 0:
                new_session.status = "COMPLETED"
            else:
                new_session.status = f"COMPLETED ({no_signal_count}/{len(classrooms)} lớp mất tín hiệu/cần kiểm tra)"
            db.commit()

            # Giám sát ngân sách thời gian quét (Cảnh báo nếu quét toàn hệ thống vượt 45 giây)
            scan_duration = round(time.time() - start_scan_time, 2)
            time_budget_warning = False
            if scan_duration > 45.0:
                time_budget_warning = True
                logger.warning(
                    f"⚠️ CẢNH BÁO NGÂN SÁCH THỜI GIAN: Tổng thời gian quét là {scan_duration}s "
                    "đã vượt quá ngân sách 45s quy định! Đề xuất chia lượt NVR hoặc tăng số luồng song song."
                )

            logger.info(
                f"=== KẾT QUẢ ĐIỂM DANH: Tổng {len(classrooms)} lớp | "
                f"Sĩ số: {total_standard} | Hiện diện: {total_present} | Vắng: {total_absent} | "
                f"Thời gian quét: {scan_duration}s ==="
            )

            progress_tracker.update(
                step=3,
                step_title="3/3: Lưu CSDL & Xuất Báo Cáo Excel",
                percent=92,
                current_item="Đang tạo báo cáo Excel...",
                log_text="Lưu phiên điểm danh vào CSDL và xuất file Excel..."
            )

            # 5. Tự động xuất báo cáo Excel và gửi thông báo
            from services.excel_exporter import excel_exporter
            from services.notification import notification_service

            excel_path = excel_exporter.generate_daily_report(new_session.id)
            if excel_path:
                new_session.excel_report_path = str(excel_path)
                db.commit()
                # Phân phối báo cáo
                notification_service.send_attendance_report(new_session.id, excel_path)

            result_payload = {
                "success": True,
                "session_id": new_session.id,
                "session_code": session_code,
                "date": date_str,
                "time": scan_time_str,
                "scan_duration_seconds": scan_duration,
                "time_budget_warning": time_budget_warning,
                "total_classes": len(classrooms),
                "total_standard": total_standard,
                "total_present": total_present,
                "total_absent": total_absent,
                "excel_report": new_session.excel_report_path,
                "details": details_list
            }

            progress_tracker.finish(
                True,
                f"Hoàn tất điểm danh {len(classrooms)} lớp! (Hiện diện: {total_present}/{total_standard}, Vắng: {total_absent})",
                result=result_payload
            )
            return result_payload

        except Exception as e:
            db.rollback()
            logger.error(f"Lỗi trong quá trình điểm danh tự động: {e}")
            progress_tracker.finish(False, f"Lỗi trong quá trình điểm danh: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Luôn trả camera về chế độ tự động kể cả khi gặp ngoại lệ trong quá trình điểm danh
            if trigger_led and 'classrooms' in locals() and classrooms:
                try:
                    relay_service.restore_classrooms_auto(classrooms)
                except Exception:
                    pass
            db.close()

    def scan_classroom_multi_pass(
        self,
        cls: Classroom,
        num_passes: int = 10,
        delay_seconds: float = 10.0,
        initial_frame: Optional[np.ndarray] = None,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Quy trình quét 10 lần liên tiếp cho 1 phòng học:
        Vòng lặp: Bắt hình -> Gọi AI ra kết quả -> Lặp lại đủ num_passes lần (nghỉ delay_seconds).
        Sau đó áp dụng thuật toán trọng số Phương án 1 (Confidence-Weighted Frequency Mode) để tổng kết.
        """
        samples = []
        latest_dir = settings.CAPTURES_DIR / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)

        cam_conf = getattr(cls, 'conf_threshold', None)
        min_lap = getattr(cls, 'laplacian_threshold', None) or 5.0

        for pass_idx in range(1, num_passes + 1):
            frame = None
            is_ok = False

            # Lần 1 có thể tái sử dụng initial_frame nếu có sẵn và hợp lệ
            if pass_idx == 1 and initial_frame is not None and is_valid_frame(initial_frame):
                frame = initial_frame
                is_ok = True
            elif cls.rtsp_url:
                try:
                    fetch_ok, fetched, _, _ = rtsp_client._fetch_frame_from_source(cls.rtsp_url)
                    if fetch_ok and fetched is not None and is_valid_frame(fetched):
                        frame = fetched
                        is_ok = True
                except Exception as e_fetch:
                    logger.debug(f"[MultiPass] Lớp {cls.name} lần {pass_idx}: Lỗi đọc camera: {e_fetch}")

            # Fallback ảnh đĩa nếu không bắt được luồng trực tiếp
            if frame is None:
                latest_file = latest_dir / f"Lop_{cls.id}.jpg"
                if latest_file.exists():
                    frame = cv2.imread(str(latest_file))
                    is_ok = (frame is not None)
                else:
                    extracted = list((settings.BASE_DIR / "dataset" / "extracted_frames").glob("*.jpg"))
                    if extracted:
                        sample_file = extracted[(cls.id - 1) % len(extracted)]
                        frame = cv2.imread(str(sample_file))
                        is_ok = (frame is not None)

            if not is_ok or frame is None:
                samples.append({
                    "pass_index": pass_idx,
                    "frame": None,
                    "present_count": None,
                    "confidence_avg": 0.0,
                    "laplacian_sharpness": 0.0,
                    "brightness": 0.0,
                    "detected_students": [],
                    "annotated_img": None,
                    "is_valid": False
                })
                if progress_callback:
                    try:
                        progress_callback(pass_idx, num_passes, None, 0.0)
                    except TypeError:
                        progress_callback(pass_idx, num_passes, None, 0.0, "")
                continue

            # Kiểm tra độ sáng và độ nét
            try:
                gray_chk = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = float(gray_chk.mean())
                lap_sharpness = float(cv2.Laplacian(gray_chk, cv2.CV_64F).var())
            except Exception:
                brightness = 100.0
                lap_sharpness = 20.0

            if brightness < 15.0 or lap_sharpness < min_lap:
                logger.debug(f"[MultiPass] Lớp {cls.name} lần {pass_idx}: Ảnh mờ/tối (b={brightness:.1f}, lap={lap_sharpness:.1f})")
                samples.append({
                    "pass_index": pass_idx,
                    "frame": frame,
                    "present_count": None,
                    "confidence_avg": 0.0,
                    "laplacian_sharpness": lap_sharpness,
                    "brightness": brightness,
                    "detected_students": [],
                    "annotated_img": None,
                    "is_valid": False
                })
                if progress_callback:
                    try:
                        progress_callback(pass_idx, num_passes, None, 0.0)
                    except TypeError:
                        progress_callback(pass_idx, num_passes, None, 0.0, "")
                continue

            # Gọi AI nhận diện qua /api/predict
            present_count, detected_students, annotated_img = detector.detect_students_in_classroom(
                image=frame,
                conf_threshold=cam_conf,
                classroom_name=cls.name,
                standard_count=cls.standard_count,
                apply_clahe=False
            )

            conf_avg = (
                sum(s.get("confidence", 0.85) for s in detected_students) / max(1, len(detected_students))
                if detected_students else 0.85
            )

            samples.append({
                "pass_index": pass_idx,
                "frame": frame,
                "present_count": present_count,
                "confidence_avg": conf_avg,
                "laplacian_sharpness": lap_sharpness,
                "brightness": brightness,
                "detected_students": detected_students,
                "annotated_img": annotated_img,
                "is_valid": True
            })

            if progress_callback:
                try:
                    progress_callback(pass_idx, num_passes, present_count, conf_avg)
                except TypeError:
                    progress_callback(pass_idx, num_passes, present_count, conf_avg, "")

            # Nghỉ giữa các lần bắt hình để camera có khung hình mới (kèm đếm ngược nếu delay >= 2s)
            if pass_idx < num_passes and delay_seconds > 0:
                if delay_seconds >= 2.0 and progress_callback:
                    sleep_int = int(delay_seconds)
                    for sec_left in range(sleep_int, 0, -1):
                        try:
                            progress_callback(pass_idx, num_passes, present_count, conf_avg, f"Nghỉ {sec_left}s...")
                        except TypeError:
                            pass
                        time.sleep(1.0)
                    rem = delay_seconds - sleep_int
                    if rem > 0:
                        time.sleep(rem)
                else:
                    time.sleep(delay_seconds)

        return compute_weighted_attendance_result(samples, standard_count=cls.standard_count)

    def run_single_classroom_attendance(
        self,
        classroom_id: int
    ) -> Dict[str, Any]:
        """
        Quét lại điểm danh AI riêng cho 1 phòng học:
        1. Thực hiện quét 10 lần liên tiếp (Multi-pass Temporal Sampling, nghỉ 10s).
        2. Áp dụng thuật toán trọng số tần số tin cậy (Phương án 1) để chọn sĩ số chuẩn nhất.
        3. Chọn ảnh đối chứng đẹp nhất và cập nhật CSDL.
        4. Bắn cập nhật tiến trình chi tiết qua progress_tracker (kèm đếm ngược).
        """
        start_time = time.time()
        now = get_now()
        date_str = now.strftime("%Y-%m-%d")
        scan_time_str = now.strftime("%H:%M:%S")

        db: Session = SessionLocal()
        try:
            cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
            if not cls:
                msg = f"Không tìm thấy phòng học có ID {classroom_id}"
                logger.error(msg)
                progress_tracker.finish(False, msg)
                return {"success": False, "error": msg}

            num_passes = getattr(settings, "ATTENDANCE_NUM_PASSES", 10)
            delay_sec = getattr(settings, "ATTENDANCE_PASS_DELAY_SECONDS", 10.0)

            progress_tracker.start(
                action="ATTENDANCE_SCAN_SINGLE",
                title=f"Quét AI {num_passes} Lần - {cls.name}",
                total_steps=2,
                total_items=num_passes
            )

            def on_pass_progress(cur_pass, total_passes, count, conf, countdown_msg=""):
                pct = int(10 + (cur_pass / max(1, total_passes)) * 75)
                count_str = f"{count} HS" if count is not None else "đang kiểm tra..."
                log_suffix = f" | ⏱️ {countdown_msg}" if countdown_msg else ""
                progress_tracker.update(
                    step=1,
                    step_title=f"1/2: Quét Đa Khung Hình ({total_passes} Lần Liên Tiếp)",
                    percent=pct,
                    current=cur_pass,
                    total=total_passes,
                    current_item=f"{cls.name} (Lần {cur_pass}/{total_passes})",
                    log_text=f"Lần {cur_pass}/{total_passes}: Bắt hình camera -> AI đếm: {count_str} (độ tin cậy: {conf:.1%}){log_suffix}"
                )

            # Thực thi quét 10 lần
            scan_res = self.scan_classroom_multi_pass(
                cls=cls,
                num_passes=num_passes,
                delay_seconds=delay_sec,
                progress_callback=on_pass_progress
            )

            progress_tracker.update(
                step=2,
                step_title="2/2: Tổng Hợp Trọng Số & Lưu CSDL",
                percent=90,
                current_item=cls.name,
                log_text=f"Thuật toán trọng số: {scan_res['audit_notes']}"
            )

            present_count = scan_res["present_count"]
            absent_count = scan_res["absent_count"]
            status = scan_res["status"]
            confidence_avg = scan_res["confidence_avg"]
            notes = f"{scan_res['audit_notes']} lúc {scan_time_str}"

            today_capture_dir = settings.CAPTURES_DIR / date_str
            today_capture_dir.mkdir(parents=True, exist_ok=True)
            today_annotated_dir = settings.ANNOTATED_DIR / date_str
            today_annotated_dir.mkdir(parents=True, exist_ok=True)
            latest_dir = settings.CAPTURES_DIR / "latest"
            latest_dir.mkdir(parents=True, exist_ok=True)

            raw_path = ""
            annotated_path = ""

            best_raw = scan_res.get("best_frame")
            if best_raw is not None:
                today_raw_path = today_capture_dir / f"Lop_{cls.id}.jpg"
                cv2.imwrite(str(today_raw_path), best_raw, [cv2.IMWRITE_JPEG_QUALITY, 95])
                latest_raw = latest_dir / f"Lop_{cls.id}.jpg"
                cv2.imwrite(str(latest_raw), best_raw, [cv2.IMWRITE_JPEG_QUALITY, 95])
                raw_path = str(today_raw_path)

            best_annotated = scan_res.get("best_annotated_img")
            if best_annotated is not None:
                today_annotated_file = today_annotated_dir / f"Lop_{cls.id}_result.jpg"
                cv2.imwrite(str(today_annotated_file), best_annotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
                latest_annotated = latest_dir / f"Lop_{cls.id}_annotated.jpg"
                cv2.imwrite(str(latest_annotated), best_annotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
                annotated_path = str(today_annotated_file)

            # Cập nhật CSDL
            session = db.query(AttendanceSession).filter(AttendanceSession.scan_date == date_str).order_by(AttendanceSession.id.desc()).first()
            if not session:
                session = db.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()

            if not session:
                session = AttendanceSession(
                    session_code=f"SESSION_{now.strftime('%Y%m%d_%H%M%S')}",
                    scan_date=date_str,
                    scan_time=scan_time_str,
                    total_classes=1,
                    total_standard=cls.standard_count,
                    total_present=present_count,
                    total_absent=absent_count,
                    status="COMPLETED"
                )
                db.add(session)
                db.flush()

            detail = db.query(AttendanceDetail).filter(
                AttendanceDetail.session_id == session.id,
                AttendanceDetail.classroom_id == cls.id
            ).first()

            if not detail:
                detail = AttendanceDetail(
                    session_id=session.id,
                    classroom_id=cls.id,
                    standard_count=cls.standard_count,
                    raw_image_path=raw_path
                )
                db.add(detail)

            detail.present_count = present_count
            detail.absent_count = absent_count
            detail.status = status
            detail.notes = notes
            detail.confidence_avg = confidence_avg
            if raw_path:
                detail.raw_image_path = raw_path
            if annotated_path:
                detail.annotated_image_path = annotated_path

            all_details = db.query(AttendanceDetail).filter(AttendanceDetail.session_id == session.id).all()
            session.total_present = sum(d.present_count for d in all_details)
            session.total_absent = sum(d.absent_count for d in all_details)
            db.commit()

            duration = round(time.time() - start_time, 2)
            annotated_url = f"/storage/annotated/{date_str}/Lop_{cls.id}_result.jpg?t={int(time.time() * 1000)}" if annotated_path else ""
            snapshot_url = f"/storage/captures/latest/Lop_{cls.id}.jpg?t={int(time.time() * 1000)}"

            result_payload = {
                "success": True,
                "classroom_id": cls.id,
                "classroom_name": cls.name,
                "standard_count": cls.standard_count,
                "present_count": present_count,
                "absent_count": absent_count,
                "status": status,
                "notes": notes,
                "scan_time": scan_time_str,
                "duration_seconds": duration,
                "annotated_url": annotated_url,
                "snapshot_url": snapshot_url,
                "message": f"Đã quét lại thành công {cls.name}! Có mặt: {present_count}/{cls.standard_count} HS (Vắng: {absent_count} HS)"
            }

            progress_tracker.finish(
                True,
                f"Hoàn tất quét lại {cls.name}: Có mặt {present_count}/{cls.standard_count} HS (Vắng {absent_count} HS)",
                result=result_payload
            )
            return result_payload

        except Exception as e:
            db.rollback()
            logger.error(f"Lỗi khi quét lại phòng học {classroom_id}: {e}", exc_info=True)
            progress_tracker.finish(False, f"Lỗi khi quét lại phòng học: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

attendance_engine = AttendanceEngine()
