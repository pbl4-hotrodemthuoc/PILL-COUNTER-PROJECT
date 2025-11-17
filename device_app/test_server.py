import asyncio
import websockets
import cv2
import numpy as np
from ultralytics import YOLO

MODEL_PATH = 'models/best.pt'
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8765

model = YOLO(MODEL_PATH)

async def handler(websocket):  # chỉ 1 tham số
    client_ip = websocket.remote_address[0]
    print(f"[INFO] Client kết nối từ {client_ip}")
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                nparr = np.frombuffer(message, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    results = model(frame, verbose=False)
                    pill_count = len(results[0].boxes)
                    print(f"Đã xử lý frame, phát hiện {pill_count} viên.")
            else:
                print(f"[WARN] Nhận tin nhắn text: {message}")
    except websockets.exceptions.ConnectionClosed:
        print(f"[INFO] Client {client_ip} đã ngắt kết nối.")

async def main():
    print(f"[INFO] Server chạy tại ws://{SERVER_HOST}:{SERVER_PORT}")
    async with websockets.serve(handler, SERVER_HOST, SERVER_PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())