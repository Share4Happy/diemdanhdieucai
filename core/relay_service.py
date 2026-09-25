import base64
import datetime
import hashlib
import os
import time
import threading
import requests
from urllib.parse import urlparse, parse_qs, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Tuple
from requests.auth import HTTPDigestAuth, HTTPBasicAuth

from config.settings import settings
from config.logging_config import logger

class RelayService:
    """
    Module điều khiển đèn hồng ngoại (IR LEDs) tích hợp của Camera và Relay cảnh báo.
    Quy trình hoạt động:
    1. Báo hiệu: Bật đèn hồng ngoại camera (đèn đỏ sáng, tiếng click kính lọc) trong 3-4 giây
       để thông báo cho học sinh ngồi ngay ngắn vào vị trí.
    2. Chuyển màu: Tự động chuyển camera về chế độ Màu (Color Mode) để ảnh chụp AI là ẢNH MÀU 100%.
    3. Trả về tự động: Sau khi hoàn tất phiên điểm danh, đưa camera về chế độ Tự động (Auto).
    """

    _reachability_cache: Dict[str, Tuple[bool, float]] = {}

    @classmethod
    def is_host_online(cls, host: str, port: int = 80, probe_timeout: float = 0.20) -> bool:
        """Kiểm tra nhanh kết nối TCP (Fast TCP Socket Probe) với bộ nhớ đệm 10 giây để tránh timeout lâu khi camera ngắt kết nối."""
        if not host:
            return False
        if any(k in host.lower() for k in ["mock", "test", "demo", "example"]):
            return False
        
        now = time.time()
        cache_key = f"{host}:{port}"
        if cache_key in cls._reachability_cache:
            status, ts = cls._reachability_cache[cache_key]
            if now - ts < 10.0:
                return status

        import socket
        is_online = False
        try:
            with socket.create_connection((host, int(port)), timeout=probe_timeout):
                is_online = True
        except Exception:
            is_online = False

        cls._reachability_cache[cache_key] = (is_online, now)
        return is_online

    def __init__(self):
        self.relay_type = settings.RELAY_TYPE
        self.default_host = settings.RELAY_HOST
        self.default_port = settings.RELAY_PORT
        self.default_user = settings.DVR_USER
        self.default_password = settings.DVR_PASSWORD
        self.is_on = False

    @staticmethod
    def parse_camera_info(camera_data: Any) -> Dict[str, Any]:
        """
        Trích xuất thông số IP, cổng HTTP, thông tin xác thực và kênh từ Camera/Lớp học.
        Hỗ trợ cả dict và đối tượng SQLAlchemy Classroom.
        """
        if isinstance(camera_data, dict):
            c_id = camera_data.get("id", 0)
            c_name = camera_data.get("name", "")
            rtsp_url = (camera_data.get("rtsp_url") or "").strip()
            relay_ip = (camera_data.get("relay_ip") or "").strip()
            channel_number = camera_data.get("channel_number") or 1
        else:
            c_id = getattr(camera_data, "id", 0)
            c_name = getattr(camera_data, "name", "")
            rtsp_url = (getattr(camera_data, "rtsp_url", "") or "").strip()
            relay_ip = (getattr(camera_data, "relay_ip", "") or "").strip()
            channel_number = getattr(camera_data, "channel_number", 1) or 1

        info = {
            "id": c_id,
            "name": c_name,
            "host": "",
            "http_port": 80,
            "username": settings.DVR_USER,
            "password": settings.DVR_PASSWORD,
            "channel": channel_number,
            "brand": "DAHUA",
            "is_network_camera": False
        }

        # Nếu là webcam nội bộ (0, 1) hoặc file video/ảnh
        if not rtsp_url or rtsp_url.isdigit() or any(rtsp_url.lower().endswith(ext) for ext in [".mp4", ".avi", ".jpg", ".png"]):
            if relay_ip:
                info["host"] = relay_ip
                info["is_network_camera"] = True
            return info

        # Phân giải thông số từ RTSP URL
        try:
            parsed = urlparse(rtsp_url)
            if parsed.hostname:
                info["host"] = parsed.hostname
                info["is_network_camera"] = True

            if parsed.username:
                info["username"] = unquote(parsed.username)
            if parsed.password:
                info["password"] = unquote(parsed.password)

            # Lấy số kênh từ query param ?channel=X
            if parsed.query:
                qs = parse_qs(parsed.query)
                if "channel" in qs and qs["channel"]:
                    try:
                        info["channel"] = int(qs["channel"][0])
                    except ValueError:
                        pass

            # Nhận diện thương hiệu camera
            path_lower = (parsed.path or "").lower()
            if "cam/realmonitor" in path_lower:
                info["brand"] = "DAHUA"
            elif "isapi" in path_lower or "streaming/channels" in path_lower:
                info["brand"] = "HIKVISION"

        except Exception as e:
            logger.debug(f"Lỗi phân giải RTSP URL '{rtsp_url}': {e}")

        # relay_ip ưu tiên đè host nếu có thiết lập riêng
        if relay_ip:
            info["host"] = relay_ip
            info["is_network_camera"] = True

        return info

    @staticmethod
    def _create_onvif_ws_auth(username: str, password: str) -> str:
        """Tạo tiêu đề WS-UsernameToken với PasswordDigest SHA1 theo chuẩn ONVIF."""
        created = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        nonce_bytes = os.urandom(16)
        nonce_b64 = base64.b64encode(nonce_bytes).decode("ascii")
        sha = hashlib.sha1()
        sha.update(nonce_bytes + created.encode("utf-8") + (password or "").encode("utf-8"))
        digest_b64 = base64.b64encode(sha.digest()).decode("ascii")
        return (
            f'<s:Header>'
            f'<Security s:mustUnderstand="1" xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">'
            f'<UsernameToken>'
            f'<Username>{username}</Username>'
            f'<Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest_b64}</Password>'
            f'<Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</Nonce>'
            f'<Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">{created}</Created>'
            f'</UsernameToken>'
            f'</Security>'
            f'</s:Header>'
        )

    def _send_onvif_ircut(
        self,
        host: str,
        http_port: int,
        username: str,
        password: str,
        filter_val: str,
        timeout: float = 2.0
    ) -> bool:
        """
        Gửi lệnh ONVIF SetImagingSettings chuyển đổi IrCutFilter (Hồng ngoại / Màu / Tự động).
        Tương thích 100% với các camera Imou (IPC-F32P,...), Dahua WiFi, Ezviz, Hikvision, Tapo...
        filter_val:
        - "ON": Night Mode (Kính lọc mở, đèn hồng ngoại sáng, ảnh B&W phát tín hiệu báo giờ)
        - "OFF": Day/Color Mode (Kính lọc đóng, ảnh màu chuẩn 100% để phục vụ AI nhận diện)
        - "AUTO": Trả về chế độ tự động theo cảm biến ánh sáng
        """
        if not host or not username:
            return False

        url = f"http://{host}:{http_port}/onvif/imaging_service"
        tokens = ["VideoSource000", "000", "VideoSource1"]

        for token in tokens:
            try:
                auth_header = self._create_onvif_ws_auth(username, password)
                body = (
                    f'<?xml version="1.0" encoding="utf-8"?>'
                    f'<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
                    f'xmlns:timg="http://www.onvif.org/ver20/imaging/wsdl" '
                    f'xmlns:tt="http://www.onvif.org/ver10/schema">'
                    f'{auth_header}'
                    f'<s:Body>'
                    f'<timg:SetImagingSettings>'
                    f'<timg:VideoSourceToken>{token}</timg:VideoSourceToken>'
                    f'<timg:ImagingSettings>'
                    f'<tt:IrCutFilter>{filter_val}</tt:IrCutFilter>'
                    f'</timg:ImagingSettings>'
                    f'<timg:ForcePersistence>true</timg:ForcePersistence>'
                    f'</timg:SetImagingSettings>'
                    f'</s:Body>'
                    f'</s:Envelope>'
                )
                headers = {
                    "Content-Type": "application/soap+xml; charset=utf-8; action=\"http://www.onvif.org/ver20/imaging/wsdl/SetImagingSettings\""
                }
                res = requests.post(url, data=body.encode("utf-8"), headers=headers, timeout=timeout)
                if res.status_code in [200, 204]:
                    logger.info(f"[ONVIF-SUCCESS]: Đã chuyển IrCutFilter={filter_val} trên {host} (Token: {token})")
                    return True
                elif res.status_code in [400, 500] and ("InvalidToken" in res.text or "Token" in res.text):
                    continue
            except Exception as e:
                logger.debug(f"[ONVIF]: Gửi lệnh tới {host}:{http_port} (token {token}) không thành công: {e}")
                break

        return False

    def set_camera_day_night(
        self,
        camera_data: Any,
        mode: str = "COLOR",
        timeout: float = 2.0
    ) -> bool:
        """
        Điều khiển chế độ Day/Night (Hồng ngoại / Màu / Tự động) trên 1 camera.
        mode:
        - "IR_ON": Bật đèn hồng ngoại camera (Night/BW Mode) -> LED hồng ngoại phát sáng đỏ báo hiệu
        - "COLOR": Khóa chế độ ảnh màu ban ngày -> Đảm bảo ảnh chụp có màu chuẩn 100%
        - "AUTO": Trả về chế độ tự động thông thường
        - "WHITE_LIGHT_ON": Bật đèn trợ sáng ánh sáng trắng (nếu camera có hỗ trợ)
        - "WHITE_LIGHT_OFF": Tắt đèn trợ sáng ánh sáng trắng
        """
        info = self.parse_camera_info(camera_data)
        host = info["host"]
        if not host or not info["is_network_camera"]:
            # Giả lập thành công cho webcam máy tính hoặc file mẫu
            return True

        user = info["username"]
        pwd = info["password"]
        ch = info["channel"]
        brand = info["brand"]
        http_port = info["http_port"]

        # Kiểm tra nhanh kết nối TCP tới thiết bị, nếu không online thì bỏ qua ngay để không nghẽn timeout
        if not self.is_host_online(host, port=http_port):
            return False

        # Ánh xạ giá trị ONVIF IrCutFilter theo đặc tả chuẩn quốc tế (ONVIF Imaging Service):
        # "OFF" = Ngắt kính lọc hồng ngoại -> Kính lọc mở cho tia hồng ngoại vào -> BẬT ĐÈN HỒNG NGOẠI (Night Mode / B&W)
        # "ON"  = Bật kính lọc hồng ngoại -> Kính lọc chặn tia hồng ngoại -> CHẾ ĐỘ BAN NGÀY (Day Mode / ẢNH MÀU 100%)
        # "AUTO" = Chế độ tự động cảm biến ánh sáng
        onvif_filter = "AUTO"
        if mode == "IR_ON":
            onvif_filter = "OFF"
        elif mode == "COLOR":
            onvif_filter = "ON"
        elif mode == "AUTO":
            onvif_filter = "AUTO"

        # 1. ƯU TIÊN SỐ 1: GỬI QUA ONVIF IMAGING SERVICE
        # Phương thức này tương thích cao nhất với camera Imou, Dahua WiFi, Ezviz, Hikvision,...
        if mode in ["IR_ON", "COLOR", "AUTO"]:
            if self._send_onvif_ircut(host, http_port, user, pwd, onvif_filter, timeout=timeout):
                return True

        auth_digest = HTTPDigestAuth(user, pwd)

        try:
            # 2. XỬ LÝ CAMERA DAHUA / KBVISION QUA CGI (Cả Camera IPC độc lập và Đầu ghi NVR đa kênh)
            if brand == "DAHUA":
                # Chuẩn Dahua DayNightColor: 0 = Color (Ngày/Màu), 1 = Auto (Tự động), 2 = Black&White (Đêm/Bật hồng ngoại)
                if mode == "IR_ON":
                    color_val = 2
                    is_ir = "true"
                    light_state = "On"
                elif mode == "AUTO":
                    color_val = 1
                    is_ir = "auto"
                    light_state = "Auto"
                else:  # COLOR
                    color_val = 0
                    is_ir = "false"
                    light_state = "Off"

                ch_idx = max(0, ch - 1)

                # Thử các cú pháp lệnh CGI tương thích cho cả Dahua IPC và Đầu ghi Dahua NVR
                dahua_endpoints = [
                    f"?action=setConfig&VideoInOptions[{ch_idx}].DayNightColor={color_val}",
                    f"?action=setConfig&VideoInOptions[{ch_idx}].NormalOptions.DayNightColor={color_val}",
                    f"?action=setConfig&VideoInOptions[{ch_idx}].NightOptions.DayNightColor={color_val}&VideoInOptions[{ch_idx}].NightOptions.InfraRed={is_ir}",
                    f"?action=setConfig&Lighting[{ch_idx}][0].Mode={'Manual' if mode == 'IR_ON' else 'Auto'}&Lighting[{ch_idx}][0].State={light_state}"
                ]

                for ep in dahua_endpoints:
                    try:
                        url = f"http://{host}:{http_port}/cgi-bin/configManager.cgi{ep}"
                        res = requests.get(url, auth=auth_digest, timeout=timeout)
                        if res.status_code in [200, 204] and ("OK" in res.text or not res.text.strip()):
                            logger.info(f"[DAHUA-CGI]: Đã gửi lệnh '{ep}' thành công tới {host}")
                            return True
                    except Exception:
                        pass

                # Lệnh 2.2: Bật / Tắt đèn trợ sáng trắng / Active Deterrence (cho camera hỗ trợ Coaxial / NVR)
                if mode in ["IR_ON", "WHITE_LIGHT_ON"]:
                    url_light = f"http://{host}:{http_port}/cgi-bin/coaxialControlIO.cgi?action=control&channel={ch}&info[0].Type=1&info[0].IO=1"
                else:
                    url_light = f"http://{host}:{http_port}/cgi-bin/coaxialControlIO.cgi?action=control&channel={ch}&info[0].Type=1&info[0].IO=0"

                try:
                    res = requests.get(url_light, auth=auth_digest, timeout=timeout)
                    if res.status_code in [200, 204]:
                        logger.info(f"[DAHUA-LIGHT]: Đã điều khiển đèn trợ sáng trên {host}")
                        return True
                except Exception:
                    pass

                # Lệnh 2.3: Alarm Output CGI (nếu có chân relay cảnh báo)
                if mode == "IR_ON":
                    url_alarm = f"http://{host}:{http_port}/cgi-bin/alarmOut.cgi?action=setTrigger&channel={ch}"
                else:
                    url_alarm = f"http://{host}:{http_port}/cgi-bin/alarmOut.cgi?action=resetTrigger&channel={ch}"

                try:
                    res = requests.get(url_alarm, auth=auth_digest, timeout=timeout)
                    if res.status_code in [200, 204]:
                        logger.info(f"[DAHUA-ALARM]: Đã kích hoạt cổng alarm out trên {host}")
                        return True
                except Exception:
                    pass

            # 3. XỬ LÝ CAMERA HIKVISION QUA ISAPI
            elif brand == "HIKVISION":
                filter_mode = "day"
                if mode == "IR_ON":
                    filter_mode = "night"
                elif mode == "AUTO":
                    filter_mode = "auto"

                hik_channels = [ch, ch * 100 + 1] if ch < 100 else [ch]
                for h_ch in hik_channels:
                    url_hik = f"http://{host}:{http_port}/ISAPI/Image/channels/{h_ch}/IrcutFilter"
                    xml_data = (
                        f'<IrcutFilter version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">'
                        f'<IrcutFilterType>{filter_mode}</IrcutFilterType>'
                        f'</IrcutFilter>'
                    )
                    try:
                        res = requests.put(
                            url_hik,
                            data=xml_data,
                            headers={"Content-Type": "application/xml"},
                            auth=auth_digest,
                            timeout=timeout
                        )
                        if res.status_code in [200, 204]:
                            logger.info(f"[HIK-ISAPI]: Đã chuyển IrcutFilter={filter_mode} trên kênh {h_ch} ({host})")
                            return True
                    except Exception:
                        pass

            # 4. THỬ QUA HTTP RELAY THÔNG DỤNG (ESP32, SHELLY)
            if mode in ["IR_ON", "WHITE_LIGHT_ON"]:
                url_relay = f"http://{host}:{http_port}/relay/0?turn=on"
            else:
                url_relay = f"http://{host}:{http_port}/relay/0?turn=off"

            try:
                res = requests.get(url_relay, timeout=1.5)
                if res.status_code in [200, 204]:
                    logger.info(f"[HTTP-RELAY]: Đã gửi lệnh relay tới {host}")
                    return True
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"[CAMERA-SIGNAL]: Lỗi khi gửi lệnh điều khiển tới {info['name']} ({host}): {e}")
            return False

        logger.warning(f"[CAMERA-SIGNAL]: Camera {info['name']} ({host}) không phản hồi bất kỳ giao thức điều khiển nào (ONVIF, CGI, ISAPI, Relay).")
        return False

    def signal_classrooms_before_capture(
        self,
        classrooms: List[Any],
        signal_seconds: int = 3,
        capture_color: bool = True,
        max_workers: int = 15
    ) -> Dict[str, Any]:
        """
        Chu trình báo hiệu đồng loạt trên 30 camera lớp học trước khi chụp ảnh:
        1. BẬT đèn hồng ngoại trên tất cả camera để học sinh thấy đèn đỏ báo hiệu và ngồi vào vị trí.
        2. Chờ `signal_seconds` (3-4 giây) để học sinh ổn định.
        3. Nếu `capture_color = True`: Tự động chuyển camera về chế độ MÀU (Color Mode) để ảnh chụp là ẢNH MÀU 100%.
        """
        if not classrooms:
            return {"success": True, "count": 0}

        # Kiểm tra nhanh: Nếu toàn bộ camera mạng đều offline (chưa cắm NVR thật) -> Bỏ qua ngay để tiết kiệm ~65s
        has_any_network_online = False
        for cls in classrooms:
            info = self.parse_camera_info(cls)
            if info.get("is_network_camera") and info.get("host"):
                if self.is_host_online(info["host"], port=info.get("http_port", 80)):
                    has_any_network_online = True
                    break

        if not has_any_network_online:
            logger.info(
                f"[CAMERA-SIGNAL]: Toàn bộ {len(classrooms)} camera IP/NVR hiện chưa online (IP không phản hồi TCP). "
                f"Tự động bỏ qua chu trình đèn để chụp và quét AI ngay lập tức (Tiết kiệm ~65s)!"
            )
            return {
                "success": True,
                "classes_count": len(classrooms),
                "skipped_offline": True,
                "signal_seconds": 0,
                "capture_color": capture_color,
            }

        logger.info(
            f"=== [CAMERA-SIGNAL]: BẮT ĐẦU PHÁT TÍN HIỆU ĐÈN HỒNG NGOẠI TRÊN {len(classrooms)} CAMERA "
            f"(Báo hiệu {signal_seconds}s trước khi chụp) ==="
        )

        # Bước 1: Gửi lệnh BẬT HỒNG NGOẠI đồng loạt qua đa luồng
        start_t = time.time()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.set_camera_day_night, cls, "IR_ON")
                for cls in classrooms
            ]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception:
                    pass

        elapsed_ir = time.time() - start_t
        logger.info(
            f"[CAMERA-SIGNAL]: Đã kích hoạt đèn hồng ngoại 30 camera ({elapsed_ir:.2f}s). "
            f"Học sinh có {signal_seconds} giây ổn định vị trí..."
        )

        # Bước 2: Chờ thời gian báo hiệu cho học sinh
        time.sleep(signal_seconds)

        # Bước 3: Nếu yêu cầu chụp ảnh màu -> Chuyển camera về chế độ COLOR
        if capture_color:
            logger.info("[CAMERA-SIGNAL]: Đang chuyển camera sang chế độ ẢNH MÀU (Color Mode) để AI đếm chuẩn xác...")
            start_color = time.time()
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(self.set_camera_day_night, cls, "COLOR")
                    for cls in classrooms
                ]
                for f in as_completed(futures):
                    try:
                        f.result()
                    except Exception:
                        pass

            elapsed_color = time.time() - start_color
            # Chờ 1 giây để kính lọc IR-Cut đóng lại và cảm biến ổn định độ phơi sáng
            time.sleep(1.0)
            logger.info(f"[CAMERA-SIGNAL]: Đã sẵn sàng chụp ẢNH MÀU 100% (Chuyển chế độ mất {elapsed_color:.2f}s).")

        return {
            "success": True,
            "classes_count": len(classrooms),
            "signal_seconds": signal_seconds,
            "capture_color": capture_color
        }

    def restore_classrooms_auto(
        self,
        classrooms: List[Any],
        max_workers: int = 15
    ):
        """
        Trả toàn bộ 30 camera về chế độ Tự Động (AUTO) sau khi phiên chụp điểm danh kết thúc.
        """
        if not classrooms:
            return

        def _restore_job():
            try:
                logger.info(f"[CAMERA-SIGNAL]: Đang đưa {len(classrooms)} camera về chế độ Tự Động (Auto Day/Night)...")
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [
                        executor.submit(self.set_camera_day_night, cls, "AUTO")
                        for cls in classrooms
                    ]
                    for f in as_completed(futures):
                        try:
                            f.result()
                        except Exception:
                            pass
                logger.info("[CAMERA-SIGNAL]: Hoàn tất trả camera về chế độ Tự Động.")
            except Exception:
                pass

        threading.Thread(target=_restore_job, daemon=True).start()

    # ==================== CÁC PHƯƠNG THỨC TƯƠNG THÍCH NGƯỢC (BACKWARD COMPATIBILITY) ====================

    def turn_on(self, host: Optional[str] = None) -> bool:
        """Bật đèn hồng ngoại / Relay theo host cấu hình mặc định."""
        target_host = host or self.default_host
        logger.info(f"Gửi lệnh BẬT đèn hồng ngoại / Relay (Host: {target_host})")
        self.is_on = True
        dummy_cam = {"relay_ip": target_host, "name": f"Device_{target_host}"}
        return self.set_camera_day_night(dummy_cam, "IR_ON")

    def turn_off(self, host: Optional[str] = None) -> bool:
        """Tắt đèn hồng ngoại / Relay theo host cấu hình mặc định."""
        target_host = host or self.default_host
        logger.info(f"Gửi lệnh TẮT đèn hồng ngoại / Relay (Host: {target_host})")
        self.is_on = False
        dummy_cam = {"relay_ip": target_host, "name": f"Device_{target_host}"}
        return self.set_camera_day_night(dummy_cam, "AUTO")

    def activate_timed_signal(self, duration_seconds: int = None):
        """Kích hoạt đèn LED chạy ngầm trong khoảng thời gian xác định rồi tự động tắt."""
        if duration_seconds is None:
            duration_seconds = settings.RELAY_DURATION_SECONDS

        def _run():
            self.turn_on()
            time.sleep(duration_seconds)
            self.turn_off()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        logger.info(f"Đã lập tiến trình chạy đèn LED trong {duration_seconds} giây.")

relay_service = RelayService()
