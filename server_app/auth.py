# File: server_app/auth.py
# Module chịu trách nhiệm xử lý các nghiệp vụ xác thực người dùng:
# Đăng nhập, Đăng ký, Đăng xuất.

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

# Import các model và Enum cần thiết
from .extensions import db
from .models import NguoiDung, VaiTroEnum, GioiTinhEnum

# Tạo một Blueprint tên là 'auth'
auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Hàm xử lý logic cho trang đăng nhập.
    Bao gồm cả việc chuyển hướng người dùng đã đăng nhập.
    """
    
    # --- BƯỚC 1: KIỂM TRA NẾU NGƯỜI DÙNG ĐÃ ĐĂNG NHẬP ---
    if current_user.is_authenticated:
        flash('Bạn đã đăng nhập rồi!', 'info')
        if current_user.vai_tro == VaiTroEnum.admin:
            # SỬA LẠI Ở ĐÂY: Trỏ đến blueprint 'admin'
            return redirect(url_for('admin.dashboard'))
        else:
            # SỬA LẠI Ở ĐÂY: Trỏ đến blueprint 'pharmacist'
            return redirect(url_for('pharmacist.dashboard'))

    # --- BƯỚC 2: XỬ LÝ KHI NGƯỜI DÙNG SUBMIT FORM (METHOD POST) ---
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = NguoiDung.query.filter_by(email=email).first()

        if not user or not user.check_password(password) or not user.dang_hoat_dong:
            flash('Email, mật khẩu không đúng hoặc tài khoản đã bị khóa.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        flash('Đăng nhập thành công!', 'success')
        
        # --- PHÂN LUỒNG CHUYỂN HƯỚNG DỰA TRÊN VAI TRÒ ---
        if user.vai_tro == VaiTroEnum.admin:
            # SỬA LẠI Ở ĐÂY: Trỏ đến blueprint 'admin'
            return redirect(url_for('admin.dashboard'))
        else:
            # SỬA LẠI Ở ĐÂY: Trỏ đến blueprint 'pharmacist'
            return redirect(url_for('pharmacist.dashboard'))

    # --- BƯỚC 3: HIỂN THỊ TRANG ĐĂNG NHẬP (METHOD GET) ---
    return render_template('auth/login.html')


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    """Hàm xử lý logic cho trang đăng ký tài khoản."""
    if request.method == 'POST':
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        password = request.form.get('password')
        phone_number = request.form.get('phone_number')
        gender = request.form.get('gender')

        # Kiểm tra xem username hoặc email đã tồn tại chưa
        user_by_username = NguoiDung.query.filter_by(ten_dang_nhap=username).first()
        if user_by_username:
            flash('Tên đăng nhập đã tồn tại.', 'warning')
            return redirect(url_for('auth.signup'))
        
        user_by_email = NguoiDung.query.filter_by(email=email).first()
        if user_by_email:
            flash('Địa chỉ email đã được sử dụng.', 'warning')
            return redirect(url_for('auth.signup'))

        gender_enum = None
        if gender in [e.name for e in GioiTinhEnum]:
             gender_enum = GioiTinhEnum[gender]

        new_user = NguoiDung(
            email=email,
            ho_ten=full_name,
            ten_dang_nhap=username,
            so_dien_thoai=phone_number,
            gioi_tinh=gender_enum
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Đăng ký tài khoản thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html')


@auth.route('/logout')
@login_required
def logout():
    """Hàm xử lý đăng xuất."""
    logout_user()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('auth.login'))