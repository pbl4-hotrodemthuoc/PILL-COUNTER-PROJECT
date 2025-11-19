# File: server_app/models.py
# Phiên bản hoàn thiện, kết hợp cấu trúc CSDL đầy đủ và các hàm logic nghiệp vụ.

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, text
import enum
import datetime  # Giữ lại để tránh lỗi tham chiếu vòng

# Khởi tạo đối tượng SQLAlchemy để các model có thể kế thừa
db = SQLAlchemy()

# ============================================
# ĐỊNH NGHĨA CÁC ENUM (DANH SÁCH CÁC GIÁ TRỊ CỐ ĐỊNH)
# ============================================

class VaiTroEnum(enum.Enum):
    # Giữ lại tiếng Anh để dễ xử lý logic phân quyền trong code (ví dụ: if user.role == 'admin')
    admin = 'admin'
    pharmacist = 'pharmacist'
# ----- THÊM LỚP ENUM CÒN THIẾU VÀO ĐÂY -----
class GioiTinhEnum(enum.Enum):
    male = 'Nam'
    female = 'Nữ'
    other = 'Khác'
class CaLamViecEnum(enum.Enum):
    morning = 'Sáng'
    afternoon = 'Chiều'
    evening = 'Tối'
    fulltime = 'Cả ngày'

class TrangThaiThietBiEnum(enum.Enum):
    online = 'Đang hoạt động'
    offline = 'Ngoại tuyến'

class TrangThaiDonEnum(enum.Enum):
    pending = 'Chờ xử lý'
    counting = 'Đang đếm'
    completed = 'Hoàn thành'
    error = 'Bị lỗi'

class TrangThaiKhopDonEnum(enum.Enum):
    perfect = 'Khớp hoàn toàn'
    partial = 'Khớp một phần'
    mismatch = 'Sai lệch'
    
class TrangThaiKhopChiTietEnum(enum.Enum):
    match = 'Khớp'
    over = 'Thừa'
    under = 'Thiếu'
    missing = 'Không tìm thấy'

class LoaiSuCoEnum(enum.Enum):
    drug_defect = 'Lỗi thuốc'
    device_error = 'Lỗi thiết bị'
    ai_error = 'Lỗi AI'
    other = 'Khác'

class TrangThaiSuCoEnum(enum.Enum):
    pending = 'Chờ xử lý'
    reviewing = 'Đang xem xét'
    resolved = 'Đã giải quyết'
    rejected = 'Bị từ chối'

class LoaiThongBaoEnum(enum.Enum):
    info = 'Thông tin'
    warning = 'Cảnh báo'
    error = 'Lỗi'
    success = 'Thành công'

class LoaiLogEnum(enum.Enum):
    info = 'Thông tin'
    warning = 'Cảnh báo'
    error = 'Lỗi'

# ============================================
# CÁC MODEL (TƯƠNG ỨNG VỚI CÁC BẢNG TRONG CSDL)
# ============================================

class NguoiDung(UserMixin, db.Model):
    """Model cho bảng người dùng (users)"""
    __tablename__ = 'nguoi_dung'
    id = db.Column(db.Integer, primary_key=True)
    ten_dang_nhap = db.Column(db.String(100), unique=True, nullable=False)
    mat_khau = db.Column(db.String(255), nullable=False)
    ho_ten = db.Column(db.String(200), nullable=False)
    gioi_tinh = db.Column(db.Enum(GioiTinhEnum), nullable=True)
    vai_tro = db.Column(db.Enum(VaiTroEnum), nullable=False, default=VaiTroEnum.pharmacist)
    so_dien_thoai = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    ca_lam_viec = db.Column(db.Enum(CaLamViecEnum), nullable=True)
    dang_hoat_dong = db.Column(db.Boolean, nullable=False, default=True)
    dang_trong_ca = db.Column(db.Boolean, nullable=False, default=False)
    tong_don_da_xu_ly = db.Column(db.Integer, default=0)
    tong_vien_da_dem = db.Column(db.Integer, default=0)
    thoi_gian_xu_ly_tb = db.Column(db.DECIMAL(5, 2), nullable=True)
    ty_le_chinh_xac = db.Column(db.DECIMAL(5, 2), nullable=True)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=func.current_timestamp())
    lan_dang_nhap_cuoi = db.Column(db.TIMESTAMP, nullable=True)

    # Mối quan hệ: Một người dùng có thể có nhiều đơn thuốc, báo cáo, thông báo...
    cac_don_thuoc = db.relationship('DonThuoc', backref='duoc_si', cascade="all, delete")
    cac_bao_cao = db.relationship('BaoCaoSuCo', backref='nguoi_bao_cao', cascade="all, delete")
    cac_thong_bao = db.relationship('ThongBao', backref='nguoi_dung', cascade="all, delete")
    cac_nhat_ky = db.relationship('NhatKyHeThong', backref='nguoi_thuc_hien', cascade="all, delete")

    def set_password(self, password): self.mat_khau = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.mat_khau, password)

class LoaiThuoc(db.Model):
    """Model cho bảng danh mục thuốc"""
    __tablename__ = 'loai_thuoc'
    id = db.Column(db.Integer, primary_key=True)
    ten_thuoc = db.Column(db.String(255), nullable=False)
    ma_thuoc = db.Column(db.String(50), unique=True, nullable=False)
    mo_ta = db.Column(db.Text, nullable=True)
    url_hinh_anh = db.Column(db.String(500), nullable=True)
    don_vi_tinh = db.Column(db.String(20), default='viên')
    ton_kho_uoc_tinh = db.Column(db.Integer, default=0)
    nguong_canh_bao = db.Column(db.Integer, nullable=True)
    dang_su_dung = db.Column(db.Boolean, default=True)
    tong_luong_da_dem = db.Column(db.Integer, default=0)
    so_lan_duoc_dem = db.Column(db.Integer, default=0)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=func.current_timestamp())
    ngay_cap_nhat = db.Column(db.TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

class ThietBi(db.Model):
    """Model cho bảng thiết bị"""
    __tablename__ = 'thiet_bi'
    id = db.Column(db.Integer, primary_key=True)
    ma_thiet_bi = db.Column(db.String(100), nullable=False, default='Pi-01')
    ten_thiet_bi = db.Column(db.String(200), default='Thiết bị đếm thuốc')
    trang_thai = db.Column(db.Enum(TrangThaiThietBiEnum), default=TrangThaiThietBiEnum.offline)
    lan_ket_noi_cuoi = db.Column(db.TIMESTAMP, nullable=True)
    tong_don_da_dem = db.Column(db.Integer, default=0)

class DonThuoc(db.Model):
    """Model cho bảng đơn thuốc"""
    __tablename__ = 'don_thuoc'
    id = db.Column(db.Integer, primary_key=True)
    ma_don_thuoc = db.Column(db.String(50), unique=True, nullable=False)
    id_duoc_si = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=False)
    id_thiet_bi = db.Column(db.Integer, db.ForeignKey('thiet_bi.id'), nullable=True, default=1)
    thoi_gian_tao_don = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    thoi_gian_bat_dau = db.Column(db.DateTime, nullable=True)
    thoi_gian_ket_thuc = db.Column(db.DateTime, nullable=True)
    thoi_gian_xu_ly_giay = db.Column(db.Integer, nullable=True)
    tong_so_loai_thuoc = db.Column(db.Integer, default=0)
    tong_vien_yeu_cau = db.Column(db.Integer, default=0)
    tong_vien_dem_duoc = db.Column(db.Integer, default=0)
    trang_thai_don = db.Column(db.Enum(TrangThaiDonEnum), default=TrangThaiDonEnum.pending)
    trang_thai_khop = db.Column(db.Enum(TrangThaiKhopDonEnum), nullable=True)
    ghi_chu_duoc_si = db.Column(db.Text, nullable=True)
    ghi_chu_he_thong = db.Column(db.Text, nullable=True)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=func.current_timestamp())
    
    chi_tiet_don = db.relationship('ChiTietDonThuoc', backref='don_thuoc', cascade="all, delete")
    cac_bao_cao = db.relationship('BaoCaoSuCo', backref='don_thuoc', cascade="all, delete")

class ChiTietDonThuoc(db.Model):
    """Model cho bảng chi tiết đơn thuốc"""
    __tablename__ = 'chi_tiet_don_thuoc'
    id = db.Column(db.Integer, primary_key=True)
    id_don_thuoc = db.Column(db.Integer, db.ForeignKey('don_thuoc.id'), nullable=False)
    id_loai_thuoc = db.Column(db.Integer, db.ForeignKey('loai_thuoc.id'), nullable=False)
    so_luong_yeu_cau = db.Column(db.Integer, nullable=False)
    so_luong_dem_duoc = db.Column(db.Integer, nullable=True)
    do_tin_cay = db.Column(db.DECIMAL(5, 2), nullable=True)
    thoi_gian_nhan_dien_ms = db.Column(db.Integer, nullable=True)
    trang_thai_khop = db.Column(db.Enum(TrangThaiKhopChiTietEnum), nullable=True)
    chenh_lech = db.Column(db.Integer, nullable=True)
    url_hinh_anh = db.Column(db.String(500), nullable=True)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=func.current_timestamp())

    loai_thuoc_info = db.relationship('LoaiThuoc')

class BaoCaoSuCo(db.Model):
    """Model cho bảng báo cáo sự cố"""
    __tablename__ = 'bao_cao_su_co'
    id = db.Column(db.Integer, primary_key=True)
    id_nguoi_bao_cao = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=False)
    loai_su_co = db.Column(db.Enum(LoaiSuCoEnum), nullable=False)
    id_don_thuoc = db.Column(db.Integer, db.ForeignKey('don_thuoc.id'), nullable=True)
    mo_ta = db.Column(db.Text, nullable=False)
    url_hinh_anh = db.Column(db.String(500), nullable=True)
    trang_thai = db.Column(db.Enum(TrangThaiSuCoEnum), default=TrangThaiSuCoEnum.pending)
    phan_hoi_admin = db.Column(db.Text, nullable=True)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=func.current_timestamp())
    ngay_xu_ly = db.Column(db.TIMESTAMP, nullable=True)

class ThongBao(db.Model):
    """Model cho bảng thông báo"""
    __tablename__ = 'thong_bao'
    id = db.Column(db.Integer, primary_key=True)
    id_nguoi_dung = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=False)
    loai = db.Column(db.Enum(LoaiThongBaoEnum), default=LoaiThongBaoEnum.info)
    tieu_de = db.Column(db.String(255), nullable=False)
    noi_dung = db.Column(db.Text, nullable=False)
    da_doc = db.Column(db.Boolean, default=False)
    thoi_gian_doc = db.Column(db.TIMESTAMP, nullable=True)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=func.current_timestamp())

class NhatKyHeThong(db.Model):
    """Model cho bảng nhật ký hệ thống"""
    __tablename__ = 'nhat_ky_he_thong'
    id = db.Column(db.Integer, primary_key=True)
    loai_log = db.Column(db.Enum(LoaiLogEnum), default=LoaiLogEnum.info)
    noi_dung = db.Column(db.Text, nullable=False)
    id_nguoi_dung = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=True)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=func.current_timestamp())


# ============================================
# HÀM KHỞI TẠO DỮ LIỆU MẪU (CHO LỆNH CLI)
# ============================================

def khoi_tao_du_lieu_mau():
    """Hàm này sẽ được gọi bởi lệnh 'flask seed-db' để tạo dữ liệu ban đầu."""
    
    if NguoiDung.query.first():
        print("CSDL đã có dữ liệu. Bỏ qua việc tạo dữ liệu mẫu.")
        return

    print("Đang xóa dữ liệu cũ (nếu có) và tạo dữ liệu mẫu...")
    
    db.session.execute(text('SET FOREIGN_KEY_CHECKS = 0;')) # Đã sửa
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.execute(text('SET FOREIGN_KEY_CHECKS = 1;')) # Đã sửa

    admin = NguoiDung(
        ten_dang_nhap='admin', ho_ten='Quản trị viên', vai_tro=VaiTroEnum.admin,
        email='admin@demthuoc.com', so_dien_thoai='0901234567'
    )
    admin.set_password('admin123')
    
    duoc_si = NguoiDung(
        ten_dang_nhap='duocsi', ho_ten='Nguyễn Thị An', vai_tro=VaiTroEnum.pharmacist,
        email='duocsi@demthuoc.com', so_dien_thoai='0912345678', ca_lam_viec=CaLamViecEnum.fulltime
    )
    duoc_si.set_password('duocsi123')
    db.session.add_all([admin, duoc_si])
    
    thiet_bi = ThietBi(id=1, trang_thai=TrangThaiThietBiEnum.online)
    db.session.add(thiet_bi)
    
    thuoc_list_data = [
        {'ten_thuoc': 'Paracetamol 500mg', 'ma_thuoc': 'PARA500', 'ton_kho_uoc_tinh': 1250, 'nguong_canh_bao': 500},
        {'ten_thuoc': 'Amoxicillin 250mg', 'ma_thuoc': 'AMOX250', 'ton_kho_uoc_tinh': 380, 'nguong_canh_bao': 500},
        {'ten_thuoc': 'Vitamin C 100mg', 'ma_thuoc': 'VITC100', 'ton_kho_uoc_tinh': 850, 'nguong_canh_bao': 300},
    ]
    for data in thuoc_list_data:
        db.session.add(LoaiThuoc(**data))
    
    db.session.commit()
    print("✅ Đã tạo tài khoản, thiết bị, và thuốc mẫu.")

    tb = ThongBao(
        id_nguoi_dung=duoc_si.id, loai=LoaiThongBaoEnum.info, tieu_de="Chào mừng đến với hệ thống",
        noi_dung="Hãy bắt đầu công việc bằng cách tạo một đơn thuốc mới!"
    )
    db.session.add(tb)
    
    log = NhatKyHeThong(
        loai_log=LoaiLogEnum.info, noi_dung='Hệ thống đã khởi tạo dữ liệu mẫu thành công.'
    )
    db.session.add(log)

    db.session.commit()
    print("✅ Đã tạo thông báo và log mẫu. Quá trình khởi tạo hoàn tất!")