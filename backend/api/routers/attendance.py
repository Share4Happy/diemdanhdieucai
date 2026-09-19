import os
import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db
from database.models import Classroom, AttendanceSession, AttendanceDetail
from core.attendance_engine import attendance_engine

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.post("/trigger")
async def trigger_attendance_scan():
    """Kích hoạt quét điểm danh đồng loạt 30 lớp ngay lập tức."""
    result = attendance_engine.run_daily_attendance(trigger_led=True)
    return result

@router.get("/latest")
async def get_latest_attendance(db: Session = Depends(get_db)):
    """Lấy kết quả của phiên điểm danh gần nhất kèm tham số chống cache ảnh cho trình duyệt."""
    session = db.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()
    if not session:
        return {"session": None, "details": []}

    details = (
        db.query(AttendanceDetail)
        .filter(AttendanceDetail.session_id == session.id)
        .order_by(AttendanceDetail.classroom_id)
        .all()
    )

    now_ts = int(time.time() * 1000)
    details_data = []
    for d in details:
        cname = d.classroom.name if d.classroom else f"Lớp {d.classroom_id}"
        room = d.classroom.room_number if d.classroom else ""

        raw_url = ""
        if d.raw_image_path:
            p = Path(d.raw_image_path)
            mtime = int(p.stat().st_mtime * 1000) if p.exists() else now_ts
            raw_url = f"/storage/captures/{p.parent.name}/{p.name}?t={mtime}"

        annotated_url = ""
        if d.annotated_image_path:
            p = Path(d.annotated_image_path)
            mtime = int(p.stat().st_mtime * 1000) if p.exists() else now_ts
            annotated_url = f"/storage/annotated/{p.parent.name}/{p.name}?t={mtime}"

        details_data.append({
            "classroom_id": d.classroom_id,
            "class_name": cname,
            "room_number": room,
            "standard_count": d.standard_count,
            "present_count": d.present_count,
            "absent_count": d.absent_count,
            "raw_image_path": raw_url,
            "annotated_image_path": annotated_url,
            "confidence_avg": d.confidence_avg,
            "notes": d.notes
        })

    return {
        "session": {
            "id": session.id,
            "session_code": session.session_code,
            "scan_date": session.scan_date,
            "scan_time": session.scan_time,
            "total_classes": session.total_classes,
            "total_standard": session.total_standard,
            "total_present": session.total_present,
            "total_absent": session.total_absent,
            "status": session.status,
            "excel_report_path": session.excel_report_path
        },
        "details": details_data
    }

@router.get("/download-excel")
async def download_excel(db: Session = Depends(get_db)):
    """Tải file báo cáo Excel của phiên điểm danh gần nhất."""
    session = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.excel_report_path.isnot(None), AttendanceSession.excel_report_path != "", AttendanceSession.excel_report_path != "''")
        .order_by(AttendanceSession.id.desc())
        .first()
    )
    if session and session.excel_report_path and os.path.exists(session.excel_report_path):
        file_path = session.excel_report_path
        filename = Path(file_path).name
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Dự phòng 1: Thư mục latest
    latest_copy = settings.REPORTS_DIR / "latest" / "BaoCaoDiemDanh_MoiNhat.xlsx"
    if latest_copy.exists():
        return FileResponse(
            path=str(latest_copy),
            filename="BaoCaoDiemDanh_MoiNhat.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Dự phòng 2: File .xlsx mới nhất trong toàn bộ thư mục reports
    all_reports = sorted(settings.REPORTS_DIR.rglob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if all_reports:
        latest_report = all_reports[0]
        return FileResponse(
            path=str(latest_report),
            filename=latest_report.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    raise HTTPException(status_code=404, detail="Chưa có file báo cáo Excel nào được xuất.")

@router.get("/history")
async def get_attendance_history(limit: int = 150, db: Session = Depends(get_db)):
    """Lấy toàn bộ lịch sử điểm danh từ CSDL kèm đường dẫn ảnh đối chứng."""
    details = (
        db.query(AttendanceDetail)
        .join(AttendanceSession)
        .join(Classroom)
        .order_by(AttendanceSession.id.desc(), Classroom.id.asc())
        .limit(limit)
        .all()
    )

    records = []
    for d in details:
        s = d.session
        c = d.classroom

        raw_url = ""
        if d.raw_image_path and os.path.exists(d.raw_image_path):
            p = Path(d.raw_image_path)
            raw_url = f"/storage/captures/{p.parent.name}/{p.name}"

        annotated_url = ""
        if d.annotated_image_path and os.path.exists(d.annotated_image_path):
            p = Path(d.annotated_image_path)
            annotated_url = f"/storage/annotated/{p.parent.name}/{p.name}"

        records.append({
            "id": d.id,
            "session_code": s.session_code if s else "",
            "scan_date": s.scan_date if s else "",
            "scan_time": s.scan_time if s else "",
            "class_name": c.name if c else f"Lớp {d.classroom_id}",
            "room_number": c.room_number if c else "",
            "standard_count": d.standard_count,
            "present_count": d.present_count,
            "absent_count": d.absent_count,
            "raw_image_path": raw_url,
            "annotated_image_path": annotated_url,
            "confidence_avg": d.confidence_avg,
            "notes": d.notes
        })

    return {"records": records}
    
@router.post("/clear-history")
@router.delete("/clear-history")
async def clear_attendance_history(db: Session = Depends(get_db)):
    """Xóa toàn bộ lịch sử các phiên điểm danh để làm mới hệ thống."""
    try:
        db.query(AttendanceDetail).delete()
        num_sessions = db.query(AttendanceSession).delete()
        db.commit()
        return {
            "success": True, 
            "message": f"Đã xóa sạch toàn bộ lịch sử ({num_sessions} phiên điểm danh) thành công."
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi khi xóa lịch sử điểm danh: {e}")
        raise HTTPException(status_code=500, detail=str(e))
