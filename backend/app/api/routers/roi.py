"""
API Router: Quản Lý Cấu Hình Vùng ROI (Spatial ROI)
[TOÀN BỘ CẤU HÌNH ROI ĐÃ ĐƯỢC COMMENT LẠI THEO YÊU CẦU NGƯỜI DÙNG]
Hệ thống chuyển sang sử dụng thuần túy 100% Endpoint /api/predict (Depth-NMS).
Không áp dụng bất kỳ vùng Green Zone (bàn học) hay Red Zone (bục giảng) nào.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db_session import get_db
from backend.app.schemas.roi_schemas import ROISaveRequest, ROIApplyAllRequest
from backend.app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/roi", tags=["ROI (Đã Vô Hiệu Hóa)"], dependencies=[Depends(get_current_user)])

# =============================================================================
# [CẤU HÌNH ROI ĐÃ ĐƯỢC COMMENT LẠI TOÀN BỘ THEO YÊU CẦU NGƯỜI DÙNG]
# =============================================================================

@router.post("/apply-all")
async def apply_all_roi(data: ROIApplyAllRequest, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    """
    [COMMENTED OUT] Áp dụng cấu hình tọa độ ROI cho danh sách lớp học.
    Đã vô hiệu hóa: Hệ thống hiện tại chỉ dùng thuần túy API /api/predict không qua ROI.
    """
    # target_ids = data.target_classroom_ids
    # if target_ids:
    #     classrooms = db.query(Classroom).filter(Classroom.id.in_(target_ids)).all()
    # else:
    #     classrooms = db.query(Classroom).all()
    # for cls in classrooms:
    #     roi = cls.roi or ROIPolygon(classroom_id=cls.id)
    #     roi.red_zone = data.red_zone or []
    #     roi.green_zone = data.green_zone or []
    # db.commit()
    return {
        "success": True,
        "message": "Cấu hình ROI đã được vô hiệu hóa theo yêu cầu. Hệ thống chạy thuần túy 100% /api/predict.",
        "updated_count": 0,
        "green_zone_points": 0
    }

@router.get("/{classroom_id}")
async def get_classroom_roi(classroom_id: int, refresh: bool = False, db: Session = Depends(get_db)):
    """
    [COMMENTED OUT] Lấy tọa độ Red Zone & Green Zone của lớp học.
    Đã vô hiệu hóa: Luôn trả về danh sách rỗng để đảm bảo AI quét toàn phòng không bị ROI cắt xén.
    """
    # cls = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    # red_zone = cls.roi.red_zone if cls.roi else []
    # green_zone = cls.roi.green_zone if cls.roi else []
    return {
        "classroom_id": classroom_id,
        "name": f"Lớp {classroom_id}",
        "standard_count": 40,
        "red_zone": [],
        "green_zone": [],
        "roi_note": "Cấu hình ROI đã được comment lại theo yêu cầu. Hệ thống quét toàn ảnh bằng /api/predict."
    }

@router.post("/{classroom_id}")
async def save_classroom_roi(classroom_id: int, data: ROISaveRequest, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    """
    [COMMENTED OUT] Lưu tọa độ ROI cho một lớp học.
    Đã vô hiệu hóa: Không ghi đè và không áp dụng ROI vào quá trình nhận diện.
    """
    return {
        "success": True,
        "message": "Cấu hình ROI đã được vô hiệu hóa theo yêu cầu. Hệ thống chạy thuần túy /api/predict.",
        "present_count": None,
        "absent_count": None
    }
