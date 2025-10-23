# File: server_app/__init__.py (PHIÊN BẢN CẬP NHẬT)
from flask import Flask
from .models import db, User
from flask_login import LoginManager
import os
from dotenv import load_dotenv
import click # Thư viện để tạo lệnh

load_dotenv()

def create_app():
    app = Flask(__name__)

    # Cấu hình từ file .flaskenv
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint)
    
    # --- PHẦN MỚI: TẠO LỆNH 'flask init-db' ---
    @app.cli.command("init-db")
    def init_db_command():
        """Xóa các bảng cũ và tạo các bảng mới, bao gồm dữ liệu mẫu."""
        db.drop_all()
        db.create_all()
        
        # 1. Tạo tài khoản admin và user mẫu với đầy đủ thông tin
        admin_user = User(
            username='admin', 
            role='admin',
            full_name='Quản trị viên Hệ thống',
            email='admin@pillcounter.com'
        )
        admin_user.set_password('admin')

        user_1 = User(
            username='nhanvien1', 
            role='user',
            full_name='Nguyễn Văn A',
            email='nhanvien1@pillcounter.com',
            phone_number='0987654321'
        )
        user_1.set_password('123456')

        db.session.add_all([admin_user, user_1])
        db.session.commit()
        print("Đã tạo tài khoản admin và user mẫu.")

        # ... (Phần tạo thuốc và log giữ nguyên) ...
        # ...
        
        print("---")
        print("Khởi tạo cơ sở dữ liệu hoàn tất!")

    return app