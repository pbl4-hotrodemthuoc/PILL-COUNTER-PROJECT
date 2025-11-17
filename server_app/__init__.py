# File: server_app/__init__.py
import os
from flask import Flask
from .models import db  # Import đối tượng 'db' từ models.py
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
import click

# Tải các biến môi trường từ file .env
load_dotenv()

# Khởi tạo các extension ở ngoài App Factory để có thể import ở nơi khác
migrate = Migrate()
login_manager = LoginManager()

# Cấu hình cho Flask-Login
login_manager.login_view = 'auth.login' # Tên blueprint.tên_hàm_login
login_manager.login_message = "Vui lòng đăng nhập để truy cập trang này."
login_manager.login_message_category = "info" # Loại flash message (bootstrap)

def create_app():
    """Hàm "Nhà máy" (App Factory) để tạo và cấu hình ứng dụng Flask."""
    app = Flask(__name__)

    # --- 1. Cấu hình ứng dụng từ file .env ---
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- 2. Gắn các extension vào ứng dụng ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # --- 3. Cấu hình user_loader cho Flask-Login ---
    # Import model NguoiDung ở đây để tránh lỗi import vòng tròn (circular import)
    from .models import NguoiDung

    @login_manager.user_loader
    def load_user(user_id):
        # Hàm này cho Flask-Login biết cách tìm một người dùng dựa trên ID của họ
        return NguoiDung.query.get(int(user_id))

    # --- 4. Đăng ký các Blueprint (các module chứa routes) ---
    with app.app_context():
        from .auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint, url_prefix='/auth')

        from .main import main as main_blueprint
        app.register_blueprint(main_blueprint)

        from .api import api as api_blueprint
        app.register_blueprint(api_blueprint, url_prefix='/api')
    
    # --- 5. Đăng ký các lệnh CLI tùy chỉnh ---
    register_commands(app)

    return app

def register_commands(app):
    """Hàm đăng ký các lệnh CLI (ví dụ: flask seed-db)."""
    
    # Import hàm khởi tạo dữ liệu từ models.py
    from .models import khoi_tao_du_lieu_mau
    
    @app.cli.command("seed-db")
    @click.confirmation_option(prompt='CẢNH BÁO: Lệnh này sẽ XÓA TẤT CẢ dữ liệu hiện tại. Bạn có chắc muốn tiếp tục không?')
    def seed_db_command():
        """Xóa dữ liệu cũ và tạo lại dữ liệu mẫu cho toàn bộ hệ thống."""
        
        # Gọi hàm đã được định nghĩa trong models.py
        khoi_tao_du_lieu_mau()