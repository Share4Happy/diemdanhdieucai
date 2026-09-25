"""
Dịch vụ Sao lưu Google Drive (THPT Điều Cải - Hệ Thống Điểm Danh AI).

- Xác thực OAuth 2.0 kiểu "Desktop App" (đổi mã code lấy refresh_token, chỉ cần kết nối 1 lần).
- Upload / liệt kê / tải về / xóa các file backup .zip qua Google Drive REST API (scope drive.file).
- Token được lưu trong config/gdrive_token.json (KHÔNG nằm trong storage/ public).
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests

from config.settings import settings
from config.logging_config import logger
from core.timezone_utils import get_app_timezone

OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"


class GoogleDriveService:
    """Quản lý kết nối & thao tác file backup trên Google Drive."""

    def __init__(self):
        self.token_file = settings.BASE_DIR / "config" / "gdrive_token.json"
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Cấu hình & trạng thái
    # ------------------------------------------------------------------
    def is_configured(self) -> bool:
        return bool(settings.GOOGLE_DRIVE_CLIENT_ID and settings.GOOGLE_DRIVE_CLIENT_SECRET)

    def is_connected(self) -> bool:
        data = self._load_store()
        return bool(data.get("refresh_token"))

    def status(self) -> Dict[str, Any]:
        return {
            "success": True,
            "configured": self.is_configured(),
            "connected": self.is_connected(),
            "account_email": self._load_store().get("account_email", ""),
            "folder_id": settings.GOOGLE_DRIVE_FOLDER_ID or "",
            "remote_only": settings.GOOGLE_DRIVE_REMOTE_ONLY,
            "redirect_uri": settings.GOOGLE_DRIVE_REDIRECT_URI,
        }

    # ------------------------------------------------------------------
    # Vòng đời kết nối OAuth
    # ------------------------------------------------------------------
    def get_consent_url(self, state: str = "") -> str:
        """Tạo URL xác nhận Google. Người dùng mở, đồng ý, rồi dán mã code vào giao diện."""
        if not self.is_configured():
            raise ValueError("Chưa cấu hình GOOGLE_DRIVE_CLIENT_ID / GOOGLE_DRIVE_CLIENT_SECRET trong .env")

        params = {
            "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_DRIVE_REDIRECT_URI,
            "response_type": "code",
            "scope": DRIVE_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
        if state:
            params["state"] = state
        query = "&".join(f"{requests.utils.quote(k)}={requests.utils.quote(str(v))}" for k, v in params.items())
        return f"{OAUTH_AUTH_URL}?{query}"

    def exchange_code(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Đổi mã code lấy refresh_token + access_token rồi lưu thông tin tài khoản."""
        if not self.is_configured():
            return {"success": False, "message": "Chưa cấu hình Google Drive trong .env (client ID/Secret)."}
        if not code or not code.strip():
            return {"success": False, "message": "Mã kết nối trống."}

        clean_code = code.strip()
        # Hỗ trợ tự động trích xuất mã code nếu người dùng dán nguyên URL http://localhost/?code=...
        if "code=" in clean_code:
            import urllib.parse
            parsed = urllib.parse.urlparse(clean_code)
            params = urllib.parse.parse_qs(parsed.query or parsed.path)
            if "code" in params and params["code"]:
                clean_code = params["code"][0]

        redirect = redirect_uri or settings.GOOGLE_DRIVE_REDIRECT_URI
        payload = {
            "code": clean_code,
            "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
            "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
        }
        resp = None
        try:
            resp = requests.post(OAUTH_TOKEN_URL, data=payload, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Lỗi đổi mã code Google (không lưu token): {e}")
            detail = ""
            if resp is not None:
                try:
                    detail = resp.json().get("error_description") or resp.json().get("error")
                except Exception:
                    detail = ""
            return {"success": False, "message": f"Kết nối thất bại: {detail or str(e)}"}

        tokens = resp.json()
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            return {"success": False, "message": "Không nhận được refresh_token (không có prompt=consent/offline)."}

        expires_in = int(tokens.get("expires_in", 3600))
        store = {
            "refresh_token": refresh_token,
            "access_token": tokens.get("access_token", ""),
            "token_expires_at": time.time() + expires_in - 120,
            "account_email": "",
        }

        # Lấy email tài khoản để hiển thị
        try:
            h = {"Authorization": f"Bearer {store['access_token']}"}
            about = requests.get(f"{DRIVE_API_BASE}/about", headers=h, params={"fields": "user(emailAddress,displayName)"}, timeout=20)
            if about.status_code == 200:
                udata = about.json().get("user", {})
                store["account_email"] = udata.get("emailAddress", "")
        except Exception:
            pass

        self._save_store(store)
        logger.info("Đã kết nối Google Drive thành công.")
        return {"success": True, "account_email": store["account_email"], "message": "Đã kết nối Google Drive."}

    def disconnect(self) -> Dict[str, Any]:
        try:
            if self.token_file.exists():
                self.token_file.unlink()
            logger.info("Đã ngắt kết nối Google Drive.")
            return {"success": True, "message": "Đã ngắt kết nối Google Drive."}
        except Exception as e:
            return {"success": False, "message": f"Lỗi ngắt kết nối: {e}"}

    # ------------------------------------------------------------------
    # Token
    # ------------------------------------------------------------------
    def _load_store(self) -> Dict[str, Any]:
        try:
            if self.token_file.exists():
                return json.loads(self.token_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Lỗi đọc token Google Drive: {e}")
        return {}

    def _save_store(self, store: Dict[str, Any]) -> None:
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

    def _get_access_token(self) -> Optional[str]:
        """Trả access_token hợp lệ, tự động refresh nếu sắp hết hạn."""
        with self._lock:
            store = self._load_store()
            if not store.get("refresh_token"):
                return None
            access = store.get("access_token")
            expires = store.get("token_expires_at", 0)
            if access and expires and expires > time.time() + 60:
                return access

            payload = {
                "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
                "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
                "refresh_token": store["refresh_token"],
                "grant_type": "refresh_token",
            }
            try:
                resp = requests.post(OAUTH_TOKEN_URL, data=payload, timeout=30)
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Lỗi refresh token Google Drive: {e}")
                return None

            tokens = resp.json()
            new_access = tokens.get("access_token")
            if not new_access:
                logger.error("Refresh token Google Drive không còn hợp lệ.")
                return None
            store["access_token"] = new_access
            store["token_expires_at"] = time.time() + int(tokens.get("expires_in", 3600)) - 120
            self._save_store(store)
            return new_access

    def _folder_query(self) -> str:
        """Câu query Drive dựa trên folder đã cấu hình (mặc định ngầm là 'root')."""
        folder = (settings.GOOGLE_DRIVE_FOLDER_ID or "").strip()
        return f"'{folder}' in parents" if folder else "'root' in parents"

    # ------------------------------------------------------------------
    # Thao tác file backup
    # ------------------------------------------------------------------
    def upload_file(self, local_path: Path) -> Dict[str, Any]:
        """Upload file .zip lên Google Drive (folder cấu hình hoặc My Drive)."""
        access_token = self._get_access_token()
        if not access_token:
            return {"success": False, "error": "Chưa kết nối Google Drive hoặc token đã hết hạn."}
        if not local_path.exists():
            return {"success": False, "error": f"File {local_path.name} không tồn tại."}

        parent = (settings.GOOGLE_DRIVE_FOLDER_ID or "").strip()
        metadata = {"name": local_path.name}
        if parent:
            metadata["parents"] = [parent]

        try:
            with local_path.open("rb") as fh:
                files = [
                    ("metadata", (None, json.dumps(metadata), "application/json")),
                    ("file", (local_path.name, fh, "application/zip")),
                ]
                headers = {"Authorization": f"Bearer {access_token}"}
                url = f"{DRIVE_UPLOAD_BASE}/files?uploadType=multipart&fields=id,name,webViewLink,size"
                resp = requests.post(url, headers=headers, files=files, timeout=120)
            if resp.status_code not in (200, 201):
                detail = resp.json().get("error", {}).get("message", resp.text[:200])
                return {"success": False, "error": f"Lỗi upload ({resp.status_code}): {detail}"}
            body = resp.json()
            return {"success": True, "file_id": body.get("id"), "web_view_link": body.get("webViewLink", "")}
        except Exception as e:
            logger.error(f"Lỗi upload Google Drive {local_path.name}: {e}")
            return {"success": False, "error": f"Lỗi mạng khi upload: {e}"}

    def list_files(self) -> List[Dict[str, Any]]:
        """Lấy danh sách file .zip backup trong folder đã cấu hình."""
        access_token = self._get_access_token()
        if not access_token:
            return []

        headers = {"Authorization": f"Bearer {access_token}"}
        tz = get_app_timezone()
        results = []
        page_token = None
        try:
            while True:
                query = f"{self._folder_query()} and trashed=false"
                params = {
                    "q": query,
                    "fields": "files(id,name,size,createdTime,webViewLink),nextPageToken",
                    "pageSize": 200,
                    "orderBy": "createdTime desc",
                }
                if page_token:
                    params["pageToken"] = page_token
                resp = requests.get(f"{DRIVE_API_BASE}/files", headers=headers, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.warning(f"Lỗi liệt kê Google Drive ({resp.status_code})")
                    break
                body = resp.json()
                for f in body.get("files", []):
                    created_dt = None
                    try:
                        created_dt = datetime.fromisoformat(f.get("createdTime", "").replace("Z", "+00:00"))
                        created_dt = created_dt.astimezone(tz)
                        created_str = created_dt.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        created_str = f.get("createdTime", "")
                    size_bytes = int(f.get("size", 0) or 0)
                    results.append({
                        "filename": f.get("name", ""),
                        "file_id": f.get("id", ""),
                        "size_bytes": size_bytes,
                        "size_mb": round(size_bytes / (1024 * 1024), 2),
                        "created_at": created_str,
                        "created_timestamp": created_dt.timestamp() if created_dt else 0,
                        "web_view_link": f.get("webViewLink", ""),
                        "source": "gdrive",
                        "drive_file_id": f.get("id", ""),
                        "note": "Bản sao lưu Google Drive",
                        "backup_type": "FULL",
                        "total_sessions": "--",
                        "total_details": "--",
                    })
                page_token = body.get("nextPageToken")
                if not page_token:
                    break
            results.sort(key=lambda x: x.get("created_timestamp", 0), reverse=True)
        except Exception as e:
            logger.error(f"Lỗi liệt kê file Google Drive: {e}")
        return results

    def find_by_name(self, filename: str) -> Optional[Dict[str, Any]]:
        """Tìm file backup theo tên trên Drive (trong folder đã cấu hình)."""
        for f in self.list_files():
            if f.get("filename") == filename:
                return f
        return None

    def download_file(self, file_id: str, dest_path: Path) -> bool:
        """Tải file từ Drive về đường dẫn local."""
        access_token = self._get_access_token()
        if not access_token:
            return False
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"{DRIVE_API_BASE}/files/{file_id}?alt=media"
            with requests.get(url, headers=headers, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with dest_path.open("wb") as fh:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            fh.write(chunk)
            return True
        except Exception as e:
            logger.error(f"Lỗi tải file Google Drive {file_id}: {e}")
            return False

    def delete_file(self, file_id: str) -> bool:
        access_token = self._get_access_token()
        if not access_token:
            return False
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = requests.delete(f"{DRIVE_API_BASE}/files/{file_id}", headers=headers, timeout=30)
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Lỗi xóa file Google Drive {file_id}: {e}")
            return False


gdrive_service = GoogleDriveService()