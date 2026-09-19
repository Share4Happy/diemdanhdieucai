import pytest
import os
import openpyxl
import uuid
from database.db_session import SessionLocal, init_db
from database.models import Classroom, AttendanceSession, AttendanceDetail
from services.excel_exporter import excel_exporter

def test_excel_export_generation():
    init_db()
    db = SessionLocal()

    # Tạo phiên điểm danh test với mã duy nhất
    session = AttendanceSession(
        session_code=f"TEST_SESSION_{uuid.uuid4().hex[:8]}",
        scan_date="2026-09-18",
        scan_time="06:45:00",
        total_classes=3,
        total_standard=120,
        total_present=116,
        total_absent=4,
        status="COMPLETED"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    classrooms = db.query(Classroom).limit(3).all()
    for idx, c in enumerate(classrooms):
        detail = AttendanceDetail(
            session_id=session.id,
            classroom_id=c.id,
            standard_count=40,
            present_count=39 if idx == 0 else 40,
            absent_count=1 if idx == 0 else 0,
            notes="Khớp dữ liệu test"
        )
        db.add(detail)
    db.commit()

    # Xuất Excel
    report_path = excel_exporter.generate_daily_report(session.id)
    assert report_path is not None
    assert os.path.exists(str(report_path))

    # Đọc và kiểm tra nội dung file Excel
    wb = openpyxl.load_workbook(str(report_path), data_only=False)
    assert "Báo Cáo Điểm Danh" in wb.sheetnames
    ws = wb["Báo Cáo Điểm Danh"]

    # Kiểm tra tiêu đề
    assert "TRƯỜNG TRUNG HỌC PHỔ THÔNG ĐIỀU CẢI" in str(ws["A1"].value)
    assert "BÁO CÁO TỔNG HỢP ĐIỂM DANH SĨ SỐ" in str(ws["A2"].value)

    db.close()
