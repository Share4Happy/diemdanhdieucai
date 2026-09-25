"""Tiện ích bảo mật dùng chung cho các router: rate-limit, che URL stream, validate host/SSRF."""
import ipaddress
import re
import time
import urllib.parse
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException

from config.logging_config import logger

# ---------------------------------------------------------------- Rate limiting
# Bộ nhớ trong tiến trình (per-worker): đủ cho deployment đơn tiến trình hiện tại (uvicorn 1 worker).
# Nếu chuyển sang đa worker, thay bằng Redis.
_RATE_STATE: Dict[str, List[float]] = {}
_MAX_KEYS = 10000


def _rate_key(kind: str, key: str) -> str:
    return f"{kind}:{key}"


def check_rate_limit(kind: str, key: str, limit: int, window_seconds: int) -> None:
    """Đếm số lần gọi trong cửa sổ thời gian; vượt quá limit thì trả 429."""
    now = time.time()
    rk = _rate_key(kind, key)
    bucket = [t for t in _RATE_STATE.get(rk, []) if now - t < window_seconds]
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="Quá nhiều yêu cầu trong thời gian ngắn. Vui lòng thử lại sau.")
    bucket.append(now)
    _RATE_STATE[rk] = bucket

    # Dọn dẹp ánh xạ cũ để không phình bộ nhớ
    if len(_RATE_STATE) > _MAX_KEYS:
        stale_kinds = ("login", "forgot", "action", "restore")
        for k in list(_RATE_STATE.keys()):
            if k.split(":", 1)[0] in stale_kinds:
                if all(now - t > 3600 * 2 for t in _RATE_STATE[k]):
                    del _RATE_STATE[k]


def client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------- URL masking


def mask_stream_url(url: str) -> str:
    """Che phần credential trong URL stream: rtsp://user:pass@host → rtsp://user:****@host."""
    if not url:
        return url
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.username is not None:
            hostname = parsed.hostname or ""
            port = f":{parsed.port}" if parsed.port else ""
            masked = urllib.parse.urlunsplit((
                parsed.scheme,
                f"{parsed.username}:***@{hostname}{port}",
                parsed.path,
                parsed.query,
                parsed.fragment,
            ))
            return masked
    except Exception:
        pass
    return url


def mask_secret_in_text(text: str, secret: str) -> str:
    """Mask một secret trong chuỗi log (không in ra ngoài nếu secret rỗng)."""
    if not text or not secret:
        return text
    try:
        return text.replace(secret, "***")
    except Exception:
        return text


# ---------------------------------------------------------------- Host/SSRF validation

_LOCAL_RANGES = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def _host_is_private(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False  # hostname không phải IP -> không coi là nội bộ (chống DNS-rebinding/SSRF)
    return any(addr in net for net in _LOCAL_RANGES)


def validate_relay_ip(relay_ip: str) -> None:
    """relay_ip phải là địa chỉ IP nội bộ/loopback của relay phòng học; chặn IP public và hostname."""
    if not relay_ip:
        return
    host = relay_ip.strip()
    if not _host_is_private(host):
        raise HTTPException(status_code=400, detail="Địa chỉ relay/đèn LED phải là IP thuộc mạng nội bộ.")

# -- Stream source (test-connection / test-ir-by-url / nvr probe) --


def validate_stream_source(source_url: str) -> None:
    """
    Chống SSRF/đọc file tùy ý cho nguồn camera:
    - Cho phép: rtsp://, rtmp://, http(s):// (chỉ IP nội bộ vì camera nằm trong LAN), 
      số nguyên (webcam), hoặc đường dẫn file media bên trong thư mục dự án (dataset/captures).
    - Chặn: file:// và đường dẫn tuyệt đối ngoài thư mục dự án.
    """
    url = (source_url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Thiếu nguồn camera.")

    lowered = url.lower()
    if lowered.startswith("file://"):
        raise HTTPException(status_code=400, detail="Không cho phép nguồn file://.")

    if url.isdigit():
        return  # webcam index

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme in ("rtsp", "rtmp", "rtspu"):
        host = parsed.hostname or ""
        if not _host_is_private(host):
            raise HTTPException(status_code=400, detail="Chỉ cho phép kết nối tới camera trong mạng nội bộ.")
        return
    if parsed.scheme in ("http", "https"):
        host = parsed.hostname or ""
        if not _host_is_private(host):
            raise HTTPException(status_code=400, detail="Chỉ cho phép kết nối web/HTTP tới thiết bị trong mạng nội bộ.")
        return

    # Path file cục bộ: cho phép đuôi media và phải nằm trong project
    allowed_ext = (".jpg", ".jpeg", ".png", ".bmp", ".mp4", ".avi", ".mkv", ".mov", ".rmvb")
    if url.lower().endswith(allowed_ext):
        from config.settings import settings
        import os
        from pathlib import Path
        p = Path(url)
        if p.is_absolute():
            base = settings.BASE_DIR.resolve()
            try:
                resolved = Path(url).resolve()
                if not str(resolved).startswith(str(base)):
                    raise HTTPException(status_code=400, detail="Không cho phép đọc file ngoài thư mục dự án.")
            except Exception:
                pass
        return

    raise HTTPException(status_code=400, detail="Nguồn camera không hợp lệ (chỉ hỗ trợ RTSP/RTMP/HTTP nội bộ, webcam hoặc file media trong dự án).")


def validate_external_http_url(url: str, allowed_hosts: List[str]) -> bool:
    """Kiểm tra URL HTTP ngoài có host nằm trong danh sách được phép (chống SSRF + gửi tùy ý)."""
    if not url:
        return True
    try:
        parsed = urllib.parse.urlsplit(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if not _host_is_private(host):
        pass  # cho phép host public nhưng phải trong danh sách allowlist
    return host in {h.strip().lower() for h in allowed_hosts if h}


# rtsp://user:pass@host → rtsp://user:***@host
_RTSP_CRED_RE = re.compile(r"(rtsp://|rtmp://)([^/\s:]+):([^@/\s]+)@", re.IGNORECASE)
# password=..., secret=..., token=... → giá trị bị che
_PASS_ATTR_RE = re.compile(r"(password|passwd|pwd|secret|api[_-]?key|token)(\s*[=:]\s*)(\S+)", re.IGNORECASE)


def redact_sensitive_text(text: str) -> str:
    """Che credential RTSP và giá trị password/secret/token trong chuỗi log."""
    if not text:
        return text
    out = text
    out = _RTSP_CRED_RE.sub("\\1\\2:***@", out)
    out = _PASS_ATTR_RE.sub("\\1\\2***", out)
    return out


def log_info_redacted(msg: str, sensitive: str = "") -> None:
    logger.info(mask_secret_in_text(redact_sensitive_text(msg), sensitive))