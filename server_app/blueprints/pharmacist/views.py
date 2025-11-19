# File: server_app/blueprints/pharmacist/views.py

from flask import Blueprint, render_template
from ....extensions import socketio
from flask_socketio import emit
import cv2
import numpy as np
import base64
from ultralytics import YOLO

pharmacist = Blueprint('pharmacist', __name__)

# --- CẤU HÌNH ---
# Tải model 1 lần duy nhất
model = None
try:
    model = YOLO('models/best.pt')
    print("✅ SERVER: AI Ready!")
except:
    print("⚠️ SERVER: Running without AI")

# Biến trạng thái
state = {
    'target': 0,
    'locked': False,
    'stable_count': 0,
    'last_val': -1,
    'final_val': 0
}

# Hàm giải mã nhanh
def base64_to_cv2(b64):
    try:
        if "," in b64: _, b64 = b64.split(",", 1)
        data = base64.b64decode(b64)
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except: return None

# Hàm nén nhanh để gửi về Web
def cv2_to_base64(img):
    # Nén nhẹ để gửi về web cho nhanh
    _, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')

@socketio.on('update_target')
def handle_target(data):
    state['target'] = int(data.get('target', 0))
    state['locked'] = False
    state['stable_count'] = 0
    print(f"🎯 Target: {state['target']}")

@socketio.on('process_frame_pi')
def handle_pi_stream(data):
    # KHÔNG DÙNG PRINT Ở ĐÂY ĐỂ TRÁNH LAG
    
    try:
        # 1. Nhận ảnh
        frame = base64_to_cv2(data.get('image'))
        if frame is None: return

        display_count = 0
        
        # 2. Xử lý AI
        if model:
            if not state['locked']:
                # AI Detect
                results = model(frame, verbose=False, conf=0.5)
                cnt = len(results[0].boxes)
                frame = results[0].plot() # Vẽ đè lên frame gốc

                # Logic ổn định
                if cnt == state['last_val']: state['stable_count'] += 1
                else: state['last_val'], state['stable_count'] = cnt, 0
                
                if state['stable_count'] >= 5: # 5 khung hình ổn định -> Chốt
                    state['locked'] = True
                    state['final_val'] = cnt
                    print(f"🔒 LOCKED: {cnt}")
                
                display_count = cnt
            else:
                # Đã chốt -> Không chạy AI -> Vẽ chữ Locked
                display_count = state['final_val']
                cv2.rectangle(frame, (0,0), (frame.shape[1], frame.shape[0]), (0,255,0), 5)
                cv2.putText(frame, f"LOCKED: {display_count}", (50, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)

        # 3. Gửi về Web ngay lập tức
        target = state['target']
        diff = display_count - target
        percent = round((display_count/target)*100, 1) if target > 0 else 0
        
        status, color = "Đang đếm...", "warning"
        if state['locked']:
            if diff == 0: status, color = "Khớp", "success"
            elif diff > 0: status, color = f"Dư {diff}", "warning"
            else: status, color = f"Thiếu {abs(diff)}", "danger"

        emit('ai_result', {
            'processed_image': cv2_to_base64(frame),
            'count': display_count,
            'status_text': status,
            'status_color': color,
            'percent': percent,
            'is_locked': state['locked']
        }, broadcast=True)

    except: pass

@pharmacist.route('/counting')
def counting_page_no_id():
    # Data giả để test
    fake = [{'detail_id': 1, 'drug_name': 'Thuốc Mẫu A', 'req_qty': 10},
            {'detail_id': 2, 'drug_name': 'Thuốc Mẫu B', 'req_qty': 20}]
    return render_template('pharmacist/counting.html', details=fake, order={'ma_don_thuoc': 'LIVE-STREAM'})