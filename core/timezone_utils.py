import os
from datetime import datetime, date
from zoneinfo import ZoneInfo
from config.settings import settings

def get_app_timezone() -> ZoneInfo:
    """Trả về ZoneInfo cấu hình cho ứng dụng (mặc định Asia/Ho_Chi_Minh)."""
    tz_name = getattr(settings, "TIMEZONE", "Asia/Ho_Chi_Minh") or "Asia/Ho_Chi_Minh"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("Asia/Ho_Chi_Minh")

def get_now() -> datetime:
    """
    Trả về thời gian hiện tại chuẩn theo múi giờ ứng dụng (Việt Nam GMT+7).
    Độc lập hoàn toàn với múi giờ của máy chủ VPS nước ngoài.
    """
    return datetime.now(get_app_timezone())

def get_today() -> date:
    """Trả về ngày hiện tại theo giờ Việt Nam."""
    return get_now().date()

def get_today_str() -> str:
    """Trả về chuỗi ngày YYYY-MM-DD theo giờ Việt Nam."""
    return get_now().strftime("%Y-%m-%d")

def get_current_time_str() -> str:
    """Trả về chuỗi giờ HH:MM:SS theo giờ Việt Nam."""
    return get_now().strftime("%H:%M:%S")
