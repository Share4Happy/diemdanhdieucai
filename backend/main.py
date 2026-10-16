"""
backend/main.py - Entrypoint tương thích ngược cho Docker và CLI.
Ủy quyền toàn bộ cho ứng dụng FastAPI chuẩn trong backend.app.main.
"""
from backend.app.main import app

__all__ = ["app"]
