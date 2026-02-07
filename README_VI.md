# Pill Counter System - Hệ Thống Đếm Thuốc Tự Động

> Hệ thống tự động hóa kiểm tra số lượng thuốc sử dụng công nghệ AI (YOLOv11) và Raspberry Pi 4, được thiết kế để nâng cao độ chính xác và hiệu quả vận hành tại các nhà thuốc.

<p align="center">
  <img src="server_app/static/README/banner1.jpg" width="45%" />
  <img src="server_app/static/README/banner2.jpg" width="45%" />
</p>

## Mục lục

1. [Giới thiệu](#giới-thiệu)
2. [Tính năng chính](#tính-năng-chính)
3. [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
4. [Công nghệ sử dụng](#công-nghệ-sử-dụng)
5. [Cài đặt và Triển khai](#cài-đặt-và-triển-khai)
6. [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
7. [Hình ảnh minh họa](#hình-ảnh-minh-họa)
8. [Cấu trúc dự án](#cấu-trúc-dự-án)

---

## Giới thiệu

**Pill Counter System** là giải pháp phần cứng và phần mềm tích hợp, hỗ trợ dược sĩ trong quy trình đếm số lượng thuốc theo đơn. Hệ thống giải quyết vấn đề sai sót của con người trong quá trình đếm thủ công, đồng thời số hóa dữ liệu giao dịch để quản lý kho hiệu quả.

**Các thành phần cốt lõi:**
*   **AI Engine:** Sử dụng mô hình YOLOv11 tùy chỉnh để phát hiện và đếm số lượng viên thuốc với độ chính xác cao.
*   **Thiết bị IoT:** Raspberry Pi 4 thu nhận hình ảnh, hiển thị kết quả lên màn hình LCD và xử lý sơ bộ.
*   **Xử lý thời gian thực:** Đồng bộ dữ liệu tức thời giữa thiết bị và máy chủ quản lý qua WebSocket.
*   **Hệ thống quản trị:** Web Dashboard tập trung để giám sát hoạt động và báo cáo.

### Video Demo
![Video Demo](link_video_demo_here)

---

## Tính năng chính

### Dành cho Dược sĩ (Vận hành)
*   Tạo và quản lý đơn thuốc trên hệ thống kỹ thuật số.
*   Đếm số lượng thuốc tự động thông qua camera giám sát.
*   Tự động đối chiếu số lượng thực tế với yêu cầu trong đơn thuốc.
*   Xem lịch sử giao dịch và thống kê hiệu suất cá nhân.
*   Ghi nhận và báo cáo các sự cố bất thường.

### Dành cho Quản trị viên (Quản lý)
*   Bảng điều khiển (Dashboard) phân tích dữ liệu tổng quan.
*   Quản lý tài khoản người dùng và phân quyền.
*   Quản lý danh mục thuốc và kho dữ liệu.
*   Xuất báo cáo hiệu suất và nhật ký hệ thống.

### Đặc điểm kỹ thuật AI
*   **Phát hiện đối tượng thời gian thực:** Tốc độ phản hồi cao.
*   **Cơ chế Auto-locking:** Thuật toán tự động chốt kết quả khi số lượng đếm ổn định trong chuỗi khung hình, giảm thiểu thao tác thủ công.
*   **Confidence Scoring:** Hiển thị độ tin cậy của kết quả phát hiện đối tượng.



---

## Kiến trúc hệ thống

Hệ thống được thiết kế theo mô hình Client-Server với các module chuyên biệt:

```mermaid
graph TB
    subgraph Device["Thiết bị (Client)"]
        CAM[Camera Module]
        LCD[Màn hình LCD]
        PI_APP["Ứng dụng Pi (PyQt5)"]
    end
    
    subgraph Server["Máy chủ (Server)"]
        WEB[Web Dashboard]
        AI[YOLO AI Engine]
        DB[(MySQL Database)]
        SOCKET[SocketIO Server]
    end
    
    subgraph Users["Người dùng"]
        ADMIN[Quản trị viên]
        PHARM[Dược sĩ]
    end
    
    CAM -->|Video Stream| PI_APP
    PI_APP -->|Hiển thị| LCD
    PI_APP -->|WebSocket/Images| SOCKET
    SOCKET -->|Xử lý ảnh| AI
    AI -->|Kết quả đếm| WEB
    WEB --> DB
    ADMIN --> WEB
    PHARM --> WEB
```

### Quy trình xử lý
1.  **Thu thập:** Camera trên Raspberry Pi ghi nhận hình ảnh khay thuốc.
2.  **Truyền tải:** Hình ảnh được truyền về Server qua giao thức WebSocket bảo mật.
3.  **Phân tích:** Mô hình YOLOv11 phân tích hình ảnh, phát hiện và đếm số lượng viên thuốc.
4.  **Xác thực:** Hệ thống kiểm tra độ ổn định (Auto-lock) và tự động reset khi phát hiện chuyển động (Motion Detection).
5.  **Hiển thị & Lưu trữ:** Kết quả được hiển thị lên **Giao diện Đếm thuốc** để Dược sĩ xác nhận, sau đó mới lưu vào cơ sở dữ liệu.

```mermaid
flowchart LR
    CAM([Camera Pi]) -->|1. Thu thập| WS{WebSocket}
    WS -->|2. Truyền tải| YOLO[YOLOv11 AI]
    YOLO -->|3. Phân tích & Đếm| LOCK{Auto-Lock}
    
    LOCK --Ổn định--> UI[Giao diện Đếm thuốc]
    LOCK --Chưa ổn định--> YOLO
    
    UI -->|Xác nhận| SAVE[(Lưu CSDL)]
    LOCK -.->|Kết quả| LCD([Màn hình LCD])
    
    style CAM fill:#ff9999,stroke:#333,stroke-width:2px
    style YOLO fill:#99ccff,stroke:#333,stroke-width:2px
    style SAVE fill:#99ff99,stroke:#333,stroke-width:2px
    style UI fill:#e1d5e7,stroke:#9673a6,stroke-width:2px
```
*Hình 1: Sơ đồ luồng dữ liệu chi tiết của hệ thống.*

---

## Công nghệ sử dụng

### Backend (Server)
*   **Ngôn ngữ:** Python 3.8+
*   **Web Framework:** Flask
*   **Database:** MySQL (Sử dụng Flask-SQLAlchemy ORM)
*   **Real-time:** Flask-SocketIO
*   **AI/Computer Vision:** Ultralytics YOLOv11, OpenCV

### Frontend (Web)
*   **Interface:** Bootstrap 5, Jinja2 Templates
*   **Visualization:** Chart.js
*   **Communication:** Socket.IO Client

### Thiết bị IoT (Edge)
*   **Hardware:** Raspberry Pi 4 Model B
*   **OS:** Raspberry Pi OS (64-bit)
*   **Client App:** PyQt5
*   **Camera:** Module v2 hoặc Webcam USB
*   **Display:** Màn hình LCD (I2C/SPI) giao tiếp với Pi



---

## Cài đặt và Triển khai

### 1. Yêu cầu hệ thống
*   **Server:** CPU 4-core, RAM 8GB, GPU (khuyến nghị cho AI inference).
*   **Client:** Raspberry Pi 4 (RAM 4GB trở lên).

### 2. Thiết lập Máy chủ (Server)

```bash
# Clone source code
git clone <repo_url>
cd PILL_COUNTER_PROJECT

# Thiết lập môi trường ảo
python3 -m venv venv
source venv/bin/activate

# Cài đặt thư viện phụ thuộc
pip install -r server_app/requirements_server.txt

# Cấu hình biến môi trường (.env)
cp .env.example .env
# Chỉnh sửa thông tin Database trong file .env

# Khởi tạo cơ sở dữ liệu
flask db upgrade
flask seed-db

# Khởi chạy server
python run.py
```

### 3. Thiết lập Máy trạm (Raspberry Pi)

```bash
# Truy cập Raspberry Pi
ssh pi@<ip_address>

# Cài đặt thư viện client
cd device_app
pip install -r requirements_pi.txt

# Chạy ứng dụng client
python main.py
```

---

## Hướng dẫn sử dụng

### Đăng nhập
*   **Quản trị viên:** Tài khoản mặc định `admin`
*   **Dược sĩ:** Tài khoản được cấp bởi quản trị viên (ví dụ: `duocsi1`)

### Quy trình đếm thuốc
1.  **Tạo đơn:** Dược sĩ tạo đơn thuốc mới trên Web Dashboard.
2.  **Chuẩn bị:** Đặt thuốc lên khay đếm dưới camera.
3.  **Xử lý:**
    *   Hệ thống tự động phát hiện viên thuốc.
    *   Kết quả được hiển thị đồng thời trên **Màn hình LCD** (tại chỗ) và **Web Dashboard** (từ xa).
    *   Khi số lượng ổn định, hệ thống tự động khóa kết quả (Auto-lock).
    *   Dược sĩ kiểm tra lại và nhấn xác nhận.
4.  **Hoàn tất:** Dữ liệu được lưu vào lịch sử giao dịch.

```mermaid
sequenceDiagram
    autonumber
    actor D as Dược sĩ
    participant W as Web Dashboard
    participant H as Phần cứng (Pi/Cam)
    participant L as Màn hình LCD
    participant S as Hệ thống AI

    Note over D, W: 1. Khởi tạo đơn thuốc
    D->>W: Tạo đơn thuốc mới (Nhập số lượng yêu cầu)
    W-->>D: Xác nhận đơn thuốc

    Note over D, H: 2. Chuẩn bị
    D->>H: Đặt thuốc lên khay đếm

    Note over H, S: 3. Xử lý thời gian thực
    loop Nhận diện liên tục
        H->>S: Gửi hình ảnh stream (WebSocket)
        S->>S: AI Phát hiện & Đếm số lượng
        par Hiển thị đa nền tảng
            S-->>W: Cập nhật Web Dashboard
            S-->>H: Trả về kết quả
            H->>L: Hiển thị số lượng
        end
    end

    Note over S: 4. Cơ chế Auto-Lock
    S->>S: Số lượng ổn định? (Stable Check)
    S-->>W: Tự động khóa kết quả (Locked)
    S-->>H: Khóa kết quả
    H->>L: Hiển thị trạng thái "Đã chốt"

    Note over D, W: 5. Hoàn tất
    D->>W: Kiểm tra & Xác nhận kết quả
    W->>W: Lưu vào Lịch sử Giao dịch
    W-->>D: Thông báo thành công
```

---

## Hình ảnh minh họa

### Giao diện Quản trị (Admin Dashboard)
![Admin Dashboard Screenshot](server_app/static/README/Admin_Dashboard.png)
*Hình 2: Bảng điều khiển quản trị viên với các thông số tổng quan.*

### Dashboard Dược sĩ (Pharmacist Dashboard)
![Pharmacist Dashboard Screenshot](server_app/static/README/duosi.png)
*Hình 3: Giao diện trang chủ dành cho dược sĩ.*

### Tạo đơn thuốc (Create Prescription)
![Create Prescription Screenshot](server_app/static/README/taodon.png)
*Hình 4: Giao diện tạo đơn thuốc mới.*

### Giao diện Đếm thuốc (Pharmacist View)
![Counting Interface Screenshot](server_app/static/README/counting.png)
*Hình 5: Màn hình thao tác chính của dược sĩ.*

### Lịch sử đơn thuốc (Prescription History)
![Prescription History Screenshot](server_app/static/README/History.png)
*Hình 6: Danh sách lịch sử các đơn thuốc đã thực hiện.*

### Báo cáo và Thống kê
![Statistics Screenshot](server_app/static/README/Admin_Dashboard.png)
*Hình 7: Biểu đồ thống kê hiệu suất và lịch sử hoạt động.*

---



## Cấu trúc dự án

```text
PILL_COUNTER_PROJECT/
├── server_app/              # Mã nguồn Backend & Web Server
│   ├── models.py            # Định nghĩa dữ liệu (Database Models)
│   ├── admin.py             # Logic quản trị
│   ├── pharmacist.py        # Logic nghiệp vụ dược sĩ & AI
│   └── templates/           # Giao diện người dùng
│
├── device_app/              # Mã nguồn thiết bị IoT (Client)
│   ├── main.py              # Chương trình chính
│   ├── ai_processor.py      # Module xử lý AI
│   └── ui_controller.py     # Giao diện điều khiển tại thiết bị
│
├── data_and_training/       # Dữ liệu & Huấn luyện mô hình
│   ├── dataset/             # Dữ liệu ảnh thô & nhãn
│   └── train.py             # Script huấn luyện YOLO
│
└── requirements.txt         # Danh sách thư viện
```

---

## Thông tin thêm

### Dữ liệu huấn luyện (Dataset)
Mô hình YOLOv11 được huấn luyện trên bộ dữ liệu thuốc tuỳ chỉnh chất lượng cao, bao gồm:
### Dữ liệu huấn luyện (Dataset)
Mô hình được huấn luyện trên bộ dữ liệu hình ảnh thuốc được thu thập thực tế và gán nhãn thủ công, đảm bảo hoạt động ổn định trong các điều kiện ánh sáng khác nhau.


---

## Đóng góp

Dự án được phát triển phục vụ mục đích nghiên cứu và giáo dục. Mọi sự đóng góp từ cộng đồng đều được hoan nghênh và trân trọng.

---

## Tác giả

**Thành viên nhóm phát triển:**

**Nguyễn Thanh Huyền**
- GitHub: [@Chizk23](https://github.com/Chizk23)

**Nguyễn Thị Bích Uyên**
- GitHub: [@BichUyen2609](https://github.com/BichUyen2609)

**Trần Thị Phượng**
- GitHub: [@PhuongTran2212](https://github.com/PhuongTran2212)

---

**⭐ If you find this project helpful, please give it a star!**
