import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from config.settings import settings
from services.gdrive_service import GoogleDriveService
from services.backup_service import BackupService


@pytest.fixture
def mock_gdrive_env(tmp_path):
    """Giả lập môi trường cấu hình Google Drive và file token tạm thời."""
    service = GoogleDriveService()
    service.token_file = tmp_path / "gdrive_token.json"

    with patch.object(settings, "GOOGLE_DRIVE_CLIENT_ID", "test-client-id.apps.googleusercontent.com"), \
         patch.object(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "test-client-secret"), \
         patch.object(settings, "GOOGLE_DRIVE_FOLDER_ID", "test-folder-123"), \
         patch.object(settings, "GOOGLE_DRIVE_REDIRECT_URI", "http://localhost"), \
         patch.object(settings, "GOOGLE_DRIVE_REMOTE_ONLY", True):
        yield service


def test_gdrive_not_configured():
    service = GoogleDriveService()
    with patch.object(settings, "GOOGLE_DRIVE_CLIENT_ID", ""), \
         patch.object(settings, "GOOGLE_DRIVE_CLIENT_SECRET", ""):
        assert service.is_configured() is False
        assert service.is_connected() is False
        st = service.status()
        assert st["configured"] is False
        assert st["connected"] is False

        with pytest.raises(ValueError, match="Chưa cấu hình"):
            service.get_consent_url()


def test_gdrive_configured_and_consent_url(mock_gdrive_env):
    service = mock_gdrive_env
    assert service.is_configured() is True
    assert service.is_connected() is False

    url = service.get_consent_url(state="test-state")
    assert "https://accounts.google.com/o/oauth2/v2/auth?" in url
    assert "client_id=test-client-id.apps.googleusercontent.com" in url
    assert "scope=" in url
    assert "access_type=offline" in url
    assert "state=test-state" in url


def test_gdrive_exchange_code_success(mock_gdrive_env):
    service = mock_gdrive_env

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {
        "access_token": "mock-access-token-123",
        "refresh_token": "mock-refresh-token-456",
        "expires_in": 3600,
    }

    mock_about_resp = MagicMock()
    mock_about_resp.status_code = 200
    mock_about_resp.json.return_value = {
        "user": {"emailAddress": "admin@truongdieucai.edu.vn", "displayName": "Admin"}
    }

    with patch("requests.post", return_value=mock_token_resp), \
         patch("requests.get", return_value=mock_about_resp):
        # Kiểm tra dán nguyên URL http://localhost/?code=...
        result = service.exchange_code("http://localhost/?code=mock-code-789&scope=drive")
        assert result["success"] is True
        assert result["account_email"] == "admin@truongdieucai.edu.vn"
        assert service.is_connected() is True
        assert service.token_file.exists()

        st = service.status()
        assert st["connected"] is True
        assert st["account_email"] == "admin@truongdieucai.edu.vn"

    # Ngắt kết nối
    dis_res = service.disconnect()
    assert dis_res["success"] is True
    assert service.is_connected() is False
    assert not service.token_file.exists()


def test_gdrive_upload_and_list_files(mock_gdrive_env, tmp_path):
    service = mock_gdrive_env
    # Giả lập đã kết nối
    service.token_file.write_text(json.dumps({
        "access_token": "mock-access-token",
        "refresh_token": "mock-refresh-token",
        "token_expires_at": time.time() + 3600,
        "account_email": "admin@truongdieucai.edu.vn"
    }))

    # Tạo file test zip
    test_zip = tmp_path / "backup_test.zip"
    test_zip.write_bytes(b"dummy zip content")

    mock_upload_resp = MagicMock()
    mock_upload_resp.status_code = 200
    mock_upload_resp.json.return_value = {
        "id": "drive-file-id-999",
        "name": "backup_test.zip",
        "webViewLink": "https://drive.google.com/file/d/drive-file-id-999/view"
    }

    with patch("requests.post", return_value=mock_upload_resp):
        up_res = service.upload_file(test_zip)
        assert up_res["success"] is True
        assert up_res["file_id"] == "drive-file-id-999"

    # Kiểm tra list_files
    mock_list_resp = MagicMock()
    mock_list_resp.status_code = 200
    mock_list_resp.json.return_value = {
        "files": [
            {
                "id": "drive-file-id-999",
                "name": "backup_test.zip",
                "size": "1048576",
                "createdTime": "2026-09-25T00:00:00.000Z",
                "webViewLink": "https://drive.google.com/file/d/drive-file-id-999/view"
            }
        ]
    }

    with patch("requests.get", return_value=mock_list_resp):
        files = service.list_files()
        assert len(files) == 1
        assert files[0]["filename"] == "backup_test.zip"
        assert files[0]["source"] == "gdrive"
        assert files[0]["drive_file_id"] == "drive-file-id-999"

        # find_by_name
        found = service.find_by_name("backup_test.zip")
        assert found is not None
        assert found["file_id"] == "drive-file-id-999"


def test_gdrive_download_and_delete(mock_gdrive_env, tmp_path):
    service = mock_gdrive_env
    service.token_file.write_text(json.dumps({
        "access_token": "mock-access-token",
        "refresh_token": "mock-refresh-token",
        "token_expires_at": time.time() + 3600
    }))

    # Test download
    mock_dl_resp = MagicMock()
    mock_dl_resp.status_code = 200
    mock_dl_resp.__enter__.return_value = mock_dl_resp
    mock_dl_resp.iter_content.return_value = [b"chunk1", b"chunk2"]

    dest_file = tmp_path / "downloaded.zip"
    with patch("requests.get", return_value=mock_dl_resp):
        ok = service.download_file("drive-file-id-999", dest_file)
        assert ok is True
        assert dest_file.exists()
        assert dest_file.read_bytes() == b"chunk1chunk2"

    # Test delete
    mock_del_resp = MagicMock()
    mock_del_resp.status_code = 204
    with patch("requests.delete", return_value=mock_del_resp):
        ok = service.delete_file("drive-file-id-999")
        assert ok is True
