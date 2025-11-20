from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

# --- QUAN TRỌNG: Import thêm ThongBao và ThietBi để lấy dữ liệu cho layout ---
from .models import db, NguoiDung, CaLamViecEnum, VaiTroEnum, ThongBao, ThietBi
from . import db

main = Blueprint('main', __name__)

# ================================================================
# THÊM ĐOẠN NÀY ĐỂ SỬA LỖI UNDEFINED ERROR
# ================================================================
@main.context_processor
def inject_main_data():
    """
    Hàm này cung cấp dữ liệu chung (thông báo, thiết bị) cho các template
    được render bởi blueprint 'main' (bao gồm trang profile).
    """
    if current_user.is_authenticated:
        # 1. Lấy thông báo chưa đọc
        unread_notifications = ThongBao.query.filter_by(
            id_nguoi_dung=current_user.id, 
            da_doc=False
        ).all()
        
        # 2. Lấy trạng thái thiết bị (giả sử ID=1) để hiển thị trên Header nếu cần
        device = ThietBi.query.get(1)
        status = device.trang_thai.name if device else 'offline'

        return dict(
            unread_notifications_count=len(unread_notifications),
            notifications=unread_notifications,
            device_status=status
        )
    return {}
# ================================================================

@main.route('/')
def index():
    """
    Route trang chủ: Tự động chuyển hướng người dùng đến trang phù hợp.
    """
    if current_user.is_authenticated:
        if current_user.vai_tro == VaiTroEnum.admin:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('pharmacist.dashboard'))
    return redirect(url_for('auth.login'))

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    Route xem và chỉnh sửa hồ sơ cá nhân.
    """
    # Dựa vào vai trò để quyết định kế thừa từ layout nào
    if current_user.vai_tro == VaiTroEnum.admin:
        layout = 'admin/layout.html'
    else:
        layout = 'pharmacist/layout.html'

    if request.method == 'POST':
        action = request.form.get('action')

        # --- XỬ LÝ CẬP NHẬT THÔNG TIN ---
        if action == 'update_info':
            ho_ten = request.form.get('ho_ten')
            so_dien_thoai = request.form.get('so_dien_thoai')
            email = request.form.get('email')
            
            if not ho_ten:
                flash('Họ tên không được để trống.', 'danger')
            else:
                current_user.ho_ten = ho_ten
                current_user.so_dien_thoai = so_dien_thoai
                current_user.email = email
                try:
                    db.session.commit()
                    flash('Cập nhật thông tin thành công!', 'success')
                except Exception:
                    db.session.rollback()
                    flash('Có lỗi xảy ra khi lưu dữ liệu.', 'danger')
            return redirect(url_for('main.profile'))

        # --- XỬ LÝ ĐỔI MẬT KHẨU ---
        elif action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not check_password_hash(current_user.mat_khau, current_password):
                flash('Mật khẩu hiện tại không đúng.', 'danger')
            elif new_password != confirm_password:
                flash('Mật khẩu mới và xác nhận không khớp.', 'danger')
            elif len(new_password) < 6:
                flash('Mật khẩu mới phải có ít nhất 6 ký tự.', 'warning')
            else:
                current_user.mat_khau = generate_password_hash(new_password)
                try:
                    db.session.commit()
                    flash('Đổi mật khẩu thành công!', 'success')
                except:
                    db.session.rollback()
                    flash('Lỗi hệ thống khi đổi mật khẩu.', 'danger')
            return redirect(url_for('main.profile'))

    return render_template('profile.html', user=current_user, layout_template=layout)