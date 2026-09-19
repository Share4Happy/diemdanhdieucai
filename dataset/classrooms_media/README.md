# BỘ DỮ LIỆU ĐA PHƯƠNG TIỆN 30 LỚP HỌC - TRƯỜNG THPT ĐIỀU CẢI

Bộ dữ liệu cung cấp đầy đủ **5 hình ảnh Full HD** và **1 video 15 giây chuẩn** cho từng lớp trong tổng số **30 lớp học** của Trường THPT Điều Cải, phục vụ điểm danh AI tự động, thử nghiệm kiểm chuẩn benchmark và giả lập nguồn camera cục bộ.

## 1. Cấu Trúc Thư Mục

```text
dataset/classrooms_media/
├── danh_sach_si_so_toan_truong.xlsx   <- Báo cáo Excel chi tiết sĩ số 30 lớp
├── danh_sach_si_so_toan_truong.json   <- Dữ liệu cấu trúc JSON toàn trường
├── README.md                          <- Tài liệu thuyết minh bộ dữ liệu
│
├── Lop_10A1/                          <- Thư mục riêng từng lớp
│   ├── image_1.jpg                    <- Ảnh Full HD 1920x1080 (Đủ 100% sĩ số)
│   ├── image_2.jpg                    <- Ảnh Full HD 1920x1080 (Vắng 1 HS)
│   ├── image_3.jpg                    <- Ảnh Full HD 1920x1080 (Góc nhìn học tập)
│   ├── image_4.jpg                    <- Ảnh Full HD 1920x1080 (Vắng 2 HS)
│   ├── image_5.jpg                    <- Ảnh Full HD 1920x1080 (Kiểm tra chốt)
│   ├── video_15s.mp4                  <- Video chuẩn 15 giây (225 frames, 15fps)
│   ├── info.json                      <- Siêu dữ liệu máy đọc về sĩ số và tệp tin
│   └── thong_tin_lop.txt              <- Thông tin lớp dạng văn bản ngắn gọn
├── Lop_10A2/
...
└── Lop_12A10/
```

## 2. Bảng Thống Kê Sĩ Số Học Sinh 30 Lớp

| STT | Khối | Mã Lớp | Tên Lớp | Phòng Học | Sĩ Số Chuẩn | Số Ảnh Cấp | Video Cấp |
|:---:|:---:|:---:|:---|:---:|:---:|:---:|:---:|
| 01 | 10 | LOP_10A1 | Lớp 10A1 | Phòng 101 | **42** | 5 ảnh 1080p | 1 video 15s |
| 02 | 10 | LOP_10A2 | Lớp 10A2 | Phòng 102 | **40** | 5 ảnh 1080p | 1 video 15s |
| 03 | 10 | LOP_10A3 | Lớp 10A3 | Phòng 103 | **41** | 5 ảnh 1080p | 1 video 15s |
| 04 | 10 | LOP_10A4 | Lớp 10A4 | Phòng 104 | **43** | 5 ảnh 1080p | 1 video 15s |
| 05 | 10 | LOP_10A5 | Lớp 10A5 | Phòng 105 | **39** | 5 ảnh 1080p | 1 video 15s |
| 06 | 10 | LOP_10A6 | Lớp 10A6 | Phòng 106 | **42** | 5 ảnh 1080p | 1 video 15s |
| 07 | 10 | LOP_10A7 | Lớp 10A7 | Phòng 107 | **40** | 5 ảnh 1080p | 1 video 15s |
| 08 | 10 | LOP_10A8 | Lớp 10A8 | Phòng 108 | **41** | 5 ảnh 1080p | 1 video 15s |
| 09 | 10 | LOP_10A9 | Lớp 10A9 | Phòng 109 | **40** | 5 ảnh 1080p | 1 video 15s |
| 10 | 10 | LOP_10A10 | Lớp 10A10 | Phòng 110 | **42** | 5 ảnh 1080p | 1 video 15s |
| 11 | 11 | LOP_11A1 | Lớp 11A1 | Phòng 111 | **44** | 5 ảnh 1080p | 1 video 15s |
| 12 | 11 | LOP_11A2 | Lớp 11A2 | Phòng 112 | **43** | 5 ảnh 1080p | 1 video 15s |
| 13 | 11 | LOP_11A3 | Lớp 11A3 | Phòng 113 | **42** | 5 ảnh 1080p | 1 video 15s |
| 14 | 11 | LOP_11A4 | Lớp 11A4 | Phòng 114 | **40** | 5 ảnh 1080p | 1 video 15s |
| 15 | 11 | LOP_11A5 | Lớp 11A5 | Phòng 115 | **41** | 5 ảnh 1080p | 1 video 15s |
| 16 | 11 | LOP_11A6 | Lớp 11A6 | Phòng 116 | **42** | 5 ảnh 1080p | 1 video 15s |
| 17 | 11 | LOP_11A7 | Lớp 11A7 | Phòng 117 | **39** | 5 ảnh 1080p | 1 video 15s |
| 18 | 11 | LOP_11A8 | Lớp 11A8 | Phòng 118 | **41** | 5 ảnh 1080p | 1 video 15s |
| 19 | 11 | LOP_11A9 | Lớp 11A9 | Phòng 119 | **40** | 5 ảnh 1080p | 1 video 15s |
| 20 | 11 | LOP_11A10 | Lớp 11A10 | Phòng 120 | **43** | 5 ảnh 1080p | 1 video 15s |
| 21 | 12 | LOP_12A1 | Lớp 12A1 | Phòng 121 | **45** | 5 ảnh 1080p | 1 video 15s |
| 22 | 12 | LOP_12A2 | Lớp 12A2 | Phòng 122 | **44** | 5 ảnh 1080p | 1 video 15s |
| 23 | 12 | LOP_12A3 | Lớp 12A3 | Phòng 123 | **42** | 5 ảnh 1080p | 1 video 15s |
| 24 | 12 | LOP_12A4 | Lớp 12A4 | Phòng 124 | **43** | 5 ảnh 1080p | 1 video 15s |
| 25 | 12 | LOP_12A5 | Lớp 12A5 | Phòng 125 | **41** | 5 ảnh 1080p | 1 video 15s |
| 26 | 12 | LOP_12A6 | Lớp 12A6 | Phòng 126 | **40** | 5 ảnh 1080p | 1 video 15s |
| 27 | 12 | LOP_12A7 | Lớp 12A7 | Phòng 127 | **42** | 5 ảnh 1080p | 1 video 15s |
| 28 | 12 | LOP_12A8 | Lớp 12A8 | Phòng 128 | **41** | 5 ảnh 1080p | 1 video 15s |
| 29 | 12 | LOP_12A9 | Lớp 12A9 | Phòng 129 | **40** | 5 ảnh 1080p | 1 video 15s |
| 30 | 12 | LOP_12A10 | Lớp 12A10 | Phòng 130 | **42** | 5 ảnh 1080p | 1 video 15s |
| **TỔNG** | - | **30 Lớp** | **Toàn Trường** | **30 Phòng** | **1.245 HS** | **150 Ảnh** | **30 Video** |

## 3. Cách Sử Dụng Trong Hệ Thống Điểm Danh

1. **Dùng làm nguồn giả lập camera cho lớp học:**
   - Trong trang Quản lý Camera (`cameras.html`), chọn loại nguồn **File cục bộ**.
   - Nhập đường dẫn: `dataset/classrooms_media/Lop_10A1/video_15s.mp4` hoặc `dataset/classrooms_media/Lop_10A1/image_1.jpg`.
2. **Khởi chạy quét điểm danh toàn diện:**
   - Hệ thống AI sẽ đọc trực tiếp khung hình từ file video/ảnh, áp dụng nhận diện YOLOv8 và đối soát chuẩn xác với sĩ số lớp.
