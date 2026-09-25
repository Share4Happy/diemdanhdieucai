import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel

from config.settings import settings
from config.logging_config import logger
from backend.api.deps import get_current_user, require_admin
from services.backup_service import backup_service
from services.gdrive_service import gdrive_service

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

# ============================ GOOGLE DRIVE ============================

class GDriveConnectRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None

@router.get("/gdrive/status")
async def gdrive_status(_admin=Depends(require_admin)):
    """Trạng thái kết nối Google Drive."""
    return gdrive_service.status()

@router.get("/gdrive/auth-url")
async def gdrive_auth_url(state: str = "", _admin=Depends(require_admin)):
    """Tạo URL xác nhận Google Drive để admin mở & lấy mã code."""
    try:
        return {"success": True, "url": gdrive_service.get_consent_url(state=state)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/gdrive/connect")
async def gdrive_connect(req: GDriveConnectRequest, _admin=Depends(require_admin)):
    """Đổi mã code lấy token Google Drive (kết nối một lần)."""
    result = gdrive_service.exchange_code(req.code, req.redirect_uri)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Kết nối thất bại"))
    return result

@router.post("/gdrive/disconnect")
async def gdrive_disconnect(_admin=Depends(require_admin)):
    """Ngắt kết nối Google Drive (xoá token đã lưu)."""
    return gdrive_service.disconnect()

@router.get("/download/{filename}")
async def download_backup(filename: str, _admin=Depends(require_admin)):
    """Tải file bản sao lưu về máy tính của quản trị viên (local hoặc Google Drive)."""
    clean_name = Path(filename).name
    resolved = backup_service.resolve_backup_zip(clean_name)
    if not resolved.get("success"):
        raise HTTPException(status_code=404, detail=resolved.get("message", "Không tìm thấy bản sao lưu."))
    cleanup_task = None
    if resolved.get("cleanup"):
        cleanup_task = BackgroundTask(resolved["zip_path"].unlink, missing_ok=True)
    return FileResponse(
        path=str(resolved["zip_path"]),
        filename=clean_name,
        media_type="application/zip",
        background=cleanup_task,
    )

@router.post("/restore/{filename}")
async def restore_backup(filename: str, _admin=Depends(require_admin)):
    """Phục hồi dữ liệu từ bản sao lưu đã có (local hoặc Google Drive)."""
    clean_name = Path(filename).name
    resolved = backup_service.resolve_backup_zip(clean_name)
    if not resolved.get("success"):
        raise HTTPException(status_code=404, detail=resolved.get("message", "Không tìm thấy bản sao lưu."))
    try:
        result = backup_service.restore_backup(filename=clean_name, zip_path=resolved["zip_path"])
    finally:
        if resolved.get("cleanup"):
            try:
                resolved["zip_path"].unlink(missing_ok=True)
            except Exception:
                pass
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
