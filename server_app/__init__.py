# File: server_app/__init__.py
import os
from flask import Flask
from .models import db
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_moment import Moment  # <-- 1. IMPORT MOMENT
from dotenv import load_dotenv
import click

load_dotenv()

# Khởi tạo các extension
migrate = Migrate()
login_manager = LoginManager()
moment = Moment()  # <-- 2. KHỞI TẠO ĐỐI TƯỢNG MOMENT

# Cấu hình Flask-Login
login_manager.login_view = 'auth.login'
login_manager.login_message = "Vui lòng đăng nhập để truy cập trang này."
login_manager.login_message_category = "info"


def create_app():
    """Hàm "Nhà máy" (App Factory) để tạo và cấu hình ứng dụng Flask."""
    app = Flask(__name__)

    # --- Cấu hình ứng dụng ---
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- Gắn các extension vào ứng dụng ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    moment.init_app(app)  # <-- 3. GẮN MOMENT VÀO APP

    # --- Cấu hình user_loader ---
    from .models import NguoiDung
    @login_manager.user_loader
    def load_user(user_id):
        return NguoiDung.query.get(int(user_id))

    # --- Đăng ký các Blueprint ---
    with app.app_context():
        from .main import main as main_blueprint
        app.register_blueprint(main_blueprint)
        
        from .auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint, url_prefix='/auth')

        from .admin import admin as admin_blueprint
        app.register_blueprint(admin_blueprint, url_prefix='/admin')

        from .pharmacist import pharmacist as pharmacist_blueprint
        app.register_blueprint(pharmacist_blueprint, url_prefix='/pharmacist')

        # from .api import api as api_blueprint
        # app.register_blueprint(api_blueprint, url_prefix='/api')
    
    # --- Đăng ký các lệnh CLI ---
    register_commands(app)

    return app

def register_commands(app):
    """Đăng ký các lệnh CLI (ví dụ: flask seed-db)."""
    from .models import khoi_tao_du_lieu_mau
    
    @app.cli.command("seed-db")
    @click.confirmation_option(prompt='CẢNH BÁO: Lệnh này sẽ XÓA TẤT CẢ dữ liệu hiện tại. Bạn có chắc muốn tiếp tục không?')
    def seed_db_command():
        """Xóa dữ liệu cũ và tạo lại dữ liệu mẫu cho toàn bộ hệ thống."""
        khoi_tao_du_lieu_mau()