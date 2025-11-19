# File: server_app/main.py
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from .models import VaiTroEnum

main = Blueprint('main', __name__)

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

@main.route('/profile')
@login_required
def profile():
    """
    Route trang hồ sơ cá nhân (dùng chung cho cả admin và dược sĩ).
    """
    # Dựa vào vai trò để quyết định kế thừa từ layout nào
    if current_user.vai_tro == VaiTroEnum.admin:
        layout = 'admin/layout.html'
    else:
        layout = 'pharmacist/layout.html'
    return render_template('profile.html', user=current_user, layout_template=layout)