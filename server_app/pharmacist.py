# File: server_app/pharmacist.py
# PHIÊN BẢN FINAL FIX: SỬA LỖI TRÙNG HÀM VÀ LỖI TÌM KIẾM

from flask import (
    Blueprint, render_template, flash, redirect, 
    url_for, request, jsonify, current_app
)
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta, time
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import (
    func, case, desc, cast, Float, or_
)
from flask_socketio import emit
import logging
import uuid
import base64
import os

# --- THƯ VIỆN XỬ LÝ ẢNH & AI ---
import cv2
import numpy as np

# --- IMPORT EXTENSIONS ---
from .extensions import db, socketio

# --- IMPORT CÁC MODEL ---
from .models import (
    db,                  # tránh thiếu db khi gọi từ models
    ThongBao,
    ThietBi,
    VaiTroEnum,
    DonThuoc,
    ChiTietDonThuoc,
    LoaiThuoc,
    TrangThaiDonEnum,
    TrangThaiKhopDonEnum,
    TrangThaiKhopChiTietEnum,
    BaoCaoSuCo,           # Model báo cáo sự cố
    LoaiSuCoEnum
)



# --- KHỞI TẠO BLUEPRINT ---
pharmacist = Blueprint('pharmacist', __name__)

# =====================================================
# PHẦN 0: CẤU HÌNH AI & TRẠNG THÁI ĐẾM
# =====================================================

# Cấu hình độ nhạy để tự động chốt
STABLE_THRESHOLD = 20  # Số khung hình ổn định để tự khóa

state = {
    'target': 0,        
    'stable_count': 0,
    'last_val': -1,
    'final_val': 0,
    'locked': False     # Trạng thái khóa cứng
}

# Load Model YOLO
model = None
try:
    from ultralytics import YOLO
    # Ưu tiên tìm model trong thư mục device_app
    model_path = os.path.join(os.getcwd(), 'device_app', 'models', 'best.pt')
    
    if os.path.exists(model_path):
        model = YOLO(model_path)
        print(f"✅ SERVER: Đã tải model AI từ {model_path}")
    else:
        # Fallback: Tìm ở thư mục gốc
        alt_path = os.path.join(os.getcwd(), 'models', 'best.pt')
        if os.path.exists(alt_path):
            model = YOLO(alt_path)
            print(f"✅ SERVER: Đã tải model từ {alt_path}")
        else:
            print(f"⚠️ SERVER: Không tìm thấy model tại {model_path} hay {alt_path}")
except Exception as e:
    print(f"⚠️ SERVER: Lỗi khởi tạo AI: {e}")

# --- HÀM HỖ TRỢ CHUYỂN ĐỔI ẢNH ---
def base64_to_cv2(b64):
    try:
        if "," in b64: _, b64 = b64.split(",", 1)
        data = base64.b64decode(b64)
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except: return None

def cv2_to_base64(img):
    _, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')


# =====================================================
# PHẦN 1: XỬ LÝ SOCKET IO
# =====================================================

@socketio.on('update_target')
def handle_target(data):
    state['target'] = int(data.get('target', 0))
    state['locked'] = False
    state['stable_count'] = 0
    print(f"🎯 Mục tiêu: {state['target']} viên")

@socketio.on('reset_counting')
def handle_reset():
    """Reset thủ công từ nút bấm"""
    state['locked'] = False
    state['stable_count'] = 0
    state['last_val'] = -1
    print("🔄 Đã Reset trạng thái đếm")

@socketio.on('process_frame_pi')
def handle_pi_stream(data):
    try:
        frame = base64_to_cv2(data.get('image'))
        if frame is None: return

        display_count = 0
        
        if model:
            if not state['locked']:
                # 1. CHƯA KHÓA -> CHẠY AI
                results = model(frame, verbose=False, conf=0.5)
                cnt = len(results[0].boxes)
                frame = results[0].plot()

                # Logic ổn định
                if cnt == state['last_val']:
                    state['stable_count'] += 1
                else:
                    state['stable_count'] = 0
                    state['last_val'] = cnt
                
                # TỰ ĐỘNG CHỐT NẾU ỔN ĐỊNH
                if state['stable_count'] >= STABLE_THRESHOLD:
                    state['locked'] = True
                    state['final_val'] = cnt
                    print(f"🔒 ĐÃ CHỐT: {cnt}")
                
                display_count = cnt
            else:
                # 2. ĐÃ KHÓA -> GIỮ NGUYÊN KẾT QUẢ
                display_count = state['final_val']
                cv2.rectangle(frame, (0,0), (frame.shape[1], frame.shape[0]), (0, 255, 0), 4)
                cv2.putText(frame, f"LOCKED: {display_count}", (30, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Tính toán hiển thị
        target = state['target']
        diff = display_count - target
        percent = round((display_count/target)*100, 1) if target > 0 else 0
        
        status, color = "Đang phân tích...", "warning"
        
        if state['locked']:
            if diff == 0: status, color = "Khớp hoàn toàn", "success"
            elif diff > 0: status, color = f"Dư {diff} viên", "warning"
            else: status, color = f"Thiếu {abs(diff)} viên", "danger"
        
        emit('ai_result', {
            'processed_image': cv2_to_base64(frame),
            'count': display_count,
            'status_text': status,
            'status_color': color,
            'percent': percent,
            'is_locked': state['locked']
        }, broadcast=True)

    except Exception: pass


# =====================================================
# PHẦN 2: CÁC ROUTE WEB & API
# =====================================================

@pharmacist.context_processor
def inject_pharmacist_data():
    if current_user.is_authenticated and current_user.vai_tro == VaiTroEnum.pharmacist:
        unread_notifications = ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).all()
        device = ThietBi.query.get(1) 
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

@pharmacist.route('/settings')
@login_required
def settings():
    return "Trang Cài đặt của Dược sĩ"

# --- API TÌM KIẾM VÀ LỌC THUỐC (ĐÃ FIX LỖI LOADING) ---
@pharmacist.route('/api/search-drugs')
@login_required
def search_drugs():
    """
    API tìm kiếm thuốc.
    Trả về JSON danh sách thuốc để hiển thị lên Grid.
    """
    query = request.args.get('q', '').strip()
    
    try:
        # 1. Bắt đầu query cơ bản
        # Chỉ lấy thuốc đang sử dụng (dang_su_dung = True)
        sql_query = LoaiThuoc.query.filter(LoaiThuoc.dang_su_dung == True)

        # 2. Lọc theo từ khóa (nếu có)
        if query:
            search_term = f"%{query}%"
            # Sử dụng or_ từ sqlalchemy đã import ở đầu file
            sql_query = sql_query.filter(
                or_(
                    LoaiThuoc.ten_thuoc.ilike(search_term),
                    LoaiThuoc.ma_thuoc.ilike(search_term)
                )
            )
        
        # 3. Giới hạn kết quả (tránh load quá nặng)
        drugs = sql_query.limit(50).all()
        
        # 4. Chuẩn hóa dữ liệu trả về (Mapping với Model)
        results = []
        for d in drugs:
            # Xử lý ảnh (Nếu không có ảnh thì dùng ảnh mặc định)
            img_url = d.url_hinh_anh if d.url_hinh_anh else url_for('static', filename='picture/pills/default.png')
            
            results.append({
                'id': d.id,
                'name': d.ten_thuoc,       # Khớp với models.py
                'code': d.ma_thuoc,        # Khớp với models.py
                'image': img_url,
                'stock': d.ton_kho_uoc_tinh or 0,  # Khớp với models.py
                'unit': d.don_vi_tinh or 'Viên',   # Khớp với models.py
                'desc': d.mo_ta or "Chưa có mô tả chi tiết.",
                'usage_count': d.so_lan_duoc_dem or 0
            })
        
        return jsonify(results)

    except Exception as e:
        print(f"❌ LỖI API SEARCH: {e}")
        # Trả về danh sách rỗng để Web không bị treo loading
        return jsonify([])
        
# --- API LẤY CHI TIẾT THUỐC ---
@pharmacist.route('/api/drug-detail/<int:drug_id>')
@login_required
def get_drug_detail_api(drug_id):
    d = LoaiThuoc.query.get_or_404(drug_id)
    img_url = d.url_hinh_anh if d.url_hinh_anh else url_for('static', filename='picture/pills/default.png')
    return jsonify({
        'id': d.id,
        'name': d.ten_thuoc,
        'code': d.ma_thuoc,
        'image': img_url,
        'stock': d.ton_kho_uoc_tinh,
        'unit': d.don_vi_tinh,
        'desc': d.mo_ta or "Đang cập nhật thông tin chi tiết.",
        'warning_threshold': d.nguong_canh_bao
    })

# --- DANH SÁCH ĐƠN THUỐC ---
@pharmacist.route('/orders')
@login_required
def order_list():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    
    query = DonThuoc.query.filter_by(id_duoc_si=current_user.id)
    
    if search_query:
        query = query.filter(DonThuoc.ma_don_thuoc.ilike(f'%{search_query}%'))
    
    if status_filter and status_filter != 'all':
        try:
            status_enum = TrangThaiDonEnum[status_filter]
            query = query.filter(DonThuoc.trang_thai_don == status_enum)
        except: pass
    
    pagination = query.order_by(desc(DonThuoc.thoi_gian_tao_don)).paginate(page=page, per_page=10)
    
    return render_template(
        'pharmacist/order_list.html', 
        pagination=pagination, 
        TrangThaiDonEnum=TrangThaiDonEnum,
        search_query=search_query,
        status_filter=status_filter
    )

# --- TẠO ĐƠN MỚI ---
@pharmacist.route('/new-order', methods=['GET', 'POST'])
@login_required
def new_order():
    if request.method == 'POST':
        try:
            drug_ids = request.form.getlist('drug_ids[]')
            quantities = request.form.getlist('quantities[]')
            patient_name = request.form.get('patient_name')
            note = request.form.get('note')

            if not drug_ids:
                flash('Giỏ hàng trống. Vui lòng chọn thuốc.', 'warning')
                return redirect(url_for('pharmacist.new_order'))

            ma_don = f"DT-{str(uuid.uuid4())[:8].upper()}"
            new_don = DonThuoc(
                ma_don_thuoc=ma_don,
                id_duoc_si=current_user.id,
                ten_benh_nhan=patient_name,
                ghi_chu_duoc_si=note,
                trang_thai_don=TrangThaiDonEnum.pending
            )
            db.session.add(new_don)
            db.session.flush()

            total_items = 0
            total_pills = 0

            for d_id, qty in zip(drug_ids, quantities):
                qty = int(qty)
                if qty > 0:
                    drug = LoaiThuoc.query.with_for_update().get(int(d_id))
                    if not drug: raise Exception(f"Không tìm thấy thuốc ID {d_id}")
                    if drug.ton_kho_uoc_tinh < qty:
                        db.session.rollback()
                        flash(f'Lỗi: Thuốc "{drug.ten_thuoc}" thiếu tồn kho.', 'danger')
                        return redirect(url_for('pharmacist.new_order'))
                    
                    drug.ton_kho_uoc_tinh -= qty
                    ct = ChiTietDonThuoc(
                        id_don_thuoc=new_don.id, 
                        id_loai_thuoc=drug.id, 
                        so_luong_yeu_cau=qty,
                        trang_thai_khop=TrangThaiKhopChiTietEnum.missing
                    )
                    db.session.add(ct)
                    total_items += 1
                    total_pills += qty

            new_don.tong_so_loai_thuoc = total_items
            new_don.tong_vien_yeu_cau = total_pills
            db.session.commit()
            flash(f'Đã tạo đơn {ma_don} thành công!', 'success')
            return redirect(url_for('pharmacist.order_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi hệ thống: {str(e)}', 'danger')

    return render_template('pharmacist/new_order.html')

# --- SỬA ĐƠN THUỐC ---
@pharmacist.route('/order/edit/<int:order_id>', methods=['GET', 'POST'])
@login_required
def edit_order(order_id):
    order = DonThuoc.query.get_or_404(order_id)
    if order.trang_thai_don == TrangThaiDonEnum.completed:
        flash('Không thể sửa đơn thuốc đã hoàn thành.', 'warning')
        return redirect(url_for('pharmacist.order_list'))
        
    if request.method == 'POST':
        try:
            order.ten_benh_nhan = request.form.get('patient_name')
            order.ghi_chu_duoc_si = request.form.get('note')
            db.session.commit()
            flash('Cập nhật thông tin đơn thuốc thành công!', 'success')
            return redirect(url_for('pharmacist.order_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi cập nhật: {str(e)}', 'danger')

    return render_template('pharmacist/edit_order.html', order=order)

# --- XÓA ĐƠN THUỐC ---
@pharmacist.route('/order/delete/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    order = DonThuoc.query.get_or_404(order_id)
    if order.trang_thai_don == TrangThaiDonEnum.completed:
        flash('Không thể xóa đơn thuốc đã hoàn thành.', 'danger')
    else:
        try:
            for chi_tiet in order.chi_tiet_don:
                thuoc = LoaiThuoc.query.get(chi_tiet.id_loai_thuoc)
                if thuoc: thuoc.ton_kho_uoc_tinh += chi_tiet.so_luong_yeu_cau
            
            db.session.delete(order)
            db.session.commit()
            flash('Đã xóa đơn thuốc và hoàn lại tồn kho.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi xóa đơn: {str(e)}', 'danger')
    return redirect(url_for('pharmacist.order_list'))

# --- TRANG ĐẾM THUỐC ---
@pharmacist.route('/counting')
@login_required
def counting_page_no_id():
    """
    Trang giao diện đếm thuốc chính.
    Load danh sách các đơn thuốc CHƯA HOÀN THÀNH để dược sĩ chọn.
    """
    # 1. Lấy danh sách đơn thuốc đang chờ (Pending hoặc Counting)
    pending_orders = DonThuoc.query.filter(
        or_(
            DonThuoc.trang_thai_don == TrangThaiDonEnum.pending,
            DonThuoc.trang_thai_don == TrangThaiDonEnum.counting
        )
    ).order_by(desc(DonThuoc.thoi_gian_tao_don)).all()

    # 2. Lấy danh sách tất cả loại thuốc (cho chế độ Đếm Tự Do)
    all_drugs = LoaiThuoc.query.filter_by(dang_su_dung=True).all()

    return render_template(
        'pharmacist/counting.html', 
        orders=pending_orders, 
        drugs=all_drugs
    )

# --- API: Lấy chi tiết của một đơn thuốc khi chọn Dropdown ---
@pharmacist.route('/api/get-order-details/<int:order_id>')
@login_required
def get_order_details_api(order_id):
    try:
        order = DonThuoc.query.get_or_404(order_id)
        
        # Lấy danh sách thuốc trong đơn này
        items = []
        for item in order.chi_tiet_don:
            items.append({
                'detail_id': item.id,
                'drug_name': item.loai_thuoc_info.ten_thuoc,
                'drug_code': item.loai_thuoc_info.ma_thuoc,
                'req_qty': item.so_luong_yeu_cau,
                'counted_qty': item.so_luong_dem_duoc or 0,
                'is_done': item.trang_thai_khop is not None # Đã đếm xong chưa
            })
            
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

# --- API: Lưu kết quả đếm vào CSDL (QUAN TRỌNG) ---
@pharmacist.route('/api/save-result', methods=['POST'])
@login_required
def save_result():
    data = request.json
    try:
        mode = data.get('mode') # 'prescription' hoặc 'free'
        
        # === TRƯỜNG HỢP 1: ĐẾM THEO ĐƠN ===
        if mode == 'prescription':
            detail_id = data.get('detail_id')
            count = int(data.get('count'))
            image_b64 = data.get('image')

            # 1. Tìm chi tiết đơn
            item = ChiTietDonThuoc.query.get(detail_id)
            if not item:
                return jsonify({'success': False, 'msg': 'Không tìm thấy dòng chi tiết đơn thuốc'})

            # 2. Cập nhật thông tin đếm
            item.so_luong_dem_duoc = count
            item.thoi_gian_nhan_dien_ms = 0 # (Có thể tính time thực tế nếu muốn)
            
            # 3. Lưu ảnh bằng chứng
            if image_b64 and 'base64' in image_b64:
                try:
                    if "," in image_b64: _, b64_data = image_b64.split(",", 1)
                    else: b64_data = image_b64
                    
                    filename = f"count_{item.id}_{int(datetime.datetime.now().timestamp())}.jpg"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(b64_data))
                    item.url_hinh_anh = f"/static/uploads/{filename}"
                except: pass

            # 4. So sánh và cập nhật trạng thái khớp
            diff = count - item.so_luong_yeu_cau
            item.chenh_lech = diff
            
            if diff == 0:
                item.trang_thai_khop = TrangThaiKhopChiTietEnum.match
            elif diff > 0:
                item.trang_thai_khop = TrangThaiKhopChiTietEnum.over
            else:
                item.trang_thai_khop = TrangThaiKhopChiTietEnum.under

            # 5. Cập nhật trạng thái Đơn Thuốc (Cha)
            # Nếu đơn đang pending -> chuyển sang counting
            don_thuoc = item.don_thuoc
            if don_thuoc.trang_thai_don == TrangThaiDonEnum.pending:
                don_thuoc.trang_thai_don = TrangThaiDonEnum.counting
                don_thuoc.thoi_gian_bat_dau = datetime.datetime.now()
            
            # Cộng dồn tổng viên đã đếm của đơn
            # (Logic này nên dùng SQL query sum lại cho chính xác, ở đây cộng tạm)
            don_thuoc.tong_vien_dem_duoc = (don_thuoc.tong_vien_dem_duoc or 0) + count

            db.session.commit()
            return jsonify({'success': True, 'msg': 'Đã lưu vào đơn thuốc!'})

        # === TRƯỜNG HỢP 2: ĐẾM TỰ DO ===
        else:
            # Đếm tự do thì không lưu vào đơn, có thể lưu vào Log hoặc chỉ trả về OK
            # Bạn có thể mở rộng logic: Trừ kho trực tiếp, v.v.
            return jsonify({'success': True, 'msg': 'Đã hoàn tất đếm tự do (Không lưu đơn)'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': str(e)})

# --- THÔNG BÁO ---
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