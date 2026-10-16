import pytest
import os
from pathlib import Path
from database.db_session import init_db, SessionLocal
from database.models import AttendanceSession, AttendanceDetail, Classroom
from backend.core.attendance_engine import attendance_engine

def test_full_attendance_pipeline():
    init_db()
    db = SessionLocal()

    try:
        from database.db_session import seed_default_classes
        if db.query(Classroom).count() == 0:
            seed_default_classes(db)

        # Tạm thời chỉ bật 5 lớp để test chạy nhanh trên CPU máy dev (~5-8s)
        # Các lớp khác vẫn giữ nguyên trong DB
        db.query(Classroom).update({Classroom.is_active: False})
        active_classes = db.query(Classroom).limit(5).all()
        expected_count = len(active_classes)
        for c in active_classes:
            c.is_active = True
        db.commit()
    finally:
        db.close()

    try:
        result = attendance_engine.run_daily_attendance(trigger_led=False)
        assert result["success"] is True
        assert result["total_classes"] == expected_count
        assert result["total_standard"] > 0
        assert result["total_present"] >= 0
        assert result["total_absent"] >= 0
        assert os.path.exists(result["excel_report"])
    finally:
        # Khôi phục bật lại toàn bộ lớp cho hệ thống hoạt động chính thức
        db_restore = SessionLocal()
        try:
            db_restore.query(Classroom).update({Classroom.is_active: True})
            db_restore.commit()
        finally:
            db_restore.close()

    # Kiểm tra trong Database
    db_check = SessionLocal()
    try:
        session = db_check.query(AttendanceSession).filter(AttendanceSession.id == result["session_id"]).first()
        assert session is not None
        assert session.status.startswith("COMPLETED")

        details = db_check.query(AttendanceDetail).filter(AttendanceDetail.session_id == session.id).all()
        assert len(details) == expected_count

        for d in details:
            assert d.standard_count > 0
            assert d.status in ["OK", "NO_SIGNAL", "STALE", "CAN_KIEM_TRA"]
            if d.status == "OK":
                assert d.present_count >= 0
                assert d.absent_count >= 0
                assert d.absent_count == max(0, d.standard_count - d.present_count)
            else:
                assert d.status in ["NO_SIGNAL", "CAN_KIEM_TRA", "STALE"]
                assert d.present_count == 0
                assert d.absent_count == 0
            assert os.path.exists(d.raw_image_path)
            assert os.path.exists(d.annotated_image_path)
    finally:
        db_check.close()
