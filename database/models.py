from datetime import datetime
import json
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class NVRDevice(Base):
    __tablename__ = "nvr_devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), default="Đầu ghi NVR")              # e.g. "Đầu ghi NVR Điều Cải 30 Kênh"
    ip_address = Column(String(100), nullable=False)                # e.g. "192.168.10.200"
    rtsp_port = Column(Integer, default=554)
    http_port = Column(Integer, default=80)
    username = Column(String(100), default="admin")
    password = Column(String(100), default="")
    brand = Column(String(50), default="DAHUA")                    # "DAHUA", "HIKVISION", "UNIVIEW", "CUSTOM"
    channels_count = Column(Integer, default=30)
    custom_url_pattern = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    classrooms = relationship("Classroom", back_populates="nvr")

class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False) # e.g. "LOP_10A1"
    name = Column(String(100), nullable=False)                         # e.g. "Lớp 10A1"
    room_number = Column(String(50), default="")                       # e.g. "Phòng 201"
    standard_count = Column(Integer, default=40, nullable=False)       # Sĩ số chuẩn
    rtsp_url = Column(String(255), default="")                         # Luồng RTSP
    relay_ip = Column(String(100), default="")                         # IP Relay đèn LED
    is_active = Column(Boolean, default=True)
    nvr_id = Column(Integer, ForeignKey("nvr_devices.id", ondelete="SET NULL"), nullable=True)
    channel_number = Column(Integer, nullable=True)

    nvr = relationship("NVRDevice", back_populates="classrooms")
    roi = relationship("ROIPolygon", back_populates="classroom", uselist=False, cascade="all, delete-orphan")
    attendance_details = relationship("AttendanceDetail", back_populates="classroom")

class ROIPolygon(Base):
    __tablename__ = "roi_polygons"

    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), unique=True, nullable=False)
    # Tọa độ đa giác lưu dạng JSON [[x1, y1], [x2, y2], ...] tỉ lệ chuẩn hoặc pixel
    red_zone_json = Column(Text, default="[]")   # Bàn học sinh (Cần đếm)
    green_zone_json = Column(Text, default="[]") # Bục giảng giáo viên (Bỏ qua)
    image_width = Column(Integer, default=1920)
    image_height = Column(Integer, default=1080)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    classroom = relationship("Classroom", back_populates="roi")

    @property
    def red_zone(self):
        try:
            return json.loads(self.red_zone_json) if self.red_zone_json else []
        except Exception:
            return []

    @red_zone.setter
    def red_zone(self, points):
        self.red_zone_json = json.dumps(points)

    @property
    def green_zone(self):
        try:
            return json.loads(self.green_zone_json) if self.green_zone_json else []
        except Exception:
            return []

    @green_zone.setter
    def green_zone(self, points):
        self.green_zone_json = json.dumps(points)

class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_code = Column(String(50), unique=True, index=True) # e.g. "SESSION_20260918_0645"
    scan_date = Column(String(20), index=True)                 # "2026-09-18"
    scan_time = Column(String(20))                             # "06:45:00"
    total_classes = Column(Integer, default=30)
    total_standard = Column(Integer, default=0)
    total_present = Column(Integer, default=0)
    total_absent = Column(Integer, default=0)
    excel_report_path = Column(String(255), default="")
    status = Column(String(50), default="COMPLETED")           # "PROCESSING", "COMPLETED", "FAILED"
    created_at = Column(DateTime, default=datetime.utcnow)

    details = relationship("AttendanceDetail", back_populates="session", cascade="all, delete-orphan")

class AttendanceDetail(Base):
    __tablename__ = "attendance_details"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    standard_count = Column(Integer, default=0)
    present_count = Column(Integer, default=0)
    absent_count = Column(Integer, default=0)
    raw_image_path = Column(String(255), default="")
    annotated_image_path = Column(String(255), default="")
    confidence_avg = Column(Float, default=0.0)
    notes = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("AttendanceSession", back_populates="details")
    classroom = relationship("Classroom", back_populates="attendance_details")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(150), default="")
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="staff", nullable=False)  # "admin" | "staff"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reset_tokens")
