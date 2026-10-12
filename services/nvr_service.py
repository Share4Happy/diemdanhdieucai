import os
import cv2
import time
import base64
import socket
from urllib.parse import quote, urlparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

from config.settings import settings
from config.logging_config import logger
from core.rtsp_client import is_valid_frame

class NVRService:
    """
    Dịch vụ chuyên biệt quản lý và tích hợp Đầu Ghi Hình Camera (NVR / DVR)
    Hỗ trợ Dahua, Hikvision, Uniview, Custom RTSP và quét đồng loạt 30 kênh.
    """

    DEFAULT_30_CLASSES = [
        ("12A1", 48, "Phòng 1"), ("12A2", 45, "Phòng 2"), ("12A3", 41, "Phòng 3"),
        ("12A4", 44, "Phòng 4"), ("12A5", 42, "Phòng 5"), ("12A6", 41, "Phòng 6"),
        ("12A7", 44, "Phòng 7"), ("12A8", 44, "Phòng 8"), ("12A9", 39, "Phòng 9"),
        ("12A10", 40, "Phòng 10"),
        ("11A1", 43, "Phòng 11"), ("11A2", 43, "Phòng 12"), ("11A3", 31, "Phòng 13"),
        ("11A4", 35, "Phòng 14"), ("11A5", 45, "Phòng 15"), ("11A6", 45, "Phòng 16"),
        ("11A7", 34, "Phòng 17"), ("11A8", 30, "Phòng 18"), ("11A9", 36, "Phòng 19"),
        ("11A10", 35, "Phòng 20"),
        ("10A1", 44, "Phòng 21"), ("10A6", 48, "Phòng 22"), ("10A2", 40, "Phòng 23"),
        ("10A3", 38, "Phòng 24"), ("10A4", 45, "Phòng 25"), ("10A5", 44, "Phòng 26"),
        ("10A7", 46, "Phòng 27"), ("10A8", 35, "Phòng 28"), ("10A9", 37, "Phòng 29"),
        ("10A10", 47, "Phòng 30")
    ]

    @staticmethod
    def build_rtsp_url(
        brand: str,
        ip_address: str,
        rtsp_port: int,
        username: str,
        password: str,
        channel: int,
        subtype: int = 0,
        custom_pattern: str = ""
    ) -> str:
        """
        Sinh đường dẫn RTSP chuẩn hóa theo từng hãng đầu ghi.
        """
        encoded_pwd = quote(password or "")
        user = quote(username or "admin")
        host = ip_address.strip()
        port = int(rtsp_port or 554)
        brand_upper = (brand or "DAHUA").strip().upper()

        if brand_upper == "CUSTOM" and custom_pattern:
            return custom_pattern.format(
                user=user,
                password=encoded_pwd,
                ip=host,
                port=port,
                channel=channel,
                subtype=subtype
            )
        elif brand_upper in ["HIK", "HIKVISION", "EZVIZ"]:
            # Hikvision: channel 1 -> 101 (main) / 102 (sub), channel 2 -> 201 / 202
            stream_code = f"{channel}0{1 if subtype == 0 else 2}"
            return f"rtsp://{user}:{encoded_pwd}@{host}:{port}/Streaming/Channels/{stream_code}"
        elif brand_upper in ["UNV", "UNIVIEW"]:
            return f"rtsp://{user}:{encoded_pwd}@{host}:{port}/unicast/c{channel}/s{subtype}/live"
        else:
            # Mặc định chuẩn DAHUA / KBVISION / IMOU
            return f"rtsp://{user}:{encoded_pwd}@{host}:{port}/cam/realmonitor?channel={channel}&subtype={subtype}"

    @staticmethod
    def is_tcp_port_open(host: str, port: int, timeout: float = 0.35) -> bool:
        """Kiểm tra nhanh socket port RTSP trước khi mở ffmpeg stream."""
        try:
            if any(k in host.lower() for k in ["mock", "demo", "example"]):
                return False
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    _cached_sample_frames = None

    @classmethod
    def _get_sample_frame(cls, channel_num: int):
        if cls._cached_sample_frames is None:
            frames = []
            frame_files = sorted(list((settings.BASE_DIR / "dataset" / "extracted_frames").glob("*.jpg")))
            for f in frame_files[:15]:
                img = cv2.imread(str(f))
                if img is not None:
                    frames.append(img)
            cls._cached_sample_frames = frames
        
        if cls._cached_sample_frames:
            return cls._cached_sample_frames[(channel_num - 1) % len(cls._cached_sample_frames)].copy()
        return None

    def probe_single_channel(
        self,
        channel_num: int,
        rtsp_url: str,
        host: str,
        port: int,
        is_nvr_reachable: bool,
        name_hint: str = "",
        room_hint: str = "",
        standard_count_hint: int = 40
    ) -> Dict[str, Any]:
        """
        Thăm dò kết nối và lấy 1 khung hình thumbnail của kênh camera.
        """
        start_t = time.time()
        frame = None
        is_online = False
        is_simulated = False
        latency_ms = 0
        resolution = "1920x1080"

        # 1. Thử lấy luồng thật nếu host đầu ghi có thông mạng
        if is_nvr_reachable:
            try:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                    "timeout;4000000|rtsp_transport;tcp|buffer_size;2048000|analyzeduration;1000000|probesize;1000000"
                )
                # Ưu tiên lấy thumbnail nhanh từ luồng phụ để quét 30 kênh siêu mượt mà không nghẽn NVR
                main_url = rtsp_url
                sub_url = ""
                if rtsp_url.endswith("01"):
                    sub_url = rtsp_url[:-2] + "02"
                elif "subtype=0" in rtsp_url:
                    sub_url = rtsp_url.replace("subtype=0", "subtype=1")

                urls_to_try = [sub_url, main_url] if sub_url else [main_url]

                for u in urls_to_try:
                    cap = cv2.VideoCapture(u, cv2.CAP_FFMPEG)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if cap.isOpened():
                        # Warm-up: Xả đệm 5 frames đầu để loại bỏ P-frame cũ
                        for _ in range(5):
                            cap.grab()

                        read_start = time.time()
                        timeout_limit = 2.5 if (u.endswith("02") or "subtype=1" in u) else 3.5
                        while time.time() - read_start < timeout_limit:
                            ret, f = cap.read()
                            if ret and f is not None and is_valid_frame(f):
                                frame = f
                                is_online = True
                                h, w = frame.shape[:2]
                                resolution = f"{w}x{h}"
                                break
                            time.sleep(0.02)
                    cap.release()
                    if is_online:
                        break
            except Exception as e:
                logger.debug(f"Không thể đọc stream kênh {channel_num}: {e}")

        elapsed_ms = int((time.time() - start_t) * 1000)

        # 2. Cơ chế fallback khi camera chưa cắm hoặc kênh offline
        if frame is None:
            is_simulated = True
            is_online = False
            frame = self._get_sample_frame(channel_num)
            
            if frame is None:
                # Tạo ảnh giả lập có nền lớp học
                frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                frame[:] = (45, 55, 72)
                cv2.putText(
                    frame,
                    f"CAM CH{channel_num:02d} - {name_hint or f'Phong {channel_num}'}",
                    (60, 360),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.3,
                    (255, 255, 255),
                    3
                )
            latency_ms = max(15, elapsed_ms)
        else:
            latency_ms = elapsed_ms

        # 3. Tạo ảnh thumbnail Base64 kích thước 320x180 để truyền siêu nhanh qua JSON
        thumb_b64 = ""
        if frame is not None:
            thumb = cv2.resize(frame, (320, 180))
            # Vẽ nhãn OSD nhỏ góc dưới tương tự màn hình NVR
            label_text = f"CH{channel_num:02d} | {name_hint or f'P.{channel_num}'}"
            cv2.rectangle(thumb, (4, 154), (190, 176), (0, 0, 0), -1)
            cv2.putText(thumb, label_text, (8, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 200), 1)
            
            _, buf = cv2.imencode('.jpg', thumb, [cv2.IMWRITE_JPEG_QUALITY, 80])
            thumb_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"

        return {
            "channel": channel_num,
            "code": f"LOP_{self.DEFAULT_30_CLASSES[channel_num-1][0]}" if channel_num <= len(self.DEFAULT_30_CLASSES) else f"CAM_CH{channel_num:02d}",
            "name": name_hint or (f"Lớp {self.DEFAULT_30_CLASSES[channel_num-1][0]}" if channel_num <= len(self.DEFAULT_30_CLASSES) else f"Camera Kênh {channel_num}"),
            "room_number": room_hint or (self.DEFAULT_30_CLASSES[channel_num-1][2] if channel_num <= len(self.DEFAULT_30_CLASSES) else f"Phòng {100 + channel_num}"),
            "standard_count": standard_count_hint,
            "rtsp_url": rtsp_url,
            "is_online": is_online,
            "is_simulated": is_simulated,
            "latency_ms": latency_ms,
            "resolution": resolution,
            "thumbnail": thumb_b64,
            "is_selected": True
        }

    def probe_all_nvr_channels(
        self,
        ip_address: str,
        rtsp_port: int = 554,
        username: str = "admin",
        password: str = "",
        brand: str = "DAHUA",
        channels_count: int = 30,
        naming_mode: str = "DEFAULT_30_CLASSES",
        custom_pattern: str = ""
    ) -> Dict[str, Any]:
        """
        Quét đa luồng song song tất cả các kênh camera của Đầu Ghi NVR.
        """
        start_time = time.time()
        host = ip_address.strip()
        port = int(rtsp_port or 554)
        channels_count = max(1, min(64, int(channels_count or 30)))

        is_nvr_reachable = self.is_tcp_port_open(host, port, timeout=0.4)
        logger.info(f"Dò NVR {host}:{port} ({brand}) - Trạng thái cổng RTSP: {'MỞ' if is_nvr_reachable else 'ĐÓNG/CHƯA CẮM DÂY'}")

        results = []
        with ThreadPoolExecutor(max_workers=min(3, channels_count)) as executor:
            future_to_ch = {}
            for ch in range(1, channels_count + 1):
                time.sleep(0.08)  # Giãn cách 80ms để không dồn dập NVR CPU
                url = self.build_rtsp_url(
                    brand=brand,
                    ip_address=host,
                    rtsp_port=port,
                    username=username,
                    password=password,
                    channel=ch,
                    subtype=0,
                    custom_pattern=custom_pattern
                )

                name_hint = ""
                room_hint = ""
                std_hint = 40
                if naming_mode == "DEFAULT_30_CLASSES" and (ch - 1) < len(self.DEFAULT_30_CLASSES):
                    cname, cstd, croom = self.DEFAULT_30_CLASSES[ch - 1]
                    name_hint = f"Lớp {cname}"
                    room_hint = croom
                    std_hint = cstd
                else:
                    name_hint = f"Camera Kênh {ch}"
                    room_hint = f"Phòng {100 + ch}"
                    std_hint = 40

                f = executor.submit(
                    self.probe_single_channel,
                    ch,
                    url,
                    host,
                    port,
                    is_nvr_reachable,
                    name_hint,
                    room_hint,
                    std_hint
                )
                future_to_ch[f] = ch

            for f in as_completed(future_to_ch):
                try:
                    data = f.result()
                    results.append(data)
                except Exception as e:
                    ch_idx = future_to_ch[f]
                    logger.error(f"Lỗi thăm dò kênh {ch_idx}: {e}")

        # Sắp xếp lại theo đúng thứ tự kênh 1 -> 30
        results.sort(key=lambda x: x["channel"])
        elapsed = round(time.time() - start_time, 2)
        online_count = sum(1 for r in results if r["is_online"])

        return {
            "success": True,
            "ip_address": host,
            "rtsp_port": port,
            "brand": brand,
            "total_channels": channels_count,
            "online_channels": online_count,
            "is_nvr_reachable": is_nvr_reachable,
            "elapsed_seconds": elapsed,
            "channels": results
        }

nvr_service = NVRService()
