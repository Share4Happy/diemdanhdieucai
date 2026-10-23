import json
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, scoped_session
from config.settings import settings
from config.logging_config import logger
from database.models import Base, Classroom, ROIPolygon, NVRDevice, User, DEFAULT_30_CLASSES

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in settings.DATABASE_URL else {}
)

# Kích hoạt WAL mode và busy_timeout cho SQLite chống lỗi 'database is locked'
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

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
        classes_info = DEFAULT_30_CLASSES
        default_green_zone = []
        default_red_zone = []

        created_count = 0
        for idx, (cname, standard_count, room_name) in enumerate(classes_info, 1):
            clean_code = f"LOP_{cname}"
            sub = 0
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
                if "stream_type" not in existing_cols:
                    conn.execute(text("ALTER TABLE classrooms ADD COLUMN stream_type VARCHAR(20) DEFAULT 'main'"))
                if "codec" not in existing_cols:
                    conn.execute(text("ALTER TABLE classrooms ADD COLUMN codec VARCHAR(20) DEFAULT 'H.264'"))
                if "conf_threshold" not in existing_cols:
                    conn.execute(text("ALTER TABLE classrooms ADD COLUMN conf_threshold FLOAT"))
                if "laplacian_threshold" not in existing_cols:
                    conn.execute(text("ALTER TABLE classrooms ADD COLUMN laplacian_threshold FLOAT"))
                
                # Migration bảng attendance_details
                att_cols_res = conn.execute(text("PRAGMA table_info(attendance_details)")).fetchall()
                att_existing_cols = [row[1] for row in att_cols_res]
                if att_cols_res:
                    if "status" not in att_existing_cols:
                        conn.execute(text("ALTER TABLE attendance_details ADD COLUMN status VARCHAR(30) DEFAULT 'OK'"))
                    if "is_manual_override" not in att_existing_cols:
                        conn.execute(text("ALTER TABLE attendance_details ADD COLUMN is_manual_override BOOLEAN DEFAULT 0"))
                    if "override_by" not in att_existing_cols:
                        conn.execute(text("ALTER TABLE attendance_details ADD COLUMN override_by VARCHAR(100)"))
                    if "override_reason" not in att_existing_cols:
                        conn.execute(text("ALTER TABLE attendance_details ADD COLUMN override_reason TEXT"))
                    if "override_at" not in att_existing_cols:
                        conn.execute(text("ALTER TABLE attendance_details ADD COLUMN override_at DATETIME"))
                    # Tạo index cho session_id và classroom_id để tối ưu truy vấn O(1)
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_attendance_details_session_id ON attendance_details(session_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_attendance_details_classroom_id ON attendance_details(classroom_id)"))

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

