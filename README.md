# 💊 Pill Counter System - Automated Medication Counting System

> An intelligent pill counting system using AI (YOLOv11) and Raspberry Pi 4 to automate prescription verification in pharmacies.

![Banner](link_anh_banner_here)

## 📋 Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Technologies](#technologies)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Demo](#demo)

---

## 🎯 Introduction

**Pill Counter System** is an automation solution for pharmacies that helps pharmacists count and verify prescriptions quickly and accurately. The system combines:

- **AI Vision** with YOLOv11 for pill detection and counting
- **Raspberry Pi 4** as the image acquisition device
- **Real-time Processing** via WebSocket and SocketIO
- **Web Dashboard** for prescription management and analytics

### 🎬 Demo Video
![Demo Video](link_video_demo_here)

---

## ✨ Features

### 🔹 For Pharmacists
- ✅ Create and manage digital prescriptions
- ✅ Automatic counting with AI (high accuracy)
- ✅ Compare actual quantity vs prescription
- ✅ View prescription history and personal statistics
- ✅ Report incidents (defective pills, device errors)

### 🔹 For Administrators
- 📊 Comprehensive dashboard analytics
- 👥 User management (pharmacists)
- 💊 Medication catalog management
- 📈 Performance reports (AI accuracy, processing time)
- 🔧 Device management (Raspberry Pi)

### 🔹 AI Technology
- **YOLOv11** - Real-time pill detection and counting
- **Auto-locking** - Automatic result confirmation when stable
- **Confidence scoring** - Reliability assessment
- **OpenCV** - Pill color classification (optional)

![AI Detection](link_anh_ai_detection_here)

---

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph Device["🔴 Raspberry Pi 4"]
        CAM[Camera Module]
        PI_APP[PyQt5 Client App]
    end
    
    subgraph Server["💻 Flask Server"]
        WEB[Web Dashboard]
        AI[YOLO AI Engine]
        DB[(MySQL Database)]
        SOCKET[SocketIO Real-time]
    end
    
    subgraph Users["👥 Users"]
        ADMIN[Admin]
        PHARM[Pharmacist]
    end
    
    CAM -->|WebSocket Stream| PI_APP
    PI_APP -->|Base64 Frames| SOCKET
    SOCKET -->|Process| AI
    AI -->|Results| WEB
    WEB --> DB
    ADMIN --> WEB
    PHARM --> WEB
    
    style Device fill:#ff6b6b
    style Server fill:#4ecdc4
    style Users fill:#95e1d3
```

### Workflow

1. **Raspberry Pi Camera** → Captures pill images
2. **Stream Transfer** → Sends frames via WebSocket
3. **AI Processing** → YOLO detects and counts pills
4. **Auto-lock** → Automatically confirms when count stabilizes
5. **Save to Database** → Compares with prescription, updates status
6. **Notification** → Real-time updates via SocketIO

![System Flow](link_anh_system_flow_here)

---

## 🛠️ Technologies

### Backend
- **Flask** - Main web framework
- **Flask-SQLAlchemy** - ORM for MySQL
- **Flask-SocketIO + Eventlet** - Real-time bi-directional communication
- **Ultralytics YOLOv11** - Object detection model
- **OpenCV** - Image processing
- **MySQL** - Relational database

### Frontend
- **Jinja2 Templates** - Server-side rendering
- **Socket.IO Client** - Real-time updates
- **Bootstrap 5** - Responsive UI
- **Chart.js** - Data visualization

### IoT Device (Raspberry Pi 4)
- **PyQt5** - Desktop client application
- **WebSocket** - Video streaming
- **Ultralytics YOLO** - On-device inference (optional)
- **OpenCV** - Camera capture

### AI Training
- **Roboflow** - Dataset annotation and management
- **YOLOv11** - Training and inference
- **PyTorch** - Deep learning framework

![Technology Stack](link_anh_tech_stack_here)

---

## 📦 Installation

### 1️⃣ System Requirements

**Server**
- Python 3.8+
- MySQL 5.7+
- 4GB RAM (minimum)
- GPU (recommended for AI)

**Raspberry Pi 4**
- Raspberry Pi OS (64-bit)
- Camera Module v2 or USB Camera
- 2GB RAM (minimum)

### 2️⃣ Server Installation

```bash
# Clone repository
git clone <repo_url>
cd PILL_COUNTER_PROJECT

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r server_app/requirements_server.txt

# Configure database (create .env file)
cat > .env << EOF
DATABASE_URL=mysql://user:password@localhost/pill_counter_db
SECRET_KEY=your-secret-key-here
UPLOAD_FOLDER=server_app/static/uploads
EOF

# Create database and import schema
flask db upgrade

# Seed sample data
flask seed-db

# Run server
python run.py
```

Server will run at: `http://127.0.0.1:5001`

### 3️⃣ Raspberry Pi Client Installation

```bash
# SSH into Raspberry Pi
ssh pi@<raspberry_pi_ip>

# Clone code (or copy device_app folder)
cd PILL_COUNTER_PROJECT/device_app

# Install dependencies
pip install -r requirements_pi.txt

# Configure server URL (edit in main.py if needed)
# Run application
python main.py
```

### 4️⃣ Train Model (Optional)

```bash
cd data_and_training

# Ensure dataset exists in ./dataset (from Roboflow)
# Structure: dataset/train, dataset/valid, dataset/test

# Run training
python train.py

# Model will be saved at: runs/detect/trainX/weights/best.pt
# Copy model to correct location
cp runs/detect/train/weights/best.pt ../device_app/models/best.pt
```

---

## 🚀 Usage

### System Login

**Admin**
- Username: `admin`
- Password: `admin123`

**Pharmacist**
- Username: `duocsi1` - `duocsi5`
- Password: `duocsi123`

### Pill Counting Workflow

1. **Create Prescription**
   - Go to `Pharmacist Dashboard` → `New Prescription`
   - Add medications and required quantities
   - Save prescription

2. **Connect Device**
   - Start application on Raspberry Pi
   - Check connection status (green icon)

3. **Count Pills**
   - Go to `Counting` → Select prescription to process
   - Place pills in camera view area
   - System automatically counts and locks result
   - Confirm and save

4. **View Reports**
   - Dashboard displays detailed statistics
   - Prescription history can be exported to Excel

![Usage Flow](link_anh_usage_flow_here)

---

## 📂 Project Structure

```
PILL_COUNTER_PROJECT/
├── 📁 server_app/              # Flask backend
│   ├── __init__.py
│   ├── models.py               # Database models (13 tables)
│   ├── admin.py                # Admin routes
│   ├── pharmacist.py           # Pharmacist routes + AI logic
│   ├── auth.py                 # Authentication
│   ├── extensions.py           # Flask extensions
│   ├── templates/              # Jinja2 templates
│   ├── static/                 # CSS, JS, images
│   └── requirements_server.txt
│
├── 📁 device_app/              # Raspberry Pi client
│   ├── main.py                 # Main entry point
│   ├── ai_processor.py         # YOLO inference
│   ├── camera_handler.py       # WebSocket video stream
│   ├── ui_controller.py        # PyQt5 UI
│   ├── models/best.pt          # YOLOv11 model
│   └── requirements_pi.txt
│
├── 📁 data_and_training/       # AI training
│   ├── dataset/                # Roboflow dataset
│   ├── train.py                # Training script
│   ├── data.yaml               # YOLO config
│   └── preprocess_images.py
│
├── 📁 migrations/              # Database migrations
├── run.py                      # Server entry point
└── README.md
```

---

## 🎨 Screenshots

### Admin Dashboard
![Admin Dashboard](link_anh_admin_dashboard_here)

### Pharmacist Counting Interface
![Counting Interface](link_anh_counting_interface_here)

### Statistics & Reports
![Statistics](link_anh_statistics_here)

---

## 📊 Database Schema

The system uses **13 main tables**:

- `nguoi_dung` - User management (admin, pharmacists)
- `loai_thuoc` - Medication catalog
- `don_thuoc` - Prescriptions
- `chi_tiet_don_thuoc` - Prescription details per medication
- `thiet_bi` - Raspberry Pi device management
- `bao_cao_su_co` - Incident reports
- `thong_bao` - Notification system
- `nhat_ky_he_thong` - System logs

![Database Schema](link_anh_database_schema_here)

---

## 🔬 AI Model Details

### Training Dataset
- **Source**: Roboflow (custom pill dataset)
- **Classes**: 1 class (`cap` - pill)
- **Annotations**: YOLO format
- **Splits**: Train/Valid/Test

### Model Performance
- **Framework**: YOLOv11n (Nano - optimized for Edge devices)
- **Input**: 640x640
- **Inference Time**: ~20-30ms on GPU, ~100-150ms on Raspberry Pi
- **Confidence Threshold**: 0.5

### Auto-locking Algorithm
```python
# Auto-lock when count is stable for 8 consecutive frames
if count == last_count:
    stable_count += 1
    if stable_count >= STABLE_THRESHOLD:
        locked = True
```

---

## 🤝 Contributing

This project is developed for educational and research purposes. All contributions are welcome!

---

## 👨‍💻 Authors

**Team Members:**

**Nguyen Thanh Huyen**
- GitHub: [@Chizk23](https://github.com/Chizk23)

**Nguyen Thi Bich Uyen**
- GitHub: [@BichUyen2609](https://github.com/BichUyen2609)

**Tran Thi Phuong**
- GitHub: [@PhuongTran2212](https://github.com/PhuongTran2212)

---

## 🙏 Acknowledgments

- **Ultralytics** - YOLOv11 framework
- **Roboflow** - Dataset management platform
- **Flask Community** - Web framework and extensions

---

**⭐ If you find this project helpful, please give it a star!**
