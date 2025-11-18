# File: device_app/main.py (PHIÊN BẢN ỔN ĐỊNH NHẤT)

import sys
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, QObject

from ui_controller import UIController
from camera_handler import StreamReceiver

class ServerWorker(QObject):
    """
    Lop Worker de chay StreamReceiver trong mot luong rieng.
    Cach nay dam bao cac doi tuong khong bi xoa boi garbage collector.
    """
    def __init__(self):
        super().__init__()
        self.stream_receiver = StreamReceiver()

    def run(self):
        """Phuong thuc nay se duoc chay khi luong bat dau."""
        print("[WORKER] Bat dau luong server...")
        self.stream_receiver.run_in_thread()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 1. Tao cua so chinh (luong chinh)
    main_window = UIController()
    
    # 2. Tao luong QThread de chay server
    server_thread = QThread()
    # Tao worker chua logic server
    server_worker = ServerWorker()
    
    # 3. Di chuyen worker vao luong server
    # Dieu nay dam bao toan bo code cua worker se chay trong luong do
    server_worker.moveToThread(server_thread)
    
    # 4. Ket noi cac tin hieu (quan trong!)
    # Ket noi signal cua worker (chay trong luong server) voi slot cua window (chay trong luong chinh)
    server_worker.stream_receiver.comm.raw_frame_received.connect(main_window.handle_new_raw_frame)
    server_worker.stream_receiver.comm.connection_status.connect(main_window.update_connection_status)
    
    # Khi luong bat dau, no se goi ham run() cua worker
    server_thread.started.connect(server_worker.run)
    
    # Don dep an toan khi ung dung dong
    app.aboutToQuit.connect(server_thread.quit) # Yeu cau luong dung lai
    app.aboutToQuit.connect(server_thread.wait) # Cho luong dung hoan toan
    
    # 5. Bat dau luong server
    server_thread.start()
    
    # 6. Hien thi cua so chinh
    main_window.show()
    
    # 7. Bat dau vong lap su kien cua ung dung
    sys.exit(app.exec_())