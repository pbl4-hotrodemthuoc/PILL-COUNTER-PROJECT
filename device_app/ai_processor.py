# File: device_app/ai_processor.py (PHIEN BAN HOAN THIEN)

from ultralytics import YOLO
import cv2
import numpy as np

class AIProcessor:
    def __init__(self, model_path='models/best.pt'):
        try:
            self.model = YOLO(model_path)
            print("[INFO] Da tai model YOLO thanh cong!")
        except Exception as e:
            self.model = None
            print(f"[CRITICAL] Khong the tai model YOLO: {e}")

    def classify_pill_color(self, pill_image):
        """
        Su dung OpenCV de phan loai mau sac cua vien thuoc da duoc cat.
        """
        # Chuyen anh sang khong gian mau HSV (de phan tich mau sac tot hon)
        hsv_image = cv2.cvtColor(pill_image, cv2.COLOR_BGR2HSV)

        # --- Dinh nghia cac dai mau HSV cho cac loai thuoc ---
        # Ban co the them hoac chinh sua cac dai mau nay
        color_ranges = {
            "TRANG": ([0, 0, 180], [180, 40, 255]),      # Mau trang
            "XANH_DUONG": ([90, 80, 2], [126, 255, 255]),   # Mau xanh duong
            "VANG": ([20, 100, 100], [30, 255, 255]),    # Mau vang
            "DO": ([0, 120, 70], [10, 255, 255])         # Mau do (co 2 dai, day la dai duoi)
        }

        max_pixels = 0
        detected_color = "KHONG_RO"

        for color_name, (lower, upper) in color_ranges.items():
            lower_bound = np.array(lower)
            upper_bound = np.array(upper)
            
            # Tao mot mask chi giu lai cac pixel trong dai mau
            mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
            
            # Dem so pixel cua mau do
            pixel_count = cv2.countNonZero(mask)
            
            if pixel_count > max_pixels:
                max_pixels = pixel_count
                detected_color = color_name
        
        return detected_color

    def process_frame_with_classification(self, frame):
        """
        Quy trinh xu ly 2 buoc: Phat hien bang YOLO, Phan loai bang OpenCV.
        """
        if self.model is None:
            return frame, {}

        # Buoc 1: Dung YOLO de phat hien vi tri tat ca cac vien thuoc
        results = self.model(frame, verbose=False)
        
        annotated_frame = frame.copy()
        pill_counts = {}

        # Buoc 2: Lap qua tung vien thuoc da phat hien
        for box in results[0].boxes:
            # Lay toa do hop bao
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Cat rieng hinh anh cua vien thuoc
            pill_crop = frame[y1:y2, x1:x2]
            
            if pill_crop.size == 0:
                continue
            
            # Dung OpenCV de phan loai mau sac
            color_label = self.classify_pill_color(pill_crop)
            
            # Cap nhat so luong dem duoc
            pill_counts[color_label] = pill_counts.get(color_label, 0) + 1
            
            # Ve hop bao va ten loai thuoc len anh
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(annotated_frame, color_label, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Ve bang tong ket so luong len goc anh
        y_offset = 30
        for label, count in pill_counts.items():
            summary_text = f"{label}: {count}"
            cv2.putText(annotated_frame, summary_text, (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)
            y_offset += 30
            
        return annotated_frame, pill_counts