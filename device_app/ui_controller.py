# File: device_app/ui_controller.py (Thêm các dòng print)

from PyQt5.QtWidgets import QMainWindow, QLabel, QWidget, QVBoxLayout, QStatusBar
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
import cv2

from ai_processor import AIProcessor # Sửa lại thành import tuyệt đối

class UIController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bang Dieu Khien AI Dem & Phan Loai Thuoc")
        self.setGeometry(100, 100, 900, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        self.video_label = QLabel("Dang cho tin hieu tu Raspberry Pi...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: 2px solid #555; background-color: black; color: white;")
        layout.addWidget(self.video_label)
        self.setStatusBar(QStatusBar())

        self.ai_processor = AIProcessor()
        print("[UI-CONTROLLER] Da khoi tao xong.")

    def handle_new_raw_frame(self, raw_frame):
        print("[UI-CONTROLLER] Da nhan duoc tin hieu raw_frame_received!")
        if self.ai_processor.model:
            processed_frame, pill_counts = self.ai_processor.process_frame_with_classification(raw_frame)
            print("[UI-CONTROLLER] Da xu ly AI xong, chuan bi cap nhat giao dien.")
            self.update_video_display(processed_frame)
            
            status_text = "Ket qua: " + " | ".join([f"{k}: {v}" for k, v in pill_counts.items()])
            self.statusBar().showMessage(status_text)

    def update_video_display(self, cv_img):
        print("[UI-CONTROLLER] Dang cap nhat hinh anh len giao dien...")
        try:
            rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            print("[UI-CONTROLLER] Cap nhat hinh anh thanh cong.")
        except Exception as e:
            print(f"[UI-CONTROLLER ERROR] Loi khi hien thi anh: {e}")
        
    def update_connection_status(self, message):
        print(f"[UI-CONTROLLER] Cap nhat trang thai: {message}")
        self.statusBar().showMessage(message)