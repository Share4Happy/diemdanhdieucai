import pytest
import os
from pathlib import Path
from database.db_session import init_db, SessionLocal
from database.models import AttendanceSession, AttendanceDetail, Classroom
from core.attendance_engine import attendance_engine

def test_full_attendance_pipeline():
    init_db()
    db = SessionLocal()

    # Tạm thời chỉ bật 5 lớp để test chạy nhanh trên CPU máy dev (~5-8s)
    # Các lớp khác vẫn giữ nguyên trong DB
    db.query(Classroom).update({Classroom.is_active: False})
    active_classes = db.query(Classroom).limit(5).all()
    for c in active_classes:
        c.is_active = True
    db.commit()

    result = attendance_engine.run_daily_attendance(trigger_led=False)

    assert result["success"] is True
    assert result["total_classes"] == 5
    assert result["total_standard"] > 0
    assert result["total_present"] > 0
    assert result["total_absent"] >= 0
    assert os.path.exists(result["excel_report"])

    # Khôi phục bật lại toàn bộ 30 lớp cho hệ thống hoạt động chính thức
    db.query(Classroom).update({Classroom.is_active: True})
    db.commit()

    # Kiểm tra trong Database
    session = db.query(AttendanceSession).filter(AttendanceSession.id == result["session_id"]).first()
    assert session is not None
    assert session.status == "COMPLETED"

    details = db.query(AttendanceDetail).filter(AttendanceDetail.session_id == session.id).all()
    assert len(details) == 5

    for d in details:
        assert d.standard_count > 0
        assert d.present_count >= 0
        assert d.absent_count >= 0
        assert d.absent_count == max(0, d.standard_count - d.present_count)
        assert os.path.exists(d.raw_image_path)
        assert os.path.exists(d.annotated_image_path)

    db.close()
