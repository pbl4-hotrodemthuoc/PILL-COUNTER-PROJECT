# File: server_app/__init__.py

import os
import click
from flask import Flask
from dotenv import load_dotenv

# Import các extension từ file extensions.py
from .extensions import db, migrate, login_manager, moment, socketio

load_dotenv()

def create_app():
    """Hàm 'Nhà máy' (App Factory) để tạo và cấu hình ứng dụng Flask."""
    app = Flask(__name__)

    # --- Cấu hình ứng dụng ---
    # Ưu tiên lấy từ biến môi trường, nếu không có thì dùng giá trị mặc định
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key_12345')
    
    # Cấu hình CSDL MySQL (Thay đổi cho phù hợp với máy bạn)
    # Ví dụ: mysql+mysqlconnector://root:@localhost:3307/pharmacy_db
    db_uri = os.getenv('DATABASE_URI')
    if not db_uri:
        # Fallback nếu không có trong .env
        db_user = os.getenv('DB_USER', 'root')
        db_pass = os.getenv('DB_PASSWORD', '')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_name = os.getenv('DB_NAME', 'pharmacy_db')
        db_uri = f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}/{db_name}"
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    
    # Cấu hình thư mục upload
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # --- Gắn các extension vào ứng dụng ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    moment.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*") # Quan trọng cho WebSocket

    # --- Cấu hình Flask-Login ---
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Vui lòng đăng nhập để truy cập trang này."
    login_manager.login_message_category = "warning"

    # Import model NguoiDung sau khi db đã sẵn sàng để tránh lỗi
    from .models import NguoiDung
    @login_manager.user_loader
    def load_user(user_id):
        return NguoiDung.query.get(int(user_id))

    # --- Đăng ký các Blueprint ---
    # Import bên trong hàm để tránh circular import với models/auth...
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from .pharmacist import pharmacist as pharmacist_blueprint
    app.register_blueprint(pharmacist_blueprint, url_prefix='/pharmacist')

    # --- Đăng ký các lệnh CLI ---
    register_commands(app)

    return app

def register_commands(app):
    """Đăng ký các lệnh CLI tùy chỉnh."""
    from .models import khoi_tao_du_lieu_mau # Import hàm tạo dữ liệu
    
    @app.cli.command("init-db")
    def init_db_command():
        """Xóa tất cả bảng và tạo lại cấu trúc CSDL mới tinh."""
        with app.app_context():
            print("Dang xoa CSDL cu...")
            db.drop_all()
            print("Dang tao bang moi...")
            db.create_all()
            print("✅ Da tao xong cau truc CSDL!")

    @app.cli.command("seed-db")
    @click.confirmation_option(prompt='CẢNH BÁO: Lệnh này sẽ XÓA và TẠO LẠI toàn bộ dữ liệu mẫu. Tiếp tục?')
    def seed_db_command():
        """Nạp dữ liệu mẫu (Admin, Dược sĩ, Thuốc, Đơn hàng...)."""
        with app.app_context():
            khoi_tao_du_lieu_mau()
            print("✅ Da nap du lieu mau thanh cong!")