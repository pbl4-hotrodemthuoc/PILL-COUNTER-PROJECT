# File: server_app/pharmacist.py
# Phiên bản hoàn chỉnh với chức năng Lịch sử và API được xử lý lỗi tốt hơn.

# --- CÁC THƯ VIỆN CẦN THIẾT ---
from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta, time
import logging # Thêm thư viện logging
from sqlalchemy import func, case, desc, cast, Float
import os # Thêm thư viện os để xử lý đường dẫn file
from werkzeug.utils import secure_filename # Thêm để bảo mật tên file upload

# --- IMPORT CÁC MODEL TỪ DATABASE ---
from .models import (
    db, 
    ThongBao, 
    ThietBi, 
    VaiTroEnum, 
    DonThuoc, 
    ChiTietDonThuoc, 
    LoaiThuoc, 
    TrangThaiKhopDonEnum,
    BaoCaoSuCo,      # <<< THÊM MODEL NÀY
    LoaiSuCoEnum 
)


# --- KHỞI TẠO BLUEPRINT ---
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


@pharmacist.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    
    # 1. THỐNG KÊ TRONG NGÀY (4 Cards trên cùng)
    # Lấy các đơn đã hoàn thành hôm nay của user hiện tại
    stats_query = db.session.query(
        func.count(DonThuoc.id).label('total_orders'),
        func.sum(DonThuoc.tong_vien_dem_duoc).label('total_pills'),
        func.avg(DonThuoc.thoi_gian_xu_ly_giay).label('avg_time'),
        func.sum(DonThuoc.tong_vien_yeu_cau).label('total_requested')
    ).filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don == 'completed',
        func.date(DonThuoc.thoi_gian_ket_thuc) == today
    ).first()

    # Xử lý số liệu để tránh None
    orders_today = stats_query.total_orders or 0
    pills_today = int(stats_query.total_pills or 0)
    avg_time = round(float(stats_query.avg_time or 0), 1)
    
    # Tính tỷ lệ chính xác (Tổng đếm được / Tổng yêu cầu * 100)
    total_req = stats_query.total_requested or 0
    accuracy = 100.0
    if total_req > 0:
        accuracy = (pills_today / total_req) * 100
        # Giới hạn max 100% nếu đếm thừa, hoặc hiển thị đúng thực tế tùy logic
        if accuracy > 100: accuracy = 100 - (accuracy - 100) # Ví dụ đơn giản
    accuracy = round(accuracy, 1)

    # 2. DANH SÁCH ĐƠN CẦN XỬ LÝ (Bảng bên trái)
    # Lấy đơn pending hoặc counting
    pending_orders = DonThuoc.query.filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don.in_(['pending', 'counting'])
    ).order_by(
        # Ưu tiên đơn đang đếm lên đầu, sau đó đến đơn mới nhất
        case((DonThuoc.trang_thai_don == 'counting', 0), else_=1),
        DonThuoc.thoi_gian_tao_don.desc()
    ).limit(10).all()

    # 3. THÔNG BÁO GẦN ĐÂY (Widget phải)
    recent_notifications = ThongBao.query.filter_by(id_nguoi_dung=current_user.id)\
        .order_by(ThongBao.ngay_tao.desc()).limit(3).all()

    # 4. HOẠT ĐỘNG GẦN ĐÂY (Widget phải - Đơn vừa xong)
    recent_history = DonThuoc.query.filter_by(
        id_duoc_si=current_user.id, 
        trang_thai_don='completed'
    ).order_by(DonThuoc.thoi_gian_ket_thuc.desc()).limit(3).all()

    return render_template('pharmacist/dashboard.html',
                           orders_today=orders_today,
                           pills_today=pills_today,
                           avg_time=avg_time,
                           accuracy=accuracy,
                           pending_orders=pending_orders,
                           recent_notifications=recent_notifications,
                           recent_history=recent_history)

@pharmacist.route('/new-order')
@login_required
def new_order():
    return render_template('pharmacist/new_order.html')

@pharmacist.route('/history')
@login_required
def my_history():
    """
    Hiển thị lịch sử các đơn thuốc đã xử lý của dược sĩ,
    hỗ trợ tìm kiếm, lọc và phân trang.
    """
    page = request.args.get('page', 1, type=int)
    
    query = DonThuoc.query.filter_by(id_duoc_si=current_user.id)\
                          .order_by(DonThuoc.thoi_gian_ket_thuc.desc())

    search_ma_don_thuoc = request.args.get('search_ma_don_thuoc', '').strip()
    filter_date_range = request.args.get('filter_date_range', '').strip()
    filter_trang_thai_khop = request.args.get('filter_trang_thai_khop', '').strip()

    if search_ma_don_thuoc:
        query = query.filter(DonThuoc.ma_don_thuoc.ilike(f'%{search_ma_don_thuoc}%'))

    if filter_trang_thai_khop:
        try:
            status_enum = TrangThaiKhopDonEnum[filter_trang_thai_khop]
            query = query.filter(DonThuoc.trang_thai_khop == status_enum)
        except KeyError:
            pass

    if filter_date_range:
        try:
            start_date_str, end_date_str = filter_date_range.split(' - ')
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y').date()
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y').date()
            query = query.filter(db.func.date(DonThuoc.thoi_gian_ket_thuc) >= start_date,
                                 db.func.date(DonThuoc.thoi_gian_ket_thuc) <= end_date)
        except (ValueError, IndexError):
            flash('Định dạng ngày tháng không hợp lệ.', 'warning')
    
    processed_statuses = ['completed', 'error']
    query = query.filter(DonThuoc.trang_thai_don.in_(processed_statuses))
    
    orders = query.paginate(page=page, per_page=10, error_out=False)

    current_filters = {
        'search_ma_don_thuoc': search_ma_don_thuoc,
        'filter_date_range': filter_date_range,
        'filter_trang_thai_khop': filter_trang_thai_khop
    }

    return render_template('pharmacist/my_history.html', 
                           orders=orders, 
                           current_filters=current_filters)


@pharmacist.route('/stats')
@login_required
def my_stats():
    period = request.args.get('period', '7days')
    today = date.today()
    
    if period == '30days':
        start_date = today - timedelta(days=29)
    elif period == 'this_month':
        start_date = today.replace(day=1)
    else: # Mặc định là '7days'
        start_date = today - timedelta(days=6)
    
    end_date = today

    # --- 1. TRUY VẤN CƠ SỞ ---
    # Lấy tất cả chi tiết đơn thuốc đã hoàn thành trong khoảng thời gian
    base_query = db.session.query(
        DonThuoc, ChiTietDonThuoc
    ).join(
        ChiTietDonThuoc, DonThuoc.id == ChiTietDonThuoc.id_don_thuoc
    ).filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don == 'completed',
        db.func.date(DonThuoc.thoi_gian_ket_thuc).between(start_date, end_date)
    )

    completed_orders_in_period = base_query.distinct(DonThuoc.id).count()
    
    # --- 2. BẢNG TỔNG HỢP SỐ LIỆU ---
    summary_stats = {
        'total_orders': completed_orders_in_period,
        'total_pills_counted': 0,
        'total_pills_requested': 0,
        'avg_processing_time': 0
    }
    if completed_orders_in_period > 0:
        summary_q = db.session.query(
            func.sum(DonThuoc.tong_vien_dem_duoc),
            func.sum(DonThuoc.tong_vien_yeu_cau),
            func.avg(DonThuoc.thoi_gian_xu_ly_giay)
        ).filter(
            DonThuoc.id_duoc_si == current_user.id,
            DonThuoc.trang_thai_don == 'completed',
            db.func.date(DonThuoc.thoi_gian_ket_thuc).between(start_date, end_date)
        ).first()
        summary_stats['total_pills_counted'] = int(summary_q[0] or 0)
        summary_stats['total_pills_requested'] = int(summary_q[1] or 0)
        summary_stats['avg_processing_time'] = round(float(summary_q[2] or 0), 2)

    # --- 3. BIỂU ĐỒ XU HƯỚNG HIỆU SUẤT (LINE CHART) ---
    trend_data = db.session.query(
        db.func.date(DonThuoc.thoi_gian_ket_thuc).label('date'),
        func.avg(DonThuoc.thoi_gian_xu_ly_giay).label('avg_time'),
        (func.sum(DonThuoc.tong_vien_dem_duoc) * 100.0 / func.sum(DonThuoc.tong_vien_yeu_cau)).label('accuracy')
    ).filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don == 'completed',
        DonThuoc.tong_vien_yeu_cau > 0,
        db.func.date(DonThuoc.thoi_gian_ket_thuc).between(start_date, end_date)
    ).group_by('date').order_by('date').all()
    
    trend_chart_data = {
        'labels': [d.date.strftime('%d/%m') for d in trend_data],
        'accuracy_data': [round(float(d.accuracy), 2) for d in trend_data],
        'time_data': [round(float(d.avg_time), 2) for d in trend_data]
    }

    # --- 4. BIỂU ĐỒ PHÂN BỐ LỖI (PIE CHART) ---
    error_dist = base_query.with_entities(
        func.sum(case((ChiTietDonThuoc.chenh_lech < 0, func.abs(ChiTietDonThuoc.chenh_lech)), else_=0)).label('under'),
        func.sum(case((ChiTietDonThuoc.chenh_lech > 0, ChiTietDonThuoc.chenh_lech), else_=0)).label('over')
    ).first()
    
    pie_chart_data = {
        'under_count': int(error_dist.under or 0),
        'over_count': int(error_dist.over or 0),
    }
    pie_chart_data['total_errors'] = pie_chart_data['under_count'] + pie_chart_data['over_count']
    
    # --- 5. TOP 5 LOẠI THUỐC ---
    # Top 5 đếm nhiều nhất
    top_counted_drugs = base_query.with_entities(
        LoaiThuoc.ten_thuoc,
        func.sum(ChiTietDonThuoc.so_luong_dem_duoc).label('total')
    ).join(LoaiThuoc, ChiTietDonThuoc.id_loai_thuoc == LoaiThuoc.id)\
     .group_by(LoaiThuoc.ten_thuoc)\
     .order_by(desc('total'))\
     .limit(5).all()

    # Top 5 hay đếm sai nhất (tỷ lệ chính xác thấp nhất)
    top_inaccurate_drugs_q = base_query.with_entities(
        LoaiThuoc.ten_thuoc,
        (cast(func.sum(ChiTietDonThuoc.so_luong_dem_duoc), Float) * 100 / func.sum(ChiTietDonThuoc.so_luong_yeu_cau)).label('accuracy'),
        func.sum(ChiTietDonThuoc.so_luong_yeu_cau).label('total_req')
    ).join(LoaiThuoc, ChiTietDonThuoc.id_loai_thuoc == LoaiThuoc.id)\
     .filter(ChiTietDonThuoc.so_luong_yeu_cau > 0)\
     .group_by(LoaiThuoc.ten_thuoc)\
     .having(func.sum(ChiTietDonThuoc.so_luong_dem_duoc) != func.sum(ChiTietDonThuoc.so_luong_yeu_cau))\
     .order_by('accuracy')\
     .limit(5).all()

    return render_template(
        'pharmacist/my_stats.html',
        period=period,
        summary_stats=summary_stats,
        trend_chart_data=trend_chart_data,
        pie_chart_data=pie_chart_data,
        top_counted_drugs=top_counted_drugs,
        top_inaccurate_drugs=top_inaccurate_drugs_q
    )


@pharmacist.route('/report-incident', methods=['GET', 'POST'])
@login_required
def report_incident():
    if request.method == 'POST':
        loai_su_co_str = request.form.get('loai_su_co')
        ma_don_thuoc = request.form.get('ma_don_thuoc', '').strip()
        mo_ta = request.form.get('mo_ta', '').strip()
        file = request.files.get('hinh_anh')

        if not loai_su_co_str or not mo_ta:
            flash('Loại sự cố và Mô tả chi tiết là bắt buộc.', 'danger')
            return redirect(url_for('pharmacist.report_incident'))
        
        try:
            loai_su_co_enum = LoaiSuCoEnum[loai_su_co_str]
        except KeyError:
            flash('Loại sự cố không hợp lệ.', 'danger')
            return redirect(url_for('pharmacist.report_incident'))

        url_hinh_anh_luu = None
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'server_app/static/uploads/incidents')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)
            url_hinh_anh_luu = f'uploads/incidents/{unique_filename}'
        
        id_don_thuoc_db = None
        if ma_don_thuoc:
            don_thuoc = DonThuoc.query.filter_by(ma_don_thuoc=ma_don_thuoc).first()
            if don_thuoc:
                id_don_thuoc_db = don_thuoc.id
            else:
                flash(f'Không tìm thấy đơn thuốc với mã "{ma_don_thuoc}". Báo cáo vẫn được gửi nhưng không liên kết với đơn thuốc.', 'warning')

        new_report = BaoCaoSuCo(
            id_nguoi_bao_cao=current_user.id,
            loai_su_co=loai_su_co_enum,
            id_don_thuoc=id_don_thuoc_db,
            mo_ta=mo_ta,
            url_hinh_anh=url_hinh_anh_luu
        )
        
        db.session.add(new_report)
        db.session.commit()
        
        flash('Báo cáo của bạn đã được gửi thành công!', 'success')
        return redirect(url_for('pharmacist.report_incident'))

    past_reports = BaoCaoSuCo.query.filter_by(id_nguoi_bao_cao=current_user.id)\
                                   .order_by(BaoCaoSuCo.ngay_tao.desc())\
                                   .all()

    return render_template('pharmacist/report_incident.html', 
                           incident_types=LoaiSuCoEnum, 
                           past_reports=past_reports)

@pharmacist.route('/guide')
@login_required
def guide():
    return render_template('pharmacist/guide.html')


# --- CÁC ROUTE XỬ LÝ NGHIỆP VỤ CHO LAYOUT ---

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
    return redirect(request.referrer or url_for('pharmacist.dashboard'))


# --- CẬP NHẬT FILE: server_app/pharmacist.py ---

@pharmacist.route('/notifications/all')
@login_required
def all_notifications():
    page = request.args.get('page', 1, type=int)
    filter_loai = request.args.get('filter_loai', '')
    search_query = request.args.get('search_query', '').strip()
    per_page = 15

    # Query cơ bản
    query = ThongBao.query.filter_by(id_nguoi_dung=current_user.id)

    # 1. Xử lý Tìm kiếm (Tìm theo tiêu đề hoặc nội dung)
    if search_query:
        query = query.filter(
            (ThongBao.tieu_de.ilike(f'%{search_query}%')) | 
            (ThongBao.noi_dung.ilike(f'%{search_query}%'))
        )

    # 2. Xử lý Lọc loại
    if filter_loai and filter_loai != 'all':
        try:
            # Giả sử bạn đã import LoaiThongBaoEnum
            query = query.filter(ThongBao.loai == filter_loai)
        except:
            pass

    # 3. Sắp xếp (Chưa đọc lên trước, Mới nhất lên trước)
    query = query.order_by(ThongBao.da_doc.asc(), ThongBao.ngay_tao.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    notifications = pagination.items

    return render_template('pharmacist/notifications.html', 
                           notifications=notifications, 
                           pagination=pagination,
                           current_filter=filter_loai,
                           search_query=search_query) # Truyền lại search_query ra view

@pharmacist.route('/settings')
@login_required
def settings():
    return "Trang Cài đặt của Dược sĩ"


# --- API ENDPOINT ĐỂ LẤY CHI TIẾT ĐƠN THUỐC (ĐÃ CẬP NHẬT) ---

@pharmacist.route('/api/order-details/<int:order_id>')
@login_required
def get_order_details(order_id):
    """
    API endpoint để lấy chi tiết một đơn thuốc dưới dạng JSON.
    Đã thêm xử lý lỗi để đảm bảo hoạt động ổn định.
    """
    try:
        order = DonThuoc.query.filter_by(id=order_id, id_duoc_si=current_user.id).first()

        if not order:
            return jsonify({'error': 'Không tìm thấy đơn thuốc hoặc bạn không có quyền truy cập.'}), 404

        details = db.session.query(
            ChiTietDonThuoc, LoaiThuoc.ten_thuoc
        ).join(
            LoaiThuoc, ChiTietDonThuoc.id_loai_thuoc == LoaiThuoc.id
        ).filter(
            ChiTietDonThuoc.id_don_thuoc == order.id
        ).all()

        details_list = [
            {
                'ten_thuoc': ten_thuoc,
                'so_luong_yeu_cau': detail.so_luong_yeu_cau,
                'so_luong_dem_duoc': detail.so_luong_dem_duoc or 0,
                'chenh_lech': detail.chenh_lech or 0,
                'url_hinh_anh': detail.url_hinh_anh,
            } for detail, ten_thuoc in details
        ]

        response_data = {
            'ma_don_thuoc': order.ma_don_thuoc,
            'duoc_si_xu_ly': order.duoc_si.ho_ten,
            'thoi_gian_tao_don': order.thoi_gian_tao_don.strftime('%H:%M %d/%m/%Y'),
            'thoi_gian_ket_thuc': order.thoi_gian_ket_thuc.strftime('%H:%M %d/%m/%Y') if order.thoi_gian_ket_thuc else 'N/A',
            'thoi_gian_xu_ly_giay': order.thoi_gian_xu_ly_giay,
            'tong_vien_yeu_cau': order.tong_vien_yeu_cau,
            'tong_vien_dem_duoc': order.tong_vien_dem_duoc,
            'ghi_chu_duoc_si': order.ghi_chu_duoc_si or '',
            'ghi_chu_he_thong': order.ghi_chu_he_thong or '',
            'chi_tiet': details_list
        }
        return jsonify(response_data)

    except Exception as e:
        # Ghi lại lỗi ra console của server để debug
        logging.error(f"Error fetching order details for order_id {order_id}: {e}")
        # Trả về một lỗi chung cho client
        return jsonify({'error': 'Đã xảy ra lỗi ở máy chủ khi truy vấn dữ liệu.'}), 500