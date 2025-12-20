# # File: server_app/main.py
# from flask import Blueprint, render_template, redirect, url_for
# from flask_login import login_required, current_user
# from .models import VaiTroEnum

# main = Blueprint('main', __name__)

# @main.route('/')
# def index():
#     """
#     Route trang chủ: Tự động chuyển hướng người dùng đến trang phù hợp.
#     """
#     if current_user.is_authenticated:
#         if current_user.vai_tro == VaiTroEnum.admin:
#             return redirect(url_for('admin.dashboard'))
#         else:
#             return redirect(url_for('pharmacist.dashboard'))
#     return redirect(url_for('auth.login'))

# @main.route('/profile')
# @login_required
# def profile():
#     """
#     Route trang hồ sơ cá nhân (dùng chung cho cả admin và dược sĩ).
#     """
#     # Dựa vào vai trò để quyết định kế thừa từ layout nào
#     if current_user.vai_tro == VaiTroEnum.admin:
#         layout = 'admin/layout.html'
#     else:
#         layout = 'pharmacist/layout.html'
#     return render_template('profile.html', user=current_user, layout_template=layout)
# File: server_app/main.py
# CẬP NHẬT: FIX LỖI UNDEFINED VÀ THÊM TÍNH NĂNG CẬP NHẬT PROFILE

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from .models import VaiTroEnum, ThongBao, ThietBi
from .extensions import db  # Import db để lưu dữ liệu

main = Blueprint('main', __name__)

# =====================================================
# 1. CONTEXT PROCESSOR (FIX LỖI UNDEFINED ERROR)
# =====================================================
@main.context_processor
def inject_common_data():
    """
    Hàm này tự động chạy trước khi render template.
    Nó gửi các biến chung (thông báo, trạng thái thiết bị) sang giao diện.
    """
    if current_user.is_authenticated:
        # Lấy số thông báo chưa đọc
        unread = ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).count()
        
        # Lấy danh sách thông báo (để hiển thị ở menu drop-down nếu có)
        notifs = ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).order_by(ThongBao.ngay_tao.desc()).limit(5).all()
        
        # Lấy trạng thái thiết bị
        d_status = 'offline'
        try:
            device = ThietBi.query.get(1)
            if device: d_status = device.trang_thai.name
        except: pass

        return dict(
            unread_notifications_count=unread,
            notifications=notifs,
            device_status=d_status
        )
    
    # Giá trị mặc định nếu chưa đăng nhập
    return dict(unread_notifications_count=0, notifications=[], device_status='offline')


# =====================================================
# 2. CÁC ROUTE CHÍNH
# =====================================================

@main.route('/')
def index():
    """Route trang chủ: Điều hướng người dùng về đúng dashboard."""
    if current_user.is_authenticated:
        if current_user.vai_tro == VaiTroEnum.admin:
            return redirect(url_for('admin.dashboard'))
        elif current_user.vai_tro == VaiTroEnum.pharmacist:
            return redirect(url_for('pharmacist.dashboard'))
    return redirect(url_for('auth.login'))

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    Route trang hồ sơ cá nhân.
    Hỗ trợ cả xem (GET) và cập nhật thông tin (POST).
    """
    # 1. Xác định Layout (Giao diện) dựa trên vai trò
    if current_user.vai_tro == VaiTroEnum.admin:
        # Nếu chưa có layout admin riêng thì dùng tạm layout pharmacist hoặc base
        layout = 'admin/layout.html' 
    else:
        layout = 'pharmacist/layout.html'

    # 2. Xử lý khi bấm nút "Lưu thay đổi" (POST)
    if request.method == 'POST':
        ho_ten = request.form.get('ho_ten')
        email = request.form.get('email')
        sdt = request.form.get('so_dien_thoai')
        
        # Cập nhật thông tin chung
        current_user.ho_ten = ho_ten
        current_user.email = email
        current_user.so_dien_thoai = sdt

        # Xử lý đổi mật khẩu (nếu người dùng có nhập)
        new_pass = request.form.get('mat_khau_moi')
        confirm_pass = request.form.get('xac_nhan_mat_khau')

        if new_pass:
            if new_pass != confirm_pass:
                flash('Mật khẩu xác nhận không khớp!', 'danger')
                return render_template('profile.html', user=current_user, layout_template=layout)
            else:
                current_user.set_password(new_pass)
                flash('Đã cập nhật thông tin và đổi mật khẩu thành công.', 'success')
        else:
            flash('Đã cập nhật thông tin cá nhân thành công.', 'success')

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi lưu dữ liệu: {e}', 'danger')
            
        return redirect(url_for('main.profile'))

    # 3. Hiển thị trang hồ sơ (GET)
    return render_template('profile.html', user=current_user, layout_template=layout)