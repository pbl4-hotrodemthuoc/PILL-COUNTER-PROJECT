# # File: server_app/pharmacist.py
# # PHIÊN BẢN FINAL FIX: SỬA LỖI TRÙNG HÀM VÀ LỖI TÌM KIẾM

# from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
# from flask_login import login_required, current_user
# from .models import DonThuoc, ChiTietDonThuoc, LoaiThuoc, TrangThaiDonEnum, TrangThaiKhopChiTietEnum, ThongBao, ThietBi, VaiTroEnum
# from sqlalchemy import desc, or_  # [QUAN TRỌNG] Import or_ ở đây
# from flask_socketio import emit
# import datetime
# import uuid
# import base64
# import os
# from sqlalchemy import or_

# # --- THƯ VIỆN XỬ LÝ ẢNH & AI ---
# import cv2
# import numpy as np

# # --- IMPORT EXTENSIONS ---
# from .extensions import db, socketio

# # --- KHỞI TẠO BLUEPRINT ---
# pharmacist = Blueprint('pharmacist', __name__)

# # =====================================================
# # PHẦN 0: CẤU HÌNH AI & TRẠNG THÁI ĐẾM
# # =====================================================

# # Cấu hình độ nhạy để tự động chốt
# STABLE_THRESHOLD = 8  # Số khung hình ổn định để tự khóa

# state = {
#     'target': 0,        
#     'stable_count': 0,
#     'last_val': -1,
#     'final_val': 0,
#     'locked': False     # Trạng thái khóa cứng
# }

# # Load Model YOLO
# model = None
# try:
#     from ultralytics import YOLO
#     # Ưu tiên tìm model trong thư mục device_app
#     model_path = os.path.join(os.getcwd(), 'device_app', 'models', 'best.pt')
    
#     if os.path.exists(model_path):
#         model = YOLO(model_path)
#         print(f"✅ SERVER: Đã tải model AI từ {model_path}")
#     else:
#         # Fallback: Tìm ở thư mục gốc
#         alt_path = os.path.join(os.getcwd(), 'models', 'best.pt')
#         if os.path.exists(alt_path):
#             model = YOLO(alt_path)
#             print(f"✅ SERVER: Đã tải model từ {alt_path}")
#         else:
#             print(f"⚠️ SERVER: Không tìm thấy model tại {model_path} hay {alt_path}")
# except Exception as e:
#     print(f"⚠️ SERVER: Lỗi khởi tạo AI: {e}")

# # --- HÀM HỖ TRỢ CHUYỂN ĐỔI ẢNH ---
# def base64_to_cv2(b64):
#     try:
#         if "," in b64: _, b64 = b64.split(",", 1)
#         data = base64.b64decode(b64)
#         return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
#     except: return None

# def cv2_to_base64(img):
#     # Nếu ảnh lớn hơn 800px thì resize nhẹ về 800 để Web load mượt
#     # Nếu nhỏ hơn thì giữ nguyên
#     if img.shape[1] > 800:
#         img = cv2.resize(img, (800, 600))
        
#     # Nén 60 là đủ đẹp cho Web, giúp truyền từ Server -> Browser nhanh hơn
#     _, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
#     return "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')


# # =====================================================
# # PHẦN 1: XỬ LÝ SOCKET IO
# # =====================================================

# # --- TÌM VÀ THAY THẾ KHỐI NÀY TRONG server_app/pharmacist.py ---

# @socketio.on('update_target')
# def handle_target(data):
#     state['target'] = int(data.get('target', 0))
#     # Khi đổi mục tiêu -> Reset toàn bộ
#     state['locked'] = False
#     state['stable_count'] = 0
#     state['last_val'] = -1
#     print(f"🎯 Mục tiêu mới: {state['target']}")

# @socketio.on('reset_counting')
# def handle_reset():
#     """
#     Hàm này chạy khi bấm nút MÀU VÀNG (Đếm lại/Mở khóa)
#     """
#     global state
#     state['locked'] = False       # Mở khóa ngay lập tức
#     state['stable_count'] = 0     # Reset bộ đếm ổn định về 0
#     state['last_val'] = -1        # Reset giá trị cũ để bắt buộc so sánh lại
#     # Lưu ý: Không reset state['target'] vì đang đếm tiếp đơn đó
    
#     print("🔄 SERVER: Đã nhận lệnh RESET (Mở khóa)")
    
#     # [QUAN TRỌNG] Gửi tín hiệu mở khóa ngay lập tức về UI để tránh độ trễ
#     # (Dùng ảnh rỗng tạm thời hoặc giữ nguyên ảnh cũ ở client)
#     emit('count_status_update', {'is_locked': False}, broadcast=True)

# @socketio.on('process_frame_pi')
# def handle_pi_stream(data):
#     try:
#         frame = base64_to_cv2(data.get('image'))
#         if frame is None: return

#         display_count = 0
        
#         if model:
#             # --- LOGIC AI ---
#             if not state['locked']:
#                 # 1. ĐANG MỞ KHÓA -> CHẠY AI LIÊN TỤC
#                 results = model(frame, verbose=False, conf=0.5)
#                 cnt = len(results[0].boxes)
#                 frame = results[0].plot()

#                 # Logic ổn định: Nếu số lượng GIỐNG khung hình trước
#                 if cnt == state['last_val']:
#                     state['stable_count'] += 1
#                 else:
#                     # Nếu số lượng thay đổi (bạn đang thêm/bớt thuốc) -> Reset ổn định
#                     state['stable_count'] = 0
#                     state['last_val'] = cnt
                
#                 # CHỐT: Nếu ổn định đủ 20 frames (khoảng 1-2 giây) -> KHÓA
#                 if state['stable_count'] >= STABLE_THRESHOLD:
#                     state['locked'] = True
#                     state['final_val'] = cnt
#                     print(f"🔒 AUTO-LOCK: {cnt}")
                
#                 display_count = cnt
#             else:
#                 # 2. ĐÃ KHÓA -> GIỮ NGUYÊN KẾT QUẢ
#                 display_count = state['final_val']
#                 # Vẽ khung xanh báo hiệu
#                 cv2.rectangle(frame, (0,0), (frame.shape[1], frame.shape[0]), (0, 255, 0), 4)
#                 cv2.putText(frame, f"LOCKED: {display_count}", (30, 50), 
#                             cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

#         # --- GỬI VỀ WEB ---
#         target = state['target']
#         diff = display_count - target
#         percent = round((display_count/target)*100, 1) if target > 0 else 0
        
#         status, color = "Đang đếm...", "warning"
        
#         if state['locked']:
#             if diff == 0: status, color = "Khớp hoàn toàn", "success"
#             elif diff > 0: status, color = f"Dư {diff} viên", "warning"
#             else: status, color = f"Thiếu {abs(diff)} viên", "danger"
#         else:
#             # Nếu chưa khóa nhưng số lượng > 0
#             if display_count > 0:
#                  status = "Chờ ổn định..."
        
#         emit('ai_result', {
#             'processed_image': cv2_to_base64(frame),
#             'count': display_count,
#             'status_text': status,
#             'status_color': color,
#             'percent': percent,
#             'is_locked': state['locked']
#         }, broadcast=True)

#     except Exception: pass

# # =====================================================
# # PHẦN 2: CÁC ROUTE WEB & API
# # =====================================================

# @pharmacist.context_processor
# def inject_pharmacist_data():
#     if current_user.is_authenticated and current_user.vai_tro == VaiTroEnum.pharmacist:
#         unread_notifications = ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).all()
#         device = ThietBi.query.get(1) 
#         return dict(
#             unread_notifications_count=len(unread_notifications),
#             notifications=unread_notifications,
#             device_status=device.trang_thai.name if device else 'offline'
#         )
#     return {}

# @pharmacist.route('/dashboard')
# @login_required
# def dashboard():
#     return render_template('pharmacist/dashboard.html')

# @pharmacist.route('/history')
# @login_required
# def my_history():
#     return render_template('pharmacist/my_history.html') 

# @pharmacist.route('/stats')
# @login_required
# def my_stats():
#     return render_template('pharmacist/my_stats.html')

# @pharmacist.route('/report-incident')
# @login_required
# def report_incident():
#     return render_template('pharmacist/report_incident.html')

# @pharmacist.route('/guide')
# @login_required
# def guide():
#     return render_template('pharmacist/guide.html')

# @pharmacist.route('/settings')
# @login_required
# def settings():
#     return "Trang Cài đặt của Dược sĩ"

# # --- API TÌM KIẾM VÀ LỌC THUỐC (ĐÃ SỬA LỖI or_) ---
# @pharmacist.route('/api/search-drugs')
# @login_required
# def search_drugs():
#     query = request.args.get('q', '').strip()
#     category = request.args.get('category', 'all')
    
#     try:
#         sql_query = LoaiThuoc.query.filter(LoaiThuoc.dang_su_dung == True)

#         if query:
#             search_term = f"%{query}%"
#             # SỬA LỖI: Dùng or_() của sqlalchemy thay vì db.or_()
#             sql_query = sql_query.filter(
#                 or_(
#                     LoaiThuoc.ten_thuoc.ilike(search_term),
#                     LoaiThuoc.ma_thuoc.ilike(search_term)
#                 )
#             )
        
#         if category == 'antibiotic':
#             sql_query = sql_query.filter(LoaiThuoc.mo_ta.ilike('%kháng sinh%'))
#         elif category == 'painkiller':
#             sql_query = sql_query.filter(or_(LoaiThuoc.mo_ta.ilike('%giảm đau%'), LoaiThuoc.mo_ta.ilike('%hạ sốt%')))
#         elif category == 'vitamin':
#             sql_query = sql_query.filter(LoaiThuoc.ten_thuoc.ilike('%vitamin%'))
        
#         drugs = sql_query.limit(30).all()
        
#         results = []
#         for d in drugs:
#             img_url = d.url_hinh_anh if d.url_hinh_anh else url_for('static', filename='picture/pills/default.png')
#             results.append({
#                 'id': d.id,
#                 'name': d.ten_thuoc,
#                 'code': d.ma_thuoc,
#                 'image': img_url,
#                 'stock': d.ton_kho_uoc_tinh,
#                 'unit': d.don_vi_tinh,
#                 'desc': d.mo_ta or "Chưa có mô tả.",
#                 'usage_count': d.so_lan_duoc_dem
#             })
#         return jsonify(results)
#     except Exception as e:
#         print(f"❌ LỖI API SEARCH: {e}")
#         return jsonify([])

# # --- API LẤY CHI TIẾT THUỐC ---
# @pharmacist.route('/api/drug-detail/<int:drug_id>')
# @login_required
# def get_drug_detail_api(drug_id):
#     d = LoaiThuoc.query.get_or_404(drug_id)
#     img_url = d.url_hinh_anh if d.url_hinh_anh else url_for('static', filename='picture/pills/default.png')
#     return jsonify({
#         'id': d.id,
#         'name': d.ten_thuoc,
#         'code': d.ma_thuoc,
#         'image': img_url,
#         'stock': d.ton_kho_uoc_tinh,
#         'unit': d.don_vi_tinh,
#         'desc': d.mo_ta or "Đang cập nhật thông tin chi tiết.",
#         'warning_threshold': d.nguong_canh_bao
#     })

# # --- DANH SÁCH ĐƠN THUỐC ---
# @pharmacist.route('/orders')
# @login_required
# def order_list():
#     page = request.args.get('page', 1, type=int)
#     search_query = request.args.get('q', '').strip()
#     status_filter = request.args.get('status', '')
    
#     query = DonThuoc.query.filter_by(id_duoc_si=current_user.id)
    
#     if search_query:
#         query = query.filter(DonThuoc.ma_don_thuoc.ilike(f'%{search_query}%'))
    
#     if status_filter and status_filter != 'all':
#         try:
#             status_enum = TrangThaiDonEnum[status_filter]
#             query = query.filter(DonThuoc.trang_thai_don == status_enum)
#         except: pass
    
#     pagination = query.order_by(desc(DonThuoc.thoi_gian_tao_don)).paginate(page=page, per_page=10)
    
#     return render_template(
#         'pharmacist/order_list.html', 
#         pagination=pagination, 
#         TrangThaiDonEnum=TrangThaiDonEnum,
#         search_query=search_query,
#         status_filter=status_filter
#     )

# # --- TẠO ĐƠN MỚI ---
# @pharmacist.route('/new-order', methods=['GET', 'POST'])
# @login_required
# def new_order():
#     if request.method == 'POST':
#         try:
#             drug_ids = request.form.getlist('drug_ids[]')
#             quantities = request.form.getlist('quantities[]')
#             patient_name = request.form.get('patient_name')
#             note = request.form.get('note')

#             if not drug_ids:
#                 flash('Giỏ hàng trống. Vui lòng chọn thuốc.', 'warning')
#                 return redirect(url_for('pharmacist.new_order'))

#             ma_don = f"DT-{str(uuid.uuid4())[:8].upper()}"
#             new_don = DonThuoc(
#                 ma_don_thuoc=ma_don,
#                 id_duoc_si=current_user.id,
#                 ten_benh_nhan=patient_name,
#                 ghi_chu_duoc_si=note,
#                 trang_thai_don=TrangThaiDonEnum.pending
#             )
#             db.session.add(new_don)
#             db.session.flush()

#             total_items = 0
#             total_pills = 0

#             for d_id, qty in zip(drug_ids, quantities):
#                 qty = int(qty)
#                 if qty > 0:
#                     drug = LoaiThuoc.query.with_for_update().get(int(d_id))
#                     if not drug: raise Exception(f"Không tìm thấy thuốc ID {d_id}")
#                     if drug.ton_kho_uoc_tinh < qty:
#                         db.session.rollback()
#                         flash(f'Lỗi: Thuốc "{drug.ten_thuoc}" thiếu tồn kho.', 'danger')
#                         return redirect(url_for('pharmacist.new_order'))
                    
#                     drug.ton_kho_uoc_tinh -= qty
#                     ct = ChiTietDonThuoc(
#                         id_don_thuoc=new_don.id, 
#                         id_loai_thuoc=drug.id, 
#                         so_luong_yeu_cau=qty,
#                         trang_thai_khop=TrangThaiKhopChiTietEnum.missing
#                     )
#                     db.session.add(ct)
#                     total_items += 1
#                     total_pills += qty

#             new_don.tong_so_loai_thuoc = total_items
#             new_don.tong_vien_yeu_cau = total_pills
#             db.session.commit()
#             flash(f'Đã tạo đơn {ma_don} thành công!', 'success')
#             return redirect(url_for('pharmacist.order_list'))
#         except Exception as e:
#             db.session.rollback()
#             flash(f'Lỗi hệ thống: {str(e)}', 'danger')

#     return render_template('pharmacist/new_order.html')

# # --- SỬA ĐƠN THUỐC ---
# @pharmacist.route('/order/edit/<int:order_id>', methods=['GET', 'POST'])
# @login_required
# def edit_order(order_id):
#     order = DonThuoc.query.get_or_404(order_id)
#     if order.trang_thai_don == TrangThaiDonEnum.completed:
#         flash('Không thể sửa đơn thuốc đã hoàn thành.', 'warning')
#         return redirect(url_for('pharmacist.order_list'))
        
#     if request.method == 'POST':
#         try:
#             order.ten_benh_nhan = request.form.get('patient_name')
#             order.ghi_chu_duoc_si = request.form.get('note')
#             db.session.commit()
#             flash('Cập nhật thông tin đơn thuốc thành công!', 'success')
#             return redirect(url_for('pharmacist.order_list'))
#         except Exception as e:
#             db.session.rollback()
#             flash(f'Lỗi cập nhật: {str(e)}', 'danger')

#     return render_template('pharmacist/edit_order.html', order=order)

# # --- XÓA ĐƠN THUỐC ---
# @pharmacist.route('/order/delete/<int:order_id>', methods=['POST'])
# @login_required
# def delete_order(order_id):
#     order = DonThuoc.query.get_or_404(order_id)
#     if order.trang_thai_don == TrangThaiDonEnum.completed:
#         flash('Không thể xóa đơn thuốc đã hoàn thành.', 'danger')
#     else:
#         try:
#             for chi_tiet in order.chi_tiet_don:
#                 thuoc = LoaiThuoc.query.get(chi_tiet.id_loai_thuoc)
#                 if thuoc: thuoc.ton_kho_uoc_tinh += chi_tiet.so_luong_yeu_cau
            
#             db.session.delete(order)
#             db.session.commit()
#             flash('Đã xóa đơn thuốc và hoàn lại tồn kho.', 'success')
#         except Exception as e:
#             db.session.rollback()
#             flash(f'Lỗi xóa đơn: {str(e)}', 'danger')
#     return redirect(url_for('pharmacist.order_list'))

# @pharmacist.route('/counting')
# @login_required
# def counting_page_no_id():
#     """
#     Trang giao diện đếm thuốc.
#     Load danh sách đơn chưa hoàn thành và danh sách thuốc full.
#     """
#     # 1. Lấy danh sách đơn thuốc cần xử lý (Pending hoặc Counting)
#     pending_orders = DonThuoc.query.filter(
#         or_(
#             DonThuoc.trang_thai_don == TrangThaiDonEnum.pending,
#             DonThuoc.trang_thai_don == TrangThaiDonEnum.counting
#         )
#     ).order_by(desc(DonThuoc.thoi_gian_tao_don)).all()

#     # 2. Lấy danh sách tất cả loại thuốc (cho chế độ Đếm Tự Do)
#     all_drugs = LoaiThuoc.query.filter_by(dang_su_dung=True).all()

#     return render_template(
#         'pharmacist/counting.html', 
#         orders=pending_orders, 
#         drugs=all_drugs
#     )

# # --- API: Lấy chi tiết thuốc trong một đơn hàng ---
# # --- API: Lấy chi tiết thuốc trong một đơn hàng (BẢN FIX LỖI) ---
# @pharmacist.route('/api/get-order-details/<int:order_id>')
# @login_required
# def get_order_details_api(order_id):
#     print(f">>> API: Đang lấy chi tiết đơn hàng ID={order_id}")
#     try:
#         order = DonThuoc.query.get_or_404(order_id)
        
#         items = []
#         for item in order.chi_tiet_don:
#             # Kiểm tra quan hệ database (tránh lỗi nếu thuốc bị xóa)
#             if not item.loai_thuoc_info:
#                 print(f"⚠️ Cảnh báo: Chi tiết ID {item.id} thiếu thông tin thuốc")
#                 continue

#             # Kiểm tra trạng thái hoàn thành
#             is_done = False
#             if item.trang_thai_khop == TrangThaiKhopChiTietEnum.match:
#                 is_done = True
            
#             items.append({
#                 'detail_id': item.id,  
#                 'drug_name': item.loai_thuoc_info.ten_thuoc,
#                 'drug_code': item.loai_thuoc_info.ma_thuoc,
#                 'req_qty': item.so_luong_yeu_cau,
#                 'counted_qty': item.so_luong_dem_duoc or 0,
#                 'is_done': is_done
#             })
            
#         print(f">>> API: Tìm thấy {len(items)} loại thuốc trong đơn.")
#         return jsonify({'success': True, 'items': items})

#     except Exception as e:
#         print(f"❌ API ERROR: {e}")
#         return jsonify({'success': False, 'msg': str(e)})
# # --- API: Lưu kết quả đếm vào CSDL ---
# @pharmacist.route('/api/save-result', methods=['POST'])
# @login_required
# def save_result():
#     data = request.json
#     try:
#         mode = data.get('mode') # 'prescription' hoặc 'free'
        
#         # === TRƯỜNG HỢP 1: ĐẾM THEO ĐƠN (LƯU VÀO DB) ===
#         if mode == 'prescription':
#             detail_id = data.get('detail_id')
#             count = int(data.get('count'))
#             image_b64 = data.get('image')

#             # 1. Tìm dòng chi tiết trong DB
#             item = ChiTietDonThuoc.query.get(detail_id)
#             if not item:
#                 return jsonify({'success': False, 'msg': 'Không tìm thấy chi tiết đơn thuốc'})

#             # 2. Cập nhật số lượng đếm được
#             item.so_luong_dem_duoc = count
#             # (Tùy chọn: Tính thời gian, độ tin cậy...)
            
#             # 3. Lưu ảnh bằng chứng (Evidence)
#             if image_b64 and 'base64' in image_b64:
#                 try:
#                     if "," in image_b64: _, b64_data = image_b64.split(",", 1)
#                     else: b64_data = image_b64
                    
#                     filename = f"evidence_{item.id}_{int(datetime.datetime.now().timestamp())}.jpg"
#                     filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
#                     with open(filepath, "wb") as f:
#                         f.write(base64.b64decode(b64_data))
#                     item.url_hinh_anh = f"/static/uploads/{filename}"
#                 except: pass

#             # 4. So sánh và cập nhật trạng thái Khớp/Lệch
#             diff = count - item.so_luong_yeu_cau
#             item.chenh_lech = diff
            
#             if diff == 0:
#                 item.trang_thai_khop = TrangThaiKhopChiTietEnum.match
#             elif diff > 0:
#                 item.trang_thai_khop = TrangThaiKhopChiTietEnum.over
#             else:
#                 item.trang_thai_khop = TrangThaiKhopChiTietEnum.under

#             # 5. Cập nhật trạng thái Đơn Thuốc cha (Nếu đơn mới bắt đầu -> chuyển sang counting)
#             don_thuoc = item.don_thuoc
#             if don_thuoc.trang_thai_don == TrangThaiDonEnum.pending:
#                 don_thuoc.trang_thai_don = TrangThaiDonEnum.counting
#                 don_thuoc.thoi_gian_bat_dau = datetime.datetime.now()

#             db.session.commit()
#             return jsonify({'success': True, 'msg': f'Đã lưu kết quả: {count}/{item.so_luong_yeu_cau}'})

#         # === TRƯỜNG HỢP 2: ĐẾM TỰ DO ===
#         else:
#             # Đếm tự do không lưu vào đơn thuốc cụ thể, chỉ trả về thành công
#             return jsonify({'success': True, 'msg': 'Đếm tự do hoàn tất.'})

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'success': False, 'msg': str(e)})

# # --- THÔNG BÁO ---
# @pharmacist.route('/notifications/mark-all-read')
# @login_required
# def mark_all_read():
#     ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).update({'da_doc': True})
#     db.session.commit()
#     flash('Đã đánh dấu tất cả là đã đọc.', 'success')
#     return redirect(request.referrer or url_for('pharmacist.dashboard'))

# @pharmacist.route('/notifications/<int:id>')
# @login_required
# def view_notification(id):
#     notif = ThongBao.query.get_or_404(id)
#     if notif.id_nguoi_dung == current_user.id:
#         notif.da_doc = True
#         db.session.commit()
#     return redirect(url_for('pharmacist.dashboard'))

# @pharmacist.route('/notifications/all')
# @login_required
# def all_notifications():
#     """Trang xem tất cả thông báo"""
#     flash('Đang hiển thị tất cả thông báo.', 'info')
#     return render_template('pharmacist/dashboard.html')


# File: server_app/pharmacist.py
# PHIÊN BẢN FINAL STABLE: ĐÃ FIX LỖI CURRENT_FILTERS VÀ PILLS_TODAY

from flask import (
    Blueprint, render_template, flash, redirect, 
    url_for, request, jsonify, current_app
)
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
from sqlalchemy import func, case, desc, cast, Float, or_
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
    ThongBao, ThietBi, VaiTroEnum, DonThuoc, ChiTietDonThuoc, 
    LoaiThuoc, TrangThaiDonEnum, TrangThaiKhopDonEnum, 
    TrangThaiKhopChiTietEnum, BaoCaoSuCo, LoaiSuCoEnum,
    NhatKyHeThong, LoaiLogEnum
)

# --- KHỞI TẠO BLUEPRINT ---
pharmacist = Blueprint('pharmacist', __name__)

# =====================================================
# PHẦN 1: CẤU HÌNH AI & XỬ LÝ SOCKET (REAL-TIME)
# =====================================================

STABLE_THRESHOLD = 8
MOTION_THRESHOLD = 5.0  # Ngưỡng % pixels thay đổi để coi là có chuyển động

state = {
    'target': 0,        
    'stable_count': 0,
    'last_val': -1,
    'final_val': 0,
    'locked': False,
    'prev_frame': None,  # Lưu frame trước để phát hiện chuyển động
    'motion_cooldown': 0,  # Cooldown để tránh reset liên tục
    'counting_clients': 0  # Số clients đang ở trang counting
}

# --- LOAD MODEL YOLO ---
model = None
try:
    from ultralytics import YOLO
    model_path = os.path.join(os.getcwd(), 'device_app', 'models', 'best.pt')
    if not os.path.exists(model_path):
        model_path = os.path.join(os.getcwd(), 'models', 'best.pt')
    
    if os.path.exists(model_path):
        model = YOLO(model_path)
        print(f"✅ SERVER: Đã tải model AI từ {model_path}")
    else:
        print(f"⚠️ SERVER: Không tìm thấy model AI")
except Exception as e:
    print(f"⚠️ SERVER: Lỗi khởi tạo AI: {e}")

# --- HÀM HỖ TRỢ ẢNH ---
def base64_to_cv2(b64):
    try:
        if "," in b64: _, b64 = b64.split(",", 1)
        data = base64.b64decode(b64)
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except: return None

def cv2_to_base64(img):
    if img.shape[1] > 800: img = cv2.resize(img, (800, 600))
    _, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')

def crop_pill_thumbnail(frame, box, max_size=80):
    """
    Crop một viên thuốc từ frame gốc và resize về thumbnail.
    Args:
        frame: Ảnh gốc (numpy array BGR)
        box: YOLO box object chứa tọa độ
        max_size: Kích thước tối đa của thumbnail
    Returns:
        base64 string của ảnh thumbnail
    """
    try:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        # Đảm bảo tọa độ không vượt ra ngoài frame
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        # Crop viên thuốc
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None
            
        # Resize về max_size giữ tỉ lệ
        ch, cw = crop.shape[:2]
        scale = min(max_size/cw, max_size/ch) if cw > 0 and ch > 0 else 1
        new_w, new_h = int(cw * scale), int(ch * scale)
        if new_w > 0 and new_h > 0:
            crop_resized = cv2.resize(crop, (new_w, new_h))
        else:
            return None
        
        # Encode thành base64
        _, buf = cv2.imencode('.jpg', crop_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        return "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')
    except Exception as e:
        return None


# --- SOCKET EVENTS ---
@socketio.on('update_target')
def handle_target(data):
    state['target'] = int(data.get('target', 0))
    state['locked'] = False
    state['stable_count'] = 0
    state['last_val'] = -1
    print(f"🎯 Mục tiêu: {state['target']} viên")

# Set lưu session ID của clients đang ở trang counting
counting_sessions = set()

@socketio.on('join_counting')
def handle_join_counting():
    from flask import request
    sid = request.sid
    if sid not in counting_sessions:
        counting_sessions.add(sid)
        state['counting_clients'] = len(counting_sessions)
        print(f"👁️ Client vào trang counting ({state['counting_clients']} clients)")

@socketio.on('leave_counting')
def handle_leave_counting():
    from flask import request
    sid = request.sid
    if sid in counting_sessions:
        counting_sessions.discard(sid)
        state['counting_clients'] = len(counting_sessions)
        print(f"👋 Client rời trang counting ({state['counting_clients']} clients)")

@socketio.on('disconnect')
def handle_disconnect():
    from flask import request
    sid = request.sid
    if sid in counting_sessions:
        counting_sessions.discard(sid)
        state['counting_clients'] = len(counting_sessions)
        print(f"🔌 Client disconnect - auto leave counting ({state['counting_clients']} clients)")

@socketio.on('reset_counting')
def handle_reset():
    state['locked'] = False
    state['stable_count'] = 0
    state['last_val'] = -1
    print("🔄 Reset Counting")
    emit('count_status_update', {'is_locked': False}, broadcast=True)

@socketio.on('process_frame_pi')
def handle_pi_stream(data):
    try:
        # Cập nhật thông tin thiết bị (IP, thời gian kết nối) - LUÔN cập nhật, mỗi 60 giây
        from flask import request
        from datetime import datetime
        if not state.get('_last_device_update') or (datetime.now() - state['_last_device_update']).seconds > 60:
            try:
                device = ThietBi.query.get(1)
                if device:
                    device.dia_chi_ip = request.remote_addr
                    device.lan_ket_noi_cuoi = datetime.now()
                    device.trang_thai = TrangThaiThietBiEnum.online
                    db.session.commit()
                    state['_last_device_update'] = datetime.now()
            except:
                pass
        
        # Skip xử lý AI nếu không có client nào ở trang counting
        if state.get('counting_clients', 0) <= 0:
            return
        
        frame = base64_to_cv2(data.get('image'))
        if frame is None: return

        display_count = 0
        avg_conf = 0.0
        process_time = 0
        pills_detail = []  # Chỉ có dữ liệu khi LẦN ĐẦU LOCKED
        send_pills = False  # Flag để gửi pills_detail 1 lần duy nhất
        
        if model:
            if not state['locked']:
                results = model(frame, verbose=False, conf=0.5)
                
                speed = results[0].speed
                process_time = speed['preprocess'] + speed['inference'] + speed['postprocess']
                boxes = results[0].boxes
                cnt = len(boxes)
                
                if cnt > 0 and hasattr(boxes, 'conf'): 
                    avg_conf = float(boxes.conf.mean())

                # Lưu frame gốc TRƯỚC KHI vẽ boxes (để crop thumbnails sau)
                frame_original = frame.copy()
                
                # Vẽ boxes lên frame
                frame = results[0].plot()

                if cnt == state['last_val']: state['stable_count'] += 1
                else: state['stable_count'] = 0; state['last_val'] = cnt
                
                # LOCKED: Crop thumbnails MỘT LẦN DUY NHẤT
                if state['stable_count'] >= STABLE_THRESHOLD:
                    state['locked'] = True
                    state['final_val'] = cnt
                    
                    # Crop thumbnails từ frame gốc đã lưu - KHÔNG GIỚI HẠN SỐ LƯỢNG
                    if cnt > 0:
                        for i, box in enumerate(boxes):
                            conf = float(box.conf[0])
                            thumb = crop_pill_thumbnail(frame_original, box, max_size=70)
                            if thumb:
                                pills_detail.append({
                                    'id': i + 1,
                                    'confidence': round(conf, 3),
                                    'image': thumb
                                })
                        pills_detail.sort(key=lambda x: x['confidence'], reverse=True)
                    
                    state['locked_pills_detail'] = pills_detail
                    state['locked_confidence'] = avg_conf  # Lưu confidence khi LOCKED
                    state['pills_sent'] = False  # Chưa gửi
                    state['prev_frame'] = frame_original.copy()  # Lưu frame GỐC (chưa vẽ) để motion detection
                    send_pills = True  # Đánh dấu cần gửi lần này
                    print(f"🔒 LOCKED: {cnt} viên ({len(pills_detail)} thumbnails)")
                
                display_count = cnt
            else:
                # ĐÃ KHÓA - Kiểm tra có chuyển động không
                display_count = state['final_val']
                avg_conf = state.get('locked_confidence', 0)  # Lấy confidence đã lưu
                
                # Motion Detection: So sánh frame hiện tại với frame đã lưu
                if state['prev_frame'] is not None and state['motion_cooldown'] <= 0:
                    # Convert sang grayscale để so sánh
                    gray_curr = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray_prev = cv2.cvtColor(state['prev_frame'], cv2.COLOR_BGR2GRAY)
                    
                    # Resize nếu kích thước khác nhau
                    if gray_curr.shape != gray_prev.shape:
                        gray_prev = cv2.resize(gray_prev, (gray_curr.shape[1], gray_curr.shape[0]))
                    
                    # Tính độ khác biệt
                    diff = cv2.absdiff(gray_curr, gray_prev)
                    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
                    motion_percent = (np.count_nonzero(thresh) / thresh.size) * 100
                    
                    # Debug: In ra để xem motion_percent
                    print(f"📊 Motion: {motion_percent:.2f}% (threshold: {MOTION_THRESHOLD}%)")
                    
                    # Nếu có chuyển động lớn → Reset
                    if motion_percent > MOTION_THRESHOLD:
                        print(f"🔄 MOTION DETECTED ({motion_percent:.1f}%) - Auto Reset!")
                        state['locked'] = False
                        state['stable_count'] = 0
                        state['last_val'] = -1
                        state['motion_cooldown'] = 5  # Cooldown 5 frames
                        emit('count_status_update', {'is_locked': False, 'reason': 'motion_detected'}, broadcast=True)
                        return  # Thoát sớm, frame tiếp theo sẽ đếm lại
                
                # Giảm cooldown
                if state['motion_cooldown'] > 0:
                    state['motion_cooldown'] -= 1
                
                # Chỉ gửi pills_detail nếu chưa gửi
                if not state.get('pills_sent', False):
                    pills_detail = state.get('locked_pills_detail', [])
                    send_pills = True
                    state['pills_sent'] = True
                
                cv2.rectangle(frame, (0,0), (frame.shape[1], frame.shape[0]), (0, 255, 0), 4)
                cv2.putText(frame, f"LOCKED: {display_count}", (30, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        target = state['target']
        diff = display_count - target
        percent = round((display_count/target)*100, 1) if target > 0 else 0
        
        status, color = "Đang đếm...", "warning"
        if state['locked']:
            if diff == 0: status, color = "Khớp", "success"
            elif diff > 0: status, color = f"Dư {diff}", "warning"
            else: status, color = f"Thiếu {abs(diff)}", "danger"
        else:
            if display_count > 0: status = "Chờ ổn định..."
        
        # Chỉ gửi pills_detail khi cần (1 lần duy nhất)
        emit('ai_result', {
            'processed_image': cv2_to_base64(frame),
            'count': display_count,
            'status_text': status,
            'status_color': color,
            'percent': percent,
            'is_locked': state['locked'],
            'confidence': avg_conf,
            'inference_time': process_time,
            'pills_detail': pills_detail if send_pills else None  # None = không cập nhật
        }, broadcast=True)

    except Exception: pass


# =====================================================
# PHẦN 2: CÁC ROUTE WEB (DASHBOARD, HISTORY, ETC.)
# =====================================================

@pharmacist.context_processor
def inject_pharmacist_data():
    if current_user.is_authenticated and current_user.vai_tro == VaiTroEnum.pharmacist:
        unread = ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).count()
        try:
            device = ThietBi.query.get(1)
            d_status = device.trang_thai.name if device else 'offline'
        except:
            d_status = 'offline'
            
        return dict(
            unread_notifications_count=unread,
            notifications=ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).all(),
            device_status=d_status
        )
    return {}

@pharmacist.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    
    stats_query = db.session.query(
        func.count(DonThuoc.id).label('total_orders'),
        func.sum(DonThuoc.tong_vien_dem_duoc).label('total_pills'),
        func.avg(DonThuoc.thoi_gian_xu_ly_ms).label('avg_time'),
        func.sum(DonThuoc.tong_so_loai_thuoc).label('total_drug_types')
    ).filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don == 'completed',
        func.date(DonThuoc.thoi_gian_ket_thuc) == today
    ).first()

    orders_today = stats_query.total_orders or 0
    pills_today = int(stats_query.total_pills or 0) 
    avg_time = round(float(stats_query.avg_time or 0), 1)
    drug_types_today = int(stats_query.total_drug_types or 0)

    pending_orders = DonThuoc.query.filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don.in_(['pending', 'counting'])
    ).order_by(
        case((DonThuoc.trang_thai_don == 'counting', 0), else_=1),
        DonThuoc.thoi_gian_tao_don.desc()
    ).limit(10).all()

    recent_notifications = ThongBao.query.filter_by(id_nguoi_dung=current_user.id)\
        .order_by(ThongBao.ngay_tao.desc()).limit(3).all()
    recent_history = DonThuoc.query.filter_by(id_duoc_si=current_user.id, trang_thai_don='completed')\
        .order_by(DonThuoc.thoi_gian_ket_thuc.desc()).limit(3).all()

    return render_template('pharmacist/dashboard.html',
                           orders_today=orders_today,
                           pills_today=pills_today,
                           avg_time=avg_time,
                           drug_types_today=drug_types_today,
                           pending_orders=pending_orders,
                           recent_notifications=recent_notifications,
                           recent_history=recent_history)

@pharmacist.route('/counting')
@login_required
def counting_page_no_id():
    pending_orders = DonThuoc.query.filter(
        or_(DonThuoc.trang_thai_don == TrangThaiDonEnum.pending,
            DonThuoc.trang_thai_don == TrangThaiDonEnum.counting)
    ).order_by(desc(DonThuoc.thoi_gian_tao_don)).all()
    all_drugs = LoaiThuoc.query.filter_by(dang_su_dung=True).all()
    return render_template('pharmacist/counting.html', orders=pending_orders, drugs=all_drugs)

# --- ROUTE HISTORY ĐÃ FIX LỖI UNDEFINED ---
@pharmacist.route('/history')
@login_required
def my_history():
    page = request.args.get('page', 1, type=int)
    search_ma_don_thuoc = request.args.get('search_ma_don_thuoc', '').strip()
    filter_date_range = request.args.get('filter_date_range', '').strip()
    filter_trang_thai_khop = request.args.get('filter_trang_thai_khop', '').strip()

    # Thêm joinedload để load chi_tiet_don relationship
    from sqlalchemy.orm import joinedload
    query = DonThuoc.query.options(joinedload(DonThuoc.chi_tiet_don)).filter_by(id_duoc_si=current_user.id).order_by(DonThuoc.thoi_gian_ket_thuc.desc())

    if search_ma_don_thuoc:
        query = query.filter(DonThuoc.ma_don_thuoc.ilike(f'%{search_ma_don_thuoc}%'))

    if filter_trang_thai_khop:
        try:
            status_enum = TrangThaiKhopDonEnum[filter_trang_thai_khop]
            query = query.filter(DonThuoc.trang_thai_khop == status_enum)
        except KeyError: pass

    if filter_date_range:
        try:
            start_str, end_str = filter_date_range.split(' - ')
            start_date = datetime.strptime(start_str, '%d/%m/%Y').date()
            end_date = datetime.strptime(end_str, '%d/%m/%Y').date()
            query = query.filter(func.date(DonThuoc.thoi_gian_ket_thuc) >= start_date,
                                 func.date(DonThuoc.thoi_gian_ket_thuc) <= end_date)
        except: pass
    
    query = query.filter(DonThuoc.trang_thai_don.in_(['completed', 'error']))
    orders = query.paginate(page=page, per_page=10, error_out=False)

    # ĐÃ THÊM BIẾN NÀY ĐỂ FIX LỖI
    current_filters = {
        'search_ma_don_thuoc': search_ma_don_thuoc,
        'filter_date_range': filter_date_range,
        'filter_trang_thai_khop': filter_trang_thai_khop
    }

    return render_template('pharmacist/my_history.html', 
                           orders=orders, 
                           current_filters=current_filters)

# --- ROUTE STATS ĐÃ REDESIGN ---
@pharmacist.route('/stats')
@login_required
def my_stats():
    period = request.args.get('period', '7days')
    today = date.today()
    if period == '30days': start_date = today - timedelta(days=29)
    elif period == 'this_month': start_date = today.replace(day=1)
    else: start_date = today - timedelta(days=6)
    end_date = today

    base_query = db.session.query(DonThuoc).filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don == 'completed',
        func.date(DonThuoc.thoi_gian_ket_thuc).between(start_date, end_date)
    )

    total_orders = base_query.count()
    
    # Tổng viên đếm được
    pills_query = db.session.query(
        func.sum(ChiTietDonThuoc.so_luong_dem_duoc)
    ).join(DonThuoc, ChiTietDonThuoc.id_don_thuoc == DonThuoc.id)\
     .filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don == 'completed',
        func.date(DonThuoc.thoi_gian_ket_thuc).between(start_date, end_date)
    ).scalar()

    avg_time_query = base_query.with_entities(func.avg(DonThuoc.thoi_gian_xu_ly_ms)).scalar()
    
    # Số loại thuốc khác nhau đã đếm
    total_drug_types = db.session.query(
        func.count(func.distinct(ChiTietDonThuoc.id_loai_thuoc))
    ).join(DonThuoc, ChiTietDonThuoc.id_don_thuoc == DonThuoc.id)\
     .filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don == 'completed',
        func.date(DonThuoc.thoi_gian_ket_thuc).between(start_date, end_date)
    ).scalar() or 0

    summary_stats = {
        'total_orders': total_orders,
        'total_pills_counted': int(pills_query or 0),
        'avg_processing_time': round(float(avg_time_query or 0), 1),
        'total_drug_types': total_drug_types
    }

    # TREND CHART: Số đơn, số viên, thời gian xử lý theo ngày
    trend_data = db.session.query(
        func.date(DonThuoc.thoi_gian_ket_thuc).label('date'),
        func.count(DonThuoc.id).label('order_count'),
        func.sum(DonThuoc.tong_vien_dem_duoc).label('pill_count'),
        func.avg(DonThuoc.thoi_gian_xu_ly_ms).label('avg_time')
    ).filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don == 'completed',
        func.date(DonThuoc.thoi_gian_ket_thuc).between(start_date, end_date)
    ).group_by('date').order_by('date').all()

    trend_chart_data = {
        'labels': [d.date.strftime('%d/%m') for d in trend_data],
        'order_data': [int(d.order_count or 0) for d in trend_data],
        'pill_data': [int(d.pill_count or 0) for d in trend_data],
        'time_data': [round(float(d.avg_time or 0), 1) for d in trend_data]
    }

    # TOP 5 THUỐC ĐẾM NHIỀU NHẤT (cho Doughnut chart)
    top_counted_drugs = db.session.query(
        LoaiThuoc.ten_thuoc,
        func.sum(ChiTietDonThuoc.so_luong_dem_duoc).label('total')
    ).join(ChiTietDonThuoc, LoaiThuoc.id == ChiTietDonThuoc.id_loai_thuoc)\
     .join(DonThuoc, ChiTietDonThuoc.id_don_thuoc == DonThuoc.id)\
     .filter(
        DonThuoc.id_duoc_si == current_user.id,
        DonThuoc.trang_thai_don == 'completed',
        func.date(DonThuoc.thoi_gian_ket_thuc).between(start_date, end_date)
    ).group_by(LoaiThuoc.id)\
     .order_by(func.sum(ChiTietDonThuoc.so_luong_dem_duoc).desc())\
     .limit(5).all()
    
    # 5 ĐƠN THUỐC GẦN ĐÂY
    recent_orders = base_query.order_by(DonThuoc.thoi_gian_ket_thuc.desc()).limit(5).all()

    return render_template('pharmacist/my_stats.html', period=period, 
                           summary_stats=summary_stats, 
                           trend_chart_data=trend_chart_data, 
                           top_counted_drugs=top_counted_drugs,
                           recent_orders=recent_orders)

@pharmacist.route('/report-incident', methods=['GET', 'POST'])
@login_required
def report_incident():
    if request.method == 'POST':
        try:
            loai = LoaiSuCoEnum[request.form.get('loai_su_co')]
            mota = request.form.get('mo_ta')
            ma_don = request.form.get('ma_don_thuoc', '').strip()
            
            id_don = None
            if ma_don:
                don = DonThuoc.query.filter_by(ma_don_thuoc=ma_don).first()
                if don: id_don = don.id
            
            new_rpt = BaoCaoSuCo(
                id_nguoi_bao_cao=current_user.id, 
                loai_su_co=loai, 
                mo_ta=mota,
                id_don_thuoc=id_don
            )
            db.session.add(new_rpt)
            db.session.commit()
            
            # ✅ GỬI THÔNG BÁO CHO TẤT CẢ ADMIN
            from .utils import notify_all_admins
            from .models import LoaiThongBaoEnum
            notify_all_admins(
                title=f"Báo cáo sự cố mới từ {current_user.ho_ten}",
                content=f"Loại: {loai.value}. {mota[:100]}{'...' if len(mota) > 100 else ''}",
                notif_type=LoaiThongBaoEnum.error
            )
            
            flash('Gửi báo cáo thành công!', 'success')
        except Exception as e: 
            flash(f'Lỗi gửi báo cáo: {e}', 'danger')
        return redirect(url_for('pharmacist.report_incident'))
        
    history = BaoCaoSuCo.query.filter_by(id_nguoi_bao_cao=current_user.id).order_by(BaoCaoSuCo.ngay_tao.desc()).all()
    
    # Lấy danh sách đơn thuốc đã hoàn thành của user (cho dropdown)
    user_orders = DonThuoc.query.filter_by(
        id_duoc_si=current_user.id,
        trang_thai_don='completed'
    ).order_by(DonThuoc.thoi_gian_ket_thuc.desc()).limit(50).all()
    
    return render_template('pharmacist/report_incident.html', 
                           incident_types=LoaiSuCoEnum, 
                           past_reports=history,
                           user_orders=user_orders)

@pharmacist.route('/guide')
@login_required
def guide():
    return render_template('pharmacist/guide.html')

@pharmacist.route('/settings')
@login_required
def settings():
    return "Trang Cài đặt của Dược sĩ"

# =====================================================
# PHẦN 3: APIs & ORDER MANAGEMENT
# =====================================================

@pharmacist.route('/api/search-drugs')
@login_required
def search_drugs():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', 'all')
    
    sql = LoaiThuoc.query.filter(LoaiThuoc.dang_su_dung == True)
    
    if q: 
        sql = sql.filter(or_(
            LoaiThuoc.ten_thuoc.ilike(f'%{q}%'), 
            LoaiThuoc.ma_thuoc.ilike(f'%{q}%')
        ))
    
    # Filter by category
    if category == 'antibiotic':
        sql = sql.filter(LoaiThuoc.mo_ta.ilike('%kháng sinh%'))
    elif category == 'painkiller':
        sql = sql.filter(or_(LoaiThuoc.mo_ta.ilike('%giảm đau%'), LoaiThuoc.mo_ta.ilike('%hạ sốt%')))
    elif category == 'vitamin':
        sql = sql.filter(LoaiThuoc.ten_thuoc.ilike('%vitamin%'))
        
    drugs = sql.limit(50).all()
    
    return jsonify([{
        'id': d.id, 
        'name': d.ten_thuoc, 
        'code': d.ma_thuoc, 
        'stock': d.ton_kho_uoc_tinh or 0,
        'unit': d.don_vi_tinh,
        'image': d.url_hinh_anh,
        'warning_threshold': d.nguong_canh_bao or 0 # EXPOSE THRESHOLD
    } for d in drugs])

@pharmacist.route('/api/get-order-details/<int:order_id>')
@login_required
def get_order_details_api(order_id):
    try:
        order = DonThuoc.query.get_or_404(order_id)
        items = []
        for item in order.chi_tiet_don:
            if not item.loai_thuoc_info: continue
            drug = item.loai_thuoc_info
            
            # Simulated Avg Accuracy (Since it's not directly in DB yet, or calculated)
            # In a real scenario you might calculate this from ChiTietDonThuoc
            
            items.append({
                'detail_id': item.id, 
                'drug_id': drug.id,
                'drug_name': drug.ten_thuoc,
                'req_qty': item.so_luong_yeu_cau, 
                'is_done': item.so_luong_dem_duoc is not None, # Check if counted
                # --- NEW STATS DATA ---
                'total_counted': drug.tong_luong_da_dem or 0,
                'times_counted': drug.so_lan_duoc_dem or 0,
                'threshold': drug.nguong_canh_bao or 0,
                'image': drug.url_hinh_anh
            })
        return jsonify({'success': True, 'items': items})
    except Exception as e: return jsonify({'success': False, 'msg': str(e)})

# --- API LẤY CHI TIẾT ĐẦY ĐỦ (CHO MODAL LỊCH SỬ) ---
@pharmacist.route('/api/order-details/<int:order_id>')
@login_required
def get_order_details_full(order_id):
    try:
        order = DonThuoc.query.filter_by(id=order_id, id_duoc_si=current_user.id).first()
        if not order: return jsonify({'error': 'Không tìm thấy đơn'}), 404

        details = []
        for d in order.chi_tiet_don:
            details.append({
                'ten_thuoc': d.loai_thuoc_info.ten_thuoc,
                'so_luong_yeu_cau': d.so_luong_yeu_cau,
                'so_luong_dem_duoc': d.so_luong_dem_duoc or 0,
                'chenh_lech': d.chenh_lech or 0
            })

        # Không cần cộng thêm 7h vì đã lưu giờ VN trong DB
        created_time = order.thoi_gian_tao_don
        completed_time = order.thoi_gian_ket_thuc
        
        # Format thời gian xử lý ms -> m:ss:ms
        processing_time_str = 'N/A'
        if order.thoi_gian_xu_ly_ms:
            total_ms = order.thoi_gian_xu_ly_ms
            mins = total_ms // 60000
            secs = (total_ms % 60000) // 1000
            ms = total_ms % 1000
            processing_time_str = f"{mins}m {secs}s {ms}ms"

        return jsonify({
            'ma_don_thuoc': order.ma_don_thuoc,
            'duoc_si_xu_ly': order.duoc_si.ho_ten,
            'thoi_gian_tao_don': created_time.strftime('%H:%M %d/%m/%Y') if created_time else 'N/A',
            'thoi_gian_ket_thuc': completed_time.strftime('%H:%M %d/%m/%Y') if completed_time else 'N/A',
            'thoi_gian_xu_ly': processing_time_str,
            'tong_vien_yeu_cau': order.tong_vien_yeu_cau,
            'tong_vien_dem_duoc': order.tong_vien_dem_duoc,
            'chi_tiet': details
        })
    except Exception as e: return jsonify({'error': str(e)}), 500

@pharmacist.route('/api/save-result', methods=['POST'])
@login_required
def save_result():
    data = request.json
    try:
        if data.get('mode') == 'prescription':
            item = ChiTietDonThuoc.query.get(data.get('detail_id'))
            if not item: return jsonify({'success': False, 'msg': 'Lỗi ID'})
            
            count = int(data.get('count'))
            item.so_luong_dem_duoc = count
            item.do_tin_cay = round(float(data.get('confidence', 0))*100, 2)
            item.thoi_gian_nhan_dien_ms = int(float(data.get('time', 0)))
            
            if 'image' in data and data['image']:
                try:
                    img_data = data['image'].split(",", 1)[1] if "," in data['image'] else data['image']
                    filename = f"count_{item.id}_{int(datetime.now().timestamp())}.jpg"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    with open(filepath, "wb") as f: f.write(base64.b64decode(img_data))
                    item.url_hinh_anh = f"/static/uploads/{filename}"
                except: pass

            diff = count - item.so_luong_yeu_cau
            item.chenh_lech = diff
            item.trang_thai_khop = TrangThaiKhopChiTietEnum.match if diff == 0 else (TrangThaiKhopChiTietEnum.over if diff > 0 else TrangThaiKhopChiTietEnum.under)
            
            don = item.don_thuoc
            if don.trang_thai_don == TrangThaiDonEnum.pending:
                don.trang_thai_don = TrangThaiDonEnum.counting
                don.thoi_gian_bat_dau = datetime.now()
            
            # Cộng dồn thời gian đếm từ frontend (ms)
            elapsed_ms = data.get('elapsed_ms', 0)
            if elapsed_ms and elapsed_ms > 0:
                don.thoi_gian_xu_ly_ms = (don.thoi_gian_xu_ly_ms or 0) + int(elapsed_ms)
            
            don.tong_vien_dem_duoc = sum([(ct.so_luong_dem_duoc or 0) for ct in don.chi_tiet_don])
            
            # FLUSH TO ENSURE DATA IS WRITTEN BEFORE CHECK
            db.session.flush()
            
            # Re-query to get fresh data
            db.session.refresh(don)
            
            # CHECK IF ALL ITEMS ARE DONE -> AUTO COMPLETE
            all_done = all(ct.so_luong_dem_duoc is not None for ct in don.chi_tiet_don)
            
            if all_done:
                don.trang_thai_don = TrangThaiDonEnum.completed
                don.thoi_gian_ket_thuc = datetime.now()
                
                # Determine Overall Match Status
                total_diff = sum([abs(ct.chenh_lech or 0) for ct in don.chi_tiet_don])
                has_mismatch = any(ct.trang_thai_khop != TrangThaiKhopChiTietEnum.match for ct in don.chi_tiet_don)
                
                if total_diff == 0 and not has_mismatch:
                    don.trang_thai_khop = TrangThaiKhopDonEnum.perfect
                elif has_mismatch:
                    don.trang_thai_khop = TrangThaiKhopDonEnum.mismatch
                else:
                    don.trang_thai_khop = TrangThaiKhopDonEnum.partial
                
                # Log Completion
                log = NhatKyHeThong(
                loai_log=LoaiLogEnum.info,
                    noi_dung=f'Hoàn thành đơn {don.ma_don_thuoc} (Khớp: {don.trang_thai_khop.value})',
                    id_nguoi_dung=current_user.id
                )
                db.session.add(log)
                
                # --- CẬP NHẬT TỶ LỆ CHÍNH XÁC CỦA DƯỢC SĨ ---
                # Tính trung bình độ tin cậy từ tất cả chi tiết đơn đã hoàn thành
                avg_confidence = db.session.query(func.avg(ChiTietDonThuoc.do_tin_cay))\
                    .join(DonThuoc, ChiTietDonThuoc.id_don_thuoc == DonThuoc.id)\
                    .filter(
                        DonThuoc.id_duoc_si == current_user.id,
                        DonThuoc.trang_thai_don == 'completed',
                        ChiTietDonThuoc.do_tin_cay.isnot(None)
                    ).scalar()
                
                if avg_confidence:
                    current_user.ty_le_chinh_xac = round(float(avg_confidence), 2)

                # --- NEW: POST-COUNT STOCK RECONCILIATION & STATS ---
                for item in don.chi_tiet_don:
                    drug = item.loai_thuoc_info
                    if drug:
                        # 1. Reconciliation: Adjust stock if Count != Request
                        # If Counted (12) > Request (10) => Diff = 2 => Stock -= 2
                        # If Counted (8) < Request (10) => Diff = -2 => Stock -= -2 (Increase)
                        cnt = item.so_luong_dem_duoc or 0
                        req = item.so_luong_yeu_cau
                        diff = cnt - req
                        
                        drug.ton_kho_uoc_tinh -= diff
                        
                        # 2. Update Usage Stats
                        drug.tong_luong_da_dem += cnt
                        drug.so_lan_duoc_dem += 1
                        
                        # ✅ CẢNH BÁO TỒN KHO THẤP (< 100 viên)
                        if drug.ton_kho_uoc_tinh < 100 and drug.ton_kho_uoc_tinh > 0:
                            from .utils import notify_all_admins
                            from .models import LoaiThongBaoEnum
                            notify_all_admins(
                                title=f"Thuốc {drug.ten_thuoc} sắp hết",
                                content=f"Còn khoảng {drug.ton_kho_uoc_tinh} viên. Vui lòng nhập thêm.",
                                notif_type=LoaiThongBaoEnum.warning
                            )
            
            db.session.commit()
            
            # Calculate progress
            items_done = sum(1 for ct in don.chi_tiet_don if ct.so_luong_dem_duoc is not None)
            items_total = len(list(don.chi_tiet_don))
            
            msg = f'Đã lưu: {count}'
            if all_done:
                if don.trang_thai_khop == TrangThaiKhopDonEnum.perfect:
                    msg += ' (Đơn đã hoàn thành ✅)'
                else:
                    msg += ' (CẢNH BÁO: Đơn lệch số lượng! Đã đóng ⚠️)'
            
            return jsonify({
                'success': True, 
                'msg': msg,
                'items_done': items_done,
                'items_total': items_total,
                'order_completed': all_done
            })
        return jsonify({'success': True, 'msg': 'Đếm tự do xong'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': str(e)})

# --- CRUD ĐƠN THUỐC ---
@pharmacist.route('/orders')
@login_required
def order_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all')
    
    query = DonThuoc.query.filter_by(id_duoc_si=current_user.id)
    
    # Lọc theo trạng thái
    if status_filter == 'pending':
        query = query.filter(DonThuoc.trang_thai_don == 'pending')
    elif status_filter == 'counting':
        query = query.filter(DonThuoc.trang_thai_don == 'counting')
    elif status_filter == 'completed':
        query = query.filter(DonThuoc.trang_thai_don == 'completed')
    # 'all' thì không filter
    
    query = query.order_by(desc(DonThuoc.thoi_gian_tao_don))
    
    if search:
        query = query.filter(DonThuoc.ma_don_thuoc.ilike(f'%{search}%'))

    return render_template('pharmacist/order_list.html', 
                           pagination=query.paginate(page=page, per_page=10), 
                           TrangThaiDonEnum=TrangThaiDonEnum,
                           search_query=search,
                           status_filter=status_filter)

@pharmacist.route('/new-order', methods=['GET', 'POST'])
@login_required
def new_order():
    if request.method == 'POST':
        try:
            drug_ids = request.form.getlist('drug_ids[]')
            quantities = request.form.getlist('quantities[]')
            patient = request.form.get('patient_name')
            note = request.form.get('note')

            if not drug_ids:
                flash('Giỏ hàng trống.', 'warning')
                return redirect(url_for('pharmacist.new_order'))

            ma_don = f"DT-{str(uuid.uuid4())[:8].upper()}"
            new_don = DonThuoc(ma_don_thuoc=ma_don, id_duoc_si=current_user.id, ten_benh_nhan=patient, ghi_chu_duoc_si=note, trang_thai_don=TrangThaiDonEnum.pending)
            db.session.add(new_don)
            db.session.flush()

            total_items = 0
            total_pills = 0
            for d_id, qty in zip(drug_ids, quantities):
                qty = int(qty)
                if qty > 0:
                    # Enforce strict stock checking
                    drug = LoaiThuoc.query.with_for_update().get(int(d_id))
                    if not drug: raise Exception(f"Không tìm thấy thuốc ID {d_id}")
                    
                    if drug.ton_kho_uoc_tinh < qty:
                        db.session.rollback()
                        flash(f'Lỗi: Thuốc "{drug.ten_thuoc}" không đủ tồn kho (Còn {drug.ton_kho_uoc_tinh}).', 'danger')
                        return redirect(url_for('pharmacist.new_order'))
                    
                    # Deduct stock
                    drug.ton_kho_uoc_tinh -= qty
                    
                    ct = ChiTietDonThuoc(id_don_thuoc=new_don.id, id_loai_thuoc=int(d_id), so_luong_yeu_cau=qty, trang_thai_khop=TrangThaiKhopChiTietEnum.missing)
                    db.session.add(ct)
                    total_items += 1
                    total_pills += qty
            
            new_don.tong_so_loai_thuoc = total_items
            new_don.tong_vien_yeu_cau = total_pills
            
            # LOGGING
            log = NhatKyHeThong(
                loai_log=LoaiLogEnum.info,
                noi_dung=f'Tạo đơn thuốc mới: {ma_don} gồm {total_items} loại ({total_pills} viên)',
                id_nguoi_dung=current_user.id
            )
            db.session.add(log)
            
            db.session.commit()
            flash(f'Tạo đơn {ma_don} thành công!', 'success')
            return redirect(url_for('pharmacist.order_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {e}', 'danger')
    return render_template('pharmacist/new_order.html')

@pharmacist.route('/order/delete/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    order = DonThuoc.query.get_or_404(order_id)
    if order.trang_thai_don == TrangThaiDonEnum.completed:
        flash('Không thể xóa đơn đã hoàn thành.', 'danger')
    else:
        try:
            # REFUND STOCK BEFORE DELETING
            # Loop through all items and return quantity to inventory
            for item in order.chi_tiet_don:
                # Use with_for_update to lock the row and prevent race conditions
                drug = LoaiThuoc.query.with_for_update().get(item.id_loai_thuoc)
                if drug:
                    drug.ton_kho_uoc_tinh += item.so_luong_yeu_cau
            
            db.session.delete(order)
            
            # LOGGING
            log = NhatKyHeThong(
                loai_log=LoaiLogEnum.warning,
                noi_dung=f'Xóa đơn thuốc: {order.ma_don_thuoc} và hoàn kho',
                id_nguoi_dung=current_user.id
            )
            db.session.add(log)
            
            db.session.commit()
            flash('Đã xóa đơn thuốc và hoàn lại tồn kho.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi xóa đơn: {str(e)}', 'danger')
            
    return redirect(url_for('pharmacist.order_list'))

@pharmacist.route('/order/edit/<int:order_id>', methods=['GET', 'POST'])
@login_required
def edit_order(order_id):
    order = DonThuoc.query.get_or_404(order_id)
    
    # Chỉ cho phép sửa đơn chưa hoàn thành
    if order.trang_thai_don == TrangThaiDonEnum.completed:
        flash('Không thể sửa đơn đã hoàn thành!', 'warning')
        return redirect(url_for('pharmacist.order_list'))
        
    if request.method == 'POST':
        order.ten_benh_nhan = request.form.get('patient_name')
        order.ghi_chu_duoc_si = request.form.get('note')
        
        # Cập nhật danh sách thuốc
        drug_ids = request.form.getlist('drug_ids[]')
        quantities = request.form.getlist('quantities[]')
        
        if drug_ids and quantities:
            # 1. LƯU LẠI SỐ LƯỢNG CŨ (để tính delta kho)
            old_quantities = {}
            for detail in order.chi_tiet_don:
                old_quantities[detail.id_loai_thuoc] = detail.so_luong_yeu_cau
            
            # 2. XÓA CHI TIẾT CŨ
            ChiTietDonThuoc.query.filter_by(id_don_thuoc=order.id).delete()
            
            # 3. THÊM CHI TIẾT MỚI + GỘP TRÙNG
            new_quantities = {}
            for drug_id, qty in zip(drug_ids, quantities):
                drug_id = int(drug_id)
                qty = int(qty)
                if drug_id in new_quantities:
                    new_quantities[drug_id] += qty
                else:
                    new_quantities[drug_id] = qty
            
            total_types = 0
            total_required = 0
            for drug_id, qty in new_quantities.items():
                detail = ChiTietDonThuoc(
                    id_don_thuoc=order.id,
                    id_loai_thuoc=drug_id,
                    so_luong_yeu_cau=qty
                )
                db.session.add(detail)
                total_types += 1
                total_required += qty
                
                # 4. CẬP NHẬT KHO (DELTA = SỐ LƯỢNG CŨ - SỐ LƯỢNG MỚI)
                # Nếu tăng số lượng -> trừ kho
                # Nếu giảm số lượng -> cộng lại kho
                old_qty = old_quantities.get(drug_id, 0)
                delta = old_qty - qty  # Dương = hoàn kho, Âm = trừ kho
                
                drug = LoaiThuoc.query.get(drug_id)
                if drug:
                    drug.ton_kho_uoc_tinh = (drug.ton_kho_uoc_tinh or 0) + delta
            
            # 5. HOÀN KHO CHO THUỐC BỊ XÓA KHỎI ĐƠN
            for drug_id, old_qty in old_quantities.items():
                if drug_id not in new_quantities:
                    drug = LoaiThuoc.query.get(drug_id)
                    if drug:
                        drug.ton_kho_uoc_tinh = (drug.ton_kho_uoc_tinh or 0) + old_qty
            
            # Cập nhật tổng
            order.tong_so_loai_thuoc = total_types
            order.tong_vien_yeu_cau = total_required
        
        db.session.commit()
        flash('Đã cập nhật đơn thuốc thành công!', 'success')
        return redirect(url_for('pharmacist.order_list'))
    return render_template('pharmacist/edit_order.html', order=order)

@pharmacist.route('/notifications/mark-all-read')
@login_required
def mark_all_read():
    try:
        ThongBao.query.filter_by(id_nguoi_dung=current_user.id, da_doc=False).update({'da_doc': True})
        db.session.commit()
        flash('Đã đánh dấu tất cả là đã đọc.', 'success')
    except Exception as e:
        db.session.rollback()
    return redirect(request.referrer or url_for('pharmacist.dashboard'))

@pharmacist.route('/notifications/<int:id>')
@login_required
def view_notification(id):
    try:
        notif = ThongBao.query.get_or_404(id)
        if notif.id_nguoi_dung == current_user.id:
            notif.da_doc = True
            db.session.commit()
    except: pass
    return redirect(url_for('pharmacist.dashboard'))

@pharmacist.route('/notifications/all')
@login_required
def all_notifications():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search_query', '').strip()
    
    query = ThongBao.query.filter_by(id_nguoi_dung=current_user.id).order_by(ThongBao.ngay_tao.desc())
    if search_query:
        query = query.filter(ThongBao.noi_dung.ilike(f'%{search_query}%'))
        
    pagination = query.paginate(page=page, per_page=15)
    return render_template('pharmacist/notifications.html', 
                           notifications=pagination.items, 
                           pagination=pagination,
                           search_query=search_query)