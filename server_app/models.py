# File: server_app/models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# File: server_app/models.py (PHIÊN BẢN CẬP NHẬT)
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    
    # --- Thông tin đăng nhập ---
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    # --- Thông tin cá nhân (MỚI) ---
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=True) # Có thể không bắt buộc
    
    # --- Phân quyền và trạng thái ---
    role = db.Column(db.String(50), nullable=False, default='user')
    is_active = db.Column(db.Boolean, nullable=False, default=True) # Mặc định là hoạt động
    
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    def set_password(self, password):
        self.password = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)

class DrugType(db.Model):
    __tablename__ = 'drug_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    logs = db.relationship('TransactionLog', backref='drug_type', lazy=True)

class TransactionLog(db.Model):
    __tablename__ = 'transaction_logs'
    id = db.Column(db.Integer, primary_key=True)
    drug_id = db.Column(db.Integer, db.ForeignKey('drug_types.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    device_id = db.Column(db.String(100), nullable=False)