# 🔧 Hướng Dẫn Khắc Phục Lỗi - THPT Điều Cải

## 🚀 Cách Chạy Hệ Thống

### ✅ Cách 1: Sử dụng run.bat (KHUYẾN NGHỊ)

```batch
run.bat
```

File này sẽ tự động:
1. Kiểm tra Python
2. Khởi tạo database
3. Chuẩn bị dữ liệu mẫu
4. Chạy server

### ✅ Cách 2: Manual Steps

```bash
# Bước 1: Kiểm tra Python
python --version
# Cần: Python 3.10+

# Bước 2: Cài dependencies (nếu chưa)
pip install -r requirements.txt

# Bước 3: Khởi tạo database
python -c "from database.db_session import init_db; init_db()"

# Bước 4: Chuẩn bị dữ liệu mẫu
python sample_extractor.py

# Bước 5: Chạy server
python app.py
```

### ✅ Cách 3: Uvicorn (Development)

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

---

## ❌ Các Lỗi Thường Gặp

### 1. **ModuleNotFoundError: No module named 'XXX'**

**Nguyên nhân:** Chưa cài đủ dependencies

**Giải pháp:**
```bash
pip install -r requirements.txt
```

Hoặc cài từng package thiếu:
```bash
pip install fastapi uvicorn opencv-python numpy pillow torch ultralytics
```

---

### 2. **ImportError: cannot import name 'settings'**

**Nguyên nhân:** File config/settings.py có lỗi hoặc thiếu

**Giải pháp:**
```bash
# Kiểm tra file có tồn tại không
dir config\settings.py

# Nếu thiếu, kiểm tra lại cấu trúc project
```

---

### 3. **Database locked / OperationalError**

**Nguyên nhân:** SQLite database đang được sử dụng bởi process khác

**Giải pháp:**
```bash
# Đóng tất cả Python processes
taskkill /F /IM python.exe

# Xóa file lock (nếu có)
del database\attendance.db-journal

# Chạy lại
python app.py
```

---

### 4. **Port 8000 already in use**

**Nguyên nhân:** Port đang bị chiếm bởi process khác

**Giải pháp Option 1:**
```bash
# Tìm process đang dùng port 8000
netstat -ano | findstr :8000

# Kill process đó (thay PID bằng số thực tế)
taskkill /F /PID <PID>
```

**Giải pháp Option 2:** Đổi port trong `config/settings.py`:
```python
PORT = 8001  # Hoặc port khác
```

---

### 5. **No module named 'cv2' (OpenCV)**

**Nguyên nhân:** OpenCV chưa cài hoặc cài sai

**Giải pháp:**
```bash
pip uninstall opencv-python opencv-python-headless
pip install opencv-python
```

---

### 6. **torch/ultralytics not found**

**Nguyên nhân:** PyTorch hoặc YOLO chưa cài

**Giải pháp:**
```bash
# Cài PyTorch (CPU version)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Cài Ultralytics
pip install ultralytics
```

---

### 7. **Template Not Found Error**

**Nguyên nhân:** Đường dẫn templates sai

**Giải pháp:**
Kiểm tra cấu trúc thư mục:
```
web/
  templates/
    dashboard.html
    cameras.html
    roi_config.html
    reports.html
    modal-demo.html  ← File mới
  static/
    css/
      dashboard.css
      modal-system.css  ← File mới
    js/
```

---

### 8. **CSS/JS files not loading**

**Nguyên nhân:** Static files mount sai

**Giải pháo:**
```python
# Kiểm tra trong app.py có dòng này:
app.mount("/static", StaticFiles(directory="web/static"), name="static")
```

Truy cập thử:
- http://localhost:8000/static/css/dashboard.css
- http://localhost:8000/static/css/modal-system.css

---

### 9. **modal-demo page not found (404)**

**Nguyên nhân:** Route chưa được thêm vào app.py

**Giải pháp:**
Kiểm tra trong `app.py` có đoạn này:
```python
@app.get("/modal-demo", response_class=HTMLResponse)
async def modal_demo_page(request: Request):
    """Trang Demo Modal System"""
    return templates.TemplateResponse(
        request=request,
        name="modal-demo.html",
        context={"app_name": settings.APP_NAME}
    )
```

---

### 10. **Permission Denied / Access Denied**

**Nguyên nhân:** Windows Defender hoặc antivirus đang block

**Giải pháp:**
1. Tắt tạm Windows Defender Real-time Protection
2. Thêm folder dự án vào exclusion list
3. Chạy CMD/PowerShell as Administrator

---

## 🔍 Kiểm Tra Hệ Thống

### Quick Health Check

Chạy script này để kiểm tra:

```bash
python test_server.py
```

Hoặc manual check:

```bash
# 1. Python version
python --version

# 2. Các packages quan trọng
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
python -c "import uvicorn; print('Uvicorn:', uvicorn.__version__)"
python -c "import cv2; print('OpenCV:', cv2.__version__)"
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import ultralytics; print('YOLO:', ultralytics.__version__)"

# 3. Database
python -c "from database.db_session import init_db; init_db(); print('Database OK')"

# 4. Import app
python -c "from app import app; print('App OK')"
```

---

## 📋 Checklist Trước Khi Chạy

- [ ] Python 3.10+ đã cài
- [ ] Đã chạy `pip install -r requirements.txt`
- [ ] File `database/attendance.db` tồn tại (hoặc sẽ tự tạo)
- [ ] Folder `web/templates/` có đầy đủ file HTML
- [ ] Folder `web/static/css/` có `dashboard.css` và `modal-system.css`
- [ ] Port 8000 không bị chiếm
- [ ] Không có Python process nào khác đang chạy

---

## 🎯 Test Modal System

Sau khi server chạy thành công:

1. **Mở trình duyệt:**
   ```
   http://localhost:8000
   ```

2. **Test các trang:**
   - Dashboard: http://localhost:8000/
   - Cameras: http://localhost:8000/cameras
   - ROI Config: http://localhost:8000/roi-config
   - Reports: http://localhost:8000/reports
   - **Modal Demo** ← MỚI: http://localhost:8000/modal-demo

3. **Test modal system:**
   - Click vào các nút demo
   - Test responsive (F12 → Device toolbar)
   - Test keyboard (ESC, Tab)
   - Test backdrop click

---

## 🆘 Vẫn Không Chạy Được?

### Debug Mode

Thêm log chi tiết:

```python
# Trong app.py, thêm:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Verbose Mode

Chạy với uvicorn verbose:
```bash
uvicorn app:app --reload --log-level debug
```

### Check Logs

Xem logs trong folder `logs/`:
```bash
dir logs
type logs\app.log
```

---

## 📞 Thông Tin Hệ Thống

**Project:** THPT Điều Cải - Attendance System  
**Framework:** FastAPI + Uvicorn  
**Database:** SQLite (SQLAlchemy)  
**AI:** YOLOv8 (Ultralytics)  
**Frontend:** Jinja2 + Vanilla JS + CSS  

**New Features:**
- ✅ Modal System Component Library
- ✅ Responsive Design
- ✅ Professional UI/UX
- ✅ Demo Page

---

## ✅ Success Indicators

Khi hệ thống chạy thành công, bạn sẽ thấy:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [PID]
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
=== ĐANG KHỞI ĐỘNG HỆ THỐNG ĐIỂM DANH AI ĐIỀU CẢI ===
INFO:     Application startup complete.
```

Lúc này bạn có thể truy cập:
- http://localhost:8000 → Dashboard
- http://localhost:8000/modal-demo → Modal System Demo

---

**Last Updated:** September 19, 2026  
**Version:** 2.0 with Modal System
