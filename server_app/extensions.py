# File: server_app/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_moment import Moment
from flask_socketio import SocketIO

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
moment = Moment()

# [QUAN TRỌNG] Chuyển sang chế độ 'eventlet' để siêu tốc độ
socketio = SocketIO(
    cors_allowed_origins="*", 
    async_mode='eventlet', 
    max_http_buffer_size=10000000,
    ping_timeout=10,    # Giảm thời gian chờ để phát hiện mất kết nối nhanh hơn
    ping_interval=5
)