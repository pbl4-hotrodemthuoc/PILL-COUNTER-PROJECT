# File: main_app.py (PHIEN BAN HOAN CHINH CUOI CUNG - Chay tren MacBook)

import sys
import threading
import asyncio
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK, ConnectionClosedError
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

# tạo 1 instance global (giữ sống suốt vòng đời chương trình)
comm = Communicate()

# --- WebSocket Server Logic ---
async def handler(websocket, path=None):
    """
    websocket: ServerConnection object from websockets library.
    path: optional (websockets may pass path argument).
    """
    global previous_frame_gray, stable_counter, last_stable_count, is_locked
    connected_clients.add(websocket)
    try:
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
    except Exception:
        client_ip = "unknown"

    comm.connection_status.emit(f"Ket noi: {client_ip}")
    comm.log_message.emit(f"[INFO] Client ket noi tu {client_ip}")
    print(f"[INFO] Client ket noi tu {client_ip}")

    # reset trạng thái khi có client mới
    previous_frame_gray = None
    stable_counter = 0
    last_stable_count = -1
    is_locked = False
    comm.count_update.emit("...")

    try:
        async for message in websocket:
            try:
                # chúng ta chỉ mong nhận bytes (ảnh nén)
                if not isinstance(message, (bytes, bytearray)):
                    continue

                # decode image
                nparr = np.frombuffer(message, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    comm.log_message.emit("[WARN] Nhận frame rỗng/không decode được")
                    continue

                # motion detection (dùng ảnh gray)
                current_frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                current_frame_gray = cv2.GaussianBlur(current_frame_gray, (21, 21), 0)

                if previous_frame_gray is not None:
                    frame_delta = cv2.absdiff(previous_frame_gray, current_frame_gray)
                    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                    change_percentage = (np.count_nonzero(thresh) / (thresh.shape[0] * thresh.shape[1])) * 100
                    if change_percentage > MOTION_THRESHOLD:
                        # nếu có chuyển động lớn thì mở lock lại và reset bộ đếm ổn định
                        if is_locked:
                            comm.count_update.emit("...")
                            comm.log_message.emit("[MOTION] Phát hiện chuyển động, đếm lại...")
                        is_locked = False
                        stable_counter = 0

                previous_frame_gray = current_frame_gray

                # nếu chưa lock thì chạy detection
                annotated_frame = frame.copy()
                try:
                    if not is_locked:
                        results = model(frame, verbose=False)
                        pill_count = len(results[0].boxes)

                        if pill_count == last_stable_count:
                            stable_counter += 1
                        else:
                            last_stable_count = pill_count
                            stable_counter = 0

                        # nếu đủ ổn định -> lock kết quả
                        if stable_counter >= STABILITY_COUNT:
                            is_locked = True
                            comm.log_message.emit(f"[STABLE] Đã chốt kết quả: {last_stable_count} viên.")
                            comm.count_update.emit(str(last_stable_count))

                            response_data = {"type": "count_update", "status": "Da chot", "count": last_stable_count}
                            try:
                                await websocket.send(json.dumps(response_data))
                            except (ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                                comm.log_message.emit("[WARN] Client đóng khi gửi Da chot")
                                break
                        else:
                            # trạng thái đang đếm
                            response_data = {"type": "count_update", "status": "Dang dem", "count": ""}
                            try:
                                await websocket.send(json.dumps(response_data))
                            except (ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                                comm.log_message.emit("[WARN] Client đóng khi gửi Dang dem")
                                break

                        # tạo ảnh chú thích từ kết quả (dùng plot của ultralytics)
                        annotated_frame = results[0].plot()
                        summary_text = f"Dang dem: {last_stable_count} ({stable_counter}/{STABILITY_COUNT})"
                        cv2.putText(annotated_frame, summary_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                    else:
                        # đã lock — dùng văn bản chốt lên khung
                        summary_text = f"Da chot: {last_stable_count}"
                        cv2.putText(annotated_frame, summary_text, (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                except Exception as det_ex:
                    # nếu model lỗi, chỉ log và tiếp tục (không crash toàn bộ server)
                    comm.log_message.emit(f"[ERROR] Lỗi detection: {det_ex}")
                    traceback.print_exc()

                # gửi frame sang GUI
                try:
                    # emit phải an toàn (nếu GUI đã đóng, signal vẫn an toàn — nhưng bọc try để phòng)
                    comm.frame_processed.emit(annotated_frame)
                except RuntimeError:
                    # GUI có thể đã bị đóng; log và tiếp tục
                    print("[WARN] Không thể emit frame_processed (GUI có thể đã đóng).")

            except Exception as e:
                # lỗi trong vòng lặp xử lý 1 message
                comm.log_message.emit(f"[ERROR] Lỗi trong vòng lặp xử lý message: {e}")
                traceback.print_exc()

    except (ConnectionClosedOK, ConnectionClosedError, ConnectionClosed) as e:
        # client đóng kết nối
        comm.log_message.emit(f"[INFO] Client {client_ip} đã ngắt kết nối ({e}).")
        print(f"[INFO] Client {client_ip} da ngat ket noi. {e}")
    except Exception as e:
        comm.log_message.emit(f"[ERROR] Lỗi không mong muốn ở handler: {e}")
        traceback.print_exc()
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        comm.connection_status.emit("Ngat ket noi")
        comm.log_message.emit(f"[INFO] Cleanup kết thúc cho client {client_ip}")

# --- Cac ham chay server ---
async def start_websocket_server():
    print(f"[INFO] WebSocket server chay tai ws://{SERVER_HOST}:{SERVER_PORT}")
    comm.log_message.emit(f"[INFO] WebSocket server chay tai ws://{SERVER_HOST}:{SERVER_PORT}")
    # ping_interval và ping_timeout đặt để giữ kết nối
    async with websockets.serve(handler, SERVER_HOST, SERVER_PORT, ping_interval=20, ping_timeout=20):
        await asyncio.Future()  # chạy mãi

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
        self.count_label = QLabel("...")
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

        # connect signals
        comm.frame_processed.connect(self.update_image)
        comm.connection_status.connect(self.update_connection_status)
        comm.log_message.connect(self.add_log)
        comm.count_update.connect(self.update_count)

    def update_image(self, cv_img):
        try:
            rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            # nếu hình không hợp lệ, show text
            self.video_label.setText("Lỗi hiển thị hình ảnh")

    def update_connection_status(self, message):
        self.statusBar().showMessage(message)
        if "Ket noi" in message:
            self.status_label.setText("Trang thai: Da ket noi")
            self.status_label.setStyleSheet("color: lightgreen;")
        else:
            self.status_label.setText("Trang thai: Ngat ket noi")
            self.status_label.setStyleSheet("color: red;")
            self.video_label.setText("Tin hieu bi gian doan...")
            self.count_label.setText("...")

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

    # start websocket server in background thread
    threading.Thread(target=run_server_in_thread, daemon=True).start()

    # start Qt app
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())