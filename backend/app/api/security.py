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

_BLOCKED_RANGES = (
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback (chống SSRF vào dịch vụ nội bộ máy chủ)
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud metadata (AWS/Azure/GCP metadata service)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
)

_ALLOWED_PRIVATE_RANGES = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


def _resolve_and_validate_ip(host: str) -> bool:
    """
    Phân giải DNS và kiểm tra IP:
    - Chặn đứng 100% loopback (127.x), link-local (169.254.x.x) chống SSRF cloud metadata.
    - Chỉ cho phép IP thuộc dải Private LAN (10.x, 172.16-31.x, 192.168.x).
    """
    if not host:
        return False
    import socket
    try:
        addr = ipaddress.ip_address(host)
        resolved_ips = [addr]
    except ValueError:
        try:
            resolved_info = socket.getaddrinfo(host, None)
            resolved_ips = [ipaddress.ip_address(item[4][0]) for item in resolved_info]
        except Exception:
            return False

    for ip in resolved_ips:
        if any(ip in net for net in _BLOCKED_RANGES):
            return False
        if not any(ip in net for net in _ALLOWED_PRIVATE_RANGES):
            return False
    return True


def validate_relay_ip(relay_ip: str) -> None:
    """relay_ip phải là địa chỉ IP nội bộ của relay phòng học; chặn IP public, loopback và 169.254."""
    if not relay_ip:
        return
    host = relay_ip.strip()
    if not _resolve_and_validate_ip(host):
        raise HTTPException(status_code=400, detail="Địa chỉ relay/đèn LED phải là IP thuộc mạng LAN hợp lệ (không cho phép loopback hoặc 169.254).")

# -- Stream source (test-connection / test-ir-by-url / nvr probe) --


def validate_stream_source(source_url: str) -> None:
    """
    Chống SSRF/đọc file tùy ý cho nguồn camera:
    - Bắt buộc giao thức chuẩn: rtsp://, rtsps:// (chỉ IP camera/NVR nội bộ, chặn loopback và 169.254.x.x).
    - Chặn hoàn toàn file://, 169.254.x.x và loopback 127.0.0.1.
    """
    url = (source_url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Thiếu nguồn camera.")

    from config.settings import settings

    lowered = url.lower()
    if lowered.startswith("file://"):
        raise HTTPException(status_code=400, detail="Không cho phép nguồn file://.")

    # Chặn nguồn file hoặc webcam "0", "1" ở endpoint nếu không ở chế độ DEV/DEBUG
    if url.isdigit():
        if not getattr(settings, "DEBUG", False):
            raise HTTPException(
                status_code=400,
                detail="Chỉ cho phép luồng RTSP/RTSPS mạng LAN. Đã khóa cổng Webcam vật lý trên môi trường chính thức vì lý do bảo mật."
            )
        return  # webcam index nội bộ trong môi trường dev/test

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme in ("rtsp", "rtsps"):
        host = parsed.hostname or ""
        if not _resolve_and_validate_ip(host):
            raise HTTPException(status_code=400, detail="Chỉ cho phép kết nối RTSP/Camera trong mạng LAN (chặn loopback và 169.254).")
        return

    # Path file cục bộ: chỉ cho phép trong môi trường DEBUG/kiểm thử và file nằm trong thư mục dự án
    allowed_ext = (".jpg", ".jpeg", ".png", ".bmp", ".mp4", ".avi", ".mkv", ".mov")
    if url.lower().endswith(allowed_ext):
        if not getattr(settings, "DEBUG", False):
            raise HTTPException(
                status_code=400,
                detail="Chỉ cho phép luồng RTSP/RTSPS mạng LAN. Không cho phép nạp file media cục bộ trên môi trường chính thức (chống LFI)."
            )
        import os
        from pathlib import Path
        p = Path(url)
        if p.is_absolute():
            base = settings.BASE_DIR.resolve()
            try:
                resolved = Path(url).resolve()
                is_in_base = str(resolved).startswith(str(base))
                is_in_tmp = str(resolved).startswith("/tmp") or "\\Temp" in str(resolved) or "pytest" in str(resolved)
                if not (is_in_base or is_in_tmp):
                    raise HTTPException(status_code=400, detail="Không cho phép đọc file ngoài thư mục dự án.")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=400, detail="Đường dẫn file không hợp lệ.")
        return

    raise HTTPException(status_code=400, detail="Nguồn camera không hợp lệ. Chỉ hỗ trợ luồng RTSP/RTSPS nội bộ (rtsp://, rtsps://).")


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