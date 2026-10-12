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
            ("12A1", 48, "Phòng 1"), ("12A2", 45, "Phòng 2"), ("12A3", 41, "Phòng 3"),
            ("12A4", 44, "Phòng 4"), ("12A5", 42, "Phòng 5"), ("12A6", 41, "Phòng 6"),
            ("12A7", 44, "Phòng 7"), ("12A8", 44, "Phòng 8"), ("12A9", 39, "Phòng 9"),
            ("12A10", 40, "Phòng 10"),
            ("11A1", 43, "Phòng 11"), ("11A2", 43, "Phòng 12"), ("11A3", 31, "Phòng 13"),
            ("11A4", 35, "Phòng 14"), ("11A5", 45, "Phòng 15"), ("11A6", 45, "Phòng 16"),
            ("11A7", 34, "Phòng 17"), ("11A8", 30, "Phòng 18"), ("11A9", 36, "Phòng 19"),
            ("11A10", 35, "Phòng 20"),
            ("10A1", 44, "Phòng 21"), ("10A6", 48, "Phòng 22"), ("10A2", 40, "Phòng 23"),
            ("10A3", 38, "Phòng 24"), ("10A4", 45, "Phòng 25"), ("10A5", 44, "Phòng 26"),
            ("10A7", 46, "Phòng 27"), ("10A8", 35, "Phòng 28"), ("10A9", 37, "Phòng 29"),
            ("10A10", 47, "Phòng 30")
        ]
        default_green_zone = [
            [200, 300], [1720, 300], [1850, 1050], [80, 1050]
        ]
        default_red_zone = []

        created_count = 0
        for idx, (cname, standard_count, room_name) in enumerate(classes_info, 1):
            clean_code = f"LOP_{cname}"
            # Kênh 17 và 29 dùng sub-stream (subtype=1) chống lỗi vỡ gói / nhiễu decoder H.265
            sub = 1 if idx in (17, 29) else 0
            stream_url = settings.get_dvr_rtsp_url(idx, subtype=sub)

            existing = db.query(Classroom).filter(Classroom.code == clean_code).first()
            if not existing:
                cls = Classroom(
                    code=clean_code,
                    name=f"Lớp {cname}",
                    room_number=room_name,
                    channel_number=idx,
                    standard_count=standard_count,
                    rtsp_url=stream_url,
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
            else:
                existing.channel_number = idx
                existing.room_number = room_name
                existing.rtsp_url = stream_url
                existing.is_active = True

        db.commit()
        if created_count > 0:
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
    if "sqlite" in settings.DATABASE_URL:
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

