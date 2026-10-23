import os
import cv2
import time
import socket
import threading
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

from config.settings import settings
from config.logging_config import logger
from backend.app.core.timezone_utils import get_today_str

def has_vertical_smear_artifacts(small: np.ndarray) -> bool:
    """
    Phát hiện lỗi vỡ luồng video / rớt gói tin H.264/H.265 (Vertical Smear / Streak Artifacting):
    Khi mất gói slice macroblock hoặc decoder quá tải, FFmpeg error concealment
    sẽ lặp lại dòng pixel cuối cùng xuống dưới đáy khung hình, tạo thành các vệt sọc dọc kéo dài.
    
    Đặc điểm toán học nhận diện:
    1. Đạo hàm dọc dy = mean(|diff(gray, axis=0)|) giảm sút nghiêm trọng (thường < 3.5, trong khi ảnh sạch ~20-25).
    2. Tỷ lệ dy / dx cực nhỏ (< 0.35) do gradient ngang dx vẫn còn nhưng dọc dy triệt tiêu.
    3. Tỷ lệ pixel liên tiếp theo cột có độ lệch diff < 1.0 vượt ngưỡng (> 55% pixel hàng dọc bị nhân bản lặp lại).
    """
    if small is None or small.shape[0] < 40 or small.shape[1] < 40:
        return False
    try:
        h = small.shape[0]
        # Kiểm tra nửa dưới khung hình (nơi artifact vệt sọc kéo xuống đáy)
        bottom = small[int(h * 0.5):, :]
        gray = cv2.cvtColor(bottom, cv2.COLOR_BGR2GRAY).astype(float)
        
        dy = float(np.abs(np.diff(gray, axis=0)).mean())
        dx = float(np.abs(np.diff(gray, axis=1)).mean())
        ratio = dy / (dx + 1e-5)
        
        vert_diff = np.abs(np.diff(gray, axis=0))
        zero_diff_ratio = float((vert_diff < 1.0).mean())
        col_std = float(np.std(gray, axis=0).mean())

        # Nếu có dấu hiệu kéo vệt sọc lặp pixel dọc rõ rệt:
        if (dy < 3.5 and ratio < 0.35) or (zero_diff_ratio > 0.55) or (col_std < 2.0 and ratio < 0.25):
            return True
            
        # Kiểm tra thêm phân vùng 40% đáy (vùng nhạy cảm nhất)
        bottom_deep = small[int(h * 0.6):, :]
        gray_deep = cv2.cvtColor(bottom_deep, cv2.COLOR_BGR2GRAY).astype(float)
        dy_deep = float(np.abs(np.diff(gray_deep, axis=0)).mean())
        dx_deep = float(np.abs(np.diff(gray_deep, axis=1)).mean())
        ratio_deep = dy_deep / (dx_deep + 1e-5)
        vert_diff_deep = np.abs(np.diff(gray_deep, axis=0))
        zero_diff_deep = float((vert_diff_deep < 1.0).mean())
        
        if (dy_deep < 2.5 and ratio_deep < 0.28) or (zero_diff_deep > 0.60):
            return True

    except Exception:
        pass
    return False


def is_valid_frame(frame: Optional[np.ndarray]) -> bool:
    """
    Kiểm tra khung hình có hợp lệ và sạch hoàn toàn hay không:
    - Loại bỏ frame None, rỗng, hoặc quá nhỏ.
    - Loại bỏ frame xám un-synced (P-frame H.264/H.265 khi chưa nhận được I-frame / SPS / PPS, thường có canvas YUV=128).
    - Loại bỏ frame sọc xanh lá hoặc sọc caro hồng/trắng do lỗi decoder / rớt gói slice macroblock.
    - Loại bỏ frame vỡ luồng kéo vệt sọc dọc (Vertical smear artifacting) do mất gói tin hoặc lỗi giải mã.
    - Đảm bảo độ lệch chuẩn chi tiết (std >= 12.0) và độ nét biên (Laplacian variance >= 4.0).
    """
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return False
    h, w = frame.shape[:2]
    if h < 240 or w < 320:
        return False

    # Resize nhỏ (160x90) để tính toán thống kê siêu nhanh (~0.3ms)
    small = cv2.resize(frame, (160, 90))
    if float(small.std()) < 12.0:
        return False

    # Kiểm tra phương sai Laplacian (độ nét góc cạnh, tránh màn hình phẳng lì một màu xám/xanh/đen)
    try:
        gray_small = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        lap_var = float(cv2.Laplacian(gray_small, cv2.CV_64F).var())
        if lap_var < 4.0:
            return False
    except Exception:
        pass

    # Kiểm tra tỷ lệ màu xám YUV 128 (vùng đệm khởi tạo chưa có I-frame, BGR xấp xỉ [128, 128, 128])
    gray_mask = (np.abs(small[:, :, 0].astype(int) - 128) < 18) & \
                (np.abs(small[:, :, 1].astype(int) - 128) < 18) & \
                (np.abs(small[:, :, 2].astype(int) - 128) < 18)
    if float(gray_mask.mean()) > 0.25:
        return False

    # Kiểm tra màu xanh lá lỗi decoder YUV 0,0,0 (BGR ~ [0, 135, 0] hoặc vùng xanh lá chiếm ưu thế do tràn buffer)
    green_dominant = (small[:, :, 1] > 80) & \
                     (small[:, :, 0] < 70) & \
                     (small[:, :, 2] < 70) & \
                     ((small[:, :, 1].astype(int) - np.maximum(small[:, :, 0], small[:, :, 2])) > 30)
    if float(green_dominant.mean()) > 0.08:
        return False

    # Kiểm tra nhiễu caro hồng/tím do lỗi rớt gói slice macroblock
    pink_mask = (small[:, :, 2] > 160) & (small[:, :, 0] > 160) & (small[:, :, 1] < 140)
    if float(pink_mask.mean()) > 0.12:
        return False

    # Kiểm tra hiện tượng phân rã/vỡ luồng (vertical smear / packet loss / decoding error)
    if has_vertical_smear_artifacts(small):
        return False

    return True


class RTSPCameraClient:
    """
    Module quản lý kết nối Camera/DVR qua giao thức RTSP và chụp ảnh đồng loạt đa luồng.
    Tích hợp cơ chế kiểm tra socket nhanh (Fast TCP Probe) và Semaphore theo từng NVR để chống nghẽn thiết bị.
    """

    def __init__(self, timeout_seconds: int = 6):
        self.timeout_seconds = timeout_seconds
        self._nvr_semaphores: Dict[str, threading.Semaphore] = {}
        self._semaphore_lock = threading.Lock()
        self._max_concurrency_per_nvr = 3
        # Quản lý chính sách dự phòng luồng (Stream Failover Policy)
        self.auto_fallback_enabled: bool = True
        self.rtsp_timeout_threshold: float = 3.5

    def _get_nvr_semaphore(self, host: str) -> threading.Semaphore:
        """Lấy hoặc khởi tạo Semaphore giới hạn tải đồng thời riêng cho từng đầu ghi NVR."""
        with self._semaphore_lock:
            if host not in self._nvr_semaphores:
                self._nvr_semaphores[host] = threading.Semaphore(self._max_concurrency_per_nvr)
            return self._nvr_semaphores[host]

    @staticmethod
    def is_host_reachable(url: str, probe_timeout: float = 0.4) -> bool:
        """Kiểm tra nhanh kết nối TCP port RTSP trước khi mở ffmpeg stream để tránh timeout lâu."""
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or 554
            if not host:
                return False

            with socket.create_connection((host, port), timeout=probe_timeout):
                return True
        except Exception:
            return False

    _cached_webcams = None
    _cached_webcams_time = 0

    @classmethod
    def get_available_webcams(cls, refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Quét và liệt kê danh sách toàn bộ các Webcam vật lý và ảo đang kết nối trên máy tính.
        Trả về: ID thiết bị, tên thiết bị (Friendly Name), độ phân giải và ảnh thumbnail xem trước.
        """
        import base64
        import subprocess
        now = time.time()
        if not refresh and cls._cached_webcams is not None and (now - cls._cached_webcams_time < 60):
            return cls._cached_webcams

        # 1. Thử lấy tên thiết bị từ Windows Device Manager qua PowerShell chuẩn
        device_names = []
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-PnpDevice -Class Camera, Image -Status OK | Select-Object -ExpandProperty FriendlyName"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.5)
            if res.returncode == 0 and res.stdout:
                device_names = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
        except Exception as e:
            logger.debug(f"Lỗi lấy tên webcam qua PowerShell: {e}")

        # 2. Quét các cổng index 0, 1, 2, 3, 4
        webcams = []
        for idx in range(5):
            cap = None
            try:
                # Thử DirectShow trước trên Windows (~100ms), fallback sang MSMF và Default
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(idx, cv2.CAP_MSMF)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(idx)

                if cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
                    
                    # Đọc 2-3 frame khởi động để cảm biến camera mở đủ sáng, không bị frame đen
                    ret, frame = False, None
                    for _ in range(4):
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            break
                    cap.release()
                    cap = None

                    # Xác định chất lượng
                    if w >= 1920 or h >= 1080:
                        quality_label = "Full HD 1080p (Nét nhất)"
                    elif w >= 1280 or h >= 720:
                        quality_label = "HD 720p"
                    else:
                        quality_label = f"SD {w}x{h}"

                    # Đặt tên thân thiện
                    if idx < len(device_names):
                        dev_name = device_names[idx]
                    elif idx == 0 and device_names:
                        dev_name = device_names[0]
                    elif w >= 1920:
                        dev_name = f"Webcam Ngoài Full HD (Cổng {idx})"
                    else:
                        dev_name = f"Webcam Cổng {idx}"

                    if idx == 0 and "Mặc Định" not in dev_name:
                        display_name = f"Webcam {idx}: {dev_name} (Camera Mặc Định Máy)"
                    else:
                        display_name = f"Webcam {idx}: {dev_name}"

                    thumb_b64 = ""
                    if ret and frame is not None:
                        thumb = cv2.resize(frame, (200, 112))
                        _, buf = cv2.imencode('.jpg', thumb, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        thumb_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"

                    webcams.append({
                        "id": str(idx),
                        "index": idx,
                        "name": display_name,
                        "short_name": dev_name,
                        "resolution": f"{w}x{h}",
                        "quality_label": quality_label,
                        "width": w,
                        "height": h,
                        "thumbnail": thumb_b64,
                        "is_default": (idx == 0),
                        "is_active": True
                    })
            except Exception as e:
                logger.debug(f"Lỗi thăm dò webcam index {idx}: {e}")
            finally:
                if cap is not None and hasattr(cap, 'release'):
                    try:
                        cap.release()
                    except Exception:
                        pass

        cls._cached_webcams = webcams
        cls._cached_webcams_time = now
        logger.info(f"Đã phát hiện {len(webcams)} webcam khả dụng trên máy: {[w['name'] for w in webcams]}")
        return webcams

    def _read_rtsp_stream(self, url: str, timeout: float = 3.5) -> Optional[np.ndarray]:
        """
        Đọc 1 khung hình sạch từ luồng RTSP H.264/H.265 với cơ chế Adaptive I-frame Synchronization.
        - Ép buộc giao vận TCP chống rớt gói tin trên hạ tầng mạng LAN/Switch.
        - Mở rộng socket buffer lên 4MB để chống tràn bộ đệm khi quét đồng thời nhiều camera.
        - Vòng lặp đọc và thẩm định hình ảnh liên tục: loại bỏ các P-frame chưa đồng bộ hoặc frame vỡ luồng
          do lỗi decoder conceal macroblock, chỉ chấp nhận và trả về Keyframe (I-frame) hoàn toàn nguyên vẹn.
        """
        cap = None
        try:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;tcp|"
                "buffer_size;4194304|"
                "max_delay;500000|"
                "reorder_queue_size;500|"
                "stimeout;5000000|"
                "analyzeduration;1500000|probesize;1500000|"
                "protocol_whitelist;file,rtsp,rtp,tcp,udp,crypto,data"
            )
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not cap.isOpened():
                return None

            start_time = time.time()
            clean_frame = None
            consecutive_valid = 0

            while time.time() - start_time < timeout:
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.02)
                    continue

                if is_valid_frame(frame):
                    consecutive_valid += 1
                    clean_frame = frame
                    # Đợi tối thiểu 2 frame hợp lệ để đảm bảo decoder đã qua pha I-frame ổn định hoàn toàn
                    if consecutive_valid >= 2:
                        break
                else:
                    consecutive_valid = 0
                time.sleep(0.015)

            return clean_frame
        except Exception as e:
            logger.debug(f"Lỗi đọc luồng RTSP {url}: {e}")
            return None
        finally:
            if cap is not None and hasattr(cap, "release"):
                try:
                    cap.release()
                except Exception:
                    pass

    def _fetch_http_snapshot(self, rtsp_url: str) -> Optional[np.ndarray]:
        """
        Thử chụp ảnh tĩnh siêu tốc qua HTTP Snapshot (Dahua snapshot.cgi / Hikvision ISAPI) trước khi kết nối RTSP.
        Giảm thời gian lấy mẫu từ 2-3s xuống ~150-300ms. Fallback an toàn về RTSP nếu không hỗ trợ.
        """
        try:
            parsed = urlparse(rtsp_url)
            host = parsed.hostname
            if not host:
                return None

            # Bỏ qua nếu là chuỗi mock/demo/file
            if any(k in host.lower() for k in ["mock", "test", "demo", "example"]):
                return None

            username = parsed.username or "admin"
            password = parsed.password or ""

            # Trích xuất số kênh từ RTSP URL
            channel = 1
            if "channel=" in rtsp_url:
                try:
                    import re
                    m = re.search(r"channel=(\d+)", rtsp_url)
                    if m:
                        channel = int(m.group(1))
                except Exception:
                    pass
            elif "Channels/" in rtsp_url:
                try:
                    import re
                    m = re.search(r"Channels/(\d+)", rtsp_url)
                    if m:
                        raw_ch = int(m.group(1))
                        channel = raw_ch // 100 if raw_ch >= 100 else raw_ch
                except Exception:
                    pass

            import requests
            from requests.auth import HTTPDigestAuth, HTTPBasicAuth

            # Fast probe kiểm tra xem cổng HTTP 80/8000 của thiết bị có mở không trước khi thử snapshot
            if not self.is_host_reachable(f"http://{host}:80", probe_timeout=0.25):
                return None

            # Các endpoint snapshot phổ biến cho Dahua và Hikvision
            candidate_endpoints = [
                f"http://{host}:80/ISAPI/Streaming/channels/{channel}01/picture",
                f"http://{host}:80/cgi-bin/snapshot.cgi?channel={channel}",
                f"http://{host}:8000/ISAPI/Streaming/channels/{channel}01/picture"
            ]

            for endpoint in candidate_endpoints:
                for auth_factory in [HTTPDigestAuth, HTTPBasicAuth]:
                    try:
                        auth_obj = auth_factory(username, password) if username else None
                        resp = requests.get(endpoint, auth=auth_obj, timeout=1.8)
                        if resp.status_code == 200 and resp.content and len(resp.content) > 1024:
                            img_arr = np.frombuffer(resp.content, dtype=np.uint8)
                            frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                            if frame is not None and is_valid_frame(frame):
                                return frame
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"HTTP snapshot probe notice: {e}")
        return None

    def _fetch_frame_from_source(self, source_url: str) -> Tuple[bool, Optional[np.ndarray], str, str]:
        """
        Đọc một khung hình từ nguồn bất kỳ:
        - Số nguyên (0, 1): Webcam cắm máy tính
        - File video/ảnh cục bộ (.mp4, .avi, .jpg, .png)
        - RTSP stream (rtsp://...)
        - HTTP/MJPEG stream (http://...)
        Trả về: (thành_công, frame, loại_nguồn, thông_báo_lỗi)
        """
        source_str = str(source_url).strip()
        
        # 1. Kiểm tra nếu là Webcam cắm máy tính (0, 1, 2...)
        if source_str.isdigit():
            cam_idx = int(source_str)
            cap = None
            try:
                # Thử DirectShow trước trên Windows để mở nhanh, fallback MSMF và Default
                cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(cam_idx, cv2.CAP_MSMF)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(cam_idx)
                if cap.isOpened():
                    # Yêu cầu độ phân giải Full HD (1920x1080) để nhận diện rõ các góc xa lớp học
                    try:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                    except Exception:
                        pass
                    ret, frame = False, None
                    for _ in range(4):
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            break
                    cap.release()
                    cap = None
                    if ret and frame is not None:
                        return True, frame, "WEBCAM", ""
                return False, None, "WEBCAM", f"Không thể mở Webcam ID {cam_idx}"
            except Exception as e:
                return False, None, "WEBCAM", str(e)
            finally:
                if cap is not None and hasattr(cap, 'release'):
                    try:
                        cap.release()
                    except Exception:
                        pass

        # 2. Kiểm tra nếu là File video hoặc ảnh cục bộ
        local_path = Path(source_str)
        if not local_path.is_absolute():
            local_path = settings.BASE_DIR / source_str

        if local_path.exists() and local_path.is_file():
            ext = local_path.suffix.lower()
            if ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                frame = cv2.imread(str(local_path))
                if frame is not None:
                    return True, frame, "IMAGE_FILE", ""
                return False, None, "IMAGE_FILE", f"Không thể đọc file ảnh {local_path.name}"
            elif ext in [".mp4", ".avi", ".mkv", ".mov"]:
                cap = cv2.VideoCapture(str(local_path))
                if cap.isOpened():
                    try:
                        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

                        # Giả lập luồng camera thời gian thực (Virtual Live Stream):
                        # 1. Bỏ qua 50 frames đầu (khoảng 2s) để tránh nhiễu khởi động/khung hình đen
                        # 2. Tua khung hình theo thời gian thực (time.time()) để mỗi lần quét là một thời điểm khác nhau
                        if total_frames > 75:
                            usable_frames = max(1, total_frames - 75)
                            current_sec = int(time.time())
                            frame_offset = int(current_sec * (fps / 2)) % usable_frames
                            target_frame = 50 + frame_offset
                            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

                        # 3. Lựa chọn khung hình sắc nét nhất (Anti-Motion-Blur & Best Sharpness)
                        # Đọc tối đa 3 frame liên tiếp và chọn frame có độ nét (Laplacian variance) cao nhất
                        best_frame = None
                        max_sharpness = -1.0
                        for _ in range(3):
                            ret_f, f = cap.read()
                            if ret_f and f is not None:
                                try:
                                    gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
                                    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                                except Exception:
                                    sharpness = 1.0
                                if sharpness > max_sharpness:
                                    max_sharpness = sharpness
                                    best_frame = f

                        # Fallback nếu không bắt được qua seek
                        if best_frame is None:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret_f, best_frame = cap.read()

                        if best_frame is not None:
                            return True, best_frame, "VIDEO_FILE", ""
                    except Exception as e:
                        logger.warning(f"Lỗi khi trích xuất khung hình tối ưu từ video {local_path.name}: {e}")
                    finally:
                        cap.release()
                return False, None, "VIDEO_FILE", f"Không thể đọc khung hình từ video {local_path.name}"

        # 3. Kiểm tra nếu là luồng RTSP
        if source_str.startswith("rtsp://"):
            # 3.1. Thử HTTP Snapshot siêu tốc trước (nếu NVR hỗ trợ ISAPI / snapshot.cgi)
            try:
                snap_frame = self._fetch_http_snapshot(source_str)
                if snap_frame is not None:
                    return True, snap_frame, "HTTP_SNAPSHOT", ""
            except Exception:
                pass

            # 3.2. Fallback sang bắt tay RTSP truyền thống
            candidate_urls = [source_str]
            parsed = urlparse(source_str)
            host = parsed.hostname or ""
            
            if host.startswith("192.168.1.2") or host.startswith("192.168.10.2"):
                try:
                    last_octet = int(host.split(".")[-1])
                    if 201 <= last_octet <= 232:
                        ch_num = last_octet - 200
                        from urllib.parse import quote
                        dvr_pass = quote(settings.DVR_PASSWORD or "")
                        dvr_user = quote(settings.DVR_USER or "admin")
                        dvr_host = settings.DVR_HOST or "192.168.1.200"
                        nvr_ch_url = f"rtsp://{dvr_user}:{dvr_pass}@{dvr_host}:554/Streaming/Channels/{ch_num}01"
                        if nvr_ch_url not in candidate_urls:
                            candidate_urls.append(nvr_ch_url)
                            logger.warning(
                                f"⚠️ CẢNH BÁO REMAP: Đang tự động dự phòng chuyển IP {host} sang kênh NVR {ch_num} ({dvr_host}). "
                                f"Khuyến nghị: Cố định thông số channel_number trong bảng Classroom thay vì tự remap âm thầm!"
                            )
                except Exception:
                    pass

            # Chuẩn bị phương án dự phòng nếu được bật trong chính sách (Auto-Fallback)
            extended_urls = []
            for u in candidate_urls:
                extended_urls.append(u)
                if self.auto_fallback_enabled:
                    if u.endswith("01"):
                        extended_urls.append(u[:-2] + "02")
                    elif u.endswith("02"):
                        alt_01 = u[:-2] + "01"
                        if alt_01 not in extended_urls:
                            extended_urls.append(alt_01)
                    elif "subtype=0" in u:
                        extended_urls.append(u.replace("subtype=0", "subtype=1"))
                    elif "subtype=1" in u:
                        extended_urls.append(u.replace("subtype=1", "subtype=0"))

            for target_url in extended_urls:
                if self.is_host_reachable(target_url):
                    timeout = self.rtsp_timeout_threshold if (target_url.endswith("01") or "subtype=0" in target_url) else 2.5
                    frame = self._read_rtsp_stream(target_url, timeout=timeout)
                    if frame is not None and is_valid_frame(frame):
                        is_sub = target_url.endswith("02") or "subtype=1" in target_url
                        label = "RTSP_SUBSTREAM" if is_sub else "RTSP_STREAM"
                        return True, frame, label, ""

            return False, None, "RTSP_STREAM", "Không nhận được tín hiệu hình ảnh sạch từ camera RTSP (Đang chờ I-frame H.265)"

        # 4. Kiểm tra nếu là luồng HTTP / MJPEG
        if source_str.startswith("http://") or source_str.startswith("https://"):
            try:
                cap = cv2.VideoCapture(source_str)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                ret, f = cap.read()
                cap.release()
                if ret and f is not None:
                    return True, f, "HTTP_STREAM", ""
                return False, None, "HTTP_STREAM", "Không thể lấy frame từ HTTP stream"
            except Exception as e:
                return False, None, "HTTP_STREAM", str(e)

        return False, None, "UNKNOWN", f"Định dạng nguồn camera không được nhận diện: {source_str}"

    def test_camera_stream(self, source_url: str, trigger_signal: bool = False, relay_ip: str = "") -> dict:
        """
        Kiểm tra kết nối và độ trễ tới nguồn camera.
        Nếu trigger_signal=True: Kích hoạt đèn hồng ngoại camera báo hiệu -> Chuyển về ảnh màu -> Bắt khung hình.
        Trả về ảnh xem trước dạng base64 data URL để hiển thị ngay trên Web UI.
        """
        import base64
        cam_info = {"rtsp_url": source_url, "relay_ip": relay_ip, "name": "PreviewCamera"}

        start_t = time.time()
        success, frame, source_type, err_msg = False, None, "UNKNOWN", ""
        try:
            # Kích hoạt chu trình báo hiệu hồng ngoại trước khi bắt hình nếu được yêu cầu
            if trigger_signal:
                try:
                    from backend.app.core.relay_service import relay_service
                    logger.info("[CAMERA-SIGNAL]: Bật đèn hồng ngoại camera thử nghiệm (2.5s)...")
                    relay_service.set_camera_day_night(cam_info, "IR_ON")
                    time.sleep(2.5)
                    logger.info("[CAMERA-SIGNAL]: Chuyển về chế độ ảnh màu để bắt khung hình preview...")
                    relay_service.set_camera_day_night(cam_info, "COLOR")
                    time.sleep(0.8)
                except Exception as e:
                    logger.debug(f"Không thể kích hoạt tín hiệu đèn camera: {e}")

            success, frame, source_type, err_msg = self._fetch_frame_from_source(source_url)
        finally:
            # Luôn trả camera về chế độ tự động sau khi bắt hình kể cả khi gặp lỗi
            if trigger_signal:
                try:
                    from backend.app.core.relay_service import relay_service
                    relay_service.set_camera_day_night(cam_info, "AUTO")
                except Exception:
                    pass

        elapsed_ms = int((time.time() - start_t) * 1000)

        if success and frame is not None:
            h, w = frame.shape[:2]
            # Resize preview nếu quá lớn để tải nhanh trên modal web
            preview_img = frame
            if w > 960:
                scale = 960.0 / w
                preview_img = cv2.resize(frame, (960, int(h * scale)))
            
            _, buffer = cv2.imencode('.jpg', preview_img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            b64_str = base64.b64encode(buffer).decode('utf-8')
            preview_url = f"data:image/jpeg;base64,{b64_str}"

            signal_note = " (Đã kích hoạt đèn hồng ngoại báo hiệu)" if trigger_signal else ""
            return {
                "success": True,
                "latency_ms": elapsed_ms,
                "resolution": f"{w}x{h}",
                "source_type": source_type,
                "preview_url": preview_url,
                "message": f"Kết nối thành công tới nguồn {source_type} ({w}x{h}, độ trễ: {elapsed_ms}ms){signal_note}"
            }
        else:
            return {
                "success": False,
                "latency_ms": elapsed_ms,
                "resolution": "",
                "source_type": source_type,
                "preview_url": "",
                "message": err_msg or "Không thể kết nối tới nguồn camera."
            }

    def capture_single_camera(
        self,
        classroom_id: int,
        classroom_name: str,
        rtsp_url: str,
        target_folder: Path,
        trigger_signal: bool = False,
        relay_ip: str = ""
    ) -> Tuple[int, bool, str, Optional[np.ndarray]]:
        """
        Chụp một khung hình chất lượng cao từ Camera (RTSP, Webcam, Video file).
        Nếu trigger_signal=True: Kích hoạt đèn hồng ngoại báo hiệu rồi chụp ảnh màu.
        Nếu camera mất kết nối hoặc đang chạy mock, tự động kích hoạt cơ chế dự phòng an toàn.
        """
        target_folder.mkdir(parents=True, exist_ok=True)
        file_name = f"Lop_{classroom_id}.jpg"
        file_path = target_folder / file_name

        cam_info = {"id": classroom_id, "name": classroom_name, "rtsp_url": rtsp_url, "relay_ip": relay_ip}
        if trigger_signal:
            try:
                from backend.app.core.relay_service import relay_service
                relay_service.set_camera_day_night(cam_info, "IR_ON")
                time.sleep(2.5)
                relay_service.set_camera_day_night(cam_info, "COLOR")
                time.sleep(0.8)
            except Exception as e:
                logger.debug(f"Lỗi kích hoạt đèn khi chụp đơn lớp {classroom_name}: {e}")

        frame = None
        is_success = False

        # Điều phối kết nối theo pool NVR riêng (Per-NVR Concurrency Limiter)
        host_key = "local"
        if rtsp_url and rtsp_url.startswith("rtsp://"):
            try:
                parsed = urlparse(rtsp_url)
                if parsed.hostname:
                    host_key = parsed.hostname
            except Exception:
                pass

        sem = self._get_nvr_semaphore(host_key)
        with sem:
            # Thử lấy frame từ nguồn thật
            if rtsp_url:
                success, fetched_frame, _, _ = self._fetch_frame_from_source(rtsp_url)
                if success and fetched_frame is not None and is_valid_frame(fetched_frame):
                    frame = fetched_frame
                    is_success = True

        # Cơ chế dự phòng an toàn khi mất tín hiệu camera:
        # TUYỆT ĐỐI KHÔNG nạp ảnh cache cũ (latest) hay ảnh mẫu (sample) để tránh AI đếm sai sĩ số!
        if frame is None or not is_success:
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            frame[:] = (35, 38, 46)  # Nền tối hiện đại
            cv2.rectangle(frame, (100, 100), (1820, 980), (60, 65, 80), 3)
            cv2.putText(frame, f"CAMERA {classroom_id} - {classroom_name.upper()}", (160, 350),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.8, (240, 240, 240), 3)
            cv2.putText(frame, "TRANG THAI: MAT TIN HIEU CAMERA (NO SIGNAL)", (160, 480),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (50, 70, 230), 2)  # Màu đỏ cam cảnh báo
            cv2.putText(frame, "He thong KHONG tinh si so lop nay - Vui long kiem tra ket noi camera/NVR", (160, 580),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (180, 180, 180), 2)
            is_success = False

        # Lưu ảnh vào thư mục máy chủ với độ nén JPEG chất lượng cao 95%
        if frame is not None:
            cv2.imwrite(str(file_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            # CHỈ đồng bộ vào thư mục latest và ghi metadata TTL nếu đây là ảnh camera thực tế thành công
            if is_success:
                latest_path = settings.CAPTURES_DIR / "latest" / f"Lop_{classroom_id}.jpg"
                if str(file_path) != str(latest_path):
                    cv2.imwrite(str(latest_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                # Ghi nhận file metadata JSON kèm timestamp và TTL
                meta_path = settings.CAPTURES_DIR / "latest" / f"Lop_{classroom_id}.meta.json"
                try:
                    import json
                    with open(meta_path, "w", encoding="utf-8") as f_meta:
                        json.dump({
                            "classroom_id": classroom_id,
                            "classroom_name": classroom_name,
                            "captured_at_ts": time.time(),
                            "captured_at_iso": datetime.now().isoformat(),
                            "status": "OK"
                        }, f_meta, indent=2)
                except Exception as e_meta:
                    logger.debug(f"Không thể ghi metadata latest cho lớp {classroom_id}: {e_meta}")
            return classroom_id, is_success, str(file_path), frame
        else:
            logger.error(f"Lỗi chụp ảnh cho lớp {classroom_name}")
            return classroom_id, False, "", None

    def capture_all_classrooms(
        self,
        classrooms: List[Dict],
        date_str: Optional[str] = None,
        max_workers: int = 4,
        target_folder: Optional[Path] = None,
        progress_callback: Optional[Any] = None
    ) -> Dict[int, Dict]:
        """
        Sử dụng đa luồng (multi-threading) tối ưu để chụp ảnh từ 30 camera trường Điều Cải.
        Tích hợp Semaphore theo từng NVR để bảo vệ thiết bị phần cứng và Vòng 2 retry tự động cho camera lỗi.
        Hỗ trợ progress_callback để báo cáo tiến trình trực tiếp lên Web UI Dialog.
        """
        if target_folder is None:
            if not date_str:
                date_str = get_today_str()
            target_folder = settings.CAPTURES_DIR / date_str
        target_folder.mkdir(parents=True, exist_ok=True)

        results = {}
        logger.info(f"Bắt đầu chụp đồng loạt {len(classrooms)} camera với {max_workers} luồng xử lý (Staggered NVR RTSP & HTTP Snapshot)...")
        start_time = time.time()

        # VÒNG 1: Chụp toàn bộ danh sách camera
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_class = {}
            for cls in classrooms:
                time.sleep(0.12)  # Giãn cách 120ms ngăn ngừa xung đột bắt tay kết nối đồng thời với NVR
                fut = executor.submit(
                    self.capture_single_camera,
                    cls["id"],
                    cls["name"],
                    cls.get("rtsp_url", ""),
                    target_folder
                )
                future_to_class[fut] = cls

            for future in as_completed(future_to_class):
                cls_info = future_to_class[future]
                try:
                    cls_id, success, path, frame = future.result()
                    results[cls_id] = {
                        "classroom_id": cls_id,
                        "classroom_name": cls_info["name"],
                        "success": success,
                        "image_path": path,
                        "frame": frame
                    }
                except Exception as e:
                    logger.error(f"Lỗi chụp ảnh cho lớp {cls_info['name']}: {e}")
                    results[cls_info["id"]] = {
                        "classroom_id": cls_info["id"],
                        "classroom_name": cls_info["name"],
                        "success": False,
                        "image_path": "",
                        "frame": None
                    }
                if progress_callback:
                    try:
                        progress_callback(len(results), len(classrooms), cls_info, results[cls_info["id"]]["success"])
                    except Exception:
                        pass

        # VÒNG 2 (Secondary Retry Pass): Tự động thử lại riêng cho các camera lỗi ở vòng 1 (giãn cách 3s)
        failed_classes = [c for c in classrooms if not results.get(c["id"], {}).get("success", False)]
        if failed_classes:
            logger.warning(
                f"Phát hiện {len(failed_classes)}/{len(classrooms)} camera chưa bắt được hình ở vòng 1. "
                "Tự động giãn cách 3 giây và thử lại vòng 2..."
            )
            time.sleep(3)

            with ThreadPoolExecutor(max_workers=max_workers) as retry_executor:
                retry_future_to_class = {}
                for cls in failed_classes:
                    time.sleep(0.15)  # Giãn cách 150ms khi thử lại vòng 2
                    fut = retry_executor.submit(
                        self.capture_single_camera,
                        cls["id"],
                        cls["name"],
                        cls.get("rtsp_url", ""),
                        target_folder
                    )
                    retry_future_to_class[fut] = cls

                for fut in as_completed(retry_future_to_class):
                    cls_info = retry_future_to_class[fut]
                    try:
                        cls_id, success, path, frame = fut.result()
                        if success:
                            logger.info(f"✅ Vòng 2 thành công phục hồi tín hiệu camera {cls_info['name']}!")
                            results[cls_id] = {
                                "classroom_id": cls_id,
                                "classroom_name": cls_info["name"],
                                "success": True,
                                "image_path": path,
                                "frame": frame
                            }
                    except Exception as e:
                        logger.debug(f"Vòng 2 thử lại không thành công cho lớp {cls_info['name']}: {e}")

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results.values() if r["success"])
        logger.info(f"Hoàn thành chụp {success_count}/{len(classrooms)} camera trong {elapsed:.2f} giây.")
        return results

    def capture_sample_frames(self, source_url: str, count: int = 5) -> Dict[str, Any]:
        """
        Thu nhận liên tục 'count' khung hình (mặc định 5 frame) từ camera để kiểm tra độ ổn định,
        đo FPS thực tế, độ trễ và phân tích chất lượng cho Wizard thêm camera mới.
        """
        start_t = time.time()
        frames: List[np.ndarray] = []
        latencies: List[float] = []

        for i in range(count):
            t0 = time.time()
            success, frame, _, err = self._fetch_frame_from_source(source_url)
            t_delta = round((time.time() - t0) * 1000, 1)
            latencies.append(t_delta)
            if success and frame is not None and is_valid_frame(frame):
                frames.append(frame)
            time.sleep(0.05)

        total_elapsed_ms = round((time.time() - start_t) * 1000, 1)
        frames_read = len(frames)
        avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0

        resolution = ""
        width = 0
        height = 0
        best_frame = None
        max_sharpness = -1.0

        if frames:
            h, w = frames[0].shape[:2]
            resolution = f"{w}x{h}"
            width = w
            height = h
            # Chọn frame sắc nét nhất (Laplacian lớn nhất)
            for f in frames:
                try:
                    gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
                    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                except Exception:
                    sharp = 1.0
                if sharp > max_sharpness:
                    max_sharpness = sharp
                    best_frame = f

        return {
            "success": (frames_read >= min(2, count)),
            "requested_count": count,
            "frames_read": frames_read,
            "avg_latency_ms": avg_latency,
            "total_elapsed_ms": total_elapsed_ms,
            "resolution": resolution,
            "width": width,
            "height": height,
            "best_sharpness": round(max_sharpness, 2),
            "best_frame": best_frame,
            "frames": frames
        }

    @staticmethod
    def is_image_stale(classroom_id: int, max_age_seconds: float = 7200.0) -> Tuple[bool, float]:
        """
        Kiểm tra ảnh latest của lớp có bị quá hạn TTL (mặc định 120 phút = 7200s) hay không.
        Trả về: (is_stale, age_seconds).
        """
        meta_file = settings.CAPTURES_DIR / "latest" / f"Lop_{classroom_id}.meta.json"
        img_file = settings.CAPTURES_DIR / "latest" / f"Lop_{classroom_id}.jpg"

        if not img_file.exists():
            return True, float("inf")

        now = time.time()
        file_age = now - img_file.stat().st_mtime

        if meta_file.exists():
            try:
                import json
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    captured_ts = meta.get("captured_at_ts", 0)
                    if captured_ts > 0:
                        file_age = now - captured_ts
            except Exception:
                pass

        return (file_age > max_age_seconds), round(file_age, 1)

rtsp_client = RTSPCameraClient()
