# File: server_app/__init__.py (PHIÊN BẢN SỬA ĐỔI)
import os
from flask import Flask
from .models import db  # Chỉ import 'db' từ models.py
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
import click

load_dotenv()

# Khởi tạo các extension ở ngoài App Factory
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Vui lòng đăng nhập để truy cập trang này."
login_manager.login_message_category = "info"

def create_app():
    """App Factory để tạo và cấu hình ứng dụng Flask."""
    app = Flask(__name__)

    # Cấu hình từ file .env
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Gắn các extension vào ứng dụng
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Import model cần thiết cho user_loader
    from .models import NguoiDung

    @login_manager.user_loader
    def load_user(user_id):
        return NguoiDung.query.get(int(user_id))

    # Đăng ký các Blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    # Đăng ký các lệnh CLI
    register_commands(app)

    return app

def register_commands(app):
    """Đăng ký các lệnh CLI (ví dụ: seed-db)."""
    # Bạn có thể giữ hoặc xóa phần này nếu không dùng lệnh seed-db
    from .models import LoaiThuoc, NguoiDung, VaiTroEnum, GioiTinhEnum
    
    @app.cli.command("seed-db")
    @click.confirmation_option(prompt='Bạn có chắc muốn xóa dữ liệu cũ và tạo dữ liệu mẫu không?')
    def seed_db_command():
        # Nội dung của hàm seed-db
        print("Bắt đầu tạo dữ liệu mẫu...")
        # (Copy nội dung hàm seed-db từ các phiên bản trước vào đây nếu bạn cần)
        print("Hoàn tất.")