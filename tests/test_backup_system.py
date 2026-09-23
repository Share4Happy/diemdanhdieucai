import os
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from database.db_session import init_db
from database.models import User
from backend.api.deps import get_current_user, require_admin
from services.backup_service import backup_service
from config.settings import settings

admin_user = User(id=1, email="admin@truongdieucai.edu.vn", role="admin", is_active=True, full_name="Admin")
app.dependency_overrides[get_current_user] = lambda: admin_user
app.dependency_overrides[require_admin] = lambda: admin_user

client = TestClient(app)

def test_backup_service_create_list_delete():
    init_db()
    
    # 1. Tạo bản sao lưu
    res = backup_service.create_backup(note="Test unit backup", include_excel=False)
    assert res["success"] is True
    assert "data" in res
    backup_file = res["data"]["backup_name"]
    
    zip_path = settings.BACKUPS_DIR / backup_file
    assert zip_path.exists()
    
    # Kiểm tra nội dung bên trong file zip
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert "attendance.db" in names
        assert "metadata.json" in names
        
    # 2. Lấy danh sách bản sao lưu
    backups = backup_service.list_backups()
    assert len(backups) >= 1
    found = any(b["filename"] == backup_file for b in backups)
    assert found is True
    
    # 3. Xóa bản sao lưu vừa tạo
    del_res = backup_service.delete_backup(backup_file)
    assert del_res["success"] is True
    assert not zip_path.exists()

def test_backup_api_endpoints():
    init_db()
    
    # 1. API tạo backup
    res = client.post("/api/backup/create", json={"note": "API test backup", "include_excel": False})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    backup_name = data["data"]["backup_name"]
    
    # 2. API list backup
    list_res = client.get("/api/backup/list")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["success"] is True
    assert any(b["filename"] == backup_name for b in list_data["backups"])
    
    # 3. API download backup
    dl_res = client.get(f"/api/backup/download/{backup_name}")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/zip"
    
    # 4. API delete backup
    del_res = client.delete(f"/api/backup/{backup_name}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
