import sys
import threading
import asyncio
import websockets
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QStatusBar, QTextEdit, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QImage, QFont
from ultralytics import YOLO
import cv2
import numpy as np

# ================== CONFIG ==================
MODEL_PATH = 'models/best.pt'
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8765
STABILITY_COUNT = 5
# ============================================

# ---------------- Global vars ----------------
connected_clients = set()
stable_counter = 0
previous_count = -1
is_locked = False

# ---------------- Signal class ----------------
class Communicate(QObject):
    frame_processed = pyqtSignal(np.ndarray)
    connection_status = pyqtSignal(str)
    log_message = pyqtSignal(str)
    count_update = pyqtSignal(str)

comm = Communicate()

# ---------------- WebSocket handler ----------------
async def handler(websocket):
    global stable_counter, previous_count, is_locked
    connected_clients.add(websocket)
    client_ip = websocket.remote_address[0]
    comm.connection_status.emit(f"Ket noi: {client_ip}")
    print(f"[INFO] Client ket noi tu {client_ip}")

    stable_counter = 0
    previous_count = -1
    is_locked = False

    try:
        async for message in websocket:
            if not isinstance(message, bytes):
                continue

            nparr = np.frombuffer(message, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            annotated_frame = frame.copy()

            # --- YOLO detect ---
            results = model(frame, verbose=False)
            total_count = len(results[0].boxes)

            # Ve bounding box
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Kiem tra on dinh
            if total_count == previous_count:
                stable_counter += 1
            else:
                previous_count = total_count
                stable_counter = 1

            if stable_counter >= STABILITY_COUNT:
                is_locked = True
                comm.log_message.emit(f"[STABLE] Tong so on dinh: {total_count} vien.")

            status_text = f"Tong so: {total_count}" + (" [CHOT]" if is_locked else "")
            comm.count_update.emit(status_text)
            comm.frame_processed.emit(annotated_frame)

    finally:
        connected_clients.remove(websocket)
        comm.connection_status.emit("Ngat ket noi")
        print(f"[INFO] Client ngat ket noi.")

# ---------------- Start server ----------------
async def start_websocket_server():
    print(f"[INFO] WebSocket server chay tai ws://{SERVER_HOST}:{SERVER_PORT}")
    async with websockets.serve(handler, SERVER_HOST, SERVER_PORT, ping_interval=20, ping_timeout=20):
        await asyncio.Future()

def run_server_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_websocket_server())
    loop.close()

# ---------------- PyQt5 GUI ----------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Pill Counter - YOLO Only")
        self.setFixedSize(1200, 700)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        grid_layout = QGridLayout(main_widget)

        self.video_label = QLabel("Dang cho tin hieu...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: 2px solid #666; background-color: black; color: white; font-size: 18px;")
        grid_layout.addWidget(self.video_label, 0, 0, 1, 2)

        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        grid_layout.addWidget(control_panel, 0, 2, 1, 1)
        grid_layout.setColumnStretch(0, 2)
        grid_layout.setColumnStretch(2, 1)

        self.status_label = QLabel("Trang thai: Chua ket noi")
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.status_label.setStyleSheet("color: red;")
        control_layout.addWidget(self.status_label)

        self.count_label_title = QLabel("So luong dem duoc:")
        self.count_label_title.setFont(QFont("Arial", 12))
        self.count_label = QLabel("N/A")
        self.count_label.setFont(QFont("Arial", 28, QFont.Bold))
        self.count_label.setStyleSheet("color: cyan;")
        control_layout.addWidget(self.count_label_title)
        control_layout.addWidget(self.count_label)

        self.log_label = QLabel("Nhat ky hoat dong:")
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("background-color: #111; color: #00FF00; font-family: 'Courier New'; border: 1px solid #444;")
        control_layout.addWidget(self.log_label)
        control_layout.addWidget(self.log_console)
        control_layout.addStretch()

        self.setStatusBar(QStatusBar())

        comm.frame_processed.connect(self.update_image)
        comm.connection_status.connect(self.update_connection_status)
        comm.log_message.connect(self.add_log)
        comm.count_update.connect(self.update_count)

    def update_image(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def update_connection_status(self, message):
        self.statusBar().showMessage(message)
        if "Ket noi" in message:
            self.status_label.setText("Trang thai: Da ket noi")
            self.status_label.setStyleSheet("color: lightgreen;")
        else:
            self.status_label.setText("Trang thai: Ngat ket noi")
            self.status_label.setStyleSheet("color: red;")
            self.video_label.setText("Tin hieu bi gian doan...")

    def add_log(self, message):
        self.log_console.append(message)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    def update_count(self, text):
        self.count_label.setText(text)

# ---------------- Main ----------------
if __name__ == '__main__':
    print("Dang khoi dong AI Pill Counter Server...")
    try:
        model = YOLO(MODEL_PATH)
        print(f"[INFO] Tai model tu '{MODEL_PATH}' thanh cong!")
    except Exception as e:
        print(f"[ERROR] Khong the tai model: {e}")
        sys.exit(1)

    threading.Thread(target=run_server_in_thread, daemon=True).start()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())