# =========================================================================
# BACKEND DOCKERFILE - HỆ THỐNG ĐIỂM DANH AI THPT ĐIỀU CẢI
# Chạy FastAPI REST API, Ultralytics YOLO26m, OpenCV RTSP Camera Worker
# =========================================================================

FROM python:3.10-slim-bookworm

# Ngăn Python tạo bytecode rác và buffer console logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Ho_Chi_Minh

WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết cho OpenCV, PyTorch, FFmpeg RTSP Video decode
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt dependencies Python (cache layer)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn dự án
COPY . /app/

# Khởi tạo các thư mục lưu trữ cần thiết cho runtime
RUN mkdir -p /app/storage/captures \
             /app/storage/annotated \
             /app/storage/reports \
             /app/storage/backups \
             /app/database \
             /app/logs \
             /app/models

# Cổng FastAPI Backend
EXPOSE 8000

# Kiểm tra trạng thái sống của dịch vụ Backend qua endpoint /api/health
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Lệnh khởi chạy server sản xuất Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
