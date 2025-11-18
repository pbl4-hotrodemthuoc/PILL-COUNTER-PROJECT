# File: device_app/camera_handler.py (Giữ nguyên phiên bản tương thích)

import asyncio
import websockets
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import cv2

class Communicate(QObject):
    raw_frame_received = pyqtSignal(np.ndarray)
    connection_status = pyqtSignal(str)

class StreamReceiver:
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.comm = Communicate()

    async def _handler(self, websocket): # <--- CHỈ 1 THAM SỐ
        client_ip = websocket.remote_address[0]
        self.comm.connection_status.emit(f"Client da ket noi tu: {client_ip}")
        print(f"[SERVER-HANDLER] Client {client_ip} da ket noi.")
        try:
            async for message in websocket:
                print(f"[SERVER-HANDLER] Da nhan duoc message, kich thuoc {len(message)}")
                if isinstance(message, bytes):
                    nparr = np.frombuffer(message, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        print("[SERVER-HANDLER] Frame hop le, chuan bi emit.")
                        self.comm.raw_frame_received.emit(frame)
        except websockets.exceptions.ConnectionClosed:
            self.comm.connection_status.emit(f"Client {client_ip} da ngat ket noi.")
        finally:
            self.comm.connection_status.emit("Dang cho ket noi...")

    async def _start_server(self):
        print(f"[INFO] Khoi dong WebSocket server tai ws://{self.host}:{self.port}")
        async with websockets.serve(self._handler, self.host, self.port):
            await asyncio.Future()

    def run_in_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._start_server())
        finally:
            loop.close()