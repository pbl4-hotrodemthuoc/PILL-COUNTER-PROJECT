# File: device_app/headless_ai.py
import asyncio
import websockets
import cv2
import numpy as np
import base64
import socketio
from ultralytics import YOLO
import os

# --- CẤU HÌNH ---
WEB_URL = 'http://127.0.0.1:5001'  # Địa chỉ Web Server
WS_PORT = 8765                     # Cổng nhận video từ Pi
MODEL_PATH = 'models/best.pt'      # Đường dẫn model

# Khởi tạo
sio = socketio.Client()
model = YOLO(MODEL_PATH)

# Kết nối tới Web Server
try:
    sio.connect(WEB_URL)
    print(f"✅ Đã kết nối tới Web Server: {WEB_URL}")
except Exception as e:
    print(f"⚠️ Không thể kết nối Web Server: {e}")

async def handler(websocket):
    print(f"✅ Pi đã kết nối từ {websocket.remote_address}")
    try:
        async for message in websocket:
            if not isinstance(message, bytes): continue

            # 1. Giải mã ảnh từ Pi
            nparr = np.frombuffer(message, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None: continue

            # 2. AI Xử lý
            results = model(frame, verbose=False)
            
            count = 0
            conf_sum = 0
            pills = []

            for box in results[0].boxes:
                conf = float(box.conf[0])
                if conf < 0.5: continue # Lọc độ tin cậy thấp

                # Lấy tọa độ
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Crop ảnh viên thuốc (để hiển thị chi tiết)
                crop = frame[y1:y2, x1:x2]
                if crop.size > 0:
                    _, c_buf = cv2.imencode('.jpg', crop)
                    c_b64 = base64.b64encode(c_buf).decode('utf-8')
                    pills.append({'image': c_b64, 'conf': int(conf*100)})

                count += 1
                conf_sum += conf
                
                # Vẽ khung lên ảnh chính
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{conf:.2f}", (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            avg_conf = int((conf_sum / count) * 100) if count > 0 else 0

            # 3. Mã hóa ảnh chính để gửi lên Web
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            frame_b64 = base64.b64encode(buffer).decode('utf-8')

            # 4. Gửi dữ liệu lên Web
            if sio.connected:
                sio.emit('ai_stream_data', {
                    'main_image': frame_b64,
                    'count': count,
                    'confidence': avg_conf,
                    'pills': pills # Danh sách ảnh crop từng viên
                })

    except Exception as e:
        print(f"❌ Lỗi xử lý: {e}")
    finally:
        print("🔌 Pi ngắt kết nối")

async def main():
    print(f"🚀 AI Engine đang chạy tại ws://0.0.0.0:{WS_PORT}")
    async with websockets.serve(handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())