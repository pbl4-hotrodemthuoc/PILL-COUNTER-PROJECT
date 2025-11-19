# File: server_app/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_moment import Moment
from flask_socketio import SocketIO

# Khởi tạo các đối tượng
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
moment = Moment()

# SỬA DÒNG NÀY: Thêm cors_allowed_origins="*" để chấp nhận mọi kết nối
# async_mode='threading' để ép buộc chạy chế độ đa luồng cơ bản, không tìm eventlet
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading', max_http_buffer_size=10000000)