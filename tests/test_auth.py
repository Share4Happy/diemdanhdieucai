import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from backend.main import app
from database.db_session import init_db, SessionLocal
from database.models import User
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    yield

def test_password_hashing():
    raw_pwd = "matkhau_bi_mat_2026"
    hashed = get_password_hash(raw_pwd)
    assert hashed.startswith("pbkdf2_sha256$100000$")
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("sai_mat_khau", hashed) is False
    assert verify_password("", hashed) is False

def test_jwt_token_creation_and_decoding():
    token = create_access_token({"sub": "admin", "role": "admin"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"

    # Token hết hạn
    expired_token = create_access_token({"sub": "test"}, expires_delta=timedelta(seconds=-10))
    assert decode_access_token(expired_token) is None

def test_login_admin_success():
    res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"

def test_login_teacher_success():
    res = client.post("/api/auth/login", json={
        "username": "giaovien",
        "password": "giaovien123"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["username"] == "giaovien"
    assert data["user"]["role"] == "teacher"

def test_login_wrong_credentials():
    res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert res.status_code == 401
    assert "Tên đăng nhập hoặc mật khẩu không chính xác" in res.json()["detail"]

    res2 = client.post("/api/auth/login", json={
        "username": "khongtontai",
        "password": "admin123"
    })
    assert res2.status_code == 401

def test_oauth2_token_form_endpoint():
    res = client.post("/api/auth/token", data={
        "username": "admin",
        "password": "admin123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_me_endpoint():
    # 1. Không gửi token
    res_no_token = client.get("/api/auth/me")
    assert res_no_token.status_code == 401

    # 2. Đăng nhập lấy token
    login_res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]

    # 3. Gửi token hợp lệ
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"

def test_change_password_and_restore():
    # Login lấy token admin
    login_res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]

    # Đổi mật khẩu sang admin456
    change_res = client.post("/api/auth/change-password", headers={"Authorization": f"Bearer {token}"}, json={
        "old_password": "admin123",
        "new_password": "admin456"
    })
    assert change_res.status_code == 200
    assert change_res.json()["success"] is True

    # Thử login lại bằng pass cũ -> 401
    old_login = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert old_login.status_code == 401

    # Login bằng pass mới -> 200
    new_login = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin456"
    })
    assert new_login.status_code == 200
    new_token = new_login.json()["access_token"]

    # Trả lại pass cũ admin123 để không ảnh hưởng hệ thống
    restore_res = client.post("/api/auth/change-password", headers={"Authorization": f"Bearer {new_token}"}, json={
        "old_password": "admin456",
        "new_password": "admin123"
    })
    assert restore_res.status_code == 200

def test_admin_user_management():
    # Login admin
    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Login giaovien (teacher)
    teacher_login = client.post("/api/auth/login", json={"username": "giaovien", "password": "giaovien123"})
    teacher_token = teacher_login.json()["access_token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    # 1. Teacher gọi API Admin -> Phải bị 403 Forbidden
    teacher_forbidden = client.get("/api/auth/users", headers=teacher_headers)
    assert teacher_forbidden.status_code == 403

    # 2. Admin gọi danh sách users -> 200
    users_res = client.get("/api/auth/users", headers=admin_headers)
    assert users_res.status_code == 200
    users_list = users_res.json()
    assert len(users_list) >= 2

    # 3. Admin tạo user mới
    new_user_res = client.post("/api/auth/users", headers=admin_headers, json={
        "username": "giamthi01",
        "password": "giamthi123",
        "full_name": "Nguyễn Văn Giám Thị",
        "role": "supervisor",
        "email": "giamthi01@truongdieucai.edu.vn"
    })
    assert new_user_res.status_code == 200
    created_user = new_user_res.json()
    created_id = created_user["id"]
    assert created_user["username"] == "giamthi01"
    assert created_user["role"] == "supervisor"

    # User mới đăng nhập thử
    giamthi_login = client.post("/api/auth/login", json={
        "username": "giamthi01",
        "password": "giamthi123"
    })
    assert giamthi_login.status_code == 200

    # 4. Admin cập nhật user
    update_res = client.put(f"/api/auth/users/{created_id}", headers=admin_headers, json={
        "full_name": "Nguyễn Văn Giám Thị (Đã đổi tên)",
        "role": "teacher"
    })
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Nguyễn Văn Giám Thị (Đã đổi tên)"
    assert update_res.json()["role"] == "teacher"

    # 5. Admin xóa user vừa tạo
    del_res = client.delete(f"/api/auth/users/{created_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 6. Admin không thể tự xóa chính mình
    admin_id = admin_login.json()["user"]["id"]
    self_del = client.delete(f"/api/auth/users/{admin_id}", headers=admin_headers)
    assert self_del.status_code == 400
