import time
import socketio
import cv2
import base64
import smbus
from picamera2 import Picamera2

# --- CAU HINH ---
# SERVER_IP = '10.144.229.235'
SERVER_IP = '192.168.2.7' # IP SERVER CU
SERVER_PORT = 5001
URL = f'http://{SERVER_IP}:{SERVER_PORT}'

# 800x600: Do net cao
FRAME_WIDTH = 800
FRAME_HEIGHT = 600
JPEG_QUALITY = 65

# --- CLASS LCD I2C (Mini Lib) ---
class I2C_LCD_driver:
    def __init__(self, address=0x27, bus=1):
        self.address = address
        try:
            self.bus = smbus.SMBus(bus)
            self.lcd_write(0x03)
            self.lcd_write(0x03)
            self.lcd_write(0x03)
            self.lcd_write(0x02)
            self.lcd_write(0x20 | 0x08 | 0x04 | 0x00)
            self.lcd_write(0x08 | 0x04 | 0x00) # Display On
            self.lcd_write(0x01) # Clear
            self.lcd_write(0x04 | 0x02 | 0x00) # Entry Mode
            time.sleep(0.2)
        except Exception as e:
            print(f"⚠️ LCD Init Error: {e}")
            self.bus = None

    def lcd_write(self, cmd, mode=0):
        if not self.bus: return
        try:
            self.bus.write_byte_data(self.address, 0, mode | (cmd & 0xF0) | 0x08)
            self.bus.write_byte_data(self.address, 0, mode | ((cmd << 4) & 0xF0) | 0x08)
        except: pass

    def lcd_display_string(self, string, line):
        if not self.bus: return
        if line == 1: cmd = 0x80
        elif line == 2: cmd = 0xC0
        else: return
        self.lcd_write(cmd)
        for char in string:
            self.lcd_write(ord(char), 1)

    def clear(self):
        self.lcd_write(0x01)

# --- HAM TIEN ICH ---
def remove_accents(input_str):
    if not input_str: return ""
    replacements = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a', 'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a', 'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e', 'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o', 'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o', 'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u', 'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'Ă': 'A', 'Â': 'A', 'Đ': 'D', 'Ê': 'E', 'Ô': 'O', 'Ơ': 'O', 'Ư': 'U'
    }
    s = input_str
    for k, v in replacements.items():
        s = s.replace(k, v)
        s = s.replace(k.upper(), v.upper())
    return s

# --- KHOI TAO SOCKET & LCD ---
lcd = I2C_LCD_driver() # Dia chi mac dinh 0x27
sio = socketio.Client(reconnection=True, request_timeout=5)

# Cache de chong nhap nhay
last_line1 = ""
last_line2 = ""

@sio.event
def connect():
    print(">>> DA KET NOI SERVER!")
    lcd.clear()
    lcd.lcd_display_string("CONNECTED!", 1)
    lcd.lcd_display_string(f"IP: {SERVER_IP}", 2)
    time.sleep(2)

@sio.event
def disconnect():
    print(">>> MAT KET NOI")
    lcd.clear()
    lcd.lcd_display_string("DISCONNECTED", 1)

# Lang nghe ket qua AI tu server
@sio.on('ai_result')
def on_ai_result(data):
    # data: {'count': 10, 'is_locked': True, 'status_text': 'Dư 2 viên', ...}
    count = data.get('count', 0)
    is_locked = data.get('is_locked', False)
    status_text = data.get('status_text', "")
    
    # Xu ly text khong dau cho LCD
    clean_status = remove_accents(status_text)
    
    # Hien thi DONG 1: So luong (+ Locked icon)
    line1 = f"SL: {count}"
    if is_locked: line1 += " [LOCKED]"
    
    # Hien thi DONG 2: Trang thai (Du/Thieu/Khop)
    line2 = clean_status[:16]
    
    # --- FIX FLICKERING: CHI CAP NHAT KHI NOI DUNG THAY DOI ---
    global last_line1, last_line2
    
    new_line1 = line1.ljust(16)
    new_line2 = line2.ljust(16)

    # Chi viet lai neu noi dung khac
    if new_line1 != last_line1:
        lcd.lcd_display_string(new_line1, 1)
        last_line1 = new_line1

    if new_line2 != last_line2:
        lcd.lcd_display_string(new_line2, 2)
        last_line2 = new_line2

def main_loop():
    # 1. Khoi tao Camera
    try:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"size": (FRAME_WIDTH, FRAME_HEIGHT)})
        picam2.configure(config)
        picam2.start()
        print(f"CAMERA OK: {FRAME_WIDTH}x{FRAME_HEIGHT}")
    except Exception as e:
        print(f"Loi Camera: {e}")
        lcd.lcd_display_string("LOI CAMERA", 1)
        return

    # 2. Vong lap ket noi
    while True:
        try:
            if not sio.connected:
                print(f"Dang ket noi {URL}...")
                lcd.lcd_display_string("Connecting...", 1)
                sio.connect(URL, transports=['websocket'])
                sio.emit('join_counting') # QUAN TRONG: Join room de nhan event ai_result
            
            # 3. GUI FRAME LIEN TUC
            while sio.connected:
                img_rgb = picam2.capture_array()
                img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                _, buffer = cv2.imencode('.jpg', img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                b64_string = base64.b64encode(buffer).decode('utf-8')
                
                # Gui frame len de AI xu ly
                sio.emit('process_frame_pi', {'image': f"data:image/jpeg;base64,{b64_string}"})
                
                time.sleep(0.04) # ~25 FPS

        except Exception as e:
            print(f"Loi: {e}")
            time.sleep(2)

if __name__ == '__main__':
    main_loop()
