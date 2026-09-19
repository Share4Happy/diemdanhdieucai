from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config.settings import settings
from config.logging_config import logger
from core.attendance_engine import attendance_engine

class AttendanceScheduler:
    """
    Tiến trình chạy ngầm (Cronjob / Task Scheduler):
    Đúng 6h45 sáng hàng ngày (từ Thứ 2 đến Thứ 7), tự động kích hoạt chu trình điểm danh.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False

    def start(self):
        if self.is_running:
            return

        # Thiết lập lịch chạy lúc 06:45 sáng
        trigger = CronTrigger(
            hour=settings.SCHEDULE_TIME_HOUR,
            minute=settings.SCHEDULE_TIME_MINUTE,
            day_of_week=settings.SCHEDULE_DAYS
        )

        self.scheduler.add_job(
            func=self.run_scheduled_job,
            trigger=trigger,
            id="daily_attendance_job",
            name="Quét Điểm Danh Tự Động 30 Lớp",
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True
        logger.info(
            f"Đã khởi động bộ lập lịch điểm danh tự động: "
            f"Chạy lúc {settings.SCHEDULE_TIME_HOUR:02d}:{settings.SCHEDULE_TIME_MINUTE:02d} ({settings.SCHEDULE_DAYS})"
        )

    def run_scheduled_job(self):
        logger.info("=== [CRON 06:45 AM] TỰ ĐỘNG KÍCH HOẠT CHU TRÌNH ĐIỂM DANH ===")
        try:
            res = attendance_engine.run_daily_attendance(trigger_led=True)
            logger.info(f"Hoàn thành tác vụ lập lịch: {res.get('session_code')}")
        except Exception as e:
            logger.error(f"Lỗi khi thực thi tác vụ lập lịch: {e}")

    def trigger_now(self):
        """Kích hoạt chạy ngay lập tức (phục vụ kiểm thử hoặc bấm thủ công từ Dashboard)."""
        logger.info("Người dùng kích hoạt chạy điểm danh thủ công...")
        return attendance_engine.run_daily_attendance(trigger_led=True)

    def shutdown(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Đã dừng bộ lập lịch.")

attendance_scheduler = AttendanceScheduler()
