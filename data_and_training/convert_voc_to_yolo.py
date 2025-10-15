import xml.etree.ElementTree as ET
import os
import glob
from PIL import Image

# --- CẤU HÌNH ---
# Thư mục chứa các file XML sau khi giải nén
XML_DIR = 'pillsPicture/annotations'  # Đường dẫn tới thư mục annotations trong pillsPicture
IMAGE_DIR = 'cleaned_images'       # Đường dẫn tới thư mục images trong pillsPicture
OUTPUT_LABEL_DIR = 'dataset/labels' 
    
# Danh sách các lớp của bạn.
# Mở một vài file .xml trong thư mục annotations để xem tên class là gì.
# Dựa trên bộ dữ liệu này, tên class chỉ có một là "pill".
FINAL_CLASS_NAME = 'pill'
# Liệt kê tất cả các tên lớp có thể có trong dữ liệu gốc
POSSIBLE_CLASS_NAMES = ['pill', 'tablets'] 
# --- KẾT THÚC CẤU HÌNH ---

# Đảm bảo thư mục output tồn tại
os.makedirs(OUTPUT_LABEL_DIR, exist_ok=True)

# Hàm chuyển đổi tọa độ
def convert_voc_to_yolo(size, box):
    # size: (image_width, image_height)
    # box: (xmin, xmax, ymin, ymax)
    dw = 1. / size[0]
    dh = 1. / size[1]
    x = (box[0] + box[1]) / 2.0
    y = (box[2] + box[3]) / 2.0
    w = box[1] - box[0]
    h = box[3] - box[2]
    x = x * dw
    w = w * dw
    y = y * dh
    h = h * dh
    return (x, y, w, h)

# Lấy danh sách tất cả các file XML
xml_files = glob.glob(os.path.join(XML_DIR, '*.xml'))
print(f"Tìm thấy {len(xml_files)} file XML. Bắt đầu chuyển đổi...")

# Lấy ID của lớp cuối cùng mà chúng ta muốn (sẽ là 0)
final_class_id = 0

for xml_file in xml_files:
    basename = os.path.basename(xml_file)
    filename_no_ext = os.path.splitext(basename)[0]
    
    try:
        with Image.open(os.path.join(IMAGE_DIR, filename_no_ext + '.jpg')) as img:
            image_size = img.size
    except FileNotFoundError:
        # Bỏ qua các file XML không có ảnh tương ứng
        continue

    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    yolo_lines = []
    for obj in root.iter('object'):
        cls_name = obj.find('name').text
        
        # KIỂM TRA: Nếu tên lớp đọc được nằm trong danh sách các lớp có thể có
        if cls_name in POSSIBLE_CLASS_NAMES:
            xmlbox = obj.find('bndbox')
            b = (float(xmlbox.find('xmin').text), float(xmlbox.find('xmax').text),
                 float(xmlbox.find('ymin').text), float(xmlbox.find('ymax').text))
            
            bb = convert_voc_to_yolo(image_size, b)
            # Gán tất cả về cùng một ID là final_class_id (tức là 0)
            yolo_lines.append(f"{final_class_id} {' '.join(map(str, bb))}")

    # Chỉ ghi file nếu có nhãn hợp lệ
    if yolo_lines:
        with open(os.path.join(OUTPUT_LABEL_DIR, filename_no_ext + '.txt'), 'w') as f:
            f.write('\n'.join(yolo_lines))

print(f"\nHoàn tất! Đã chuyển đổi và lưu các file nhãn vào thư mục: '{OUTPUT_LABEL_DIR}'")