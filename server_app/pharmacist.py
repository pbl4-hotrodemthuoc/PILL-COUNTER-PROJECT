# File: server_app/pharmacist.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import db, ThongBao, ThietBi, VaiTroEnum

pharmacist = Blueprint('pharmacist', __name__)

# --- CONTEXT PROCESSOR: Cung cấp các biến chung cho MỌI template của blueprint này ---
@pharmacist.context_processor
def inject_pharmacist_data():
    """
    Hàm này tự động chạy và cung cấp các biến cho template của dược sĩ.
    Ví dụ: số thông báo chưa đọc, trạng thái thiết bị.
    """
    if current_user.is_authenticated and current_user.vai_tro == VaiTroEnum.pharmacist:
        unread_notifications = ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).all()
        device = ThietBi.query.get(1) # Lấy thiết bị mặc định có ID=1
        return dict(
            unread_notifications_count=len(unread_notifications),
            notifications=unread_notifications,
            device_status=device.trang_thai.name if device else 'offline'
        )
    return {}

# --- Các Route của Dược sĩ ---

@pharmacist.route('/dashboard')
@login_required
def dashboard():
    return render_template('pharmacist/dashboard.html')

@pharmacist.route('/new-order')
@login_required
def new_order():
    return render_template('pharmacist/new_order.html')

@pharmacist.route('/history')
@login_required
def my_history():
    return render_template('pharmacist/my_history.html')

@pharmacist.route('/stats')
@login_required
def my_stats():
    return render_template('pharmacist/my_stats.html')

@pharmacist.route('/report-incident')
@login_required
def report_incident():
    return render_template('pharmacist/report_incident.html')

@pharmacist.route('/guide')
@login_required
def guide():
    return render_template('pharmacist/guide.html')

# --- Các Route xử lý nghiệp vụ cho layout ---
@pharmacist.route('/notifications/mark-all-read')
@login_required
def mark_all_read():
    ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).update({'da_doc': True})
    db.session.commit()
    flash('Tất cả thông báo đã được đánh dấu là đã đọc.', 'success')
    return redirect(request.referrer or url_for('pharmacist.dashboard'))

@pharmacist.route('/notifications/<int:id>')
@login_required
def view_notification(id):
    notif = ThongBao.query.get_or_404(id)
    if notif.id_nguoi_dung != current_user.id:
        flash('Bạn không có quyền xem thông báo này.', 'danger')
        return redirect(url_for('pharmacist.dashboard'))
    notif.da_doc = True
    db.session.commit()
    return redirect(notif.url_lien_ket or url_for('pharmacist.dashboard'))

@pharmacist.route('/notifications/all')
@login_required
def all_notifications():
    return "Trang hiển thị tất cả thông báo của Dược sĩ"

@pharmacist.route('/settings')
@login_required
def settings():
    return "Trang Cài đặt của Dược sĩ"