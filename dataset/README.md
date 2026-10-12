# Hướng dẫn nạp Dataset mới & Huấn luyện AI - THPT Điều Cải

Thư mục này hiện đã được dọn sạch toàn bộ dữ liệu cũ (~5.5 GB). Dưới đây là hướng dẫn chuẩn bị dữ liệu mới:

---

## 1. Cấu trúc thư mục dữ liệu chuẩn YOLO

Khi tải dữ liệu từ Roboflow, Label Studio hoặc gán nhãn thủ công, bạn hãy giải nén vào thư mục `dataset/` theo cấu trúc sau:

```text
dataset/
│
├── ten_dataset_moi/
│   ├── train/
│   │   ├── images/        <-- Chứa các file ảnh huấn luyện (.jpg, .png)
│   │   └── labels/        <-- Chứa các file nhãn (.txt tọa độ YOLO: 0 x y w h)
│   ├── valid/
│   │   ├── images/        <-- Chứa các file ảnh kiểm định
│   │   └── labels/        <-- Chứa các file nhãn kiểm định
│   └── test/ (nếu có)
│       ├── images/
│       └── labels/
│
└── data_template.yaml      <-- File mẫu cấu hình huấn luyện
```

---

## 2. Cấu hình file YAML

1. Sao chép hoặc đổi tên `data_template.yaml` thành `data.yaml` (hoặc tên tùy bạn đặt, ví dụ `studenthead_v2.yaml`).
2. Mở file và cập nhật đường dẫn:
```yaml
path: D:/Vibe Code/hethongdiemdanh Dieu Cai/dataset/ten_dataset_moi
train: train/images
val: valid/images
test: test/images

names:
  0: student_head
```

---

## 3. Khởi chạy huấn luyện mô hình mới

Sau khi đã nạp data và sửa file yaml:

- **Huấn luyện từ đầu với data mới:**
  ```powershell
  .\venv_cuda\Scripts\python.exe training\train_real_camera.py --data dataset/data.yaml --epochs 30 --batch 4 --imgsz 640 --device 0
  ```
- Hoặc bạn có thể chỉnh sửa file `train_real_camera.bat` để trỏ vào file yaml mới và nháy đúp chạy.
