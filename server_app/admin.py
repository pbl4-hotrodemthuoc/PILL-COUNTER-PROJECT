# # File: server_app/admin.py
# from flask import Blueprint, render_template, flash, redirect, url_for
# from flask_login import login_required, current_user
# from functools import wraps
# from .extensions import db
# from .models import NguoiDung, LoaiThuoc, VaiTroEnum, BaoCaoSuCo, TrangThaiSuCoEnum

# admin = Blueprint('admin', __name__)

# # --- DECORATOR PHÂN QUYỀN ADMIN (Dành riêng cho blueprint này) ---
# def admin_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if not current_user.is_authenticated or current_user.vai_tro != VaiTroEnum.admin:
#             flash('Bạn không có quyền truy cập khu vực quản trị.', 'danger')
#             return redirect(url_for('main.index'))
#         return f(*args, **kwargs)
#     return decorated_function

# # --- CONTEXT PROCESSOR: Cung cấp biến chung cho tất cả template của admin ---
# @admin.context_processor
# def inject_admin_data():
#     """Cung cấp các biến chung cho giao diện của Admin."""
#     if current_user.is_authenticated and current_user.vai_tro == VaiTroEnum.admin:
#         pending_incidents_count = BaoCaoSuCo.query.filter_by(trang_thai=TrangThaiSuCoEnum.pending).count()
#         # Bạn có thể thêm unread_notifications_count cho admin ở đây nếu cần
#         return dict(
#             pending_incidents_count=pending_incidents_count
#         )
#     return {}

# # --- Các Route của Admin ---
# @admin.route('/dashboard')
# @login_required
# @admin_required
# def dashboard():
#     return render_template('admin/dashboard.html')

# @admin.route('/users')
# @login_required
# @admin_required
# def users():
#     all_users = NguoiDung.query.all()
#     return render_template('admin/users.html', users=all_users)

# @admin.route('/drugs')
# @login_required
# @admin_required
# def drugs():
#     all_drugs = LoaiThuoc.query.all()
#     return render_template('admin/drugs.html', drugs=all_drugs)

# # --- Các route placeholder để tránh lỗi BuildError ---
# @admin.route('/devices')
# @login_required
# @admin_required
# def devices():
#     return "Trang Quản lý Thiết bị"

# @admin.route('/reports')
# @login_required
# @admin_required
# def reports():
#     return "Trang Báo cáo Kinh doanh"

# @admin.route('/incidents')
# @login_required
# @admin_required
# def incidents():
#     return "Trang Quản lý Sự cố"

# @admin.route('/system-logs')
# @login_required
# @admin_required
# def system_logs():
#     return "Trang Nhật ký Hệ thống"

# @admin.route('/settings')
# @login_required
# @admin_required
# def settings():
#     return "Trang Cài đặt Hệ thống"

# @admin.route('/profile')
# @login_required
# @admin_required
# def profile():
#     return redirect(url_for('main.profile')) # Dùng chung trang profile

# # --- Các route cho Quick Actions ---
# @admin.route('/users/add')
# @login_required
# @admin_required
# def add_user():
#     return "Trang thêm người dùng mới"

# @admin.route('/drugs/add')
# @login_required
# @admin_required
# def add_drug():
#     return "Trang thêm thuốc mới"

# @admin.route('/reports/export')
# @login_required
# @admin_required
# def export_report():
#     return "Xử lý xuất báo cáo"

from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from functools import wraps
from .models import db, NguoiDung, LoaiThuoc, VaiTroEnum, BaoCaoSuCo, TrangThaiSuCoEnum, ThietBi, TrangThaiThietBiEnum, DonThuoc, ThongBao, LoaiThongBaoEnum
from werkzeug.security import generate_password_hash
from datetime import date, timedelta, datetime
from sqlalchemy import func
from .models import ChiTietDonThuoc
from flask import send_file
from openpyxl import Workbook
from openpyxl.styles import Font
from io import BytesIO
from .models import NhatKyHeThong, LoaiLogEnum
import os
from werkzeug.utils import secure_filename


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
        # Đếm thông báo chưa đọc
        unread_notifications_count = ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).count()
        # Lấy 5 thông báo mới nhất
        recent_notifications = ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False)\
            .order_by(ThongBao.ngay_tao.desc()).limit(5).all()
        return dict(
            pending_incidents_count=pending_incidents_count,
            unread_notifications_count=unread_notifications_count,
            recent_notifications=recent_notifications
        )
    return {}

# --- Các Route của Admin ---
@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """
    Cung cấp "bàn làm việc" cho admin, tổng hợp các thông tin nóng và các vấn đề cần xử lý ngay lập tức.
    """
    # --- 1. HÀNG TRÊN CÙNG: BỐN THẺ THỐNG KÊ LỚN ---
    
    # Tổng số người dùng
    total_users = NguoiDung.query.count()


    # Đơn hàng hôm nay
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    today_orders_count = DonThuoc.query.filter(
        DonThuoc.thoi_gian_tao_don.between(today_start, today_end)
    ).count()

    # Sự cố chờ xử lý (lấy từ context processor cũng được, nhưng tính lại cho rõ)
    pending_incidents_count = BaoCaoSuCo.query.filter_by(
        trang_thai=TrangThaiSuCoEnum.pending
    ).count()

    # Thiết bị (Giả định chỉ có 1 thiết bị)
    total_devices = ThietBi.query.count()

    # --- 2. CỘT TRÁI (LỚN) ---

    # Biểu đồ đường "Hoạt động trong ngày"
    hourly_activity_query = db.session.query(
        func.extract('hour', DonThuoc.thoi_gian_tao_don).label('hour'),
        func.count(DonThuoc.id).label('order_count')
    ).filter(
        DonThuoc.thoi_gian_tao_don.between(today_start, today_end)
    ).group_by('hour').all()
    
    # Chuẩn bị dữ liệu cho Chart.js.
    chart_labels = list(range(24)) # Giờ từ 0-23
    chart_data = [0] * 24
    for activity in hourly_activity_query:
        chart_data[activity.hour] = activity.order_count

    # Bảng "Hiệu suất dược sĩ hôm nay"
    # Bảng "Hiệu suất dược sĩ hôm nay"
    pharmacist_performance_today = db.session.query(
        NguoiDung.ho_ten,
        func.count(DonThuoc.id).label('total_orders'),
        func.sum(DonThuoc.tong_vien_dem_duoc).label('total_pills_counted')
    ).join(DonThuoc, NguoiDung.id == DonThuoc.id_duoc_si)\
     .filter(DonThuoc.thoi_gian_tao_don.between(today_start, today_end))\
     .filter(NguoiDung.vai_tro == VaiTroEnum.pharmacist)\
     .group_by(NguoiDung.id, NguoiDung.ho_ten)\
     .order_by(func.count(DonThuoc.id).desc())\
     .all()

    # --- 3. CỘT PHẢI (NHỎ) ---

    # Widget "Sự cố cần chú ý"
    attention_incidents = BaoCaoSuCo.query.filter_by(
        trang_thai=TrangThaiSuCoEnum.pending
    ).order_by(BaoCaoSuCo.ngay_tao.desc()).limit(5).all()

    # Widget "Nhật ký hệ thống gần đây"
    recent_system_logs = NhatKyHeThong.query.order_by(
        NhatKyHeThong.ngay_tao.desc()
    ).limit(5).all()

    # --- 4. RENDER TEMPLATE VỚI DỮ LIỆU ĐÃ TRUY VẤN ---
    return render_template(
        'admin/dashboard.html',
        # Dữ liệu cho các thẻ thống kê
        total_users=total_users,
        today_orders_count=today_orders_count,
        pending_incidents_count=pending_incidents_count,
        total_devices=total_devices,
        
        # Dữ liệu cho biểu đồ
        chart_labels=chart_labels,
        chart_data=chart_data,

        # Dữ liệu cho bảng hiệu suất
        pharmacist_performance_today=pharmacist_performance_today,

        # Dữ liệu cho các widget cột phải
        attention_incidents=attention_incidents,
        recent_system_logs=recent_system_logs
    )


@admin.route('/users')
@login_required
@admin_required
def users():
    all_users = NguoiDung.query.all()
    return render_template('admin/users.html', users=all_users)

@admin.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        ho_ten = request.form.get('ho_ten')
        ten_dang_nhap = request.form.get('ten_dang_nhap')
        email = request.form.get('email')
        so_dien_thoai = request.form.get('so_dien_thoai')
        mat_khau = request.form.get('mat_khau')
        vai_tro = request.form.get('vai_tro')
        dang_hoat_dong = 'dang_hoat_dong' in request.form

        existing_user = NguoiDung.query.filter_by(ten_dang_nhap=ten_dang_nhap).first()
        if existing_user:
            flash('Tên đăng nhập đã tồn tại.', 'danger')
            return redirect(url_for('admin.add_user'))

        new_user = NguoiDung(
            ho_ten=ho_ten,
            ten_dang_nhap=ten_dang_nhap,
            email=email,
            so_dien_thoai=so_dien_thoai,
            vai_tro=VaiTroEnum[vai_tro],
            dang_hoat_dong=dang_hoat_dong
        )
        new_user.set_password(mat_khau)
        db.session.add(new_user)
        db.session.commit()
        flash('Thêm người dùng mới thành công!', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', action='add')

@admin.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user_to_edit = NguoiDung.query.get_or_404(user_id)
    if request.method == 'POST':
        user_to_edit.ho_ten = request.form.get('ho_ten')
        user_to_edit.email = request.form.get('email')
        user_to_edit.so_dien_thoai = request.form.get('so_dien_thoai')
        user_to_edit.vai_tro = VaiTroEnum[request.form.get('vai_tro')]
        user_to_edit.dang_hoat_dong = 'dang_hoat_dong' in request.form
        
        new_password = request.form.get('mat_khau')
        if new_password:
            user_to_edit.set_password(new_password)
            
        db.session.commit()
        flash('Cập nhật thông tin người dùng thành công!', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', action='edit', user=user_to_edit)

@admin.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user_to_delete = NguoiDung.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    flash('Xóa người dùng thành công!', 'success')
    return redirect(url_for('admin.users'))

# --- QUẢN LÝ THUỐC (Drugs) ---
@admin.route('/drugs')
@login_required
@admin_required
def drugs():
    """Hiển thị danh sách tất cả các loại thuốc."""
    all_drugs = LoaiThuoc.query.order_by(LoaiThuoc.ten_thuoc).all()
    return render_template('admin/drugs.html', drugs=all_drugs)

@admin.route('/drugs/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_drug():
    """Hiển thị form và xử lý thêm thuốc mới."""
    if request.method == 'POST':
        ma_thuoc = request.form.get('ma_thuoc')
        
        # Kiểm tra xem mã thuốc đã tồn tại chưa
        existing_drug = LoaiThuoc.query.filter_by(ma_thuoc=ma_thuoc).first()
        if existing_drug:
            flash(f'Mã thuốc "{ma_thuoc}" đã tồn tại. Vui lòng chọn một mã khác.', 'danger')
            return render_template('admin/drug_form.html', action='add', drug=request.form)

        # Xử lý upload ảnh
        url_hinh_anh = None
        if 'hinh_anh' in request.files:
            file = request.files['hinh_anh']
            if file and file.filename:
                # Tạo tên file an toàn: ma_thuoc + timestamp
                ext = os.path.splitext(file.filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    filename = f"{ma_thuoc}_{int(datetime.now().timestamp())}{ext}"
                    filename = secure_filename(filename)
                    
                    # Đường dẫn thư mục lưu ảnh
                    upload_folder = os.path.join(os.path.dirname(__file__), 'static', 'picture', 'pills')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    file.save(os.path.join(upload_folder, filename))
                    url_hinh_anh = f"/static/picture/pills/{filename}"

        thuoc_moi = LoaiThuoc(
            ten_thuoc=request.form.get('ten_thuoc'),
            ma_thuoc=ma_thuoc,
            mo_ta=request.form.get('mo_ta'),
            don_vi_tinh=request.form.get('don_vi_tinh', 'viên'),
            ton_kho_uoc_tinh=int(request.form.get('ton_kho_uoc_tinh', 0)),
            nguong_canh_bao=int(request.form.get('nguong_canh_bao', 0)),
            url_hinh_anh=url_hinh_anh
        )
        db.session.add(thuoc_moi)
        db.session.commit()
        flash(f'Đã thêm thuốc "{thuoc_moi.ten_thuoc}" thành công!', 'success')
        return redirect(url_for('admin.drugs'))
        
    return render_template('admin/drug_form.html', action='add', drug={})

@admin.route('/drugs/edit/<int:drug_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_drug(drug_id):
    """Hiển thị form và xử lý cập nhật thông tin thuốc."""
    thuoc_can_sua = LoaiThuoc.query.get_or_404(drug_id)
    
    if request.method == 'POST':
        ma_thuoc_moi = request.form.get('ma_thuoc')
        
        # Kiểm tra nếu mã thuốc bị thay đổi và mã mới đã thuộc về một thuốc khác
        if thuoc_can_sua.ma_thuoc != ma_thuoc_moi:
            existing_drug = LoaiThuoc.query.filter_by(ma_thuoc=ma_thuoc_moi).first()
            if existing_drug:
                flash(f'Mã thuốc "{ma_thuoc_moi}" đã tồn tại. Vui lòng chọn một mã khác.', 'danger')
                return render_template('admin/drug_form.html', action='edit', drug=request.form)

        thuoc_can_sua.ten_thuoc = request.form.get('ten_thuoc')
        thuoc_can_sua.ma_thuoc = ma_thuoc_moi
        thuoc_can_sua.mo_ta = request.form.get('mo_ta')
        thuoc_can_sua.don_vi_tinh = request.form.get('don_vi_tinh', 'viên')
        thuoc_can_sua.ton_kho_uoc_tinh = int(request.form.get('ton_kho_uoc_tinh', 0))
        thuoc_can_sua.nguong_canh_bao = int(request.form.get('nguong_canh_bao', 0))
        
        # Xử lý upload ảnh mới
        if 'hinh_anh' in request.files:
            file = request.files['hinh_anh']
            if file and file.filename:
                ext = os.path.splitext(file.filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    # Xóa ảnh cũ nếu có
                    if thuoc_can_sua.url_hinh_anh:
                        old_filename = thuoc_can_sua.url_hinh_anh.split('/')[-1]
                        old_path = os.path.join(os.path.dirname(__file__), 'static', 'picture', 'pills', old_filename)
                        if os.path.exists(old_path) and old_filename != 'default.png':
                            try:
                                os.remove(old_path)
                            except:
                                pass
                    
                    # Lưu ảnh mới
                    filename = f"{ma_thuoc_moi}_{int(datetime.now().timestamp())}{ext}"
                    filename = secure_filename(filename)
                    upload_folder = os.path.join(os.path.dirname(__file__), 'static', 'picture', 'pills')
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, filename))
                    thuoc_can_sua.url_hinh_anh = f"/static/picture/pills/{filename}"
        
        db.session.commit()
        flash(f'Cập nhật thông tin thuốc "{thuoc_can_sua.ten_thuoc}" thành công!', 'success')
        return redirect(url_for('admin.drugs'))

    return render_template('admin/drug_form.html', action='edit', drug=thuoc_can_sua)

@admin.route('/drugs/delete/<int:drug_id>', methods=['POST'])
@login_required
@admin_required
def delete_drug(drug_id):
    """Xử lý yêu cầu xóa thuốc."""
    thuoc_can_xoa = LoaiThuoc.query.get_or_404(drug_id)
    ten_thuoc_da_xoa = thuoc_can_xoa.ten_thuoc
    db.session.delete(thuoc_can_xoa)
    db.session.commit()
    flash(f'Đã xóa thuốc "{ten_thuoc_da_xoa}" thành công.', 'success')
    return redirect(url_for('admin.drugs'))

# --- Các route placeholder để tránh lỗi BuildError ---
@admin.route('/devices', methods=['GET', 'POST'])
@login_required
@admin_required
def devices():
    """Hiển thị trang thông tin chi tiết của thiết bị đếm thuốc."""
    device = ThietBi.query.get_or_404(1)
    
    if request.method == 'POST':
        # Cập nhật thông tin thiết bị
        new_ip = request.form.get('dia_chi_ip', '').strip()
        new_name = request.form.get('ten_thiet_bi', '').strip()
        
        if new_ip:
            device.dia_chi_ip = new_ip
        if new_name:
            device.ten_thiet_bi = new_name
            
        db.session.commit()
        flash('Đã cập nhật thông tin thiết bị!', 'success')
        return redirect(url_for('admin.devices'))
    
    # Đếm số đơn thật từ database
    total_orders = DonThuoc.query.filter_by(trang_thai_don='completed').count()
    
    return render_template('admin/devices.html', 
                           device=device, 
                           total_orders=total_orders,
                           TrangThaiThietBiEnum=TrangThaiThietBiEnum)

def get_report_data(time_range, start_date_str, end_date_str):
    """Hàm helper để lấy dữ liệu báo cáo dựa trên bộ lọc thời gian."""
    today = date.today()
    start_date, end_date = None, None

    if time_range == 'today':
        start_date = today
        end_date = today + timedelta(days=1)
    elif time_range == '7_days':
        start_date = today - timedelta(days=6)
        end_date = today + timedelta(days=1)
    elif time_range == 'this_month':
        start_date = today.replace(day=1)
        # Cách tính ngày đầu của tháng sau một cách an toàn
        next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_date = next_month
    elif time_range == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() + timedelta(days=1)
        except ValueError:
            flash('Định dạng ngày không hợp lệ. Vui lòng chọn lại.', 'danger')
            start_date = today.replace(day=1)
            next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_date = next_month
    else: # Mặc định là tháng này nếu không có tham số
        start_date = today.replace(day=1)
        next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_date = next_month

    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.min.time())

    pharmacist_performance = db.session.query(
        NguoiDung.ho_ten,
        func.count(DonThuoc.id).label('total_prescriptions'),
        func.avg(DonThuoc.thoi_gian_xu_ly_ms).label('avg_time'),
        func.sum(DonThuoc.tong_vien_dem_duoc).label('total_pills_counted')
    ).join(DonThuoc, NguoiDung.id == DonThuoc.id_duoc_si)\
     .filter(DonThuoc.thoi_gian_tao_don.between(start_datetime, end_datetime))\
     .filter(NguoiDung.vai_tro == VaiTroEnum.pharmacist)\
     .group_by(NguoiDung.id, NguoiDung.ho_ten)\
     .order_by(func.count(DonThuoc.id).desc())\
     .all()

    top_drugs = db.session.query(
        LoaiThuoc.ten_thuoc,
        func.sum(ChiTietDonThuoc.so_luong_dem_duoc).label('total_counted')
    ).join(LoaiThuoc, ChiTietDonThuoc.id_loai_thuoc == LoaiThuoc.id)\
     .join(DonThuoc, ChiTietDonThuoc.id_don_thuoc == DonThuoc.id)\
     .filter(DonThuoc.thoi_gian_tao_don.between(start_datetime, end_datetime))\
     .group_by(LoaiThuoc.id)\
     .order_by(func.sum(ChiTietDonThuoc.so_luong_dem_duoc).desc())\
     .limit(10)\
     .all()

    low_stock_drugs = LoaiThuoc.query.filter(
        LoaiThuoc.ton_kho_uoc_tinh < LoaiThuoc.nguong_canh_bao
    ).order_by(LoaiThuoc.ton_kho_uoc_tinh.asc()).all()

    return {
        "pharmacist_performance": pharmacist_performance,
        "top_drugs": top_drugs,
        "low_stock_drugs": low_stock_drugs,
        "start_date": start_date,
        "end_date": end_date,
        "selected_range": time_range
    }

@admin.route('/reports')
@login_required
@admin_required
def reports():
    """Hiển thị trang báo cáo tổng hợp với bộ lọc thời gian."""
    time_range = request.args.get('range', 'this_month')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    report_data = get_report_data(time_range, start_date_str, end_date_str)
    
    return render_template('admin/reports.html',
                           pharmacist_performance=report_data["pharmacist_performance"],
                           top_drugs=report_data["top_drugs"],
                           low_stock_drugs=report_data["low_stock_drugs"],
                           selected_range=report_data["selected_range"],
                           start_date=report_data["start_date"],
                           end_date=report_data["end_date"] - timedelta(days=1)
                          )

# --- PHẦN MỚI: ROUTE ĐỂ XUẤT BÁO CÁO RA FILE EXCEL ---
@admin.route('/reports/export')
@login_required
@admin_required
def export_reports():
    """Tạo và trả về file Excel chứa dữ liệu báo cáo."""
    time_range = request.args.get('range', 'this_month')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Sử dụng lại hàm helper để lấy dữ liệu, tránh lặp code
    report_data = get_report_data(time_range, start_date_str, end_date_str)

    # Tạo file Excel trong bộ nhớ
    output = BytesIO()
    workbook = Workbook()
    bold_font = Font(bold=True)

    # --- Sheet 1: Hiệu suất Dược sĩ ---
    ws1 = workbook.active
    ws1.title = "Hieu Suat Duoc Si"
    headers1 = ["Tên Dược Sĩ", "Tổng Số Đơn", "TG Xử Lý TB (giây)", "Tỷ Lệ Chính Xác (%)"]
    ws1.append(headers1)
    for cell in ws1[1]:
        cell.font = bold_font
    for row in report_data["pharmacist_performance"]:
        ws1.append([
            row.ho_ten, 
            row.total_prescriptions, 
            f"{row.avg_time:.2f}" if row.avg_time else 0, 
            row.ty_le_chinh_xac
        ])

    # --- Sheet 2: Top Thuốc Sử Dụng ---
    ws2 = workbook.create_sheet(title="Top Thuoc Su Dung")
    headers2 = ["Tên Thuốc", "Tổng Số Lượng Đã Đếm"]
    ws2.append(headers2)
    for cell in ws2[1]:
        cell.font = bold_font
    for row in report_data["top_drugs"]:
        ws2.append([row.ten_thuoc, row.total_counted])

    # --- Sheet 3: Thuốc Sắp Hết Hàng ---
    ws3 = workbook.create_sheet(title="Thuoc Sap Het Hang")
    headers3 = ["Tên Thuốc", "Mã Thuốc", "Tồn Kho", "Ngưỡng Cảnh Báo"]
    ws3.append(headers3)
    for cell in ws3[1]:
        cell.font = bold_font
    for drug in report_data["low_stock_drugs"]:
        ws3.append([drug.ten_thuoc, drug.ma_thuoc, drug.ton_kho_uoc_tinh, drug.nguong_canh_bao])

    # Lưu workbook vào stream BytesIO
    workbook.save(output)
    output.seek(0)
    
    # Tạo tên file động dựa trên khoảng thời gian
    start_date = report_data["start_date"]
    end_date = report_data["end_date"]
    filename = f"BaoCao_{start_date.strftime('%Y%m%d')}-{(end_date - timedelta(days=1)).strftime('%Y%m%d')}.xlsx"

    # Trả về file cho người dùng tải xuống
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@admin.route('/incidents')
@login_required
@admin_required
def incidents():
    """Hiển thị danh sách sự cố với các tab lọc theo trạng thái."""
    # Lấy tham số lọc từ URL, mặc định là 'pending'
    status_filter = request.args.get('status', 'pending') 

    query = BaoCaoSuCo.query

    if status_filter == 'pending':
        query = query.filter_by(trang_thai=TrangThaiSuCoEnum.pending)
    elif status_filter == 'reviewing':
        query = query.filter_by(trang_thai=TrangThaiSuCoEnum.reviewing)
    elif status_filter == 'resolved':
        query = query.filter_by(trang_thai=TrangThaiSuCoEnum.resolved)
    # Nếu status_filter == 'all', không cần thêm filter

    # Sắp xếp các sự cố mới nhất lên đầu
    all_incidents = query.order_by(BaoCaoSuCo.ngay_tao.desc()).all()

    return render_template('admin/incidents.html', 
                           incidents=all_incidents, 
                           current_filter=status_filter)


@admin.route('/incidents/<int:incident_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def incident_detail(incident_id):
    """Hiển thị chi tiết và xử lý một sự cố."""
    incident = BaoCaoSuCo.query.get_or_404(incident_id)

    if request.method == 'POST':
        new_status_str = request.form.get('trang_thai')
        admin_response = request.form.get('phan_hoi_admin')

        # Cập nhật trạng thái
        if new_status_str and new_status_str in TrangThaiSuCoEnum.__members__:
            incident.trang_thai = TrangThaiSuCoEnum[new_status_str]
        
        # Cập nhật phản hồi
        incident.phan_hoi_admin = admin_response
        
        # Ghi nhận thời gian xử lý
        incident.ngay_xu_ly = datetime.now()
        
        db.session.commit()
        
        # ✅ GỬI THÔNG BÁO CHO DƯỢC SĨ ĐÃ BÁO CÁO
        from .utils import create_notification
        if incident.trang_thai in [TrangThaiSuCoEnum.resolved, TrangThaiSuCoEnum.rejected]:
            status_text = "đã được giải quyết" if incident.trang_thai == TrangThaiSuCoEnum.resolved else "đã bị từ chối"
            notif_type = LoaiThongBaoEnum.success if incident.trang_thai == TrangThaiSuCoEnum.resolved else LoaiThongBaoEnum.warning
            create_notification(
                user_id=incident.id_nguoi_bao_cao,
                title=f"Sự cố của bạn {status_text}",
                content=f"Phản hồi từ Admin: {admin_response[:100]}{'...' if admin_response and len(admin_response) > 100 else ''}" if admin_response else "Không có phản hồi.",
                notif_type=notif_type
            )
        
        flash('Đã cập nhật sự cố thành công!', 'success')
        return redirect(url_for('admin.incidents', status=incident.trang_thai.name))

    # Cho GET request, chỉ hiển thị trang
    return render_template('admin/incident_detail.html', 
                           incident=incident,
                           TrangThaiSuCoEnum=TrangThaiSuCoEnum) # Truyền Enum vào template

@admin.route('/system-logs')
@login_required
@admin_required
def system_logs():
    """
    Hiển thị nhật ký hệ thống với các bộ lọc và phân trang.
    """
    # Lấy số trang hiện tại từ URL, mặc định là trang 1.
    page = request.args.get('page', 1, type=int)

    # Bắt đầu với một câu truy vấn cơ bản, chưa có điều kiện lọc.
    # Chúng ta sẽ thêm các bộ lọc vào đối tượng 'query' này.
    query = NhatKyHeThong.query

    # --- Xử lý các bộ lọc từ URL ---
    log_type = request.args.get('log_type')
    user_id = request.args.get('user_id')
    log_date_str = request.args.get('log_date')

    # 1. Lọc theo Loại Log (nếu có)
    # Kiểm tra xem log_type có được cung cấp và có phải là một thành viên hợp lệ của Enum không.
    if log_type and log_type in LoaiLogEnum.__members__:
        query = query.filter(NhatKyHeThong.loai_log == LoaiLogEnum[log_type])

    # 2. Lọc theo Người Dùng (nếu có)
    if user_id:
        query = query.filter(NhatKyHeThong.id_nguoi_dung == user_id)
        
    # 3. Lọc theo Ngày (nếu có)
    if log_date_str:
        try:
            # Chuyển đổi chuỗi ngày từ form (YYYY-MM-DD) thành đối tượng date
            log_date = datetime.strptime(log_date_str, '%Y-%m-%d').date()
            # Tạo khoảng thời gian từ đầu ngày đến cuối ngày để lọc
            start_of_day = datetime.combine(log_date, datetime.min.time())
            end_of_day = datetime.combine(log_date, datetime.max.time())
            query = query.filter(NhatKyHeThong.ngay_tao.between(start_of_day, end_of_day))
        except ValueError:
            # Nếu người dùng nhập định dạng ngày sai, bỏ qua bộ lọc và thông báo lỗi.
            flash('Định dạng ngày không hợp lệ. Vui lòng chọn lại.', 'warning')

    # --- Sắp xếp và thực hiện truy vấn với phân trang ---
    # Sắp xếp theo ngày tạo, mới nhất lên đầu, và chia kết quả thành các trang (20 mục/trang)
    logs = query.order_by(NhatKyHeThong.ngay_tao.desc()).paginate(page=page, per_page=20)
    
    # Lấy danh sách tất cả người dùng để hiển thị trong dropdown của bộ lọc
    all_users = NguoiDung.query.order_by(NguoiDung.ho_ten).all()

    # Tạo một dictionary chứa các giá trị bộ lọc hiện tại để gửi đến template
    # Điều này giúp tạo "sticky form" và giữ bộ lọc khi chuyển trang.
    filters = {
        'log_type': log_type, 
        'user_id': user_id, 
        'log_date': log_date_str
    }

    # Trả về template và truyền vào các dữ liệu cần thiết
    return render_template('admin/system_logs.html', 
                           logs=logs,  # Đối tượng phân trang (chứa cả log và thông tin trang)
                           all_users=all_users,  # Danh sách người dùng cho bộ lọc
                           LoaiLogEnum=LoaiLogEnum, # Enum để tạo bộ lọc loại log
                           filters=filters) # Các giá trị bộ lọc hiện tại




@admin.route('/profile')
@login_required
@admin_required
def profile():
    return redirect(url_for('main.profile')) # Dùng chung trang profile

# --- Các route cho Quick Actions ---

# --- THÔNG BÁO (Notifications) ---
@admin.route('/notifications')
@login_required
@admin_required
def all_notifications():
    """Hiển thị tất cả thông báo của admin."""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search_query', '').strip()
    filter_loai = request.args.get('filter_loai', '')
    
    query = ThongBao.query.filter_by(id_nguoi_dung=current_user.id).order_by(ThongBao.ngay_tao.desc())
    
    if search_query:
        query = query.filter(ThongBao.noi_dung.ilike(f'%{search_query}%'))
    
    if filter_loai:
        try:
            loai_enum = LoaiThongBaoEnum[filter_loai]
            query = query.filter(ThongBao.loai == loai_enum)
        except KeyError:
            pass
    
    pagination = query.paginate(page=page, per_page=15, error_out=False)
    
    return render_template('admin/notifications.html',
                           notifications=pagination.items,
                           pagination=pagination,
                           search_query=search_query,
                           current_filter=filter_loai)


@admin.route('/notifications/history')
@login_required
@admin_required
def notification_history():
    """Xem lịch sử thông báo - có thể lọc 'của tôi' hoặc 'toàn hệ thống'."""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '').strip()
    filter_loai = request.args.get('loai', '')
    filter_user = request.args.get('user_id', 0, type=int)
    mine_only = request.args.get('mine', '') == '1'
    
    query = ThongBao.query.order_by(ThongBao.ngay_tao.desc())
    
    # Filter "Chỉ của tôi"
    if mine_only:
        query = query.filter(ThongBao.id_nguoi_dung == current_user.id)
    elif filter_user:
        query = query.filter(ThongBao.id_nguoi_dung == filter_user)
    
    if search_query:
        query = query.filter(
            (ThongBao.tieu_de.ilike(f'%{search_query}%')) |
            (ThongBao.noi_dung.ilike(f'%{search_query}%'))
        )
    
    if filter_loai:
        try:
            loai_enum = LoaiThongBaoEnum[filter_loai]
            query = query.filter(ThongBao.loai == loai_enum)
        except KeyError:
            pass
    
    pagination = query.paginate(page=page, per_page=20, error_out=False)
    all_users = NguoiDung.query.filter_by(dang_hoat_dong=True).order_by(NguoiDung.ho_ten).all()
    
    # Đếm unread của admin hiện tại
    unread_count = ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).count()
    
    return render_template('admin/notification_history.html',
                           notifications=pagination.items,
                           pagination=pagination,
                           search_query=search_query,
                           current_filter=filter_loai,
                           current_user_filter=filter_user,
                           mine_only=mine_only,
                           unread_count=unread_count,
                           all_users=all_users)


@admin.route('/notifications/mark-all-read', methods=['POST'])
@login_required
@admin_required
def mark_all_read():
    """Đánh dấu tất cả thông báo đã đọc."""
    ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).update({'da_doc': True, 'thoi_gian_doc': datetime.now()})
    db.session.commit()
    flash('Đã đánh dấu tất cả thông báo đã đọc.', 'success')
    return redirect(url_for('admin.notification_history', mine='1'))


@admin.route('/notifications/<int:id>/toggle-read', methods=['POST'])
@login_required
@admin_required
def toggle_read(id):
    """Toggle trạng thái đọc của một thông báo."""
    notif = ThongBao.query.get_or_404(id)
    
    if notif.id_nguoi_dung != current_user.id:
        return {'error': 'Unauthorized'}, 403
    
    notif.da_doc = not notif.da_doc
    if notif.da_doc:
        notif.thoi_gian_doc = datetime.now()
    else:
        notif.thoi_gian_doc = None
    
    db.session.commit()
    return {'da_doc': notif.da_doc}, 200


# --- GỬI THÔNG BÁO (Admin tạo thông báo) ---
@admin.route('/notifications/send', methods=['GET', 'POST'])
@login_required
@admin_required
def send_notification():
    """Trang gửi thông báo cho người dùng."""
    from .utils import create_notification
    
    all_users = NguoiDung.query.filter_by(dang_hoat_dong=True).order_by(NguoiDung.ho_ten).all()
    
    if request.method == 'POST':
        loai_str = request.form.get('loai', 'info')
        tieu_de = request.form.get('tieu_de', '').strip()
        noi_dung = request.form.get('noi_dung', '').strip()
        target_type = request.form.get('target_type', 'all')
        target_users = request.form.getlist('target_users[]')
        
        if not tieu_de or not noi_dung:
            flash('Vui lòng nhập đầy đủ tiêu đề và nội dung!', 'danger')
            return redirect(url_for('admin.send_notification'))
        
        # Xác định loại thông báo
        try:
            loai_enum = LoaiThongBaoEnum[loai_str]
        except KeyError:
            loai_enum = LoaiThongBaoEnum.info
        
        # Xác định danh sách người nhận (chỉ dược sĩ)
        recipients = []
        if target_type == 'pharmacists':
            recipients = [u for u in all_users if u.vai_tro == VaiTroEnum.pharmacist]
        elif target_type == 'select' and target_users:
            user_ids = [int(uid) for uid in target_users]
            recipients = NguoiDung.query.filter(NguoiDung.id.in_(user_ids), NguoiDung.vai_tro == VaiTroEnum.pharmacist).all()
        
        # Gửi thông báo
        count = 0
        for user in recipients:
            create_notification(
                user_id=user.id,
                title=tieu_de,
                content=noi_dung,
                notif_type=loai_enum
            )
            count += 1
        
        flash(f'Đã gửi thông báo thành công cho {count} người!', 'success')
        return redirect(url_for('admin.send_notification'))
    
    # GET request
    total_sent = ThongBao.query.count()
    recent_sent = ThongBao.query.order_by(ThongBao.ngay_tao.desc()).limit(10).all()
    
    return render_template('admin/send_notification.html',
                           all_users=all_users,
                           total_sent=total_sent,
                           recent_sent=recent_sent)