import time
import threading
import requests
from config.settings import settings
from config.logging_config import logger

class RelayService:
    """
    Module điều khiển Relay kích hoạt đèn LED hồng ngoại / đèn tín hiệu camera.
    Báo hiệu cho học sinh trước và trong khi hệ thống tiến hành chụp ảnh điểm danh lúc 6h45 sáng.
    """

    def __init__(self):
        self.relay_type = settings.RELAY_TYPE
        self.host = settings.RELAY_HOST
        self.port = settings.RELAY_PORT
        self.is_on = False

    def turn_on(self) -> bool:
        """Bật đèn LED hồng ngoại qua Relay."""
        logger.info(f"Gửi lệnh BẬT Relay đèn LED (Phương thức: {self.relay_type}, Host: {self.host}:{self.port})")
        self.is_on = True

        if self.relay_type == "HTTP":
            try:
                # Gửi HTTP GET/POST tới Smart Relay / Shelly / ESP32
                url = f"http://{self.host}:{self.port}/relay/0?turn=on"
                res = requests.get(url, timeout=3)
                return res.status_code == 200
            except Exception as e:
                logger.error(f"Lỗi gửi lệnh bật Relay qua HTTP: {e}")
                return False

        elif self.relay_type == "CAMERA_IO":
            try:
                from requests.auth import HTTPDigestAuth, HTTPBasicAuth
                auth = HTTPDigestAuth(settings.DVR_USER, settings.DVR_PASSWORD)
                # 1. Thử lệnh Dahua Alarm Output CGI
                url_dahua = f"http://{self.host}:{self.port}/cgi-bin/alarmOut.cgi?action=setTrigger&channel=1"
                try:
                    res = requests.get(url_dahua, auth=auth, timeout=2)
                    if res.status_code in [200, 204]:
                        return True
                except Exception:
                    pass

                # 2. Thử lệnh Hikvision ISAPI
                url_hik = f"http://{self.host}:{self.port}/ISAPI/System/IO/outputs/1/trigger"
                res = requests.put(url_hik, auth=HTTPBasicAuth(settings.DVR_USER, settings.DVR_PASSWORD), timeout=2)
                return res.status_code in [200, 204]
            except Exception as e:
                logger.warning(f"Lỗi kích hoạt Camera/DVR Alarm Out: {e}")
                return True

        # MOCK mode hoặc dự phòng
        logger.info("[RELAY-ACTIVE]: Tín hiệu kích hoạt đèn LED hồng ngoại báo hiệu học sinh sẵn sàng.")
        return True

    def turn_off(self) -> bool:
        """Tắt đèn LED hồng ngoại qua Relay."""
        logger.info(f"Gửi lệnh TẮT Relay đèn LED (Phương thức: {self.relay_type}, Host: {self.host}:{self.port})")
        self.is_on = False

        if self.relay_type == "HTTP":
            try:
                url = f"http://{self.host}:{self.port}/relay/0?turn=off"
                res = requests.get(url, timeout=3)
                return res.status_code == 200
            except Exception as e:
                logger.error(f"Lỗi gửi lệnh tắt Relay qua HTTP: {e}")
                return False

        elif self.relay_type == "CAMERA_IO":
            try:
                from requests.auth import HTTPDigestAuth
                auth = HTTPDigestAuth(settings.DVR_USER, settings.DVR_PASSWORD)
                url_dahua = f"http://{self.host}:{self.port}/cgi-bin/alarmOut.cgi?action=resetTrigger&channel=1"
                try:
                    requests.get(url_dahua, auth=auth, timeout=2)
                except Exception:
                    pass
                return True
            except Exception as e:
                logger.warning(f"Lỗi tắt Camera Alarm Out: {e}")
                return True

        logger.info("[RELAY-OFF]: Đèn LED hồng ngoại đã TẮT (Hoàn tất chu trình báo hiệu).")
        return True

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
