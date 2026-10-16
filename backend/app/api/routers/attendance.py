import os
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from database.db_session import get_db
from database.models import Classroom, AttendanceSession, AttendanceDetail, User
from pydantic import BaseModel, Field
from backend.app.core.attendance_engine import attendance_engine
from backend.app.core.timezone_utils import get_now, get_today, get_today_str, get_current_time_str
from starlette.concurrency import run_in_threadpool
from backend.app.api.deps import get_current_user, require_admin
from backend.app.api.security import check_rate_limit, client_ip

class AttendanceOverrideRequest(BaseModel):
    present_count: int = Field(..., ge=0, description="Sĩ số có mặt thực tế sau khi giáo viên/quản trị viên điều chỉnh")
    reason: str = Field(..., min_length=2, description="Lý do điều chỉnh sĩ số (phục vụ kiểm toán hệ thống)")

def format_storage_url(file_path: Optional[str], add_timestamp: bool = True) -> str:
    """Chuyển đổi đường dẫn file cục bộ thành URL web /storage/... chuẩn xác, hỗ trợ thư mục đa tầng và chống cache."""
    if not file_path:
        return ""
    s = str(file_path).replace("\\", "/").strip()
    url = ""
    if s.startswith("/storage/"):
        url = s
    elif s.startswith("storage/"):
        url = "/" + s
    else:
        p = Path(file_path)
        try:
            rel = p.relative_to(settings.STORAGE_DIR).as_posix()
            url = f"/storage/{rel}"
        except Exception:
            storage_str = str(settings.STORAGE_DIR).replace("\\", "/").rstrip("/")
            if s.startswith(storage_str):
                sub = s[len(storage_str):].lstrip("/")
                url = f"/storage/{sub}"
            else:
                url = s

    if add_timestamp:
        p = Path(file_path)
        try:
            mtime = int(p.stat().st_mtime * 1000) if p.exists() else int(time.time() * 1000)
            url += f"{'&' if '?' in url else '?'}t={mtime}"
        except Exception:
            pass
    return url

router = APIRouter(prefix="/attendance", tags=["Attendance"], dependencies=[Depends(get_current_user)])

@router.post("/trigger")
async def trigger_attendance_scan(request: Request, _admin: User = Depends(require_admin)):
    """Kích hoạt quét điểm danh đồng loạt các lớp ngay lập tức trong worker thread, không chặn event loop (chỉ admin)."""
    check_rate_limit("action", f"trigger:{client_ip(request)}", limit=3, window_seconds=120)
    result = await run_in_threadpool(attendance_engine.run_daily_attendance, trigger_led=False)
    return result

@router.get("/progress")
async def get_attendance_progress():
    """Lấy trạng thái tiến trình thời gian thực của tác vụ quét điểm danh / chụp camera."""
    from services.progress_service import progress_tracker
    return progress_tracker.get_state()

@router.get("/latest")
async def get_latest_attendance(db: Session = Depends(get_db)):
    """Lấy kết quả của phiên điểm danh gần nhất kèm tham số chống cache ảnh cho trình duyệt.
    Đảm bảo luôn trả về đầy đủ danh sách 30 lớp học (lớp chưa quét sẽ có trạng thái Chưa xử lý)."""
    all_classrooms = db.query(Classroom).order_by(Classroom.id.asc()).all()
    session = db.query(AttendanceSession).order_by(AttendanceSession.id.desc()).first()

    now_ts = int(time.time() * 1000)
    details_map = {}

    if session:
        details = (
            db.query(AttendanceDetail)
            .filter(AttendanceDetail.session_id == session.id)
            .all()
        )
        for d in details:
            details_map[d.classroom_id] = d

    details_data = []
    for c in all_classrooms:
        if c.id in details_map:
            d = details_map[c.id]
            cname = c.name or f"Lớp {c.id}"
            room = c.room_number or ""

            raw_url = format_storage_url(d.raw_image_path, add_timestamp=True)
            annotated_url = format_storage_url(d.annotated_image_path, add_timestamp=True)

            details_data.append({
                "id": d.id,
                "classroom_id": c.id,
                "class_name": cname,
                "room_number": room,
                "standard_count": d.standard_count,
                "present_count": d.present_count,
                "absent_count": d.absent_count,
                "raw_image_path": raw_url,
                "annotated_image_path": annotated_url,
                "confidence_avg": d.confidence_avg,
                "status": getattr(d, 'status', 'OK') or 'OK',
                "is_manual_override": bool(getattr(d, 'is_manual_override', False)),
                "override_by": getattr(d, 'override_by', None),
                "override_reason": getattr(d, 'override_reason', None),
                "override_at": d.override_at.isoformat() if getattr(d, 'override_at', None) else None,
                "notes": d.notes or ""
            })
        else:
            # Lớp chưa được quét trong phiên này
            std = getattr(c, 'standard_count', 45) or 45
            details_data.append({
                "id": 0,
                "classroom_id": c.id,
                "class_name": c.name or f"Lớp {c.id}",
                "room_number": c.room_number or "",
                "standard_count": std,
                "present_count": 0,
                "absent_count": 0,
                "raw_image_path": "",
                "annotated_image_path": "",
                "confidence_avg": 0,
                "status": "CHUA_XU_LY",
                "is_manual_override": False,
                "override_by": None,
                "override_reason": None,
                "override_at": None,
                "notes": "Chưa xử lý"
            })

    total_std = sum(item["standard_count"] for item in details_data)
    total_prs = sum(item["present_count"] for item in details_data)
    total_abs = sum(item["absent_count"] for item in details_data)

    if session:
        session_obj = {
            "id": session.id,
            "session_code": session.session_code,
            "scan_date": session.scan_date,
            "scan_time": session.scan_time,
            "total_classes": len(all_classrooms),
            "total_standard": total_std,
            "total_present": total_prs,
            "total_absent": total_abs,
            "status": session.status,
            "excel_report_path": session.excel_report_path
        }
    else:
        session_obj = {
            "id": 0,
            "session_code": "CHƯA CÓ PHIÊN",
            "scan_date": get_today_str(),
            "scan_time": get_current_time_str(),
            "total_classes": len(all_classrooms),
            "total_standard": total_std,
            "total_present": 0,
            "total_absent": 0,
            "status": "PENDING",
            "excel_report_path": ""
        }

    return {
        "session": session_obj,
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
async def get_attendance_history(limit: int = 500, db: Session = Depends(get_db)):
    """Lấy lịch sử điểm danh từ CSDL kèm đường dẫn ảnh đối chứng và thông tin kiểm toán (giới hạn tối đa 500 bản ghi)."""
    limit = max(1, min(limit, 500))
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

        raw_url = format_storage_url(d.raw_image_path, add_timestamp=True)
        annotated_url = format_storage_url(d.annotated_image_path, add_timestamp=True)

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
            "status": getattr(d, 'status', 'OK') or 'OK',
            "is_manual_override": bool(getattr(d, 'is_manual_override', False)),
            "override_by": getattr(d, 'override_by', None),
            "override_reason": getattr(d, 'override_reason', None),
            "override_at": d.override_at.isoformat() if getattr(d, 'override_at', None) else None,
            "notes": d.notes or ""
        })

    return {"records": records}

@router.put("/details/{detail_id}/override")
async def override_attendance_detail(
    detail_id: int,
    req: AttendanceOverrideRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cho phép giáo viên/quản trị viên điều chỉnh sĩ số thủ công sau khi quét (kiểm toán toàn diện).
    Ghi nhận đầy đủ thông tin: người sửa, lý do, thời gian sửa và cập nhật lại phiên điểm danh.
    """
    detail = db.query(AttendanceDetail).filter(AttendanceDetail.id == detail_id).first()
    if not detail:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi chi tiết điểm danh")

    old_present = detail.present_count
    detail.present_count = req.present_count
    detail.absent_count = max(0, detail.standard_count - req.present_count)
    detail.is_manual_override = True
    detail.override_by = current_user.email
    detail.override_reason = req.reason.strip()
    detail.override_at = datetime.utcnow()
    detail.status = "OK"

    # Đồng bộ lại tổng sĩ số của AttendanceSession cha
    session = db.query(AttendanceSession).filter(AttendanceSession.id == detail.session_id).first()
    if session:
        all_details = db.query(AttendanceDetail).filter(AttendanceDetail.session_id == session.id).all()
        session.total_present = sum(d.present_count for d in all_details)
        session.total_absent = sum(d.absent_count for d in all_details)

    db.commit()
    db.refresh(detail)
    logger.info(
        f"[AUDIT-OVERRIDE] {current_user.email} đã sửa sĩ số chi tiết ID={detail_id} "
        f"(Lớp {detail.classroom_id}): {old_present} -> {detail.present_count}. Lý do: {req.reason}"
    )

    return {
        "success": True,
        "message": f"Đã điều chỉnh sĩ số thành công: {detail.present_count}/{detail.standard_count}",
        "detail": {
            "id": detail.id,
            "classroom_id": detail.classroom_id,
            "standard_count": detail.standard_count,
            "present_count": detail.present_count,
            "absent_count": detail.absent_count,
            "status": detail.status,
            "is_manual_override": detail.is_manual_override,
            "override_by": detail.override_by,
            "override_reason": detail.override_reason,
            "override_at": detail.override_at.isoformat() if detail.override_at else None
        }
    }

@router.get("/sessions/{session_id}")
async def get_session_by_id(session_id: int, db: Session = Depends(get_db)):
    """Lấy chi tiết của một phiên điểm danh bất kỳ theo ID kèm thông tin kiểm toán."""
    session = db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên điểm danh")

    details = (
        db.query(AttendanceDetail)
        .filter(AttendanceDetail.session_id == session.id)
        .order_by(AttendanceDetail.classroom_id.asc())
        .all()
    )
    details_data = []
    for d in details:
        cls = d.classroom
        details_data.append({
            "id": d.id,
            "classroom_id": d.classroom_id,
            "class_name": cls.name if cls else f"Lớp {d.classroom_id}",
            "room_number": cls.room_number if cls else "",
            "standard_count": d.standard_count,
            "present_count": d.present_count,
            "absent_count": d.absent_count,
            "raw_image_path": format_storage_url(d.raw_image_path, add_timestamp=True),
            "annotated_image_path": format_storage_url(d.annotated_image_path, add_timestamp=True),
            "confidence_avg": d.confidence_avg,
            "status": getattr(d, 'status', 'OK') or 'OK',
            "is_manual_override": bool(getattr(d, 'is_manual_override', False)),
            "override_by": getattr(d, 'override_by', None),
            "override_reason": getattr(d, 'override_reason', None),
            "override_at": d.override_at.isoformat() if getattr(d, 'override_at', None) else None,
            "notes": d.notes or ""
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

@router.get("/today-sessions")
async def get_today_sessions(db: Session = Depends(get_db)):
    """Lấy danh sách các phiên điểm danh diễn ra trong ngày hôm nay kèm fallback phiên gần nhất."""
    today_str = get_today_str()
    sessions = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.scan_date == today_str)
        .order_by(AttendanceSession.id.desc())
        .all()
    )
    # Nếu ngày hôm nay chưa có phiên, fallback lấy 10 phiên gần nhất
    if not sessions:
        sessions = (
            db.query(AttendanceSession)
            .order_by(AttendanceSession.id.desc())
            .limit(10)
            .all()
        )

    sessions_data = []
    for s in sessions:
        sessions_data.append({
            "id": s.id,
            "session_code": s.session_code,
            "scan_date": s.scan_date,
            "scan_time": s.scan_time,
            "total_classes": s.total_classes,
            "total_standard": s.total_standard,
            "total_present": s.total_present,
            "total_absent": s.total_absent,
            "status": s.status,
            "excel_report_path": s.excel_report_path
        })

    return {"sessions": sessions_data, "is_today": len(sessions) > 0 and sessions[0].scan_date == today_str}

@router.get("/trend-7days")
async def get_7days_trend(db: Session = Depends(get_db)):
    """Trả về dữ liệu xu hướng chuyên cần & số học sinh vắng 7 ngày gần nhất phục vụ biểu đồ Trend Line."""
    from datetime import timedelta

    today = get_today()
    date_list = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    # Lấy các phiên điểm danh thực tế từ CSDL
    sessions = (
        db.query(AttendanceSession)
        .order_by(AttendanceSession.scan_date.desc(), AttendanceSession.id.desc())
        .limit(50)
        .all()
    )

    # Gom nhóm phiên gần nhất của từng ngày
    day_map = {}
    for s in sessions:
        if s.scan_date and s.scan_date not in day_map:
            day_map[s.scan_date] = s

    result_days = []
    day_names_vn = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"]
    standard_total = 1350

    for idx, d_str in enumerate(date_list):
        d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
        weekday_idx = (d_obj.weekday() + 1) % 7
        vn_day = day_names_vn[weekday_idx]
        is_today = (d_str == today.strftime("%Y-%m-%d"))
        display_label = f"{d_obj.strftime('%d/%m')} (Hôm nay)" if is_today else f"{d_obj.strftime('%d/%m')} ({vn_day})"

        if d_str in day_map:
            s = day_map[d_str]
            std = s.total_standard or standard_total
            prs = s.total_present or 0
            abs_cnt = s.total_absent if s.total_absent is not None else max(0, std - prs)
            rate = round((prs / std * 100), 1) if std > 0 else 100.0
            result_days.append({
                "date": d_str,
                "label": display_label,
                "total_standard": std,
                "present": prs,
                "absent": abs_cnt,
                "rate": rate,
                "is_actual": True,
                "is_today": is_today
            })
        else:
            # Ngày không có dữ liệu: Báo trung thực 0, KHÔNG tạo số liệu ngẫu nhiên ảo
            result_days.append({
                "date": d_str,
                "label": display_label,
                "total_standard": standard_total,
                "present": 0,
                "absent": 0,
                "rate": 0.0,
                "is_actual": False,
                "is_today": is_today
            })

    # Tính toán trung bình và đánh giá CHỈ dựa trên các ngày có dữ liệu thực tế
    actual_days = [d for d in result_days if d["is_actual"]]
    if actual_days:
        avg_absent = round(sum(d["absent"] for d in actual_days) / len(actual_days), 1)
    else:
        avg_absent = 0.0

    today_data = result_days[-1]
    today_absent = today_data["absent"] if today_data["is_actual"] else 0

    if not actual_days:
        assessment_status = "normal"
        assessment_text = "Hệ thống đang chờ phiên điểm danh đầu tiên."
        diff = 0.0
    else:
        diff = today_absent - avg_absent
        if diff >= 15:
            assessment_status = "danger"
            assessment_text = f"Cao hơn trung bình (+{int(round(diff))} em) • Bất thường cần lưu ý"
        elif diff >= 5:
            assessment_status = "warning"
            assessment_text = f"Tăng nhẹ so với trung bình (+{int(round(diff))} em)"
        elif diff <= -8:
            assessment_status = "success"
            assessment_text = f"Thấp hơn mức trung bình ({int(round(diff))} em) • Rất tốt"
        else:
            diff_str = f"+{int(round(diff))}" if diff > 0 else f"{int(round(diff))}"
            assessment_status = "normal"
            assessment_text = f"Ổn định quanh mức trung bình ({diff_str} em)"

    return {
        "days": result_days,
        "avg_absent": avg_absent,
        "today_absent": today_absent,
        "assessment": {
            "status": assessment_status,
            "text": assessment_text,
            "diff": round(diff, 1)
        }
    }
    
@router.post("/clear-history")
@router.delete("/clear-history")
async def clear_attendance_history(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Xóa toàn bộ lịch sử các phiên điểm danh để làm mới hệ thống (chỉ admin)."""
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
