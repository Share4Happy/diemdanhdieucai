
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

    def update_schedule(self, morning_time: str = "06:45", afternoon_time: str = "12:45", enabled: bool = True):
        """Cập nhật giờ quét tự động theo cấu hình điều chỉnh."""
        if not self.is_running:
            return

        if not enabled:
            for jid in ["daily_attendance_job", "afternoon_attendance_job"]:
                try:
                    self.scheduler.remove_job(jid)
                except Exception:
                    pass
            logger.info("Đã tạm dừng các tác vụ quét tự động theo lịch.")
            return

        # Ca sáng
        try:
            m_parts = (morning_time or "06:45").split(":")
            m_h, m_m = int(m_parts[0]), int(m_parts[1])
            trigger_m = CronTrigger(hour=m_h, minute=m_m, day_of_week=settings.SCHEDULE_DAYS)
            self.scheduler.add_job(
                func=self.run_scheduled_job,
                trigger=trigger_m,
                id="daily_attendance_job",
                name="Quét Điểm Danh Ca Sáng",
                replace_existing=True
            )
            logger.info(f"Đã cập nhật lịch quét ca sáng: {m_h:02d}:{m_m:02d} ({settings.SCHEDULE_DAYS})")
        except Exception as e:
            logger.warning(f"Lỗi cập nhật lịch ca sáng: {e}")

        # Ca chiều
        try:
            a_parts = (afternoon_time or "12:45").split(":")
            a_h, a_m = int(a_parts[0]), int(a_parts[1])
            trigger_a = CronTrigger(hour=a_h, minute=a_m, day_of_week=settings.SCHEDULE_DAYS)
            self.scheduler.add_job(
                func=self.run_scheduled_job,
                trigger=trigger_a,
                id="afternoon_attendance_job",
                name="Quét Điểm Danh Ca Chiều",
                replace_existing=True
            )
            logger.info(f"Đã cập nhật lịch quét ca chiều: {a_h:02d}:{a_m:02d} ({settings.SCHEDULE_DAYS})")
        except Exception as e:
            logger.warning(f"Lỗi cập nhật lịch ca chiều: {e}")

    def shutdown(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Đã dừng bộ lập lịch.")

attendance_scheduler = AttendanceScheduler()
