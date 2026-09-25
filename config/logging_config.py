import logging
import sys
from pathlib import Path

# Cấu hình UTF-8 cho console stdout/stderr trên Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "attendance_system.log"

class _RedactFilter(logging.Filter):
    """Che credential RTSP / password trong mọi log (chống lộ secret ra file log/console)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from backend.api.security import redact_sensitive_text

            if isinstance(record.msg, str):
                record.msg = redact_sensitive_text(record.msg)
            record.args = ()
        except Exception:
            pass
        return True


def setup_logger(name: str = "AttendanceSystem") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        redact_filter = _RedactFilter()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(redact_filter)
        logger.addHandler(console_handler)

        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(redact_filter)
        logger.addHandler(file_handler)

    return logger

logger = setup_logger()
