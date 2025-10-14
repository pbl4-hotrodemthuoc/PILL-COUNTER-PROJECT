💊 PILL_COUNTER_PROJECT/
├── 📂 device_app/                  # =========================================================
│   │                               # == ỨNG DỤNG ĐẾM THUỐC (CHẠY TRÊN RASPBERRY PI) ==
│   ├── 📂 models/
│   │   └── best.pt                 # Chức năng: Chứa file "bộ não" AI đã được huấn luyện.
│   ├── 📂 ui/
│   │   └── main_window.ui          # Chức năng: Chứa file thiết kế giao diện (tạo bằng Qt Designer).
│   ├── 📂 assets/
│   │   └── icon.png                # Chức năng: Chứa các tài nguyên hình ảnh cho giao diện.
│   ├── main.py                     # Chức năng: File chính, "nhạc trưởng" khởi động và kết nối mọi thứ.
│   ├── camera_handler.py           # Chức năng: Chuyên xử lý việc giao tiếp với camera, cung cấp hình ảnh.
│   ├── ai_processor.py             # Chức năng: Chuyên xử lý AI, nhận ảnh và trả về kết quả nhận diện.
│   ├── ui_controller.py            # Chức năng: Chuyên điều khiển logic của giao diện (nhấn nút, cập nhật text...).
│   ├── iot_client.py               # Chức năng: Chuyên gửi dữ liệu đếm thuốc lên Web Server.
│   └── requirements_pi.txt         # Chức năng: Liệt kê các thư viện Python cần cài đặt trên Pi.
│
├── 📂 server_app/                  # =========================================================
│   │                               # == WEB APP QUẢN LÝ & API SERVER (CHẠY TRÊN MÁY TÍNH) ==
│   ├── 📂 instance/
│   │   └── ...                     # Chức năng: Flask có thể dùng để chứa file CSDL SQLite (nếu dùng).
│   ├── 📂 static/
│   │   ├── css/                    # Chức năng: Chứa các file CSS để trang trí cho trang web.
│   │   └── js/                     # Chức năng: Chứa các file JavaScript để tạo tương tác, tự động cập nhật.
│   ├── 📂 templates/
│   │   ├── auth/                   # Chức năng: Chứa các file HTML cho trang Đăng nhập, Đăng ký.
│   │   ├── dashboard.html          # Chức năng: File HTML của trang Bảng điều khiển chính.
│   │   ├── drugs.html              # Chức năng: File HTML của trang Quản lý thuốc.
│   │   └── layout.html             # Chức năng: Template HTML chung cho toàn bộ trang web.
│   ├── __init__.py                 # Chức năng: Khởi tạo ứng dụng Flask, cấu hình CSDL MySQL.
│   ├── auth.py                     # Chức năng: Chứa logic xử lý Đăng nhập, Đăng ký, Đăng xuất.
│   ├── main.py                     # Chức năng: Chứa logic xử lý các trang chính (Dashboard, Reports...).
│   ├── models.py                   # Chức năng: Định nghĩa cấu trúc các bảng CSDL dưới dạng Class Python.
│   ├── api.py                      # Chức năng: Chứa logic của các API endpoint (ví dụ: nhận dữ liệu từ Pi).
│   └── requirements_server.txt     # Chức năng: Liệt kê thư viện Python cần cài (Flask, mysql-connector...).
│
├── 📂 data_and_training/           # =========================================================
│   │                               # == MÔI TRƯỜNG HUẤN LUYỆN AI (TRÊN MÁY TÍNH CÓ GPU) ==
│   ├── 📂 dataset/
│   │   ├── images/                 # Chức năng: Chứa hàng ngàn ảnh thô đã chụp từ Pi.
│   │   └── labels/                 # Chức năng: Chứa các file nhãn tương ứng với mỗi ảnh.
│   ├── train.py                    # Chức năng: Script Python để bắt đầu quá trình huấn luyện mô hình AI.
│   └── data.yaml                   # Chức năng: File cấu hình, chỉ cho script train biết dữ liệu nằm ở đâu.
│
└── README.md                       # Chức năng: File văn bản giới thiệu tổng quan, hướng dẫn cài đặt và sử dụng dự án.