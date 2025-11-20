# File: run.py

# --- [QUAN TRỌNG] KHỐI NÀY PHẢI Ở DÒNG ĐẦU TIÊN ---
# Phải gọi monkey_patch trước khi import bất kỳ thư viện nào khác
import eventlet
eventlet.monkey_patch()
# --------------------------------------------------

from server_app import create_app
from server_app.extensions import socketio

app = create_app()

if __name__ == '__main__':
    print("🚀 SERVER ĐANG CHẠY CHẾ ĐỘ: EVENTLET (HIGH PERFORMANCE)")
    print("📡 Đang lắng nghe tại: http://0.0.0.0:5001")
    
    # allow_unsafe_werkzeug=True: Cần thiết cho môi trường Dev
    # use_reloader=False: Bắt buộc tắt để tránh xung đột với Eventlet
    # log_output=False: Tắt bớt log ping/pong để Terminal đỡ bị rác (nếu muốn)
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True, use_reloader=False)