# File: server_app/auth.py
from flask import Blueprint, render_template, redirect, url_for, request, flash
from .models import db, User
from flask_login import login_user, logout_user, login_required

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('Tên đăng nhập hoặc mật khẩu không đúng.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        flash('Đăng nhập thành công!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/login.html')

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Lấy thêm dữ liệu từ form
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        password = request.form.get('password')

        # Kiểm tra xem username hoặc email đã tồn tại chưa
        user_by_username = User.query.filter_by(username=username).first()
        if user_by_username:
            flash('Tên đăng nhập đã tồn tại.', 'warning')
            return redirect(url_for('auth.signup'))
        
        user_by_email = User.query.filter_by(email=email).first()
        if user_by_email:
            flash('Địa chỉ email đã được sử dụng.', 'warning')
            return redirect(url_for('auth.signup'))

        # Tạo user mới với đầy đủ thông tin
        new_user = User(
            email=email,
            full_name=full_name,
            username=username
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