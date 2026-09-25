import os
import cv2
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import SessionLocal
from database.models import Classroom, ROIPolygon, AttendanceSession, AttendanceDetail
from core.rtsp_client import rtsp_client
from core.relay_service import relay_service
from core.detector import detector
from core.timezone_utils import get_now

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
        trigger_led: bool = True
    ) -> Dict[str, Any]:
        """
        Quy trình điểm danh đồng loạt 30 lớp:
        1. Kích hoạt Relay bật đèn LED hồng ngoại lúc 6h45.
        2. Chụp ảnh đồng loạt 30 camera qua đa luồng RTSP.
        3. Áp dụng Masking & AI YOLO đếm đầu người.
        4. Tính toán số học sinh hiện diện, số học sinh vắng.
        5. Lưu kết quả và đường dẫn file ảnh đối chứng vào CSDL.
        """
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
                return {"success": False, "message": "Không có lớp học"}

            # 1. Bật đèn hồng ngoại camera báo hiệu giờ điểm danh (trước khi chụp)
            if trigger_led:
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
            capture_results = rtsp_client.capture_all_classrooms(
                cls_data_list,
                date_str=date_str,
                target_folder=session_captures_folder
            )

            # 3. Tự động trả các camera về chế độ Tự Động (Auto) sau khi đã chụp xong
            if trigger_led:
                relay_service.restore_classrooms_auto(classrooms)

            total_standard = 0
            total_present = 0
            total_absent = 0
            details_list = []

            # 3. Chạy AI đếm số lượng cho từng lớp
            for cls in classrooms:
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

                if frame is None and raw_path and os.path.exists(raw_path):
                    frame = cv2.imread(raw_path)

                present_count = 0
                annotated_path = ""
                confidence_avg = 0.0

                if frame is not None:
                    # Chạy AI Object Detection & Masking
                    roi_dims = (cls.roi.image_width, cls.roi.image_height) if (cls.roi and cls.roi.image_width and cls.roi.image_height) else None
                    present_count, detected_students, annotated_img = detector.detect_students_in_classroom(
                        image=frame,
                        red_zone=red_zone,
                        green_zone=green_zone,
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

                # Tạo ghi chú nếu có hiện tượng bất thường
                notes = "Đủ sĩ số" if absent_count == 0 else f"Vắng {absent_count} học sinh"
                if present_count > std_count:
                    notes = f"Vượt sĩ số chuẩn (+{present_count - std_count})"

                detail = AttendanceDetail(
                    session_id=new_session.id,
                    classroom_id=c_id,
                    standard_count=std_count,
                    present_count=present_count,
                    absent_count=absent_count,
                    raw_image_path=raw_path,
                    annotated_image_path=annotated_path,
                    confidence_avg=round(confidence_avg, 2),
                    notes=notes
                )
                db.add(detail)
                details_list.append({
                    "class_name": c_name,
                    "standard": std_count,
                    "present": present_count,
                    "absent": absent_count,
                    "notes": notes,
                    "annotated_path": annotated_path
                })

            # Cập nhật kết quả tổng hợp vào Session
            new_session.total_standard = total_standard
            new_session.total_present = total_present
            new_session.total_absent = total_absent
            new_session.status = "COMPLETED"
            db.commit()

            logger.info(
                f"=== KẾT QUẢ ĐIỂM DANH: Tổng {len(classrooms)} lớp | "
                f"Sĩ số: {total_standard} | Hiện diện: {total_present} | Vắng: {total_absent} ==="
            )

            # 4. Tự động xuất báo cáo Excel và gửi thông báo
            from services.excel_exporter import excel_exporter
            from services.notification import notification_service

            excel_path = excel_exporter.generate_daily_report(new_session.id)
            if excel_path:
                new_session.excel_report_path = str(excel_path)
                db.commit()
                # Phân phối báo cáo
                notification_service.send_attendance_report(new_session.id, excel_path)

            return {
                "success": True,
                "session_id": new_session.id,
                "session_code": session_code,
                "date": date_str,
                "time": scan_time_str,
                "total_classes": len(classrooms),
                "total_standard": total_standard,
                "total_present": total_present,
                "total_absent": total_absent,
                "excel_report": new_session.excel_report_path,
                "details": details_list
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Lỗi trong quá trình điểm danh tự động: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

attendance_engine = AttendanceEngine()
