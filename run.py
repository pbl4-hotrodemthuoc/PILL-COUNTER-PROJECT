# File: run.py
# KHÔNG import eventlet ở đây nữa

from server_app import create_app
from server_app.extensions import socketio

app = create_app()

if __name__ == '__main__':
    print("✅ Server đang chạy (Chế độ Threading Standard)...")
    # allow_unsafe_werkzeug=True: Cho phép chạy SocketIO với server phát triển mặc định của Flask
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)