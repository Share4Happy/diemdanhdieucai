import os
from pathlib import Path
from pydantic import BaseModel

# Load .env file
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseModel):
    # App Settings
    BASE_DIR: Path = BASE_DIR
    APP_NAME: str = "Hệ Thống Điểm Danh Tự Động AI - Trường Điều Cải"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    TIMEZONE: str = os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh") # Múi giờ chuẩn Việt Nam (GMT+7)

    # Storage Paths
    STORAGE_DIR: Path = BASE_DIR / "storage"
    CAPTURES_DIR: Path = BASE_DIR / "storage" / "captures"
    ANNOTATED_DIR: Path = BASE_DIR / "storage" / "annotated"
    REPORTS_DIR: Path = BASE_DIR / "storage" / "reports"
    BACKUPS_DIR: Path = BASE_DIR / "storage" / "backups"
    SAMPLES_DIR: Path = BASE_DIR / "dataset" / "samples"
    CLASSROOMS_MEDIA_DIR: Path = BASE_DIR / "dataset" / "classrooms_media"
    MODELS_DIR: Path = BASE_DIR / "models"

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'database' / 'attendance.db'}"

    # DVR / NVR Hardware Settings (Đầu ghi camera thực tế trường học)
    DVR_HOST: str = "192.168.10.200"
    DVR_PORT: int = 554
    DVR_HTTP_PORT: int = 80
    DVR_USER: str = "admin"
    DVR_PASSWORD: str = "Lhu@2025"
    DVR_PROTOCOL: str = "DAHUA" # Cấu trúc /cam/realmonitor?channel={ch}&subtype=0

    def get_dvr_rtsp_url(self, channel_id: int, subtype: int = 0) -> str:
        """Tạo chuỗi RTSP chuẩn mã hóa mật khẩu Lhu@2025 (ký tự @ thành %40)."""
        from urllib.parse import quote
        encoded_pwd = quote(self.DVR_PASSWORD)
        return f"rtsp://{self.DVR_USER}:{encoded_pwd}@{self.DVR_HOST}:{self.DVR_PORT}/cam/realmonitor?channel={channel_id}&subtype={subtype}"

    # Hardware & Scheduling
    SCHEDULE_TIME_HOUR: int = 6
    SCHEDULE_TIME_MINUTE: int = 45
    SCHEDULE_DAYS: str = "mon-sat" # Thứ 2 đến thứ 7

    # Relay LED Indicator
    RELAY_TYPE: str = "CAMERA_IO"  # "HTTP", "CAMERA_IO", "MOCK"
    RELAY_HOST: str = "192.168.10.200"
    RELAY_PORT: int = 80
    RELAY_DURATION_SECONDS: int = 180 # Bật đèn LED trong 3 phút (6h45 - 6h48)

    # AI Model Settings (Ultralytics YOLO26m + Classroom Head Specialized Model)
    YOLO_FAMILY: str = "YOLO26"
    YOLO_VARIANT: str = "26m"
    YOLO_MODEL_NAME: str = os.getenv("YOLO_MODEL_NAME", str(BASE_DIR / "models" / "yolo26m.pt"))  # Mô hình thế hệ mới YOLO26m
    HEAD_MODEL_NAME: str = os.getenv("HEAD_MODEL_NAME", str(BASE_DIR / "models" / "classroom_best.pt")) # Mô hình chuyên biệt nhận diện đầu lớp học
    YOLO_IMGSZ: int = int(os.getenv("YOLO_IMGSZ", "1280"))               # Kích thước phân giải AI quét 1280px chống mờ ảnh 2K
    AI_CONFIDENCE_THRESHOLD: float = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.24")) # Ngưỡng tin cậy tối ưu phát hiện học sinh cúi đầu & ngồi xa
    AI_IOU_THRESHOLD: float = float(os.getenv("AI_IOU_THRESHOLD", "0.48"))       # Ngưỡng IoU cho deduplication
    USE_IMAGE_ENHANCEMENT: bool = True  # Áp dụng CLAHE chống ngược sáng cửa sổ
    USE_TILED_INFERENCE: bool = True    # Bật thuật toán phân mảnh quét chi tiết đa tầng (SAHI)

    # Auth / Login
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-diemdanh-dieucai")
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "12"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_HOURS", "12")) * 60
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@truongdieucai.edu.vn")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin@2025")
    ADMIN_FULL_NAME: str = os.getenv("ADMIN_FULL_NAME", "Quản trị hệ thống")
    APP_PUBLIC_URL: str = os.getenv("APP_PUBLIC_URL", "http://localhost:8000")
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000",
    )

    # Email Reporting (Ban Giám Hiệu)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = os.getenv("SMTP_USER", "admin@truongdieucai.edu.vn")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    PRINCIPAL_EMAIL: str = os.getenv("PRINCIPAL_EMAIL", "hieutruong@truongdieucai.edu.vn")
    ENABLE_EMAIL_NOTIFICATION: bool = False

    # Zalo Notification Settings (Ban Giám Hiệu & Giáo Viên)
    ENABLE_ZALO_NOTIFICATION: bool = True
    ZALO_NOTIFICATION_TYPE: str = os.getenv("ZALO_NOTIFICATION_TYPE", "BOT_API") # "BOT_API" (Khuyến nghị), "OA_API" hoặc "WEBHOOK"
    # Zalo Bot Gateway (Khuyến nghị - Gửi tin nhắn / kết bạn batch, resolve SĐT -> UID)
    ZALO_BOT_API_BASE_URL: str = os.getenv("ZALO_BOT_API_BASE_URL", "http://localhost:3000/api/gateway/v1.0")
    ZALO_BOT_ID: str = os.getenv("ZALO_BOT_ID", "")
    ZALO_BOT_API_KEY: str = os.getenv("ZALO_BOT_API_KEY", "")
    ZALO_RECIPIENT_PHONES: str = os.getenv("ZALO_RECIPIENT_PHONES", "") # Phân cách bằng dấu phẩy (Legacy - chỉ dành cho nhóm Ban Giám Hiệu)
    ZALO_RECIPIENTS_JSON: str = os.getenv("ZALO_RECIPIENTS_JSON", "") # Danh sách người nhận theo vai trò: [{"phone":"...","role":"school|class","class_code":"LOP_10A1"}]
    # Zalo Official Account (Phương thức thay thế)
    ZALO_OA_ACCESS_TOKEN: str = os.getenv("ZALO_OA_ACCESS_TOKEN", "")
    ZALO_RECIPIENT_USER_ID: str = os.getenv("ZALO_RECIPIENT_USER_ID", "")
    # Zalo Webhook (Phương thức cũ - không khuyến nghị)
    ZALO_WEBHOOK_URL: str = os.getenv("ZALO_WEBHOOK_URL", "")

    # Notification Adjust & Rules Settings
    NOTIFICATION_SEND_CONDITION: str = "always" # "always" hoặc "has_absent"
    NOTIFICATION_ALERT_THRESHOLD_PERCENT: float = 10.0
    NOTIFICATION_ALERT_CLASS_ABSENT: int = 3
    SCAN_TIME_MORNING: str = "06:45"
    SCAN_TIME_AFTERNOON: str = "12:45"
    AUTO_SCAN_ENABLED: bool = True
    ZALO_SCHOOL_TEMPLATE: str = ""
    ZALO_CLASS_TEMPLATE: str = ""
    EMAIL_SUBJECT_TEMPLATE: str = ""
    EMAIL_BODY_TEMPLATE: str = ""

    # Data Retention Settings
    DATA_RETENTION_DAYS: int = 90
    DATA_AUTO_CLEANUP_ENABLED: bool = True
    DATA_CLEANUP_EXCEL_ENABLED: bool = True

    # Authentication & Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "truong-thpt-dieu-cai-secret-key-2026-attendance-ai-secured")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 giờ


settings = Settings()

# Đảm bảo các thư mục tồn tại
for folder in [
    settings.STORAGE_DIR,
    settings.CAPTURES_DIR,
    settings.ANNOTATED_DIR,
    settings.REPORTS_DIR,
    settings.SAMPLES_DIR,
    settings.CLASSROOMS_MEDIA_DIR,
    settings.MODELS_DIR,
    BASE_DIR / "database"
]:
    folder.mkdir(parents=True, exist_ok=True)

# Khôi phục cấu hình Zalo đã lưu runtime trước đó (giữ qua mỗi lần khởi động server)
from config.zalo_runtime_store import load_runtime_zalo
load_runtime_zalo(settings)

# Khôi phục cấu hình điều chỉnh thông báo đã lưu
from config.notification_settings_store import load_notification_settings
load_notification_settings(settings)
