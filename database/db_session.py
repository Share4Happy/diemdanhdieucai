import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config.settings import settings
from config.logging_config import logger
from database.models import Base, Classroom, ROIPolygon

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Khởi tạo các bảng và tạo sẵn dữ liệu mẫu cho 30 lớp học nếu chưa có."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        count = db.query(Classroom).count()
        if count == 0:
            logger.info("Khởi tạo danh sách 30 lớp học và cấu hình ROI mặc định...")
            # Danh sách 30 lớp từ khối 10 đến khối 12 của trường
            classes_info = [
                # Khối 10 (10 lớp)
                ("10A1", 42), ("10A2", 40), ("10A3", 41), ("10A4", 43), ("10A5", 39),
                ("10A6", 42), ("10A7", 40), ("10A8", 41), ("10A9", 40), ("10A10", 42),
                # Khối 11 (10 lớp)
                ("11A1", 44), ("11A2", 43), ("11A3", 42), ("11A4", 40), ("11A5", 41),
                ("11A6", 42), ("11A7", 39), ("11A8", 41), ("11A9", 40), ("11A10", 43),
                # Khối 12 (10 lớp)
                ("12A1", 45), ("12A2", 44), ("12A3", 42), ("12A4", 43), ("12A5", 41),
                ("12A6", 40), ("12A7", 42), ("12A8", 41), ("12A9", 40), ("12A10", 42)
            ]

            # Đa giác mặc định (chuẩn hóa 1920x1080)
            # Red Zone: Vùng bàn học sinh từ giữa phòng đến cuối phòng
            default_red_zone = [
                [200, 300],
                [1720, 300],
                [1850, 1050],
                [80, 1050]
            ]
            # Green Zone: Vùng bục giảng giáo viên phía trước góc trái/giữa
            default_green_zone = [
                [350, 80],
                [900, 80],
                [950, 280],
                [300, 280]
            ]

            for idx, (cname, standard_count) in enumerate(classes_info, 1):
                cls = Classroom(
                    code=f"LOP_{cname}",
                    name=f"Lớp {cname}",
                    room_number=f"Phòng {100 + idx}",
                    standard_count=standard_count,
                    rtsp_url=settings.get_dvr_rtsp_url(idx, subtype=0),
                    relay_ip=settings.DVR_HOST,
                    is_active=True
                )
                db.add(cls)
                db.flush() # Lấy cls.id

                roi = ROIPolygon(
                    classroom_id=cls.id,
                    red_zone_json=json.dumps(default_red_zone),
                    green_zone_json=json.dumps(default_green_zone),
                    image_width=1920,
                    image_height=1080
                )
                db.add(roi)

            db.commit()
            logger.info("Đã khởi tạo thành công 30 lớp học và cấu hình ROI!")
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi khởi tạo DB: {e}")
    finally:
        db.close()
