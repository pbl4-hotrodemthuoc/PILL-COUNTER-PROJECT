# device_app/ai_processor.py

from ultralytics import YOLO
import os
import cv2

class AIProcessor:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, 'models', 'best.pt')
        self.model = YOLO(model_path)
        print(f"Model AI đã được nạp từ: {model_path}")

    def count_pills_from_file(self, image_path):
        results = self.model(image_path, verbose=False)
        result = results[0]
        
        pill_count = len(result.boxes)
        
        annotated_image = result.orig_img.copy()
        
        # --- Các tham số để vẽ hộp và số thứ tự ---
        box_color = (255, 0, 0)
        box_thickness = 1
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1
        text_color = (255, 255, 255)
        
        for i, box in enumerate(result.boxes):
            coords = box.xyxy[0].tolist()
            x1, y1, x2, y2 = map(int, coords)
            
            cv2.rectangle(annotated_image, (x1, y1), (x2, y2), box_color, box_thickness)
            
            label = str(i + 1)
            text_position = (x1, y1 - 5)
            cv2.putText(annotated_image, label, text_position, font, font_scale, text_color, font_thickness)

        # --- BƯỚC MỚI: VẼ TỔNG SỐ LƯỢNG LÊN ẢNH ---
        summary_text = f"Tong so: {pill_count}"
        
        # Các tham số cho chữ tổng kết (to hơn, nổi bật hơn)
        summary_font_scale = 1.0
        summary_font_thickness = 2
        summary_color = (0, 255, 0) # Màu xanh lá (BGR)
        
        # Vị trí ở góc trên bên trái
        summary_position = (10, 30) # 10 pixel từ trái, 30 pixel từ trên
        
        # Vẽ chữ tổng kết lên ảnh
        cv2.putText(annotated_image, summary_text, summary_position, font, summary_font_scale, summary_color, summary_font_thickness)
        
        # Trả về ảnh đã có đầy đủ thông tin
        return pill_count, annotated_image