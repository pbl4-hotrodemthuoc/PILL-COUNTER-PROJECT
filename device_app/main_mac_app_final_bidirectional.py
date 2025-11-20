# File: main_mac_app_final_bidirectional.py (Chay tren MacBook)

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
import json
import traceback

# ================== CAU HINH ==================
MODEL_PATH = 'models/best.pt'
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8765
MOTION_THRESHOLD = 0.5
STABILITY_COUNT = 5
# ===============================================

# --- Bien toan cuc ---
previous_frame_gray = None
stable_counter = 0
last_stable_count = -1
is_locked = False
connected_clients = set()

# --- Lop Giao tiep ---
class Communicate(QObject):
    frame_processed = pyqtSignal(np.ndarray)
    connection_status = pyqtSignal(str)
    log_message = pyqtSignal(str)
    count_update = pyqtSignal(str)

comm = Communicate()

# --- WebSocket Server Logic (GIAO TIEP 2 CHIEU) ---
async def handler(websocket):
    global previous_frame_gray, stable_counter, last_stable_count, is_locked
    connected_clients.add(websocket)
    client_ip = websocket.remote_address[0]
    comm.connection_status.emit(f"Ket noi: {client_ip}")
    print(f"[INFO] Client ket noi tu {client_ip}")
    
    # Reset trang thai khi co ket noi moi
    previous_frame_gray = None
    stable_counter = 0
    last_stable_count = -1
    is_locked = False

    try:
        async for message in websocket:
            try:
                # Chi xu ly tin nhan bytes (du lieu anh)
                if not isinstance(message, bytes):
                    continue

                nparr = np.frombuffer(message, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                # --- Logic Dem Thong Minh ---
                current_frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                current_frame_gray = cv2.GaussianBlur(current_frame_gray, (21, 21), 0)

                if previous_frame_gray is not None:
                    frame_delta = cv2.absdiff(previous_frame_gray, current_frame_gray)
                    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                    change_percentage = (np.count_nonzero(thresh) / (thresh.shape[0] * thresh.shape[1])) * 100
                    if change_percentage > MOTION_THRESHOLD:
                        is_locked = False
                        stable_counter = 0

                previous_frame_gray = current_frame_gray

                if not is_locked:
                    results = model(frame, verbose=False)
                    pill_count = len(results[0].boxes)
                    if pill_count == last_stable_count:
                        stable_counter += 1
                    else:
                        last_stable_count = pill_count
                        stable_counter = 1

                    if stable_counter >= STABILITY_COUNT:
                        is_locked = True
                        comm.log_message.emit(f"[STABLE] Ket qua on dinh: {pill_count} vien.")
                
                # --- PHAN NANG CAP: GUI KET QUA NGUOC LAI CHO PI ---
                try:
                    response_data = {}
                    status_text_for_gui = ""
                    
                    if is_locked:
                        response_data = {"type": "count_update", "status": "Da chot", "count": last_stable_count}
                        status_text_for_gui = f"Da chot: {last_stable_count}"
                    else:
                        response_data = {"type": "count_update", "status": "Dang dem", "count": last_stable_count}
                        status_text_for_gui = "Dang dem..."
                    
                    # Gui du lieu JSON ve cho client (Pi)
                    await websocket.send(json.dumps(response_data))
                    
                    # Cap nhat giao dien Mac
                    comm.count_update.emit(status_text_for_gui)

                except websockets.exceptions.ConnectionClosed:
                    break # Thoat vong lap neu client da ngat ket noi khi dang gui

                # --- Ve Giao dien ---
                annotated_frame = frame.copy()
                if is_locked:
                    summary_text = f"Da chot: {last_stable_count}"
                    cv2.putText(annotated_frame, summary_text, (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                else:
                    annotated_frame = model(frame, verbose=False)[0].plot()
                    summary_text = f"Dang dem: {last_stable_count} ({stable_counter}/{STABILITY_COUNT})"
                    cv2.putText(annotated_frame, summary_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

                comm.frame_processed.emit(annotated_frame)
            
            except Exception as e:
                print(f"[ERROR] Loi trong vong lap xu ly message: {e}")
                traceback.print_exc()


    except websockets.exceptions.ConnectionClosed:
        print(f"[INFO] Client {client_ip} da ngat ket noi (trong).")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        comm.connection_status.emit("Ngat ket noi")
        print(f"[INFO] Client {client_ip} da ngat ket noi (ngoai).")


# --- Cac ham chay server ---
async def start_websocket_server():
    print(f"[INFO] WebSocket server chay tai ws://{SERVER_HOST}:{SERVER_PORT}")
    # Phien ban websockets cua ban khong can 'path'
    async with websockets.serve(handler, SERVER_HOST, SERVER_PORT, ping_interval=20, ping_timeout=20):
        await asyncio.Future()

def run_server_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_websocket_server())
    finally:
        loop.close()

# --- Giao dien PyQt5 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Pill Counter - Dashboard")
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

# --- Chay ---
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