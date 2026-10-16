"""
Backend Core Package - Động cơ nghiệp vụ cốt lõi, AI YOLO và giao tiếp thiết bị Camera
"""
from backend.app.core.timezone_utils import get_now, get_today, get_today_str, get_current_time_str, get_app_timezone
from backend.app.core.image_enhancer import ImageEnhancer, image_enhancer
from backend.app.core.roi_manager import ROIManager, roi_manager
from backend.app.core.detector import StudentDetector, detector
from backend.app.core.relay_service import RelayService, relay_service
from backend.app.core.rtsp_client import RTSPCameraClient, rtsp_client, is_valid_frame, has_vertical_smear_artifacts
from backend.app.core.camera_source_manager import CameraSourceManager, camera_source_manager
from backend.app.core.attendance_engine import AttendanceEngine, attendance_engine

__all__ = [
    "get_now",
    "get_today",
    "get_today_str",
    "get_current_time_str",
    "get_app_timezone",
    "ImageEnhancer",
    "image_enhancer",
    "ROIManager",
    "roi_manager",
    "StudentDetector",
    "detector",
    "RelayService",
    "relay_service",
    "RTSPCameraClient",
    "rtsp_client",
    "is_valid_frame",
    "has_vertical_smear_artifacts",
    "CameraSourceManager",
    "camera_source_manager",
    "AttendanceEngine",
    "attendance_engine",
]
