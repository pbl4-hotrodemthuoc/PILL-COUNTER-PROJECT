# File: server_app/admin.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from .models import db, NguoiDung, LoaiThuoc, VaiTroEnum, BaoCaoSuCo, TrangThaiSuCoEnum

admin = Blueprint('admin', __name__)

# --- DECORATOR PHÂN QUYỀN ADMIN (Dành riêng cho blueprint này) ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.vai_tro != VaiTroEnum.admin:
            flash('Bạn không có quyền truy cập khu vực quản trị.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# --- CONTEXT PROCESSOR: Cung cấp biến chung cho tất cả template của admin ---
@admin.context_processor
def inject_admin_data():
    """Cung cấp các biến chung cho giao diện của Admin."""
    if current_user.is_authenticated and current_user.vai_tro == VaiTroEnum.admin:
        pending_incidents_count = BaoCaoSuCo.query.filter_by(trang_thai=TrangThaiSuCoEnum.pending).count()
        # Bạn có thể thêm unread_notifications_count cho admin ở đây nếu cần
        return dict(
            pending_incidents_count=pending_incidents_count
        )
    return {}

# --- Các Route của Admin ---
@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

@admin.route('/users')
@login_required
@admin_required
def users():
    all_users = NguoiDung.query.all()
    return render_template('admin/users.html', users=all_users)

@admin.route('/drugs')
@login_required
@admin_required
def drugs():
    all_drugs = LoaiThuoc.query.all()
    return render_template('admin/drugs.html', drugs=all_drugs)

# --- Các route placeholder để tránh lỗi BuildError ---
@admin.route('/devices')
@login_required
@admin_required
def devices():
    return "Trang Quản lý Thiết bị"

@admin.route('/reports')
@login_required
@admin_required
def reports():
    return "Trang Báo cáo Kinh doanh"

@admin.route('/incidents')
@login_required
@admin_required
def incidents():
    return "Trang Quản lý Sự cố"

@admin.route('/system-logs')
@login_required
@admin_required
def system_logs():
    return "Trang Nhật ký Hệ thống"

@admin.route('/settings')
@login_required
@admin_required
def settings():
    return "Trang Cài đặt Hệ thống"

@admin.route('/profile')
@login_required
@admin_required
def profile():
    return redirect(url_for('main.profile')) # Dùng chung trang profile

# --- Các route cho Quick Actions ---
@admin.route('/users/add')
@login_required
@admin_required
def add_user():
    return "Trang thêm người dùng mới"

@admin.route('/drugs/add')
@login_required
@admin_required
def add_drug():
    return "Trang thêm thuốc mới"

@admin.route('/reports/export')
@login_required
@admin_required
def export_report():
    return "Xử lý xuất báo cáo"