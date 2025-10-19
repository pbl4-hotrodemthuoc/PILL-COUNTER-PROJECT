# device_app/main.py

import cv2
import os
from ai_processor import AIProcessor

def main():
    # 1. Khởi tạo bộ xử lý AI
    processor = AIProcessor()

    # 2. Chỉ định đường dẫn tới ảnh cần kiểm tra
    image_path = os.path.join('device_app', 'test_images', '20241223103559_jpg.rf.10b3f2d0ae5f160fe21969691eeac3f9.jpg')

    # 3. Kiểm tra xem file ảnh có tồn tại không
    if not os.path.exists(image_path):
        print(f"Lỗi: Không tìm thấy ảnh tại '{image_path}'")
        return

    # 4. Gọi hàm đếm thuốc và nhận kết quả
    print(f"Đang xử lý ảnh: {image_path}...")
    # Biến pill_count vẫn được trả về nhưng chúng ta không dùng đến nó ở đây nữa
    pill_count, result_image = processor.count_pills_from_file(image_path)
    
    # 5. --- CÁC DÒNG PRINT KẾT QUẢ ĐÃ ĐƯỢC XÓA ---

    # 6. Hiển thị ảnh kết quả (đã có sẵn dòng tổng kết trên đó)
    # hiển thị chữ kết quả màu đen
    result_image = cv2.putText(result_image, f"Tong so: {pill_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    result_image_bgr = cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR)
    cv2.imshow("Ket qua dem thuoc", result_image_bgr)
    
    print("Một cửa sổ ảnh đã hiện lên. Nhấn phím bất kỳ trên cửa sổ đó để thoát.")
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()