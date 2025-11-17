# File: server_app/auth.py (PHIÊN BẢN HOÀN THIỆN)
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required

# --- THAY ĐỔI 1: Import đúng các model đã Việt hóa và Enum ---
from .models import db, NguoiDung, GioiTinhEnum

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # --- THAY ĐỔI 2: Query bằng model và tên cột đúng ---
        user = NguoiDung.query.filter_by(ten_dang_nhap=username).first()

        # Thêm kiểm tra tài khoản có bị khóa không (user.dang_hoat_dong)
        if not user or not user.check_password(password) or not user.dang_hoat_dong:
            flash('Tên đăng nhập, mật khẩu không đúng hoặc tài khoản đã bị khóa.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        flash('Đăng nhập thành công!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/login.html')

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # --- THAY ĐỔI 3: Lấy tất cả dữ liệu từ form, bao gồm cả sđt và giới tính ---
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        password = request.form.get('password')
        phone_number = request.form.get('phone_number')
        gender = request.form.get('gender') # Giá trị là 'male', 'female', 'other'

        # --- THAY ĐỔI 4: Query bằng model và tên cột đúng ---
        user_by_username = NguoiDung.query.filter_by(ten_dang_nhap=username).first()
        if user_by_username:
            flash('Tên đăng nhập đã tồn tại.', 'warning')
            return redirect(url_for('auth.signup'))
        
        user_by_email = NguoiDung.query.filter_by(email=email).first()
        if user_by_email:
            flash('Địa chỉ email đã được sử dụng.', 'warning')
            return redirect(url_for('auth.signup'))

        # Chuyển đổi giá trị gender từ string sang đối tượng Enum
        gender_enum = None
        if gender in [e.name for e in GioiTinhEnum]:
             gender_enum = GioiTinhEnum[gender]

        # --- THAY ĐỔI 5: Tạo user mới với đầy đủ thông tin ---
        new_user = NguoiDung(
            email=email,
            ho_ten=full_name,
            ten_dang_nhap=username,
            so_dien_thoai=phone_number,
            gioi_tinh=gender_enum
        )
        new_user.set_password(password) # Mật khẩu sẽ được hash

        db.session.add(new_user)
        db.session.commit()

        flash('Đăng ký tài khoản thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('auth.login'))