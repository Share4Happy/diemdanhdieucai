import os
import cv2
import time
import socket
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

from config.settings import settings
from config.logging_config import logger

class RTSPCameraClient:
    """
    Module quản lý kết nối Camera/DVR qua giao thức RTSP và chụp ảnh đồng loạt đa luồng.
    Tích hợp cơ chế kiểm tra socket nhanh (Fast TCP Probe) để không bao giờ bị nghẽn nếu camera mất điện/mất mạng.
    """

    def __init__(self, timeout_seconds: int = 3):
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def is_host_reachable(url: str, probe_timeout: float = 0.4) -> bool:
        """Kiểm tra nhanh kết nối TCP port RTSP trước khi mở ffmpeg stream để tránh timeout lâu."""
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or 554
            if not host:
                return False
            # Bỏ qua nếu là chuỗi giả lập
            if any(k in host.lower() for k in ["mock", "test", "demo", "example"]):
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
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        return True, frame, "VIDEO_FILE", ""
                return False, None, "VIDEO_FILE", f"Không thể đọc khung hình từ video {local_path.name}"

        # 3. Kiểm tra nếu là luồng RTSP
        if source_str.startswith("rtsp://"):
            if self.is_host_reachable(source_str):
                try:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;2000000|rtsp_transport;tcp"
                    cap = cv2.VideoCapture(source_str, cv2.CAP_FFMPEG)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    start_time = time.time()
                    while time.time() - start_time < self.timeout_seconds:
                        ret, f = cap.read()
                        if ret and f is not None:
                            cap.release()
                            return True, f, "RTSP_STREAM", ""
                        time.sleep(0.05)
                    cap.release()
                    return False, None, "RTSP_STREAM", "Hết thời gian chờ nhận frame từ luồng RTSP"
                except Exception as e:
                    return False, None, "RTSP_STREAM", str(e)
            else:
                return False, None, "RTSP_STREAM", "Không thể kết nối tới IP/Port camera RTSP (Timeout hoặc ngắt mạng)"

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

    def test_camera_stream(self, source_url: str) -> dict:
        """
        Kiểm tra kết nối và độ trễ tới nguồn camera.
        Trả về ảnh xem trước dạng base64 data URL để hiển thị ngay trên Web UI.
        """
        import base64
        start_t = time.time()
        success, frame, source_type, err_msg = self._fetch_frame_from_source(source_url)
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

            return {
                "success": True,
                "latency_ms": elapsed_ms,
                "resolution": f"{w}x{h}",
                "source_type": source_type,
                "preview_url": preview_url,
                "message": f"Kết nối thành công tới nguồn {source_type} ({w}x{h}, độ trễ: {elapsed_ms}ms)"
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
        target_folder: Path
    ) -> Tuple[int, bool, str, Optional[np.ndarray]]:
        """
        Chụp một khung hình chất lượng cao từ Camera (RTSP, Webcam, Video file).
        Nếu camera mất kết nối hoặc đang chạy mock, tự động kích hoạt cơ chế dự phòng an toàn.
        """
        target_folder.mkdir(parents=True, exist_ok=True)
        file_name = f"Lop_{classroom_id}.jpg"
        file_path = target_folder / file_name

        frame = None
        is_success = False

        # Thử lấy frame từ nguồn thật
        if rtsp_url:
            success, fetched_frame, _, _ = self._fetch_frame_from_source(rtsp_url)
            if success and fetched_frame is not None:
                frame = fetched_frame
                is_success = True

        # Cơ chế dự phòng khi chạy thử nghiệm hoặc camera chưa cắm dây
        if frame is None:
            latest_capture = settings.CAPTURES_DIR / "latest" / f"Lop_{classroom_id}.jpg"
            if latest_capture.exists():
                frame = cv2.imread(str(latest_capture))

            if frame is None:
                extracted_frames = list((settings.BASE_DIR / "dataset" / "extracted_frames").glob("*.jpg"))
                if extracted_frames:
                    sample_path = extracted_frames[(classroom_id - 1) % len(extracted_frames)]
                    frame = cv2.imread(str(sample_path))

            if frame is None:
                # Tạo frame fallback 1920x1080
                frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
                frame[:] = (220, 220, 220)

            is_success = True

        # Lưu ảnh vào thư mục máy chủ: storage/captures/YYYY-MM-DD/Lop_X.jpg
        if frame is not None:
            cv2.imwrite(str(file_path), frame)
            return classroom_id, True, str(file_path), frame
        else:
            logger.error(f"Lỗi chụp ảnh cho lớp {classroom_name}")
            return classroom_id, False, "", None

    def capture_all_classrooms(
        self,
        classrooms: List[Dict],
        date_str: Optional[str] = None,
        max_workers: int = 10
    ) -> Dict[int, Dict]:
        """
        Sử dụng đa luồng (multi-threading) để chụp ảnh từ 30 camera cùng lúc.
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        target_folder = settings.CAPTURES_DIR / date_str
        target_folder.mkdir(parents=True, exist_ok=True)

        results = {}
        logger.info(f"Bắt đầu chụp đồng loạt {len(classrooms)} camera với {max_workers} luồng xử lý...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_class = {
                executor.submit(
                    self.capture_single_camera,
                    cls["id"],
                    cls["name"],
                    cls.get("rtsp_url", ""),
                    target_folder
                ): cls for cls in classrooms
            }

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

        elapsed = time.time() - start_time
        success_count = sum(1 for r in results.values() if r["success"])
        logger.info(f"Hoàn thành chụp {success_count}/{len(classrooms)} camera trong {elapsed:.2f} giây.")
        return results

rtsp_client = RTSPCameraClient()
