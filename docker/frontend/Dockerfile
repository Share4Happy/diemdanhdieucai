# =========================================================================
# FRONTEND DOCKERFILE - HỆ THỐNG ĐIỂM DANH AI THPT ĐIỀU CẢI
# Nginx Alpine phục vụ giao diện tĩnh và Reverse Proxy API
# =========================================================================

FROM nginx:alpine

# Xóa cấu hình mặc định của Nginx
RUN rm -rf /etc/nginx/conf.d/default.conf

# Copy cấu hình tùy chỉnh của THPT Điều Cải
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy toàn bộ mã nguồn giao diện Frontend
COPY frontend/ /usr/share/nginx/html/

# Expose cổng 80 (được map sang 3000 ở docker-compose)
EXPOSE 80

# Chạy Nginx ở chế độ foreground
CMD ["nginx", "-g", "daemon off;"]
