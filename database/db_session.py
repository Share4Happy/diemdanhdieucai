import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from config.settings import settings
from config.logging_config import logger
from database.models import Base, Classroom, ROIPolygon, NVRDevice, User

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
    
    # Safe migration for existing SQLite database
    try:
        with engine.connect() as conn:
            columns_res = conn.execute(text("PRAGMA table_info(classrooms)")).fetchall()
            existing_cols = [row[1] for row in columns_res]
            if "nvr_id" not in existing_cols:
                conn.execute(text("ALTER TABLE classrooms ADD COLUMN nvr_id INTEGER"))
            if "channel_number" not in existing_cols:
                conn.execute(text("ALTER TABLE classrooms ADD COLUMN channel_number INTEGER"))
            conn.commit()
    except Exception as e:
        logger.debug(f"SQLite migration notice: {e}")

    db = SessionLocal()
    try:
        classes_info = [
            ("10A1", 42), ("10A2", 40), ("10A3", 41), ("10A4", 43), ("10A5", 39),
            ("10A6", 42), ("10A7", 40), ("10A8", 41), ("10A9", 40), ("10A10", 42),
            ("11A1", 44), ("11A2", 43), ("11A3", 42), ("11A4", 40), ("11A5", 41),
            ("11A6", 42), ("11A7", 39), ("11A8", 41), ("11A9", 40), ("11A10", 43),
            ("12A1", 45), ("12A2", 44), ("12A3", 42), ("12A4", 43), ("12A5", 41),
            ("12A6", 40), ("12A7", 42), ("12A8", 41), ("12A9", 40), ("12A10", 42)
        ]
        default_red_zone = [
            [200, 300], [1720, 300], [1850, 1050], [80, 1050]
        ]
        default_green_zone = [
            [350, 80], [900, 80], [950, 280], [300, 280]
        ]

        created_count = 0
        for idx, (cname, standard_count) in enumerate(classes_info, 1):
            clean_code = f"LOP_{cname}"
            existing = db.query(Classroom).filter(Classroom.code == clean_code).first()
            if not existing:
                cls = Classroom(
                    code=clean_code,
                    name=f"Lớp {cname}",
                    room_number=f"Phòng {100 + idx}",
                    standard_count=standard_count,
                    rtsp_url=settings.get_dvr_rtsp_url(idx, subtype=0),
                    relay_ip=settings.DVR_HOST,
                    is_active=True
                )
                db.add(cls)
                db.flush()

                roi = ROIPolygon(
                    classroom_id=cls.id,
                    red_zone_json=json.dumps(default_red_zone),
                    green_zone_json=json.dumps(default_green_zone),
                    image_width=1920,
                    image_height=1080
                )
                db.add(roi)
                created_count += 1

        if created_count > 0:
            db.commit()
            logger.info(f"Đã bổ sung thành công {created_count} lớp học chuẩn THPT Điều Cải!")

        # Khởi tạo tài khoản quản trị và giáo viên mặc định nếu chưa có
        user_count = db.query(User).count()
        if user_count == 0:
            from core.security import get_password_hash
            default_admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="Quản Trị Viên Hệ Thống",
                role="admin",
                email="admin@truongdieucai.edu.vn",
                is_active=True
            )
            default_teacher = User(
                username="giaovien",
                hashed_password=get_password_hash("giaovien123"),
                full_name="Giáo Viên / Giám Thị",
                role="teacher",
                email="giaovien@truongdieucai.edu.vn",
                is_active=True
            )
            db.add(default_admin)
            db.add(default_teacher)
            db.commit()
            logger.info("Đã tạo thành công tài khoản mặc định: admin (admin123) và giaovien (giaovien123)")
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi khởi tạo DB: {e}")
    finally:
        db.close()

