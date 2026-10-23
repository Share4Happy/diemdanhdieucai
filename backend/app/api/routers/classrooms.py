import io
import re
import json
import urllib.parse
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from config.logging_config import logger
from database.db_session import get_db
from database.models import Classroom, ROIPolygon, NVRDevice, User
from backend.app.api.deps import get_current_user, require_admin
from backend.app.schemas.classroom_schemas import (
    ClassroomCreateRequest,
    ClassroomUpdateRequest,
    ClassroomBatchImportRequest,
    ClassroomQuickUpdateCount,
)

router = APIRouter(prefix="/classrooms", tags=["Classrooms"], dependencies=[Depends(get_current_user)])

def _extract_grade(name: str) -> str:
    """Trích xuất khối lớp (10, 11, 12) từ tên lớp."""
    m = re.search(r"\b(10|11|12)", name)
    return m.group(1) if m else "Khác"

def _generate_code(name: str) -> str:
    """Tự động sinh mã lớp chuẩn, vd: 10A1 -> LOP_10A1."""
    clean = re.sub(r"[^A-Za-z0-9]", "", name).upper()
    if not clean.startswith("LOP"):
        clean = f"LOP_{clean}"
    return clean

@router.get("")
@router.get("/")
async def get_classrooms(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tên lớp, phòng, mã lớp"),
    grade: Optional[str] = Query(None, description="Lọc theo khối (10, 11, 12)"),
    has_camera: Optional[bool] = Query(None, description="Lọc theo tình trạng gắn camera"),
    db: Session = Depends(get_db)
):
    """Lấy danh sách quản lý lớp học cùng số liệu thống kê sĩ số và camera."""
    query = db.query(Classroom).options(joinedload(Classroom.roi)).order_by(Classroom.id.asc())
    all_classes = query.all()

    # Tính toán số liệu thống kê tổng thể
    total_classes = len(all_classes)
    total_students = sum(c.standard_count for c in all_classes)
    avg_students = round(total_students / total_classes, 1) if total_classes > 0 else 0
    with_camera = sum(1 for c in all_classes if (c.rtsp_url and c.rtsp_url.strip()) or c.channel_number)
    without_camera = total_classes - with_camera

    # Lọc kết quả trả về
    search_val = search.strip().lower() if isinstance(search, str) and search.strip() else None
    grade_val = grade.strip() if isinstance(grade, str) and grade.strip() else None
    has_camera_val = has_camera if isinstance(has_camera, bool) else None

    filtered = []
    for c in all_classes:
        c_grade = _extract_grade(c.name)
        if grade_val and grade_val != "all" and c_grade != grade_val:
            continue

        c_has_camera = bool((c.rtsp_url and c.rtsp_url.strip()) or c.channel_number)
        if has_camera_val is not None and c_has_camera != has_camera_val:
            continue

        if search_val:
            match = (
                search_val in c.name.lower() or
                search_val in (c.code or "").lower() or
                search_val in (c.room_number or "").lower() or
                search_val in (c.rtsp_url or "").lower()
            )
            if not match:
                continue

        camera_label = ""
        if c.channel_number:
            camera_label = f"Kênh NVR {c.channel_number}"
        elif c.rtsp_url:
            if "stream" in c.rtsp_url.lower():
                camera_label = "Luồng RTSP Mô Phỏng"
            elif c.rtsp_url.isdigit():
                camera_label = f"Webcam #{c.rtsp_url}"
            else:
                camera_label = "Camera IP / RTSP"
        else:
            camera_label = "Chưa gán camera"

        filtered.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "grade": c_grade,
            "room_number": c.room_number or "",
            "standard_count": c.standard_count,
            "rtsp_url": c.rtsp_url or "",
            "channel_number": c.channel_number,
            "nvr_id": c.nvr_id,
            "relay_ip": c.relay_ip or "",
            "is_active": c.is_active,
            "has_camera": c_has_camera,
            "camera_label": camera_label,
            "has_roi": bool(c.roi and (c.roi.green_zone or c.roi.red_zone))
        })

    return {
        "success": True,
        "stats": {
            "total_classes": total_classes,
            "total_students": total_students,
            "avg_students": avg_students,
            "with_camera": with_camera,
            "without_camera": without_camera
        },
        "count": len(filtered),
        "data": filtered
    }

@router.get("/available-cameras")
async def get_available_cameras(db: Session = Depends(get_db)):
    """Lấy danh sách các kênh camera NVR và camera khả dụng để gán cho lớp học."""
    classrooms = db.query(Classroom).all()
    channel_map = {c.channel_number: c for c in classrooms if c.channel_number}

    # 30 kênh NVR chuẩn của trường
    nvr_channels = []
    for ch in range(1, 31):
        assigned_to = channel_map.get(ch)
        nvr_channels.append({
            "channel": ch,
            "name": f"Kênh {ch:02d} (Camera Phòng {ch})",
            "default_rtsp": f"rtsp://localhost:8554/stream{ch}",
            "is_assigned": assigned_to is not None,
            "assigned_class_id": assigned_to.id if assigned_to else None,
            "assigned_class_name": assigned_to.name if assigned_to else None
        })

    return {
        "success": True,
        "nvr_channels": nvr_channels
    }

@router.get("/template")
async def download_import_template(format: str = Query("xlsx", pattern="^(xlsx|csv)$")):
    """Tải tệp mẫu Excel hoặc CSV chuẩn hóa để nhập danh sách lớp học và map camera."""
    columns = [
        "Mã Lớp", "Tên Lớp", "Khối", "Phòng Học", "Sĩ Số", "Kênh NVR (1-30)", "Luồng RTSP (Tùy chọn)"
    ]

    sample_rows = [
        ("LOP_10A1", "10A1", "10", "Phòng 21", 44, 21, "rtsp://localhost:8554/stream21"),
        ("LOP_10A2", "10A2", "10", "Phòng 23", 40, 23, "rtsp://localhost:8554/stream23"),
        ("LOP_10A3", "10A3", "10", "Phòng 24", 38, 24, "rtsp://localhost:8554/stream24"),
        ("LOP_11A1", "11A1", "11", "Phòng 11", 43, 11, "rtsp://localhost:8554/stream11"),
        ("LOP_11A2", "11A2", "11", "Phòng 12", 43, 12, "rtsp://localhost:8554/stream12"),
        ("LOP_12A1", "12A1", "12", "Phòng 1", 48, 1, "rtsp://localhost:8554/stream1"),
        ("LOP_12A2", "12A2", "12", "Phòng 2", 45, 2, "rtsp://localhost:8554/stream2"),
    ]

    if format == "csv":
        output = io.StringIO()
        df = pd.DataFrame(sample_rows, columns=columns)
        df.to_csv(output, index=False, encoding="utf-8-sig")
        mem = io.BytesIO(output.getvalue().encode("utf-8-sig"))
        mem.seek(0)
        filename = "mau_nhap_danh_sach_lop_hoc.csv"
        return StreamingResponse(
            mem,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{urllib.parse.quote(filename)}\'',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    # Tạo tệp Excel định dạng đẹp bằng openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh Sách Lớp Học"

    # Header styling
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=11)
    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    ws.append(columns)
    for col_num in range(1, len(columns) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin

    for row_data in sample_rows:
        ws.append(list(row_data))

    for row in range(2, len(sample_rows) + 2):
        for col_num in range(1, len(columns) + 1):
            cell = ws.cell(row=row, column=col_num)
            cell.font = data_font
            cell.border = border_thin
            if col_num in [3, 5, 6]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Tự động căn chỉnh độ rộng cột
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = "mau_nhap_danh_sach_lop_hoc_thpt_dieu_cai.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{urllib.parse.quote(filename)}\'',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.get("/export")
async def export_classrooms_excel(db: Session = Depends(get_db)):
    """Xuất toàn bộ danh sách lớp học hiện tại cùng sĩ số và camera ra file Excel."""
    classrooms = db.query(Classroom).order_by(Classroom.id.asc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DS Lớp Học THPT Điều Cải"

    headers = [
        "STT", "Mã Lớp", "Tên Lớp", "Khối", "Phòng Học",
        "Sĩ Số Chuẩn", "Kênh NVR", "Luồng Camera RTSP", "Trạng Thái"
    ]

    header_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=11)
    border_thin = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin

    for idx, c in enumerate(classrooms, start=1):
        status = "Đang hoạt động" if c.is_active else "Tạm ngưng"
        grade = _extract_grade(c.name)
        row = [
            idx,
            c.code,
            c.name,
            grade,
            c.room_number or "",
            c.standard_count,
            c.channel_number or "",
            c.rtsp_url or "",
            status
        ]
        ws.append(row)

    for row in range(2, len(classrooms) + 2):
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=row, column=col_num)
            cell.font = data_font
            cell.border = border_thin
            if col_num in [1, 4, 6, 7, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"danh_sach_lop_hoc_dieu_cai_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{urllib.parse.quote(filename)}\'',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@router.get("/{classroom_id}")
async def get_classroom_detail(classroom_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin chi tiết một lớp học."""
    cls = db.query(Classroom).options(joinedload(Classroom.roi)).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    return {
        "success": True,
        "data": {
            "id": cls.id,
            "code": cls.code,
            "name": cls.name,
            "grade": _extract_grade(cls.name),
            "room_number": cls.room_number or "",
            "standard_count": cls.standard_count,
            "rtsp_url": cls.rtsp_url or "",
            "channel_number": cls.channel_number,
            "nvr_id": cls.nvr_id,
            "relay_ip": cls.relay_ip or "",
            "is_active": cls.is_active,
            "has_roi": bool(cls.roi and (cls.roi.green_zone or cls.roi.red_zone))
        }
    }

@router.post("")
@router.post("/")
async def create_classroom(
    data: ClassroomCreateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Thêm một lớp học mới kèm sĩ số và camera (Chỉ Quản Trị Viên)."""
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên lớp học không được để trống")

    code = data.code.strip().upper() if data.code else _generate_code(name)
    existing = db.query(Classroom).filter((Classroom.code == code) | (Classroom.name == name)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Lớp '{name}' (Mã: {code}) đã tồn tại trong hệ thống!")

    rtsp_url = (data.rtsp_url or "").strip()
    if not rtsp_url and data.channel_number:
        rtsp_url = f"rtsp://localhost:8554/stream{data.channel_number}"

    cls = Classroom(
        code=code,
        name=name,
        room_number=(data.room_number or "").strip(),
        standard_count=data.standard_count,
        rtsp_url=rtsp_url,
        channel_number=data.channel_number,
        nvr_id=data.nvr_id,
        relay_ip=(data.relay_ip or "").strip(),
        is_active=data.is_active
    )
    db.add(cls)
    db.flush()

    # Khởi tạo vùng ROI mặc định
    roi = ROIPolygon(
        classroom_id=cls.id,
        red_zone_json="[]",
        green_zone_json="[]",
        image_width=1920,
        image_height=1080
    )
    db.add(roi)
    db.commit()
    db.refresh(cls)

    logger.info(f"Đã thêm lớp học mới: {cls.name} (Sĩ số: {cls.standard_count}, Kênh: {cls.channel_number})")
    return {
        "success": True,
        "message": f"Đã tạo thành công lớp {cls.name} với sĩ số {cls.standard_count}",
        "data": {"id": cls.id, "name": cls.name, "code": cls.code}
    }

@router.put("/{classroom_id}")
async def update_classroom(
    classroom_id: int,
    data: ClassroomUpdateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin lớp học, sĩ số hoặc camera gắn kèm (Chỉ Quản Trị Viên)."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    if data.name is not None:
        new_name = data.name.strip()
        if new_name and new_name != cls.name:
            dup = db.query(Classroom).filter(Classroom.name == new_name, Classroom.id != classroom_id).first()
            if dup:
                raise HTTPException(status_code=400, detail=f"Tên lớp '{new_name}' đã bị trùng!")
            cls.name = new_name
            if not cls.code or cls.code.startswith("LOP_"):
                cls.code = _generate_code(new_name)

    if data.room_number is not None:
        cls.room_number = data.room_number.strip()
    if data.standard_count is not None:
        cls.standard_count = data.standard_count
    if data.channel_number is not None:
        cls.channel_number = data.channel_number
        if data.channel_number > 0 and (not data.rtsp_url or not data.rtsp_url.strip()):
            cls.rtsp_url = f"rtsp://localhost:8554/stream{data.channel_number}"
    if data.rtsp_url is not None:
        cls.rtsp_url = data.rtsp_url.strip()
    if data.relay_ip is not None:
        cls.relay_ip = data.relay_ip.strip()
    if data.is_active is not None:
        cls.is_active = data.is_active

    db.commit()
    logger.info(f"Đã cập nhật lớp học ID {classroom_id} ({cls.name})")
    return {
        "success": True,
        "message": f"Cập nhật thông tin lớp {cls.name} thành công"
    }

@router.patch("/{classroom_id}/count")
async def quick_update_student_count(
    classroom_id: int,
    data: ClassroomQuickUpdateCount,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cập nhật nhanh sĩ số lớp học trực tiếp từ bảng dữ liệu (Chỉ Quản Trị Viên)."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    old_count = cls.standard_count
    cls.standard_count = data.standard_count
    db.commit()

    logger.info(f"Cập nhật nhanh sĩ số lớp {cls.name}: {old_count} -> {data.standard_count}")
    return {
        "success": True,
        "message": f"Đã cập nhật sĩ số lớp {cls.name} thành {data.standard_count} học sinh",
        "standard_count": data.standard_count
    }

@router.delete("/{classroom_id}")
async def delete_classroom(
    classroom_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xóa lớp học và dữ liệu ROI liên quan (Chỉ Quản Trị Viên)."""
    cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    db.query(ROIPolygon).filter(ROIPolygon.classroom_id == classroom_id).delete()
    cname = cls.name
    db.delete(cls)
    db.commit()

    logger.info(f"Đã xóa lớp học: {cname} (ID: {classroom_id})")
    return {
        "success": True,
        "message": f"Đã xóa thành công lớp {cname}"
    }

@router.post("/import-preview")
async def preview_import_file(
    file: UploadFile = File(...),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Đọc và tự động phân tích cột file CSV / Excel, trả về xem trước và gợi ý mapping."""
    filename = file.filename or "upload.csv"
    ext = filename.lower().split(".")[-1]
    if ext not in ["xlsx", "xls", "csv"]:
        raise HTTPException(status_code=400, detail="Hệ thống chỉ hỗ trợ tệp định dạng Excel (.xlsx, .xls) hoặc CSV (.csv)")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Tệp tin tải lên rỗng")

    try:
        if ext in ["xlsx", "xls"]:
            df = pd.read_excel(io.BytesIO(contents))
        else:
            # Hỗ trợ UTF-8 có BOM hoặc không BOM, phát hiện delimiter
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding="utf-8-sig")
            except Exception:
                df = pd.read_csv(io.BytesIO(contents), encoding="latin-1")
    except Exception as e:
        logger.error(f"Lỗi đọc file import: {e}")
        raise HTTPException(status_code=400, detail=f"Không thể đọc nội dung tệp: {str(e)}")

    # Loại bỏ các hàng hoàn toàn rỗng
    df = df.dropna(how="all")
    if df.empty:
        raise HTTPException(status_code=400, detail="Tệp tin không chứa bất kỳ dòng dữ liệu nào")

    # Lấy danh sách cột
    headers = [str(c).strip() for c in df.columns]

    # Thuật toán tự động nhận diện cột (Smart Mapping)
    detected_name_col = ""
    detected_count_col = ""
    detected_room_col = ""
    detected_channel_col = ""
    detected_rtsp_col = ""
    detected_code_col = ""

    for h in headers:
        hl = h.lower()
        if not detected_name_col and any(k in hl for k in ["tên lớp", "ten lop", "lớp", "lop", "class", "classroom"]):
            detected_name_col = h
        elif not detected_count_col and any(k in hl for k in ["sĩ số", "si so", "siso", "số lượng", "học sinh", "hoc sinh", "students", "count", "total"]):
            detected_count_col = h
        elif not detected_room_col and any(k in hl for k in ["phòng", "phong", "room"]):
            detected_room_col = h
        elif not detected_channel_col and any(k in hl for k in ["kênh", "kenh", "channel", "cam"]):
            detected_channel_col = h
        elif not detected_rtsp_col and any(k in hl for k in ["rtsp", "luồng", "luong", "stream", "url"]):
            detected_rtsp_col = h
        elif not detected_code_col and any(k in hl for k in ["mã", "ma", "code"]):
            detected_code_col = h

    # Nếu chưa tìm thấy cột tên lớp, lấy cột đầu tiên
    if not detected_name_col and headers:
        detected_name_col = headers[0]

    # Danh sách các lớp hiện tại trong cơ sở dữ liệu để đối chiếu
    existing_classes = {c.name.strip().upper(): c for c in db.query(Classroom).all()}

    # Chuẩn bị 100 dòng xem trước
    preview_rows = []
    for idx, row in df.head(100).iterrows():
        raw_name = str(row.get(detected_name_col, "")).strip() if detected_name_col else ""
        if not raw_name or raw_name.lower() == "nan":
            continue

        raw_count = row.get(detected_count_col, 40) if detected_count_col else 40
        try:
            val_count = int(float(raw_count)) if pd.notnull(raw_count) else 40
        except Exception:
            val_count = 40

        raw_room = str(row.get(detected_room_col, "")).strip() if detected_room_col else ""
        if raw_room.lower() == "nan": raw_room = ""

        raw_channel = row.get(detected_channel_col, None) if detected_channel_col else None
        val_channel = None
        if pd.notnull(raw_channel):
            try:
                # Trích xuất số nếu là "Kênh 1" hoặc "1"
                m = re.search(r"\d+", str(raw_channel))
                if m:
                    val_channel = int(m.group())
            except Exception:
                pass

        raw_rtsp = str(row.get(detected_rtsp_col, "")).strip() if detected_rtsp_col else ""
        if raw_rtsp.lower() == "nan": raw_rtsp = ""

        is_existing = raw_name.upper() in existing_classes

        preview_rows.append({
            "index": idx + 1,
            "name": raw_name,
            "standard_count": val_count,
            "room_number": raw_room,
            "channel_number": val_channel,
            "rtsp_url": raw_rtsp,
            "is_existing": is_existing,
            "action": "Cập nhật" if is_existing else "Thêm mới"
        })

    return {
        "success": True,
        "filename": filename,
        "total_rows": len(df),
        "headers": headers,
        "detected_mapping": {
            "name_col": detected_name_col,
            "count_col": detected_count_col,
            "room_col": detected_room_col,
            "channel_col": detected_channel_col,
            "rtsp_col": detected_rtsp_col,
            "code_col": detected_code_col
        },
        "preview_rows": preview_rows
    }

@router.post("/batch-import")
async def batch_import_classrooms(
    data: ClassroomBatchImportRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lưu danh sách lớp học sau khi người dùng đã xác nhận mapping cột và xem trước."""
    if not data.items:
        raise HTTPException(status_code=400, detail="Không có dữ liệu lớp học để import")

    existing_classes = {c.name.strip().upper(): c for c in db.query(Classroom).all()}
    existing_codes = {c.code.strip().upper(): c for c in db.query(Classroom).all()}

    created_count = 0
    updated_count = 0
    errors = []

    for item in data.items:
        clean_name = item.name.strip()
        if not clean_name:
            continue

        std_count = max(1, min(100, item.standard_count))
        room = (item.room_number or "").strip()
        ch = item.channel_number
        rtsp = (item.rtsp_url or "").strip()
        if not rtsp and ch:
            rtsp = f"rtsp://localhost:8554/stream{ch}"

        existing_c = existing_classes.get(clean_name.upper())

        if existing_c:
            if data.update_existing:
                existing_c.standard_count = std_count
                if room:
                    existing_c.room_number = room
                if ch:
                    existing_c.channel_number = ch
                if rtsp:
                    existing_c.rtsp_url = rtsp
                updated_count += 1
        else:
            code = (item.code or "").strip().upper() or _generate_code(clean_name)
            if code in existing_codes:
                code = f"{code}_{int(datetime.utcnow().timestamp()) % 1000}"

            new_c = Classroom(
                code=code,
                name=clean_name,
                room_number=room,
                standard_count=std_count,
                channel_number=ch,
                rtsp_url=rtsp,
                is_active=item.is_active
            )
            db.add(new_c)
            db.flush()

            # Tạo ROI đa giác mặc định
            roi = ROIPolygon(
                classroom_id=new_c.id,
                red_zone_json="[]",
                green_zone_json="[]",
                image_width=1920,
                image_height=1080
            )
            db.add(roi)

            existing_classes[clean_name.upper()] = new_c
            existing_codes[code] = new_c
            created_count += 1

    db.commit()
    logger.info(f"Import danh sách lớp học: Đã tạo {created_count} mới, cập nhật {updated_count} lớp")

    return {
        "success": True,
        "message": f"Import thành công: Đã thêm mới {created_count} lớp, cập nhật {updated_count} lớp.",
        "created_count": created_count,
        "updated_count": updated_count,
        "total_processed": len(data.items),
        "errors": errors
    }


