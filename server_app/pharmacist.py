# File: server_app/pharmacist.py
# PHIÊN BẢN HOÀN THIỆN: TÍCH HỢP LOGIC AI VÀ XỬ LÝ ẢNH TỪ PI

from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from .models import DonThuoc, ChiTietDonThuoc, LoaiThuoc, TrangThaiDonEnum, TrangThaiKhopChiTietEnum, ThongBao, ThietBi, VaiTroEnum
from sqlalchemy import desc
from flask_socketio import emit
import datetime
import uuid
import base64
import os

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

# Biến toàn cục lưu trạng thái đếm
state = {
    'target': 0,        # Số lượng cần đếm
    'locked': False,    # Đã chốt kết quả chưa
    'stable_count': 0,  # Số khung hình ổn định liên tiếp
    'last_val': -1,     # Giá trị đếm của khung hình trước
    'final_val': 0      # Giá trị cuối cùng sau khi chốt
}

# Load Model YOLO (Bọc trong Try/Except để không lỗi nếu chưa có model)
model = None
try:
    from ultralytics import YOLO
    # Đường dẫn tương đối tới file model
    model_path = os.path.join(os.getcwd(), 'models', 'best.pt')
    if os.path.exists(model_path):
        model = YOLO(model_path)
        print(f"✅ SERVER: Đã tải model AI từ {model_path}")
    else:
        print("⚠️ SERVER: Không tìm thấy file models/best.pt. Server chạy chế độ không AI.")
except Exception as e:
    print(f"⚠️ SERVER: Lỗi khởi tạo AI: {e}")

# --- HÀM HỖ TRỢ CHUYỂN ĐỔI ẢNH ---
def base64_to_cv2(b64):
    """Chuyển chuỗi Base64 từ Pi thành ảnh OpenCV"""
    try:
        if "," in b64: _, b64 = b64.split(",", 1)
        data = base64.b64decode(b64)
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except: return None

def cv2_to_base64(img):
    """Nén ảnh OpenCV thành Base64 để gửi về Web"""
    # Giảm chất lượng xuống 50% để truyền nhanh qua Wifi
    _, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')


# =====================================================
# PHẦN 1: XỬ LÝ SOCKET IO (QUAN TRỌNG NHẤT)
# =====================================================

@socketio.on('update_target')
def handle_target(data):
    """Nhận số lượng thuốc cần đếm từ giao diện Web"""
    state['target'] = int(data.get('target', 0))
    state['locked'] = False
    state['stable_count'] = 0
    state['final_val'] = 0
    print(f"🎯 Server nhận mục tiêu mới: {state['target']} viên")

@socketio.on('process_frame_pi')
def handle_pi_stream(data):
    """
    NHẬN ẢNH TỪ RASPBERRY PI -> XỬ LÝ AI -> GỬI VỀ WEB
    """
    try:
        # 1. Giải mã ảnh từ Pi gửi lên
        frame = base64_to_cv2(data.get('image'))
        if frame is None: return

        display_count = 0
        
        # 2. Xử lý AI (Nếu model đã được tải)
        if model:
            if not state['locked']:
                # --- Giai đoạn đang đếm ---
                results = model(frame, verbose=False, conf=0.5) # conf=0.5 là độ tin cậy
                cnt = len(results[0].boxes)
                
                # Vẽ khung chữ nhật quanh viên thuốc
                frame = results[0].plot() 

                # Thuật toán ổn định: Nếu kết quả giống nhau 5 lần liên tiếp thì mới chốt
                if cnt == state['last_val']: 
                    state['stable_count'] += 1
                else: 
                    state['last_val'], state['stable_count'] = cnt, 0
                
                # Nếu ổn định > 10 khung hình -> KHÓA KẾT QUẢ
                if state['stable_count'] >= 10: 
                    state['locked'] = True
                    state['final_val'] = cnt
                    print(f"🔒 ĐÃ CHỐT SỐ LƯỢNG: {cnt}")
                
                display_count = cnt
            else:
                # --- Giai đoạn đã chốt ---
                # Không chạy AI nữa để tiết kiệm tài nguyên, chỉ vẽ chữ
                display_count = state['final_val']
                cv2.putText(frame, f"LOCKED: {display_count}", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                # Vẽ viền xanh báo hiệu thành công
                cv2.rectangle(frame, (0,0), (frame.shape[1], frame.shape[0]), (0,255,0), 5)

        # 3. Tính toán trạng thái để hiển thị màu sắc trên Web
        target = state['target']
        diff = display_count - target
        percent = round((display_count/target)*100, 1) if target > 0 else 0
        
        status_text, color = "Đang đếm...", "warning"
        
        if state['locked']:
            if diff == 0: 
                status_text, color = "Khớp hoàn toàn", "success"
            elif diff > 0: 
                status_text, color = f"Dư {diff} viên", "warning" # Màu vàng nếu dư
            else: 
                status_text, color = f"Thiếu {abs(diff)} viên", "danger" # Màu đỏ nếu thiếu

        # 4. Gửi dữ liệu về trình duyệt (Web Browser)
        emit('ai_result', {
            'processed_image': cv2_to_base64(frame),
            'count': display_count,
            'status_text': status_text,
            'status_color': color,
            'percent': percent,
            'is_locked': state['locked']
        }, broadcast=True)

    except Exception as e:
        # Không in lỗi liên tục để tránh lag server
        pass


# =====================================================
# PHẦN 2: CÁC ROUTE WEB & API
# =====================================================

@pharmacist.context_processor
def inject_pharmacist_data():
    """Cung cấp biến chung cho template."""
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

# --- API TÌM KIẾM VÀ LỌC THUỐC ---
@pharmacist.route('/api/search-drugs')
@login_required
def search_drugs():
    query = request.args.get('q', '').strip()
    category = request.args.get('category', 'all')
    
    try:
        sql_query = LoaiThuoc.query.filter(LoaiThuoc.dang_su_dung == True)

        if query:
            search_term = f"%{query}%"
            sql_query = sql_query.filter(
                db.or_(
                    LoaiThuoc.ten_thuoc.ilike(search_term),
                    LoaiThuoc.ma_thuoc.ilike(search_term)
                )
            )
        
        if category == 'antibiotic':
            sql_query = sql_query.filter(LoaiThuoc.mo_ta.ilike('%kháng sinh%'))
        elif category == 'painkiller':
            sql_query = sql_query.filter(db.or_(LoaiThuoc.mo_ta.ilike('%giảm đau%'), LoaiThuoc.mo_ta.ilike('%hạ sốt%')))
        elif category == 'vitamin':
            sql_query = sql_query.filter(LoaiThuoc.ten_thuoc.ilike('%vitamin%'))
        
        drugs = sql_query.limit(30).all()
        
        results = []
        for d in drugs:
            img_url = d.url_hinh_anh if d.url_hinh_anh else url_for('static', filename='picture/pills/default.png')
            results.append({
                'id': d.id,
                'name': d.ten_thuoc,
                'code': d.ma_thuoc,
                'image': img_url,
                'stock': d.ton_kho_uoc_tinh,
                'unit': d.don_vi_tinh,
                'desc': d.mo_ta or "Chưa có mô tả.",
                'usage_count': d.so_lan_duoc_dem
            })
        return jsonify(results)
    except Exception as e:
        print(f"Lỗi API Search: {e}")
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

# --- TRANG ĐẾM THUỐC (QUAN TRỌNG) ---
@pharmacist.route('/counting')
@login_required
def counting_page_no_id():
    return render_template('pharmacist/counting.html', order=None, details=[])

@pharmacist.route('/counting/<int:order_id>')
@login_required
def counting_page(order_id):
    order = DonThuoc.query.get_or_404(order_id)
    if order.trang_thai_don == TrangThaiDonEnum.pending:
        order.trang_thai_don = TrangThaiDonEnum.counting
        db.session.commit()

    details = []
    for item in order.chi_tiet_don:
        details.append({
            'detail_id': item.id,
            'drug_name': item.loai_thuoc_info.ten_thuoc,
            'drug_code': item.loai_thuoc_info.ma_thuoc,
            'req_qty': item.so_luong_yeu_cau,
            'counted_qty': item.so_luong_dem_duoc or 0,
            'status': item.trang_thai_khop.name if item.trang_thai_khop else 'unchecked'
        })
    return render_template('pharmacist/counting.html', order=order, details=details)

# --- API LƯU KẾT QUẢ ĐẾM ---
@pharmacist.route('/api/save-result', methods=['POST'])
@login_required
def save_result():
    data = request.json
    try:
        detail_id = data.get('detail_id')
        count = int(data.get('count'))
        conf = float(data.get('confidence', 0.0))
        image_b64 = data.get('image') # Nhận ảnh từ nút "Xác nhận"

        item = ChiTietDonThuoc.query.get(detail_id)
        if not item:
            return jsonify({'success': False, 'msg': 'Không tìm thấy chi tiết đơn'})

        # Lưu ảnh vào server để làm bằng chứng
        if image_b64 and 'base64' in image_b64:
            try:
                if "," in image_b64: _, b64_data = image_b64.split(",", 1)
                else: b64_data = image_b64
                
                filename = f"proof_{detail_id}_{int(datetime.datetime.now().timestamp())}.jpg"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(b64_data))
                item.url_hinh_anh = f"/static/uploads/{filename}"
            except Exception as e:
                print(f"Lỗi lưu ảnh: {e}")

        item.so_luong_dem_duoc = count
        item.do_tin_cay = conf
        item.thoi_gian_nhan_dien_ms = 0 # Placeholder
        
        if count == item.so_luong_yeu_cau:
            item.trang_thai_khop = TrangThaiKhopChiTietEnum.match
        elif count > item.so_luong_yeu_cau:
            item.trang_thai_khop = TrangThaiKhopChiTietEnum.over
        else:
            item.trang_thai_khop = TrangThaiKhopChiTietEnum.under
            
        item.chenh_lech = count - item.so_luong_yeu_cau
        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

# --- THÔNG BÁO ---
@pharmacist.route('/notifications/mark-all-read')
@login_required
def mark_all_read():
    ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).update({'da_doc': True})
    db.session.commit()
    flash('Đã đánh dấu tất cả là đã đọc.', 'success')
    return redirect(request.referrer or url_for('pharmacist.dashboard'))

@pharmacist.route('/notifications/all')
@login_required
def all_notifications():
    """
    Trang xem tất cả thông báo.
    Tạm thời reload lại trang hiện tại hoặc render dashboard nếu chưa có template riêng.
    """
    # Nếu bạn chưa có file template riêng cho danh sách thông báo, 
    # ta tạm thời chuyển hướng về Dashboard và hiện thông báo.
    flash('Đang hiển thị tất cả thông báo.', 'info')
    return render_template('pharmacist/dashboard.html')
@socketio.on('reset_counting')
def handle_reset():
    """Hàm này chạy khi bấm nút Đếm lại trên Web"""
    global state
    state['locked'] = False       # Mở khóa để AI tiếp tục đếm
    state['stable_count'] = 0     # Reset bộ đếm ổn định
    state['last_val'] = -1        # Reset giá trị cũ
    # Không reset state['target'] vì mục tiêu vẫn giữ nguyên
    print("🔄 SERVER: Đã nhận lệnh ĐẾM LẠI!")