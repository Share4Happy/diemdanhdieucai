"""Luu/doc runtime config Zalo ra file JSON de giu cau hinh qua moi lan khoi dong server."""
import json
from pathlib import Path

RUNTIME_FILE = "zalo_runtime_config.json"

FIELDS = (
    "ENABLE_ZALO_NOTIFICATION",
    "ZALO_NOTIFICATION_TYPE",
    "ZALO_WEBHOOK_URL",
    "ZALO_OA_ACCESS_TOKEN",
    "ZALO_RECIPIENT_USER_ID",
    "ZALO_BOT_API_BASE_URL",
    "ZALO_BOT_ID",
    "ZALO_BOT_API_KEY",
    "ZALO_RECIPIENT_PHONES",
    "ZALO_RECIPIENTS_JSON",
)


def load_runtime_zalo(settings) -> None:
    """Ghi de cau hinh Zalo trong settings bang gia tri da luu runtime (neu co)."""
    path = settings.BASE_DIR / "storage" / RUNTIME_FILE
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    for field in FIELDS:
        value = data.get(field)
        if value in (None, ""):
            continue
        setattr(settings, field, value if not isinstance(value, str) else value.strip())


def save_runtime_zalo(settings) -> None:
    """Ghi cau hinh Zalo hien tai ra file JSON de khoi phuc sau khi khoi dong lai."""
    path = settings.BASE_DIR / "storage" / RUNTIME_FILE
    payload = {
        field: getattr(settings, field)
        for field in FIELDS
        if getattr(settings, field) not in (None, "")
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")