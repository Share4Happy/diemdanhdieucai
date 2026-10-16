"""
=============================================================================
PROGRESS TRACKER SERVICE - THEO DÕI TIẾN TRÌNH THỜI GIAN THỰC
Hệ Thống Điểm Danh AI Camera THPT Điều Cải
=============================================================================
Cung cấp trạng thái tiến trình (progress state) thời gian thực cho:
1. Quét Điểm Danh Toàn Trường (Chụp ảnh NVR -> AI YOLO -> Lưu CSDL/Báo Cáo)
2. Chụp Lại Đồng Loạt 30 Camera NVR
3. Chụp Lại Camera Đơn Lẻ Phòng Học
=============================================================================
"""

import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class ProgressTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            "is_running": False,
            "action": "IDLE",            # "ATTENDANCE_SCAN" | "CAPTURE_ALL" | "CAPTURE_SINGLE"
            "title": "Chưa có tác vụ nào",
            "step": 0,
            "total_steps": 3,
            "step_title": "Hệ thống đang rảnh",
            "current": 0,
            "total": 0,
            "percent": 0,
            "current_item": "",
            "status": "idle",            # "idle" | "running" | "success" | "error"
            "message": "",
            "logs": [],
            "result": None,
            "started_at": 0.0,
            "elapsed_seconds": 0.0,
        }

    def start(self, action: str, title: str, total_steps: int = 3, total_items: int = 30) -> None:
        with self._lock:
            now = time.time()
            self._state = {
                "is_running": True,
                "action": action,
                "title": title,
                "step": 1,
                "total_steps": total_steps,
                "step_title": "Bắt đầu quy trình...",
                "current": 0,
                "total": total_items,
                "percent": 5,
                "current_item": "Khởi tạo kết nối...",
                "status": "running",
                "message": title,
                "logs": [
                    {
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "text": f"Bắt đầu: {title}",
                        "type": "info"
                    }
                ],
                "result": None,
                "started_at": now,
                "elapsed_seconds": 0.0,
            }

    def update(
        self,
        step: Optional[int] = None,
        step_title: Optional[str] = None,
        current: Optional[int] = None,
        total: Optional[int] = None,
        current_item: Optional[str] = None,
        percent: Optional[int] = None,
        log_text: Optional[str] = None,
        log_type: str = "info"
    ) -> None:
        with self._lock:
            if not self._state["is_running"]:
                return

            if step is not None:
                self._state["step"] = step
            if step_title is not None:
                self._state["step_title"] = step_title
            if current is not None:
                self._state["current"] = current
            if total is not None:
                self._state["total"] = total
            if current_item is not None:
                self._state["current_item"] = current_item

            if percent is not None:
                self._state["percent"] = min(100, max(0, percent))
            else:
                cur_step = self._state["step"]
                total_s = max(1, self._state["total_steps"])
                step_weight = 100.0 / total_s
                base_pct = (cur_step - 1) * step_weight
                item_pct = 0.0
                if self._state["total"] > 0:
                    item_pct = (self._state["current"] / self._state["total"]) * step_weight
                calc = int(base_pct + item_pct)
                self._state["percent"] = min(98, max(5, calc))

            if log_text:
                self._state["logs"].append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "text": log_text,
                    "type": log_type
                })
                if len(self._state["logs"]) > 60:
                    self._state["logs"] = self._state["logs"][-60:]

            if self._state["started_at"] > 0:
                self._state["elapsed_seconds"] = round(time.time() - self._state["started_at"], 1)

    def finish(self, success: bool, message: str, result: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._state["is_running"] = False
            self._state["status"] = "success" if success else "error"
            self._state["message"] = message
            self._state["percent"] = 100 if success else self._state["percent"]
            self._state["result"] = result or {}
            if self._state["started_at"] > 0:
                self._state["elapsed_seconds"] = round(time.time() - self._state["started_at"], 1)

            self._state["logs"].append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "text": f"✓ {message}" if success else f"⚠️ {message}",
                "type": "success" if success else "error"
            })

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            st = dict(self._state)
            if st["is_running"] and st["started_at"] > 0:
                st["elapsed_seconds"] = round(time.time() - st["started_at"], 1)
            # Bản sao logs để tránh race condition
            st["logs"] = list(st["logs"])
            return st


progress_tracker = ProgressTracker()
