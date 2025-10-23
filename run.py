# File: run.py
from server_app import create_app

# Gọi "nhà máy" để tạo ra ứng dụng
app = create_app()

if __name__ == '__main__':
    # Chạy ứng dụng
    # host='0.0.0.0' cho phép các thiết bị khác trong mạng (như Pi) có thể kết nối
    app.run(host='0.0.0.0', port=5001, debug=True) # <-- Đổi thành 5001