# File: server_app/utils.py
# Các hàm tiện ích dùng chung

from .extensions import db, socketio
from .models import ThongBao, LoaiThongBaoEnum, NguoiDung, VaiTroEnum
from datetime import datetime


def create_notification(user_id, title, content, notif_type=LoaiThongBaoEnum.info, emit_socket=True):
    """
    Tạo thông báo mới và gửi realtime qua SocketIO.
    
    Args:
        user_id: ID của người dùng nhận thông báo
        title: Tiêu đề thông báo
        content: Nội dung thông báo
        notif_type: Loại thông báo (info/warning/error/success)
        emit_socket: True để gửi realtime qua SocketIO
    
    Returns:
        ThongBao object đã tạo
    """
    notif = ThongBao(
        id_nguoi_dung=user_id,
        tieu_de=title,
        noi_dung=content,
        loai=notif_type,
        da_doc=False,
        ngay_tao=datetime.now()
    )
    db.session.add(notif)
    db.session.commit()
    
    # Gửi realtime qua SocketIO
    if emit_socket:
        try:
            # Đếm số thông báo chưa đọc
            unread_count = ThongBao.query.filter_by(id_nguoi_dung=user_id, da_doc=False).count()
            
            socketio.emit('notification_received', {
                'id': notif.id,
                'title': title,
                'content': content,
                'type': notif_type.name,
                'unread_count': unread_count,
                'timestamp': notif.ngay_tao.strftime('%H:%M %d/%m/%Y')
            }, room=f"user_{user_id}")
        except Exception as e:
            print(f"[SOCKET] Lỗi emit notification: {e}")
    
    return notif


def notify_all_admins(title, content, notif_type=LoaiThongBaoEnum.info):
    """
    Gửi thông báo cho TẤT CẢ Admin.
    """
    admins = NguoiDung.query.filter_by(vai_tro=VaiTroEnum.admin, dang_hoat_dong=True).all()
    notifications = []
    
    for admin in admins:
        notif = create_notification(
            user_id=admin.id,
            title=title,
            content=content,
            notif_type=notif_type
        )
        notifications.append(notif)
    
    return notifications


def notify_all_pharmacists(title, content, notif_type=LoaiThongBaoEnum.info):
    """
    Gửi thông báo cho TẤT CẢ Dược sĩ.
    """
    pharmacists = NguoiDung.query.filter_by(vai_tro=VaiTroEnum.pharmacist, dang_hoat_dong=True).all()
    notifications = []
    
    for pharmacist in pharmacists:
        notif = create_notification(
            user_id=pharmacist.id,
            title=title,
            content=content,
            notif_type=notif_type
        )
        notifications.append(notif)
    
    return notifications
