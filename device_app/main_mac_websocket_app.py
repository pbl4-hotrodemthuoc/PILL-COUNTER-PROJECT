# File: main_mac_websocket_app.py (MacBook)

import sys
import threading
import asyncio
import websockets
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QStatusBar
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QImage
from ultralytics import YOLO
import cv2
import numpy as np
import traceback

# ================== CẤU HÌNH ==================
MODEL_PATH = 'models/best.pt'
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8765
# ===============================================

# --- Lớp Giao tiếp giữa WebSocket Server và PyQt ---
class Communicate(QObject):
    frame_processed = pyqtSignal(np.ndarray)
    connection_status = pyqtSignal(str)

comm = Communicate()


# --- WebSocket Server ---
async def handler(websocket):
    client_ip = websocket.remote_address[0]
    comm.connection_status.emit(f"📡 Client da ket noi tu: {client_ip}")
    print(f"[INFO] Client ket noi tu {client_ip}")

    try:
        async for message in websocket:
            try:
                nparr = np.frombuffer(message, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    print("[WARN] Khong the giai ma frame.")
                    continue

                # --- Xử lý bằng model YOLO ---
                results = model(frame, verbose=False)
                annotated_frame = results[0].plot()
                pill_count = len(results[0].boxes)

                # --- Ghi chữ tiếng Việt không dấu, màu trắng sáng ---
                summary_text = f"So luong: {pill_count}"
                cv2.putText(
                    annotated_frame, summary_text, (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA
                )

                # --- Phát lên giao diện ---
                comm.frame_processed.emit(annotated_frame)

            except Exception as e:
                print(f"[ERROR] Loi khi xu ly frame: {e}")
                traceback.print_exc()
                continue

    except websockets.exceptions.ConnectionClosed:
        print(f"[INFO] Client {client_ip} da ngat ket noi.")
        comm.connection_status.emit(f"Client {client_ip} da ngat ket noi.")
    except Exception as e:
        print(f"[FATAL] Loi bat thuong trong handler(): {e}")
        traceback.print_exc()
    finally:
        comm.connection_status.emit("Dang cho ket noi...")
        print("[INFO] Dang cho ket noi...")


# --- Hàm chạy server ---
async def start_websocket_server():
    print(f"[INFO] Khoi dong WebSocket server tai ws://{SERVER_HOST}:{SERVER_PORT}")
    async with websockets.serve(handler, SERVER_HOST, SERVER_PORT):
        await asyncio.Future()


def run_server_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_websocket_server())
    finally:
        loop.close()


# --- Giao diện PyQt5 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("💊 AI Pill Counter - WebSocket Realtime")
        self.setGeometry(100, 100, 900, 700)
        self.setFixedSize(900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)

        # --- Khung hiển thị video ---
        self.video_label = QLabel("Dang cho tin hieu tu Raspberry Pi...")
        self.video_label.setFixedSize(800, 600)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            border: 2px solid #aaa;
            background-color: #111;
            color: #f2f2f2;
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(self.video_label, alignment=Qt.AlignCenter)

        # --- Thanh trạng thái ---
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("color: white; background-color: #222;")
        self.setStatusBar(self.status_bar)

        comm.frame_processed.connect(self.update_image)
        comm.connection_status.connect(self.update_status)

        self.update_status("Server dang khoi dong...")

    def update_image(self, cv_img):
        try:
            rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            scaled_pixmap = pixmap.scaled(
                self.video_label.width(),
                self.video_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"[ERROR] Loi hien thi anh: {e}")
            traceback.print_exc()

    def update_status(self, message):
        self.status_bar.showMessage(message)


# --- Điểm bắt đầu ---
if __name__ == '__main__':
    print("🚀 Dang khoi dong AI Pill Counter Server...")

    try:
        model = YOLO(MODEL_PATH)
        print(f"[INFO] Tai model AI tu '{MODEL_PATH}' thanh cong!")
    except Exception as e:
        print(f"[CRITICAL] Khong the tai model AI: {e}")
        traceback.print_exc()
        sys.exit(1)

    server_thread = threading.Thread(target=run_server_in_thread, daemon=True)
    server_thread.start()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())