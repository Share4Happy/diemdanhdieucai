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

def seed_default_classes(db=None):
    """
    Bổ sung danh sách 30 lớp học chuẩn của trường THPT Điều Cải.
    Chỉ thực hiện khi người dùng yêu cầu chủ động (VD: Khôi phục mặc định).
    """
    close_at_end = False
    if db is None:
        db = SessionLocal()
        close_at_end = True
    try:
        classes_info = [
            ("10A1", 42), ("10A2", 40), ("10A3", 41), ("10A4", 43), ("10A5", 39),
            ("10A6", 42), ("10A7", 40), ("10A8", 41), ("10A9", 40), ("10A10", 42),
            ("11A1", 44), ("11A2", 43), ("11A3", 42), ("11A4", 40), ("11A5", 41),
            ("11A6", 42), ("11A7", 39), ("11A8", 41), ("11A9", 40), ("11A10", 43),
            ("12A1", 45), ("12A2", 44), ("12A3", 42), ("12A4", 43), ("12A5", 41),
            ("12A6", 40), ("12A7", 42), ("12A8", 41), ("12A9", 40), ("12A10", 42)
        ]
        default_green_zone = [
            [200, 300], [1720, 300], [1850, 1050], [80, 1050]
        ]
        default_red_zone = []

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

        from services.auth_service import seed_admin_if_empty
        seed_admin_if_empty(db)
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi khi seed lớp học: {e}")
    finally:
        if close_at_end:
            db.close()

def init_db(force_seed_classes: bool = False):
    """
    Khởi tạo cấu trúc các bảng và tài khoản mặc định.
    KHÔNG tự động thêm 30 camera khi khởi động để tôn trọng danh sách camera hiện có của người dùng.
    """
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
            
            # Migration an toàn bảng users nếu có phiên bản cũ dùng username/hashed_password
            user_cols_res = conn.execute(text("PRAGMA table_info(users)")).fetchall()
            user_existing_cols = [row[1] for row in user_cols_res]
            if user_cols_res and "password_hash" not in user_existing_cols:
                logger.info("Phát hiện bảng users cũ, tự động di trú sang bảng users chuẩn JWT bcrypt...")
                conn.execute(text("DROP TABLE IF EXISTS password_reset_tokens"))
                conn.execute(text("DROP TABLE IF EXISTS users"))
            conn.commit()
    except Exception as e:
        logger.debug(f"SQLite migration notice: {e}")

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Chỉ seed 30 camera nếu có yêu cầu cưỡng ép (người dùng bấm Khôi phục mặc định)
        if force_seed_classes:
            seed_default_classes(db)

        # Khởi tạo tài khoản quản trị mặc định theo cấu hình auth_service
        from services.auth_service import seed_admin_if_empty
        seed_admin_if_empty(db)
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi khởi tạo DB: {e}")
    finally:
        db.close()

