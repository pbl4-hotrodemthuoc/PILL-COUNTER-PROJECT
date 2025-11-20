# File: server_app/pharmacist.py
# PHIÊN BẢN FINAL FIX: SỬA LỖI TRÙNG HÀM VÀ LỖI TÌM KIẾM

from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from .models import DonThuoc, ChiTietDonThuoc, LoaiThuoc, TrangThaiDonEnum, TrangThaiKhopChiTietEnum, ThongBao, ThietBi, VaiTroEnum
from sqlalchemy import desc, or_  # [QUAN TRỌNG] Import or_ ở đây
from flask_socketio import emit
import datetime
import uuid
import base64
import os
from sqlalchemy import or_

# --- THƯ VIỆN XỬ LÝ ẢNH & AI ---
import cv2
import numpy as np

# --- IMPORT EXTENSIONS ---
from .extensions import db, socketio

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
    return render_template('pharmacist/dashboard.html')

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
@pharmacist.route('/notifications/mark-all-read')
@login_required
def mark_all_read():
    ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).update({'da_doc': True})
    db.session.commit()
    flash('Đã đánh dấu tất cả là đã đọc.', 'success')
    return redirect(request.referrer or url_for('pharmacist.dashboard'))

@pharmacist.route('/notifications/<int:id>')
@login_required
def view_notification(id):
    notif = ThongBao.query.get_or_404(id)
    if notif.id_nguoi_dung == current_user.id:
        notif.da_doc = True
        db.session.commit()
    return redirect(url_for('pharmacist.dashboard'))

@pharmacist.route('/notifications/all')
@login_required
def all_notifications():
    """Trang xem tất cả thông báo"""
    flash('Đang hiển thị tất cả thông báo.', 'info')
    return render_template('pharmacist/dashboard.html')