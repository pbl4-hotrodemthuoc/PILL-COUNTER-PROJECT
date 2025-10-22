from ultralytics import YOLO
import os
import cv2

class AIProcessor:
    def __init__(self):
        # Duong dan toi model van duoc giu nguyen, rat tot!
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, 'models', 'best.pt')
        self.model = YOLO(model_path)
        print(f"Model AI da duoc nap tu: {model_path}")

    def process_frame(self, frame):
        """
        Xu ly mot khung hinh (frame) tu camera, dem va ve ket qua.
        Day la ham chinh cho viec xu ly real-time.
        """
        # 1. Thuc hien nhan dien tren frame
        results = self.model(frame, verbose=False)
        result = results[0]
        
        # 2. Lay so luong
        pill_count = len(result.boxes)
        
        # 3. Su dung ham plot() tien loi cua ultralytics de ve hop va nhan
        # Ham nay nhanh va hieu qua hon ve thu cong
        annotated_image = result.plot()
        
        # --- VE TONG SO LUONG LEN ANH ---
        summary_text = f"Tong so: {pill_count}"
        
        # Cac tham so cho chu tong ket
        font = cv2.FONT_HERSHEY_SIMPLEX
        summary_font_scale = 1.0
        summary_font_thickness = 2
        summary_color = (0, 255, 0) # Mau xanh la (BGR)
        summary_position = (10, 30)
        
        # Ve chu
        cv2.putText(annotated_image, summary_text, summary_position, font, summary_font_scale, summary_color, summary_font_thickness)
        
        return pill_count, annotated_image

    def count_pills_from_file(self, image_path):
        """
        Phuong thuc cu de xu ly tu file, van giu lai de test neu can.
        """
        image = cv2.imread(image_path)
        if image is None:
            return 0, None
        # Goi ham xu ly frame moi de tai su dung code
        return self.process_frame(image)