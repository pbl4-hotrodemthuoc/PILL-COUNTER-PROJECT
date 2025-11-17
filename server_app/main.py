# File: server_app/main.py (PHIÊN BẢN HOÀN THIỆN)
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
# --- THAY ĐỔI 1: Import đúng các model đã Việt hóa ---
from .models import db, LoaiThuoc
from functools import wraps

main = Blueprint('main', __name__)

# --- DECORATOR PHÂN QUYỀN ADMIN ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # --- THAY ĐỔI 2: Sửa cách kiểm tra vai trò cho đúng với kiểu Enum ---
        # So sánh tên của Enum ('admin') thay vì so sánh cả đối tượng
        if not current_user.is_authenticated or current_user.vai_tro.name != 'admin':
            flash('Bạn không có quyền truy cập trang này.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@main.route('/admin')
@login_required
@admin_required
def admin_page():
    # Trang này chỉ admin mới vào được
    return render_template('admin.html', user=current_user)

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@main.route('/drugs')
@login_required
def drug_list():
    # --- THAY ĐỔI 3: Query bằng model và tên cột đúng ---
    drugs = LoaiThuoc.query.order_by(LoaiThuoc.ten_thuoc.asc()).all()
    return render_template('drugs.html', drugs=drugs, user=current_user)