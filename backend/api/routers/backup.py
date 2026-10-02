import html
import time
import jwt
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request
from fastapi.responses import FileResponse, HTMLResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel

from config.settings import settings
from config.logging_config import logger
from backend.api.deps import get_current_user, require_admin
from services.backup_service import backup_service
from services.gdrive_service import gdrive_service

router = APIRouter(prefix="/backup", tags=["Backup & Restore"])

class CreateBackupRequest(BaseModel):
    note: Optional[str] = "Sao lưu thủ công"
    include_excel: Optional[bool] = False

@router.get("/list")
async def list_backups(_user=Depends(get_current_user)):
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

def _render_oauth_popup_html(
    success: bool,
    title: str,
    message: str,
    account_email: str = "",
    error_detail: str = "",
) -> str:
    escaped_title = html.escape(title)
    escaped_msg = html.escape(message)
    escaped_email = html.escape(account_email)
    escaped_err = html.escape(error_detail)
    status_icon = (
        '<div class="icon-circle success"><i class="fa-solid fa-check"></i></div>'
        if success
        else '<div class="icon-circle error"><i class="fa-solid fa-xmark"></i></div>'
    )
    email_html = (
        f'<div class="email-badge"><i class="fa-brands fa-google"></i> {escaped_email}</div>'
        if account_email
        else ""
    )
    err_html = (
        f'<div class="error-box">{escaped_err}</div>'
        if error_detail
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escaped_title} - THPT Điều Cải</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            color: #1e293b;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .card {{
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
            max-width: 440px;
            width: 100%;
            padding: 32px 28px;
            text-align: center;
            border: 1px solid #e2e8f0;
            animation: scaleIn 0.3s ease-out;
        }}
        @keyframes scaleIn {{
            from {{ opacity: 0; transform: scale(0.95); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}
        .icon-circle {{
            width: 68px;
            height: 68px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 32px;
        }}
        .icon-circle.success {{
            background: #dcfce7;
            color: #16a34a;
            box-shadow: 0 0 0 8px #f0fdf4;
        }}
        .icon-circle.error {{
            background: #fee2e2;
            color: #dc2626;
            box-shadow: 0 0 0 8px #fef2f2;
        }}
        h2 {{
            font-size: 1.35rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 8px;
        }}
        p {{
            font-size: 0.95rem;
            color: #64748b;
            line-height: 1.5;
            margin-bottom: 16px;
        }}
        .email-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #f1f5f9;
            color: #0f172a;
            font-weight: 600;
            font-size: 0.92rem;
            padding: 8px 16px;
            border-radius: 9999px;
            margin-bottom: 20px;
            border: 1px solid #cbd5e1;
        }}
        .email-badge i {{
            color: #ea4335;
        }}
        .error-box {{
            background: #fef2f2;
            color: #991b1b;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 0.85rem;
            margin-bottom: 20px;
            text-align: left;
            word-break: break-word;
        }}
        .status-note {{
            font-size: 0.85rem;
            color: #94a3b8;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: 18px;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
            padding: 11px 18px;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
            text-decoration: none;
        }}
        .btn-secondary {{
            background: #f1f5f9;
            color: #475569;
            margin-top: 8px;
        }}
        .btn-secondary:hover {{
            background: #e2e8f0;
        }}
    </style>
</head>
<body>
    <div class="card">
        {status_icon}
        <h2>{escaped_title}</h2>
        <p>{escaped_msg}</p>
        {email_html}
        {err_html}
        <button type="button" class="btn btn-secondary" onclick="closePopup()">
            <i class="fa-solid fa-xmark"></i> Đóng Cửa Sổ
        </button>
        <div class="status-note" id="autoCloseNote">
            <i class="fa-solid fa-spinner fa-spin"></i> Tự động đồng bộ và đóng cửa sổ...
        </div>
    </div>
    <script>
        const messagePayload = {{
            type: 'gdrive_oauth_result',
            success: {str(success).lower()},
            account_email: '{escaped_email}',
            message: '{escaped_msg}'
        }};

        function closePopup() {{
            try {{
                window.close();
            }} catch (e) {{}}
        }}

        try {{
            if (window.opener && !window.opener.closed) {{
                window.opener.postMessage(messagePayload, '*');
                setTimeout(() => {{
                    closePopup();
                }}, 1300);
            }} else {{
                document.getElementById('autoCloseNote').innerHTML = '<i class="fa-solid fa-arrow-right"></i> Đang chuyển hướng về trang Báo Cáo...';
                setTimeout(() => {{
                    window.location.href = '/reports.html?tab=settings&gdrive_connected=1';
                }}, 1600);
            }}
        }} catch (err) {{
            console.error('Error posting message:', err);
        }}
    </script>
</body>
</html>"""

class GDriveConnectRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None

@router.get("/gdrive/status")
async def gdrive_status(_admin=Depends(require_admin)):
    """Trạng thái kết nối Google Drive."""
    return gdrive_service.status()

@router.get("/gdrive/auth-url")
async def gdrive_auth_url(
    request: Request,
    redirect_uri: Optional[str] = None,
    state: str = "",
    _admin=Depends(require_admin)
):
    """Tạo URL xác nhận Google Drive để admin kết nối 1 nhấn tiện lợi."""
    try:
        chosen_redirect = (redirect_uri or "").strip()
        if not chosen_redirect:
            base = str(request.base_url).rstrip("/")
            chosen_redirect = f"{base}/api/backup/gdrive/callback"

        payload = {
            "admin_id": _admin.id,
            "admin_email": _admin.email,
            "role": _admin.role,
            "purpose": "gdrive_oauth",
            "redirect_uri": chosen_redirect,
            "exp": int(time.time()) + 900,  # 15 phút
        }
        signed_state = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        consent_url = gdrive_service.get_consent_url(state=signed_state, redirect_uri=chosen_redirect)
        return {
            "success": True,
            "url": consent_url,
            "redirect_uri": chosen_redirect,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/gdrive/callback", response_class=HTMLResponse)
async def gdrive_callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None,
):
    """
    Điểm đón phản hồi (OAuth Callback) từ Google:
    - Tự động đổi code lấy refresh_token và email tài khoản Google Drive
    - Thông báo giao diện và gửi postMessage để cập nhật tab quản lý mà không cần copy/paste
    """
    if error:
        logger.info(f"Người dùng từ chối hoặc hủy cấp quyền Google: {error}")
        return HTMLResponse(
            _render_oauth_popup_html(
                success=False,
                title="Đã Hủy Kết Nối",
                message="Bạn đã hủy hoặc từ chối cấp quyền truy cập Google Drive. Bản sao lưu sẽ chỉ lưu tại máy chủ.",
                error_detail=f"Mã phản hồi từ Google: {error}",
            )
        )

    if not code:
        return HTMLResponse(
            _render_oauth_popup_html(
                success=False,
                title="Thiếu Mã Xác Thực",
                message="Không nhận được mã ủy quyền từ Google. Vui lòng bấm Kết Nối lại.",
            ),
            status_code=400,
        )

    # Giải mã và xác thực chữ ký state
    redirect_uri = None
    if state:
        try:
            payload = jwt.decode(
                state,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if payload.get("purpose") != "gdrive_oauth" or payload.get("role") != "admin":
                return HTMLResponse(
                    _render_oauth_popup_html(
                        success=False,
                        title="Xác Thực Không Hợp Lệ",
                        message="Yêu cầu kết nối không đúng quyền quản trị viên hoặc đã bị can thiệp.",
                    ),
                    status_code=403,
                )
            redirect_uri = payload.get("redirect_uri")
        except jwt.ExpiredSignatureError:
            return HTMLResponse(
                _render_oauth_popup_html(
                    success=False,
                    title="Phiên Kết Nối Đã Hết Hạn",
                    message="Phiên kết nối Google Drive đã quá 15 phút. Vui lòng quay lại trang quản trị và bấm Kết Nối lại.",
                ),
                status_code=400,
            )
        except Exception as e:
            logger.warning(f"Lỗi xác thực OAuth state: {e}")
            return HTMLResponse(
                _render_oauth_popup_html(
                    success=False,
                    title="Xác Thực Thất Bại",
                    message="Chữ ký xác thực phiên làm việc không đúng.",
                    error_detail=str(e),
                ),
                status_code=400,
            )

    # Đổi code lấy token và lưu
    result = gdrive_service.exchange_code(code=code, redirect_uri=redirect_uri)
    if not result.get("success"):
        return HTMLResponse(
            _render_oauth_popup_html(
                success=False,
                title="Kết Nối Google Drive Thất Bại",
                message=result.get("message", "Không thể hoàn tất xác thực với Google Drive."),
                error_detail=result.get("message", ""),
            ),
            status_code=400,
        )

    account_email = result.get("account_email", "")
    return HTMLResponse(
        _render_oauth_popup_html(
            success=True,
            title="Kết Nối Google Drive Thành Công!",
            message="Hệ thống đã liên kết thành công với tài khoản Google Drive của bạn. Các bản sao lưu tự động sẽ được đẩy lên Drive an toàn.",
            account_email=account_email,
        )
    )

@router.post("/gdrive/connect")
async def gdrive_connect(req: GDriveConnectRequest, _admin=Depends(require_admin)):
    """Đổi mã code lấy token Google Drive (hỗ trợ nhập mã thủ công dự phòng)."""
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
