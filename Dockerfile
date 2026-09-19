FROM python:3.11-slim

# Thiết lập múi giờ Việt Nam
ENV TZ=Asia/Ho_Chi_Minh
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cài đặt các thư viện hệ thống cần thiết cho OpenCV và hình ảnh
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . .

# Mở port 8000 cho FastAPI Web UI
EXPOSE 8000

# Khởi chạy ứng dụng
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
