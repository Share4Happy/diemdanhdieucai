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
from backend.app.core.rtsp_client import rtsp_client
from backend.app.core.relay_service import relay_service
from backend.app.core.detector import detector
from backend.app.core.timezone_utils import get_now
from services.progress_service import progress_tracker

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

            progress_tracker.update(
                step=2,
                step_title="2/3: Phân Tích AI YOLO & Đếm Sĩ Số",
                percent=50,
                log_text="Hoàn tất chụp ảnh 30 camera. Bắt đầu nhận diện AI YOLO..."
            )

            # 4. Chạy AI đếm số lượng cho từng lớp
            for idx, cls in enumerate(classrooms, start=1):
                c_id = cls.id
                c_name = cls.name
                std_count = cls.standard_count
                total_standard += std_count

                # Lấy tọa độ ROI từ DB
                red_zone = cls.roi.red_zone if cls.roi else []
                green_zone = cls.roi.green_zone if cls.roi else []

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
                    # 1. Kiểm tra phát hiện ảnh đóng băng (Frozen Frame Detection - chống camera/NVR bị treo hình)
                    is_frozen = False
                    try:
                        prev_detail = (
                            db.query(AttendanceDetail)
                            .filter(
                                AttendanceDetail.classroom_id == c_id,
                                AttendanceDetail.session_id != new_session.id,
                                AttendanceDetail.raw_image_path != ""
                            )
                            .order_by(AttendanceDetail.id.desc())
                            .first()
                        )
                        if prev_detail and prev_detail.raw_image_path and Path(prev_detail.raw_image_path).exists():
                            prev_img = cv2.imread(prev_detail.raw_image_path)
                            if prev_img is not None and prev_img.shape == frame.shape:
                                t_curr = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (64, 64))
                                t_prev = cv2.resize(cv2.cvtColor(prev_img, cv2.COLOR_BGR2GRAY), (64, 64))
                                mse = float(np.mean((t_curr.astype("float") - t_prev.astype("float")) ** 2))
                                if mse < 0.5:
                                    is_frozen = True
                                    logger.warning(f"Lớp {c_name} (ID: {c_id}): Phát hiện ảnh đóng băng (MSE={mse:.3f} < 0.5 so với phiên trước)!")
                    except Exception as e_frozen:
                        logger.debug(f"Lỗi kiểm tra đóng băng cho lớp {c_name}: {e_frozen}")

                    # 2. Kiểm tra chất lượng khung hình trước khi chạy AI (Anti-Blur & Darkness Filter)
                    try:
                        gray_chk = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        brightness = float(gray_chk.mean())
                        lap_sharpness = float(cv2.Laplacian(gray_chk, cv2.CV_64F).var())
                    except Exception:
                        brightness = 100.0
                        lap_sharpness = 20.0

                    min_lap = getattr(cls, 'laplacian_threshold', None) or 5.0
                    cam_conf = getattr(cls, 'conf_threshold', None)

                    if is_frozen:
                        status = "CAN_KIEM_TRA"
                        notes = "⚠️ Cảnh báo: Hình ảnh đóng băng (Frozen Frame - camera/NVR bị treo hình)"
                        logger.warning(f"Lớp {c_name} (ID: {c_id}): Hình ảnh đóng băng. Đánh dấu CAN_KIEM_TRA.")
                    elif brightness < 15.0 or lap_sharpness < min_lap:
                        # Ảnh mờ hoặc tối -> Đánh dấu CAN_KIEM_TRA, KHÔNG chạy AI rồi gán vắng cả lớp
                        status = "CAN_KIEM_TRA"
                        reason = "Ảnh quá tối" if brightness < 15.0 else f"Ảnh bị mờ (Độ nét: {lap_sharpness:.1f} < {min_lap})"
                        notes = f"⚠️ {reason} (Chờ kiểm tra thủ công)"
                        logger.warning(f"Lớp {c_name} (ID: {c_id}): {reason}. Đánh dấu CAN_KIEM_TRA.")
                    else:
                        # Chạy AI Object Detection & Masking với ngưỡng riêng (nếu có cấu hình)
                        roi_dims = (cls.roi.image_width, cls.roi.image_height) if (cls.roi and cls.roi.image_width and cls.roi.image_height) else None
                        present_count, detected_students, annotated_img = detector.detect_students_in_classroom(
                            image=frame,
                            red_zone=red_zone,
                            green_zone=green_zone,
                            conf_threshold=cam_conf,
                            classroom_name=c_name,
                            standard_count=std_count,
                            apply_clahe=settings.USE_IMAGE_ENHANCEMENT,
                            roi_dims=roi_dims
                        )

                        # Lưu ảnh đối chứng đã vẽ bounding box vào thư mục riêng của phiên này
                        annotated_filename = f"Lop_{c_id}_result.jpg"
                        annotated_filepath = session_annotated_folder / annotated_filename
                        cv2.imwrite(str(annotated_filepath), annotated_img)
                        annotated_path = str(annotated_filepath)

                        if detected_students:
                            confidence_avg = sum(s["confidence"] for s in detected_students) / len(detected_students)

                        absent_count = max(0, std_count - present_count)
                        total_present += present_count
                        total_absent += absent_count

                        # Kiểm tra cảnh báo độ lệch >20% so với trung bình 7 ngày trước của lớp đó
                        try:
                            past_details = (
                                db.query(AttendanceDetail)
                                .filter(
                                    AttendanceDetail.classroom_id == c_id,
                                    AttendanceDetail.session_id != new_session.id,
                                    AttendanceDetail.status == "OK"
                                )
                                .order_by(AttendanceDetail.id.desc())
                                .limit(7)
                                .all()
                            )
                            if len(past_details) >= 3:
                                avg_7d = sum(d.present_count for d in past_details) / len(past_details)
                                if avg_7d > 5 and (abs(present_count - avg_7d) / avg_7d) > 0.20:
                                    dev_pct = int(abs(present_count - avg_7d) / avg_7d * 100)
                                    dev_note = f" [Cảnh báo: Sĩ số lệch {dev_pct}% so với TB 7 ngày ({avg_7d:.0f})]"
                                    notes = (notes + dev_note) if notes else dev_note.strip()
                        except Exception as e_dev:
                            logger.debug(f"Không thể tính độ lệch 7 ngày cho lớp {c_name}: {e_dev}")

                else:
                    notes = "⚠️ Mất tín hiệu Camera (Chờ kiểm tra thủ công)"
                    logger.warning(f"Lớp {c_name} (ID: {c_id}) mất tín hiệu camera. Đánh dấu NO_SIGNAL, không tính vắng khống.")

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

                # Cập nhật tiến trình AI từng lớp (50% -> 90%)
                pct_ai = int(50 + (idx / total_cams) * 40)
                progress_tracker.update(
                    step=2,
                    step_title="2/3: Phân Tích AI YOLO & Đếm Sĩ Số",
                    current=idx,
                    total=total_cams,
                    current_item=f"{c_name}: Có mặt {present_count}/{std_count}",
                    percent=pct_ai,
                    log_text=f"AI hoàn tất lớp {c_name}: có mặt {present_count}/{std_count} (vắng {absent_count})",
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

attendance_engine = AttendanceEngine()
