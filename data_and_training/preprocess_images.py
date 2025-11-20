import os
import cv2  # Thư viện OpenCV

# --- CẤU HÌNH ---
# 1. Thiết lập đường dẫn dữ liệu
RAW_IMAGE_DIR = 'pillsPicture/images'      # Thư mục chứa ảnh gốc, lộn xộn
CLEANED_IMAGE_DIR = 'cleaned_images'       # Thư mục tạm để lưu ảnh đã được xử lý

TARGET_SIZE = (640, 640) # Kích thước chuẩn cho tất cả ảnh
# --- KẾT THÚC CẤU HÌNH ---

# 2. Viết khung chính của script
def preprocess_all_images():
    """
    Hàm này đọc tất cả ảnh từ thư mục nguồn, tiền xử lý chúng
    và lưu vào thư mục đích.
    """
    print("Bắt đầu quá trình tiền xử lý ảnh...")
    
    # Tạo thư mục đích nếu nó chưa tồn tại
    os.makedirs(CLEANED_IMAGE_DIR, exist_ok=True)

    # Lấy danh sách tất cả các file trong thư mục ảnh gốc
    filenames = os.listdir(RAW_IMAGE_DIR)
    
    # 3. Tạo vòng lặp qua thư mục
    for i, filename in enumerate(filenames):
        # Lọc ra chỉ các file ảnh
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                # Tạo đường dẫn đầy đủ đến file ảnh gốc
                source_path = os.path.join(RAW_IMAGE_DIR, filename)
                
                # Đọc ảnh bằng OpenCV
                image = cv2.imread(source_path)

                # Kiểm tra xem ảnh có đọc được không
                if image is None:
                    print(f"  - Cảnh báo: Không thể đọc file {filename}. Bỏ qua.")
                    continue
                
                # Thay đổi kích thước ảnh về kích thước chuẩn
                resized_image = cv2.resize(image, TARGET_SIZE)

                # Tạo tên file mới (luôn là .jpg để đồng nhất)
                new_filename = os.path.splitext(filename)[0] + '.jpg'
                dest_path = os.path.join(CLEANED_IMAGE_DIR, new_filename)

                # Lưu ảnh đã xử lý
                cv2.imwrite(dest_path, resized_image)

                # In ra tiến trình
                print(f"  ({i+1}/{len(filenames)}) Đã xử lý: {filename} -> {new_filename}")

            except Exception as e:
                print(f"  - Lỗi khi xử lý file {filename}: {e}")
    
    print("\nHoàn tất quá trình tiền xử lý ảnh!")
    print(f"Ảnh đã được làm sạch và lưu tại thư mục: '{CLEANED_IMAGE_DIR}'")

# Entry point để chạy script
if __name__ == '__main__':
    preprocess_all_images()