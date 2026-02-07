# Pill Counter System - Automated Medication Counting System

> Automated pill counting system using AI technology (YOLOv11) and Raspberry Pi 4, designed to enhance accuracy and operational efficiency in pharmacies.

<p align="center">
  <img src="server_app/static/README/banner1.jpg" width="45%" />
  <img src="server_app/static/README/banner2.jpg" width="45%" />
</p>

## Table of Contents

1. [Introduction](#introduction)
2. [Key Features](#key-features)
3. [System Architecture](#system-architecture)
4. [Technologies Used](#technologies-used)
5. [Installation and Deployment](#installation-and-deployment)
6. [User Guide](#user-guide)
7. [Screenshots](#screenshots)
8. [Project Structure](#project-structure)

---

## Introduction

**Pill Counter System** is an integrated hardware and software solution that assists pharmacists in the prescription counting process. The system addresses human error in manual counting while digitizing transaction data for effective inventory management.

**Core Components:**
*   **AI Engine:** Uses a custom YOLOv11 model to detect and count pills with high accuracy.
*   **IoT Device:** Raspberry Pi 4 captures images, displays results on an LCD screen, and performs preliminary processing.
*   **Real-time Processing:** Instant data synchronization between the device and the management server via WebSocket.
*   **Management System:** Centralized Web Dashboard for activity monitoring and reporting.

### Demo Video
![Demo Video](link_video_demo_here)

---

## Key Features

### For Pharmacists (Operations)
*   Create and manage prescriptions on a digital system.
*   Automatically count pills via monitoring camera.
*   Automatically cross-check actual quantity against prescription requirements.
*   View transaction history and personal performance statistics.
*   Log and report incidents.

### For Administrators (Management)
*   Dashboard for overall data analysis.
*   Manage user accounts and permissions.
*   Manage medication catalog and data inventory.
*   Export performance reports and system logs.

### AI Technical Specifications
*   **Real-time Object Detection:** High response speed.
*   **Auto-locking Mechanism:** Algorithm automatically locks results when the count is stable across a sequence of frames, minimizing manual manipulation.
*   **Confidence Scoring:** Displays the reliability of object detection results.

---

## System Architecture

The system is designed following a Client-Server model with specialized modules:

```mermaid
graph TB
    subgraph Device["Device (Client)"]
        CAM[Camera Module]
        LCD[LCD Screen]
        PI_APP["Pi App (PyQt5)"]
    end
    
    subgraph Server["Server"]
        WEB[Web Dashboard]
        AI[YOLO AI Engine]
        DB[(MySQL Database)]
        SOCKET[SocketIO Server]
    end
    
    subgraph Users["Users"]
        ADMIN[Administrator]
        PHARM[Pharmacist]
    end
    
    CAM -->|Video Stream| PI_APP
    PI_APP -->|Display| LCD
    PI_APP -->|WebSocket/Images| SOCKET
    SOCKET -->|Image Processing| AI
    AI -->|Count Result| WEB
    WEB --> DB
    ADMIN --> WEB
    PHARM --> WEB
```

### Processing Workflow
1.  **Acquisition:** Camera on Raspberry Pi captures image of the pill tray.
2.  **Transmission:** Images are transmitted to Server via secure WebSocket protocol.
3.  **Analysis:** YOLOv11 model analyzes images, detects, and counts pills.
4.  **Verification:** System checks stability (Auto-lock) and automatically resets upon detecting motion (Motion Detection).
5.  **Display & Storage:** Results are displayed on the **Counting Interface** for Pharmacist confirmation, then saved to the database.

```mermaid
flowchart LR
    CAM([Pi Camera]) -->|1. Acquire| WS{WebSocket}
    WS -->|2. Transmit| YOLO[YOLOv11 AI]
    YOLO -->|3. Analyze & Count| LOCK{Auto-Lock}
    
    LOCK --Stable--> UI[Counting Interface]
    LOCK --Unstable--> YOLO
    
    UI -->|Confirm| SAVE[(Save to DB)]
    LOCK -.->|Result| LCD([LCD Screen])
    
    style CAM fill:#ff9999,stroke:#333,stroke-width:2px
    style YOLO fill:#99ccff,stroke:#333,stroke-width:2px
    style SAVE fill:#99ff99,stroke:#333,stroke-width:2px
    style UI fill:#e1d5e7,stroke:#9673a6,stroke-width:2px
```
*Figure 1: Detailed data flow diagram of the system.*

---

## Technologies Used

### Backend (Server)
*   **Language:** Python 3.8+
*   **Web Framework:** Flask
*   **Database:** MySQL (Using Flask-SQLAlchemy ORM)
*   **Real-time:** Flask-SocketIO
*   **AI/Computer Vision:** Ultralytics YOLOv11, OpenCV

### Frontend (Web)
*   **Interface:** Bootstrap 5, Jinja2 Templates
*   **Visualization:** Chart.js
*   **Communication:** Socket.IO Client

### IoT Device (Edge)
*   **Hardware:** Raspberry Pi 4 Model B
*   **OS:** Raspberry Pi OS (64-bit)
*   **Client App:** PyQt5
*   **Camera:** Module v2 or USB Webcam
*   **Display:** LCD Screen (I2C/SPI) communicating with Pi

---

## Installation and Deployment

### 1. System Requirements
*   **Server:** 4-core CPU, 8GB RAM, GPU (recommended for AI inference).
*   **Client:** Raspberry Pi 4 (4GB RAM or higher).

### 2. Server Setup

```bash
# Clone source code
git clone <repo_url>
cd PILL_COUNTER_PROJECT

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r server_app/requirements_server.txt

# Configure environment variables (.env)
cp .env.example .env
# Edit Database info in .env file

# Initialize database
flask db upgrade
flask seed-db

# Run server
python run.py
```

### 3. Workstation Setup (Raspberry Pi)

```bash
# Access Raspberry Pi
ssh pi@<ip_address>

# Install client libraries
cd device_app
pip install -r requirements_pi.txt

# Run client application
python main.py
```

---

## User Guide

### Login
*   **Administrator:** Default account `admin`
*   **Pharmacist:** Account provided by administrator (e.g., `duocsi1`)

### Pill Counting Process
1.  **Create Order:** Pharmacist creates a new prescription on the Web Dashboard.
2.  **Prepare:** Place pills on the counting tray under the camera.
3.  **Process:**
    *   System automatically detects pills.
    *   Results are displayed simultaneously on **LCD Screen** (local) and **Web Dashboard** (remote).
    *   When quantity is stable, system automatically locks the result (Auto-lock).
    *   Pharmacist verifies and clicks confirm.
4.  **Complete:** Data is saved to transaction history.

```mermaid
sequenceDiagram
    autonumber
    actor D as Pharmacist
    participant W as Web Dashboard
    participant H as Hardware (Pi/Cam)
    participant L as LCD Screen
    participant S as AI Analysis

    Note over D, W: 1. Initialize Prescription
    D->>W: Create new prescription (Enter required qty)
    W-->>D: Confirm prescription

    Note over D, H: 2. Prepare
    D->>H: Place pills on tray

    Note over H, S: 3. Real-time Processing
    loop Continuous Detection
        H->>S: Send stream image (WebSocket)
        S->>S: AI Detect & Count
        par Multi-platform Display
            S-->>W: Update Web Dashboard
            S-->>H: Return result
            H->>L: Display quantity
        end
    end

    Note over S: 4. Auto-Lock Mechanism
    S->>S: Stable count? (Stable Check)
    S-->>W: Auto-lock result (Locked)
    S-->>H: Lock result
    H->>L: Display "Locked" status

    Note over D, W: 5. Complete
    D->>W: Verify & Confirm Result
    W->>W: Save to Transaction History
    W-->>D: Success Notification
```

---

## Screenshots

### Admin Dashboard
![Admin Dashboard Screenshot](server_app/static/README/Admin_Dashboard.png)
*Figure 2: Admin dashboard with overview statistics.*

### Pharmacist Dashboard
![Pharmacist Dashboard Screenshot](server_app/static/README/duosi.png)
*Figure 3: Home interface for pharmacists.*

### Create Prescription
![Create Prescription Screenshot](server_app/static/README/taodon.png)
*Figure 4: Interface for creating new prescriptions.*

### Counting Interface (Pharmacist View)
![Counting Interface Screenshot](server_app/static/README/counting.png)
*Figure 5: Main operation screen for pharmacists.*

### Prescription History
![Prescription History Screenshot](server_app/static/README/History.png)
*Figure 6: List of completed prescription history.*

### Reports and Statistics
![Statistics Screenshot](server_app/static/README/Admin_Dashboard.png)
*Figure 7: Performance statistics and activity history.*

---

## Project Structure

```text
PILL_COUNTER_PROJECT/
├── server_app/              # Backend & Web Server Source
│   ├── models.py            # Database Models
│   ├── admin.py             # Admin Logic
│   ├── pharmacist.py        # Pharmacist & AI Logic
│   └── templates/           # User Interface
│
├── device_app/              # IoT Device Source (Client)
│   ├── main.py              # Main Program
│   ├── ai_processor.py      # AI Processing Module
│   └── ui_controller.py     # Device UI Controller
│
├── data_and_training/       # Data & Model Training
│   ├── dataset/             # Raw Images & Labels
│   └── train.py             # YOLO Training Script
│
└── requirements.txt         # Dependency List
```

---

## Additional Information

### Training Dataset
The model is trained on a high-quality dataset of pharmaceutical pill images collected in real-world scenarios and manually labeled, ensuring stable performance under various lighting conditions.


---

## Contributing

This project is developed for research and educational purposes. All contributions from the community are welcome and appreciated.

---

## Authors

**Development Team Members:**

**Nguyen Thanh Huyen**
- GitHub: [@Chizk23](https://github.com/Chizk23)

**Nguyen Thi Bich Uyen**
- GitHub: [@BichUyen2609](https://github.com/BichUyen2609)

**Tran Thi Phuong**
- GitHub: [@PhuongTran2212](https://github.com/PhuongTran2212)

---

**⭐ If you find this project helpful, please give it a star!**
