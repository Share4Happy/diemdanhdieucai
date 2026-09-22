import pytest
import shutil
from pathlib import Path
from config.settings import settings

@pytest.fixture(scope="session", autouse=True)
def preserve_live_database():
    db_file = settings.BASE_DIR / "database" / "attendance.db"
    backup_file = db_file.with_suffix(".pytest_bak")

    # Sao lưu CSDL hiện tại trước khi toàn bộ test suite chạy
    if db_file.exists():
        shutil.copy2(db_file, backup_file)

    yield

    # Khôi phục nguyên vẹn CSDL của người dùng sau khi test suite kết thúc
    if backup_file.exists():
        shutil.copy2(backup_file, db_file)
        try:
            backup_file.unlink()
        except Exception:
            pass
