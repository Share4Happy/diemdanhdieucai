import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config.settings import settings
from config.logging_config import logger
from backend.api.deps import get_current_user, require_admin
from services.backup_service import backup_service

router = APIRouter(prefix="/backup", tags=["Backup & Restore"], dependencies=[Depends(get_current_user)])

class CreateBackupRequest(BaseModel):
    note: Optional[str] = "Sao lưu thủ công"
    include_excel: Optional[bool] = False

@router.get("/list")
async def list_backups():
    """Lấy danh sách các bản sao lưu hiện có trong hệ thống."""
    backups = backup_service.list_backups()
    return {"success": True, "backups": backups}

@router.post("/create")
async def create_backup(req: Optional[CreateBackupRequest] = None, _admin=Depends(require_admin)):
    """Tạo bản sao lưu mới ngay lập tức (Chỉ Quản trị viên)."""
    note = req.note if req else "Sao lưu thủ công"
    inc_excel = req.include_excel if req else False
    result = backup_service.create_backup(note=note, include_excel=inc_excel)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message", "Lỗi tạo bản sao lưu"))
    return result

@router.get("/download/{filename}")
async def download_backup(filename: str, _admin=Depends(require_admin)):
    """Tải file bản sao lưu về máy tính của quản trị viên."""
    clean_name = Path(filename).name
    file_path = settings.BACKUPS_DIR / clean_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file bản sao lưu.")
    return FileResponse(
        path=str(file_path),
        filename=clean_name,
        media_type="application/zip"
    )

@router.post("/restore/{filename}")
async def restore_backup(filename: str, _admin=Depends(require_admin)):
    """Phục hồi dữ liệu từ bản sao lưu đã có sẵn trên máy chủ (Chỉ Quản trị viên)."""
    result = backup_service.restore_backup(filename)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Lỗi phục hồi dữ liệu"))
    return result

@router.post("/upload-restore")
async def upload_and_restore(file: UploadFile = File(...), _admin=Depends(require_admin)):
    """Tải file .zip bản sao lưu từ máy tính lên và tiến hành phục hồi hệ thống."""
    clean_name = Path(file.filename).name
    if not clean_name.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file định dạng nén .zip bản sao lưu của hệ thống.")

    dest_path = settings.BACKUPS_DIR / f"uploaded_{clean_name}"
    try:
        content = await file.read()
        dest_path.write_bytes(content)
        result = backup_service.restore_backup(dest_path.name)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return {
            "success": True,
            "message": f"Tải lên và phục hồi thành công từ file {clean_name}!",
            "details": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi upload và restore file backup: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý file upload: {str(e)}")

@router.delete("/{filename}")
async def delete_backup(filename: str, _admin=Depends(require_admin)):
    """Xóa một bản sao lưu cũ (Chỉ Quản trị viên)."""
    result = backup_service.delete_backup(filename)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result
