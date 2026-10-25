# 🏛️ KIẾN TRÚC HỆ THỐNG ĐIỂM DANH AI - THPT ĐIỀU CẢI
*(System Architecture Documentation)*

---

## 📌 1. TỔNG QUAN KIẾN TRÚC HỆ THỐNG (SYSTEM OVERVIEW)

Hệ thống được thiết kế theo mô hình **Module hóa phân tầng (Modular Layered Architecture)** và **Kiến trúc chịu lỗi cao (Hybrid High-Availability Architecture)** nhằm phục vụ tự động điểm danh cho **30 phòng học** (khoảng **1.246 học sinh**) tại **Trường THPT Điều Cải**.

### Sơ đồ kiến trúc tổng thể (High-Level Architecture)

```mermaid
flowchart TB
    subgraph Clients["🌐 KHÁCH HÀNG & THIẾT BỊ ĐẦU CUỐI"]
        Browser["Trình Duyệt Web (BGH / Giám Thị / Quản Trị Viên)"]
        Mobile["Thiết Bị Di Động (Thông báo Zalo / Email Báo Cáo)"]
    end

    subgraph Edge["🏫 HẠ TẦNG MẠNG TRƯỜNG HỌC (LAN)"]
        NVR["Đầu Ghi NVR Camera (Dahua / Hikvision / Uniview)"]
        Cameras["Hệ Thống 30 Camera RTSP Phòng Học"]
        Relays["Bộ Điều Khiển Rơ-le Đèn Tín Hiệu Camera"]
        Cameras --> NVR
    end

    subgraph DockerHost["🐳 MÁY CHỦ HỆ THỐNG (DOCKER ENVIRONMENT)"]
        subgraph FrontendProxy["Frontend & Gateway"]
            Nginx["Nginx Reverse Proxy (Port 80/3000)<br/>• Phục vụ Static SPA<br/>• Quản lý Cookie & Security Headers<br/>• Rate Limiting & Gzip"]
        end

        subgraph BackendCore["Backend REST API (FastAPI)"]
            API_Router["Tầng API Routers<br/>(/attendance, /cameras, /auth, /reports, /system)"]
            Auth_Engine["Tầng Xác Thực & Phân Quyền<br/>(JWT HS256, HttpOnly Cookie, JTI Blacklist)"]
            Engine["Tầng Điều Phối Điểm Danh<br/>(Round-Robin Multi-Pass Attendance Engine)"]
            RTSP_Service["Tầng Giao Tiếp Thiết Bị<br/>(Fast HTTP Snapshot, RTSP Multi-thread, Relay Control)"]
            Local_Detector["Bộ Nhận Diện Cục Bộ (Fallback Safety Net)<br/>(data/models/yolo26m.pt + OpenCV Depth-NMS)"]
        end

        subgraph AIService["AI Microservice (student-detection)"]
            Predict_API["Service /api/predict (Port 8010)<br/>• YOLO Head Specialist<br/>• Depth Anything V2 Perspective Model<br/>• 3D Space Depth-NMS Suppressor"]
        end

        subgraph StorageLayer["Lưu Trữ & Dữ Liệu"]
            SQLite["CSDL SQLite (data/database/attendance.db)<br/>(Hỗ trợ mở rộng PostgreSQL)"]
            FileStorage["Kho Lưu Trữ File (data/storage/)<br/>• captures/ (Ảnh gốc)<br/>• annotated/ (Ảnh đối chứng AI)<br/>• reports/ (Báo cáo Excel chuẩn Sở)"]
        end
    end

    subgraph ExternalCloud["☁️ DỊCH VỤ ĐÁM MÂY NGOẠI VI"]
        ZaloGateway["Zalo Bot Gateway / Zalo OA (Thông báo sĩ số)"]
        SMTPServer["Máy Chủ Email SMTP (Gửi báo cáo BGH)"]
        GoogleDrive["Google Drive API (Sao lưu CSDL & Báo cáo hàng ngày)"]
    end

    Browser -->|HTTP/HTTPS + HttpOnly Cookie| Nginx
    Nginx -->|Proxy Pass /api/| API_Router
    API_Router --> Auth_Engine
    Auth_Engine --> Engine
    Engine --> RTSP_Service
    RTSP_Service -->|Kéo luồng RTSP / Lấy HTTP Snapshot| NVR
    RTSP_Service -->|Bật/Tắt Đèn Tín Hiệu| Relays

    Engine -->|Ưu Tiên 1: REST API /api/predict| Predict_API
    Engine -.->|Ưu Tiên 2 Fallback khi rớt mạng| Local_Detector

    Engine --> SQLite
    Engine --> FileStorage
    API_Router --> SQLite

    BackendCore -->|Gửi tin tức thời 06:45 AM| ZaloGateway
    BackendCore -->|Gửi file Excel đính kèm| SMTPServer
    BackendCore -->|Sao lưu định kỳ ban đêm| GoogleDrive
    ZaloGateway --> Mobile
    SMTPServer --> Mobile
```

---

## 🧠 2. QUY TRÌNH ĐIỂM DANH & THUẬT TOÁN AI (ATTENDANCE & AI PIPELINE)

Hệ thống loại bỏ hoàn toàn các phương pháp điểm danh 1 ảnh đơn lẻ (dễ sai lệch khi học sinh quay sang trao đổi, bị che khuất hoặc camera rớt gói tin) và chuyển sang **Chu trình Quét Xoay Vòng Đa Lượt (Round-Robin Multi-Pass)** kết hợp **Bình Chọn Trọng Số Tin Cậy (Confidence-Weighted Voting)**.

```mermaid
sequenceDiagram
    autonumber
    participant Sch as APScheduler (06:45 AM)
    participant Eng as AttendanceEngine
    participant RTSP as RTSP Client
    participant NVR as Hệ Thống Camera NVR
    participant AI as AI Engine (/api/predict hoặc Local YOLO)
    participant DB as SQLite Database
    participant Notif as Notification Services

    Sch->>Eng: Kích hoạt ca quét điểm danh tự động
    Eng->>RTSP: Gửi lệnh chuẩn bị luồng & chụp ảnh Vòng 1
    RTSP->>NVR: Lấy HTTP Snapshot / Kết nối luồng phụ RTSP Sub-stream
    NVR-->>RTSP: Trả về khung hình tươi (Fresh Frames)
    RTSP-->>Eng: Hoàn tất đợt chụp ban đầu toàn trường
    
    loop Xoay Vòng Toàn Trường (Round 1 -> Num_Passes, vd: 8-10 vòng)
        Eng->>RTSP: Lấy mẫu khung hình tươi theo chu kỳ nghỉ (10s delay)
        RTSP-->>Eng: Trả về khung hình sạch đã lọc nhiễu & sọc dọc
        Eng->>AI: Gửi khung hình phân tích nhận diện học sinh
        AI-->>Eng: Trả về danh sách tọa độ BBox, Độ sâu Depth, Độ tin cậy Conf
        Eng->>Eng: Lưu kết quả mẫu: (Sĩ số vòng i, Độ nét Laplacian, Độ tin cậy)
    end

    Eng->>Eng: Áp dụng thuật toán Bầu Chọn Trọng Số (Weighted Voting)
    Note over Eng: Chốt sĩ số chiến thắng có tổng điểm Score(C) cao nhất<br/>và chọn ảnh đối chứng nét nhất có Conf cao nhất
    
    Eng->>DB: Ghi nhận AttendanceSession & AttendanceDetails (Sĩ số, Vắng, Ảnh)
    Eng->>Notif: Tạo báo cáo Excel chuẩn Sở GD&ĐT
    Eng->>Notif: Gửi tin nhắn Zalo cảnh báo các lớp có học sinh vắng
    Eng->>Notif: Gửi email kèm báo cáo tổng hợp tới Ban Giám Hiệu
```

### Thuật toán Đếm Sĩ Số: Chế Độ Tần Số Trọng Số Tin Cậy (Confidence-Weighted Frequency Mode)
Đối với mỗi phòng học, sau $N$ lượt quét ($N \in [8, 10]$):
1. Nhóm các lượt quét theo số lượng học sinh đếm được: $C \in \{c_1, c_2, ..., c_k\}$.
2. Với mỗi mức sĩ số $C$, tính điểm trọng số tích lũy:
   $$\text{Score}(C) = \left( \sum_{i \in \text{Samples}(C)} \text{Confidence}_i \right) \times \left( 1.0 + \min\left(0.15, \max\left(0.0, \frac{\text{LaplacianSharpness} - 10.0}{200.0}\right)\right) \right)$$
3. **Mức sĩ số chiến thắng ($C^*$)**: Là mức sĩ số có $\text{Score}(C)$ lớn nhất.
   - *Quy tắc Tie-break*: Nếu có 2 mức sĩ số có điểm số xấp xỉ nhau, hệ thống ưu tiên mức sĩ số **lớn hơn** để tránh ghi nhận vắng khống khi học sinh tạm thời bị bạn cùng bàn che khuất.
4. **Chọn ảnh đối chứng**: Trong nhóm các lượt quét thuộc về mức sĩ số $C^*$, chọn lượt quét có tích số $(\text{Confidence} \times \text{Sharpness})$ cao nhất để lưu làm bằng chứng CSDL và xuất báo cáo.

---

## 🔒 3. KIẾN TRÚC BẢO MẬT NHIỀU LỚP (DEFENSE-IN-DEPTH SECURITY)

Hệ thống triển khai 6 tầng phòng vệ nghiêm ngặt nhằm đáp ứng tiêu chuẩn an toàn thông tin trường học:

```mermaid
flowchart LR
    subgraph L1["TẦNG 1: MẠNG & CỔNG"]
        C1["Docker Port Binding<br/>127.0.0.1:8000<br/>(Chặn scan từ Internet)"]
    end
    subgraph L2["TẦNG 2: PROXY & GATEWAY"]
        C2["Nginx Gateway<br/>• Chặn truy cập HTML trực tiếp<br/>• Security Headers<br/>• Giới hạn Payload 500MB"]
    end
    subgraph L3["TẦNG 3: RATE LIMITING"]
        C3["Chống Brute-force<br/>• 10 lần/IP trong 5 phút<br/>• 15 lần/Email trong 15 phút"]
    end
    subgraph L4["TẦNG 4: XÁC THỰC"]
        C4["JWT Cookie (HttpOnly)<br/>• Chống XSS (JS không đọc được)<br/>• SameSite=Lax (Chống CSRF)<br/>• JTI Blacklist khi Logout"]
    end
    subgraph L5["TẦNG 5: PHÂN QUYỀN"]
        C5["RBAC Dependencies<br/>• get_current_user (Tất cả router)<br/>• require_admin (CRUD Camera, NVR)"]
    end
    subgraph L6["TẦNG 6: DỮ LIỆU & NGUỒN LUỒNG"]
        C6["SSRF & LFI Shield<br/>• Chặn file://, 127.0.0.1, 169.254<br/>• Khóa webcam/file trên Production<br/>• Masking mật khẩu RTSP"]
    end

    L1 --> L2 --> L3 --> L4 --> L5 --> L6
```

1. **Cô lập Cổng Mạng (Network Port Isolation)**:
   - Backend FastAPI không bao giờ bind cổng `0.0.0.0:8000` ra Internet công cộng. Cổng 8000 chỉ lắng nghe nội bộ tại `127.0.0.1`.
   - 100% người dùng bắt buộc phải đi qua cổng Nginx (80/3000 hoặc HTTPS 443).
2. **Khóa Swagger / OpenAPI Tài Liệu Nhạy Cảm**:
   - Khi chạy ở môi trường Production (`DEBUG=false`), FastAPI tắt hoàn toàn `/docs`, `/redoc` và `/openapi.json` (trả về 404). Kẻ tấn công không thể thăm dò danh mục API của hệ thống.
3. **Xác Thực JWT HttpOnly Cookie (Chống XSS & CSRF)**:
   - Token JWT được ký bảo mật bằng thuật toán `HS256` với khóa ngẫu nhiên 256-bit trong file `.env`.
   - Token chỉ lưu trữ trong Cookie với cờ `HttpOnly=True` và `SameSite=Lax`, tuyệt đối không lưu trong `localStorage`.
   - Cơ chế thu hồi phiên tức thời (*Token Revocation / Blacklist*): Mỗi token chứa trường `jti`. Khi người dùng đăng xuất, `jti` được lưu vào danh sách đen trong bộ nhớ, vô hiệu hóa token ngay lập tức.
4. **Phòng Chống Tấn Công Dò Quét (Sliding-Window Rate Limiting)**:
   - Giới hạn tối đa 10 lần yêu cầu đăng nhập trên 1 địa chỉ IP trong 5 phút. Vượt ngưỡng sẽ trả về mã lỗi `HTTP 429 Too Many Requests`.
5. **Chống Tấn Công SSRF & LFI (Server-Side Request Forgery & Local File Inclusion)**:
   - Bộ lọc `validate_stream_source` chặn đứng mọi nguồn camera có tiền tố `file://`, dải mạng nội bộ loopback `127.0.0.1`, dải metadata đám mây `169.254.169.254`.
   - Khi ở môi trường Production (`DEBUG=false`), hệ thống tự động khóa cổng Webcam vật lý (ID `0`, `1`) và các đường dẫn file video cục bộ.
6. **Che Giấu Mật Khẩu Luồng Camera (RTSP Masking)**:
   - Mọi chuỗi RTSP chứa tài khoản/mật khẩu camera (ví dụ `rtsp://admin:pass123@192.168.1.200:554`) đều được tự động làm mờ thành `rtsp://admin:****@192.168.1.200:554` trước khi ghi vào nhật ký Log hoặc trả về giao diện.

---

## 🗄️ 4. MÔ HÌNH DỮ LIỆU THỰC THỂ (DATABASE ERD)

Cơ sở dữ liệu được thiết kế theo chuẩn quan hệ 3NF bằng SQLAlchemy ORM, tương thích hoàn hảo giữa SQLite cục bộ và PostgreSQL/MySQL:

```mermaid
erDiagram
    USERS ||--o{ SYSTEM_LOGS : generates
    CLASSROOMS ||--o{ ATTENDANCE_DETAILS : contains
    ATTENDANCE_SESSIONS ||--|{ ATTENDANCE_DETAILS : records
    NVR_DEVICES ||--o{ CLASSROOMS : connects
    USERS ||--o{ PASSWORD_RESET_TOKENS : requests

    USERS {
        int id PK
        string email UK
        string password_hash
        string full_name
        string role "admin / staff"
        boolean is_active
        datetime created_at
    }

    CLASSROOMS {
        int id PK
        string code UK
        string name
        string room_number
        int standard_count
        string rtsp_url
        string rtsp_sub_url
        string relay_ip
        boolean is_active
        int nvr_id FK
    }

    NVR_DEVICES {
        int id PK
        string name
        string host
        int port
        string username
        string password_hash
        int total_channels
        datetime created_at
    }

    ATTENDANCE_SESSIONS {
        int id PK
        string session_code UK
        string scan_date
        string scan_time
        int total_classes
        int total_standard
        int total_present
        int total_absent
        string status
        string excel_report_path
        datetime created_at
    }

    ATTENDANCE_DETAILS {
        int id PK
        int session_id FK
        int classroom_id FK
        int standard_count
        int present_count
        int absent_count
        string raw_image_path
        string annotated_image_path
        float confidence_avg
        string status "OK / CAN_KIEM_TRA / NO_SIGNAL"
        string notes
    }

    PASSWORD_RESET_TOKENS {
        int id PK
        int user_id FK
        string token_hash UK
        datetime expires_at
        boolean used
    }
```

---

## 📂 5. BẢN ĐỒ MÃ NGUỒN CHUẨN HÓA (DIRECTORY MAP)

```text
hethongdiemdanh-dieucai/
├── 🎨 frontend/                             # Giao diện người dùng Web SPA (HTML5, Vanilla CSS, JS)
│   ├── index.html                          # Dashboard theo dõi sĩ số toàn trường trực quan
│   ├── login.html                          # Giao diện đăng nhập an toàn
│   ├── classrooms.html                     # Quản lý danh sách lớp học & phân chia ca học
│   ├── cameras.html                        # Giám sát Ma Trận Camera Wall & Live Stream
│   ├── reports.html                        # Báo cáo tổng hợp, lọc theo ngày & xuất Excel
│   ├── settings.html                       # Cấu hình hệ thống, quản lý người dùng, Zalo & Email
│   ├── notifications.html                  # Nhật ký thông báo tự động
│   ├── css/                                # Hệ thống Design System: Glassmorphism, Biến CSS, Reset
│   └── js/                                 # Module JavaScript phân tách rõ trách nhiệm:
│       ├── api.js                          # API Client trung tâm (fetchAPI với credentials: include)
│       └── modules/                        # Các controller nghiệp vụ (cameras, dashboard, auth)
│
├── ⚙️ backend/app/                          # Mã nguồn Backend máy chủ FastAPI
│   ├── main.py                             # Điểm khởi chạy FastAPI, Middleware CORS, Lifespan
│   ├── api/
│   │   ├── deps.py                         # Dependency Injection: Cấp phát DB Session, Xác thực User
│   │   ├── security.py                     # Bộ lọc an ninh: Rate-limit, Masking URL, Chống SSRF/LFI
│   │   └── routers/                        # REST API phân tách theo từng miền chức năng:
│   │       ├── attendance.py               # API Quét điểm danh & Điều khiển phiên làm việc
│   │       ├── cameras.py                  # API CRUD Camera, NVR Discovery & Snapshot Live
│   │       ├── classrooms.py               # API Quản lý danh mục phòng học
│   │       ├── reports.py                  # API Truy vấn lịch sử & Tải báo cáo Excel
│   │       ├── auth.py                     # API Đăng nhập, Đăng xuất, Phân quyền RBAC
│   │       ├── backup.py                   # API Sao lưu CSDL cục bộ & Đồng bộ Google Drive
│   │       ├── predict.py                  # API Suy luận AI Depth-NMS & Proxy kết nối Microservice
│   │       └── system.py                   # API Giám sát tài nguyên máy chủ, CPU/GPU, Health
│   ├── core/                               # Cốt lõi nghiệp vụ AI & Tương tác phần cứng
│   │   ├── attendance_engine.py            # Động cơ điều phối quét đa vòng (Round-Robin Batches)
│   │   ├── rtsp_client.py                  # Thu nhận khung hình camera (HTTP Snapshot & RTSP)
│   │   ├── detector.py                     # Bộ suy luận AI cục bộ dự phòng (Fallback Safety Net)
│   │   ├── raw_ai_engine.py                # Thuật toán vẽ đối chứng chấm neon AI không che lấp
│   │   └── relay_service.py                # Giao tiếp điều khiển đèn tín hiệu hồng ngoại camera
│   ├── services/                           # Dịch vụ tích hợp ngoại vi
│   │   ├── zalo_service.py                 # Tích hợp cổng Zalo Bot Gateway / Zalo OA
│   │   ├── email_service.py                # Tích hợp SMTP gửi thư điện tử cho BGH
│   │   ├── excel_exporter.py               # Xuất file báo cáo Excel chuẩn Sở GD&ĐT
│   │   ├── gdrive_service.py               # Tích hợp OAuth 2.0 sao lưu Google Drive
│   │   └── scheduler.py                    # Trình lập lịch tự động quét 06:45 AM (APScheduler)
│   ├── database/                           # Quản lý tầng dữ liệu
│   │   ├── models.py                       # Khai báo các bảng ORM (Classroom, Session, User,...)
│   │   └── db_session.py                   # Kết nối SessionLocal, Khởi tạo bảng & Seed dữ liệu
│   └── config/                             # Cấu hình tập trung
│       ├── settings.py                     # Đọc cấu hình từ .env bằng Pydantic BaseSettings
│       └── logging_config.py               # Hệ thống ghi nhật ký chuẩn hóa xoay vòng (Log Rotation)
│
├── 📦 data/                                 # Thư mục dữ liệu Runtime (Được Mount vào Docker)
│   ├── database/attendance.db              # Tệp tin CSDL SQLite chính thức
│   ├── models/yolo26m.pt                   # Trọng số mô hình AI dự phòng cục bộ (44.25 MB)
│   ├── storage/                            # Dữ liệu ảnh captures, ảnh đối chứng, file Excel
│   └── dataset/                            # Bộ dữ liệu hình ảnh máy học phục vụ huấn luyện
│
├── 🐳 docker/                               # Cấu hình đóng gói Container
│   ├── backend/Dockerfile                  # Dockerfile tối ưu Python 3.10 FastAPI & PyTorch
│   └── frontend/nginx.conf                 # Cấu hình Nginx Reverse Proxy & Security Headers
│
├── 🧪 tests/                                # Bộ kiểm thử tự động toàn diện (36/36 tests PASSED)
│   ├── conftest.py                         # Fixtures cô lập CSDL kiểm thử và bật Test Debug Mode
│   ├── test_attendance_engine.py           # Kiểm tra động cơ điểm danh tự động
│   ├── test_camera_management.py           # Kiểm tra nghiệp vụ camera & kết nối
│   ├── test_weighted_attendance.py         # Kiểm tra thuật toán bầu chọn sĩ số đa vòng
│   ├── test_scaling_and_data_integrity.py  # Kiểm tra tính toàn vẹn dữ liệu & NVR Semaphore
│   ├── test_camera_signal_workflow.py      # Kiểm tra quy trình điều khiển đèn hồng ngoại
│   └── test_logging_redaction.py           # Kiểm tra che giấu mật khẩu trong log hệ thống
│
├── docker-compose.yml                      # Cấu hình điều phối cụm Container Frontend + Backend
├── requirements.txt                        # Danh mục thư viện Python
└── .env                                    # Biến môi trường bảo mật (Không đưa lên Git)
```

---

## 🎯 6. KẾT LUẬN

Kiến trúc trên đảm bảo:
1. **Tính sẵn sàng cao (High Availability)**: Điểm danh không bao giờ bị gián đoạn nhờ cơ chế Fallback AI 2 tầng.
2. **Khả năng mở rộng (Scalability)**: Dễ dàng mở rộng từ 30 phòng học lên 100 phòng học nhờ cơ chế hàng đợi NVR Semaphore và kiến trúc không trạng thái (Stateless API).
3. **Bảo mật chuẩn trường học (Education-Grade Security)**: Đóng toàn diện các cổng dịch vụ bên ngoài, loại bỏ hoàn toàn nguy cơ rò rỉ dữ liệu qua Swagger, Cookie an toàn chống XSS/CSRF và phân quyền chặt chẽ.
