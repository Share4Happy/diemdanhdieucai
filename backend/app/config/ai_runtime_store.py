"""
Lưu / đọc cấu hình kết nối AI Service (STUDENT_DETECTION_API_URL và USE_PREDICT_API_ENGINE)
ra file JSON và đồng bộ .env.
Mô hình Service API độc lập: Chỉ lưu URL máy chủ AI và cờ kích hoạt API.
"""
import json
import re
from pathlib import Path
from typing import Optional

RUNTIME_FILE = "ai_runtime_config.json"


def _get_storage_path(settings) -> Path:
    target = getattr(settings, "STORAGE_DIR", settings.BASE_DIR / "storage") / RUNTIME_FILE
    if not target.exists():
        legacy = settings.BASE_DIR / "storage" / RUNTIME_FILE
        if legacy.exists():
            return legacy
    return target


def load_runtime_ai(settings) -> None:
    """Nạp cấu hình Service API từ runtime JSON (nếu có)."""
    path = _get_storage_path(settings)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    url = data.get("STUDENT_DETECTION_API_URL")
    if url and isinstance(url, str) and url.strip():
        settings.STUDENT_DETECTION_API_URL = url.strip()

    if "USE_PREDICT_API_ENGINE" in data:
        settings.USE_PREDICT_API_ENGINE = bool(data["USE_PREDICT_API_ENGINE"])

    if "ATTENDANCE_NUM_PASSES" in data:
        try:
            settings.ATTENDANCE_NUM_PASSES = int(data["ATTENDANCE_NUM_PASSES"])
        except (ValueError, TypeError):
            pass

    if "ATTENDANCE_PASS_DELAY_SECONDS" in data:
        try:
            settings.ATTENDANCE_PASS_DELAY_SECONDS = float(data["ATTENDANCE_PASS_DELAY_SECONDS"])
        except (ValueError, TypeError):
            pass

    if "ATTENDANCE_SCAN_MODE" in data:
        settings.ATTENDANCE_SCAN_MODE = str(data["ATTENDANCE_SCAN_MODE"])


def save_runtime_ai(settings, api_url: Optional[str] = None, params: Optional[dict] = None) -> None:
    """Lưu cấu hình Service API vào JSON và đồng bộ vào file .env nếu có."""
    if api_url is not None and str(api_url).strip():
        settings.STUDENT_DETECTION_API_URL = str(api_url).strip()

    if params and isinstance(params, dict):
        if "use_predict_api_engine" in params and params["use_predict_api_engine"] is not None:
            settings.USE_PREDICT_API_ENGINE = bool(params["use_predict_api_engine"])

        if "num_passes" in params and params["num_passes"] is not None:
            try:
                settings.ATTENDANCE_NUM_PASSES = int(params["num_passes"])
            except (ValueError, TypeError):
                pass
        elif "ATTENDANCE_NUM_PASSES" in params and params["ATTENDANCE_NUM_PASSES"] is not None:
            try:
                settings.ATTENDANCE_NUM_PASSES = int(params["ATTENDANCE_NUM_PASSES"])
            except (ValueError, TypeError):
                pass

        if "delay_seconds" in params and params["delay_seconds"] is not None:
            try:
                settings.ATTENDANCE_PASS_DELAY_SECONDS = float(params["delay_seconds"])
            except (ValueError, TypeError):
                pass
        elif "ATTENDANCE_PASS_DELAY_SECONDS" in params and params["ATTENDANCE_PASS_DELAY_SECONDS"] is not None:
            try:
                settings.ATTENDANCE_PASS_DELAY_SECONDS = float(params["ATTENDANCE_PASS_DELAY_SECONDS"])
            except (ValueError, TypeError):
                pass

        if "scan_mode" in params and params["scan_mode"] is not None:
            settings.ATTENDANCE_SCAN_MODE = str(params["scan_mode"])
        elif "ATTENDANCE_SCAN_MODE" in params and params["ATTENDANCE_SCAN_MODE"] is not None:
            settings.ATTENDANCE_SCAN_MODE = str(params["ATTENDANCE_SCAN_MODE"])

    path = getattr(settings, "STORAGE_DIR", settings.BASE_DIR / "storage") / RUNTIME_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "STUDENT_DETECTION_API_URL": settings.STUDENT_DETECTION_API_URL,
        "USE_PREDICT_API_ENGINE": getattr(settings, "USE_PREDICT_API_ENGINE", True),
        "ATTENDANCE_NUM_PASSES": getattr(settings, "ATTENDANCE_NUM_PASSES", 10),
        "ATTENDANCE_PASS_DELAY_SECONDS": getattr(settings, "ATTENDANCE_PASS_DELAY_SECONDS", 10.0),
        "ATTENDANCE_SCAN_MODE": getattr(settings, "ATTENDANCE_SCAN_MODE", "round_robin")
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Đồng bộ vào .env (nếu file .env tồn tại)
    env_paths = [
        settings.BASE_DIR / ".env",
        settings.BASE_DIR.parent / ".env",
        Path(".env")
    ]
    for env_file in env_paths:
        if env_file.exists() and env_file.is_file():
            try:
                content = env_file.read_text(encoding="utf-8")
                for key, val in payload.items():
                    pattern = rf"^{key}=.*$"
                    new_line = f"{key}={val}"
                    if re.search(pattern, content, flags=re.MULTILINE):
                        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
                    else:
                        content = content.rstrip() + f"\n{new_line}\n"
                env_file.write_text(content, encoding="utf-8")
                break
            except Exception:
                pass
