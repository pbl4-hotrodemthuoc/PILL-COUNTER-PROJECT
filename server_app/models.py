# File: server_app/models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.mysql import JSON # Cần import JSON để sử dụng
import enum
import datetime

db = SQLAlchemy()

# --- Định nghĩa các ENUM để khớp với CSDL ---
class VaiTroEnum(enum.Enum):
    admin = 'admin'
    pharmacist = 'pharmacist'

class TrangThaiThietBiEnum(enum.Enum):
    online = 'online'
    offline = 'offline'

class TrangThaiDonEnum(enum.Enum):
    pending = 'pending'
    counting = 'counting'
    completed = 'completed'
    error = 'error'

class TrangThaiKhopDonEnum(enum.Enum):
    perfect = 'perfect'
    partial = 'partial'
    mismatch = 'mismatch'
    
class TrangThaiKhopChiTietEnum(enum.Enum):
    match = 'match'
    over = 'over'
    under = 'under'
    missing = 'missing'

class LoaiSuCoEnum(enum.Enum):
    drug_defect = 'drug_defect'
    device_error = 'device_error'
    ai_error = 'ai_error'
    other = 'other'

class TrangThaiSuCoEnum(enum.Enum):
    pending = 'pending'
    reviewing = 'reviewing'
    resolved = 'resolved'
    rejected = 'rejected'

class LoaiThongBaoEnum(enum.Enum):
    info = 'info'
    warning = 'warning'
    error = 'error'
    success = 'success'

class LoaiLogEnum(enum.Enum):
    info = 'info'
    warning = 'warning'
    error = 'error'

# ============================================
# MODEL 1: NGƯỜI DÙNG
# ============================================
class NguoiDung(UserMixin, db.Model):
    __tablename__ = 'nguoi_dung'
    id = db.Column(db.Integer, primary_key=True)
    ten_dang_nhap = db.Column(db.String(100), unique=True, nullable=False)
    mat_khau = db.Column(db.String(255), nullable=False)
    ho_ten = db.Column(db.String(200), nullable=False)
    vai_tro = db.Column(db.Enum(VaiTroEnum), nullable=False, default=VaiTroEnum.pharmacist)
    so_dien_thoai = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    ca_lam_viec = db.Column(db.String(50), nullable=True)
    dang_hoat_dong = db.Column(db.Boolean, nullable=False, default=True)
    dang_trong_ca = db.Column(db.Boolean, nullable=False, default=False)
    tong_don_da_xu_ly = db.Column(db.Integer, default=0)
    tong_vien_da_dem = db.Column(db.Integer, default=0)
    thoi_gian_xu_ly_tb = db.Column(db.DECIMAL(5, 2), nullable=True)
    ty_le_chinh_xac = db.Column(db.DECIMAL(5, 2), nullable=True)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    lan_dang_nhap_cuoi = db.Column(db.TIMESTAMP, nullable=True)

    # --- CẬP NHẬT MỐI QUAN HỆ ---
    cac_don_thuoc = db.relationship('DonThuoc', backref='duoc_si', cascade="all, delete-orphan")
    cac_bao_cao = db.relationship('BaoCaoSuCo', backref='nguoi_bao_cao', cascade="all, delete-orphan")
    cac_thong_bao = db.relationship('ThongBao', backref='nguoi_dung', cascade="all, delete-orphan")
    cac_nhat_ky = db.relationship('NhatKyHeThong', backref='nguoi_thuc_hien', cascade="all, delete-orphan")

    def set_password(self, password): self.mat_khau = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.mat_khau, password)

# ============================================
# MODEL 2: LOẠI THUỐC
# ============================================
class LoaiThuoc(db.Model):
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
    ngay_tao = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    ngay_cap_nhat = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

# ============================================
# --- MỚI: MODEL 3: THIẾT BỊ ---
# ============================================
class ThietBi(db.Model):
    __tablename__ = 'thiet_bi'
    id = db.Column(db.Integer, primary_key=True)
    ma_thiet_bi = db.Column(db.String(100), nullable=False, default='Pi-01')
    ten_thiet_bi = db.Column(db.String(200), default='Thiết bị đếm thuốc')
    trang_thai = db.Column(db.Enum(TrangThaiThietBiEnum), default=TrangThaiThietBiEnum.offline)
    lan_ket_noi_cuoi = db.Column(db.TIMESTAMP, nullable=True)
    tong_don_da_dem = db.Column(db.Integer, default=0)

# ============================================
# MODEL 4: ĐƠN THUỐC
# ============================================
class DonThuoc(db.Model):
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
    ngay_tao = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    
    chi_tiet_don = db.relationship('ChiTietDonThuoc', backref='don_thuoc', cascade="all, delete-orphan")
    cac_bao_cao = db.relationship('BaoCaoSuCo', backref='don_thuoc', cascade="all, delete-orphan")

# ============================================
# MODEL 5: CHI TIẾT ĐƠN THUỐC
# ============================================
class ChiTietDonThuoc(db.Model):
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
    ngay_tao = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    loai_thuoc_info = db.relationship('LoaiThuoc')

# ============================================
# --- MỚI: MODEL 6: BÁO CÁO SỰ CỐ ---
# ============================================
class BaoCaoSuCo(db.Model):
    __tablename__ = 'bao_cao_su_co'
    id = db.Column(db.Integer, primary_key=True)
    id_nguoi_bao_cao = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=False)
    loai_su_co = db.Column(db.Enum(LoaiSuCoEnum), nullable=False)
    id_don_thuoc = db.Column(db.Integer, db.ForeignKey('don_thuoc.id'), nullable=True)
    mo_ta = db.Column(db.Text, nullable=False)
    url_hinh_anh = db.Column(db.String(500), nullable=True)
    trang_thai = db.Column(db.Enum(TrangThaiSuCoEnum), default=TrangThaiSuCoEnum.pending)
    phan_hoi_admin = db.Column(db.Text, nullable=True)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    ngay_xu_ly = db.Column(db.TIMESTAMP, nullable=True)

# ============================================
# --- MỚI: MODEL 7: THÔNG BÁO ---
# ============================================
class ThongBao(db.Model):
    __tablename__ = 'thong_bao'
    id = db.Column(db.Integer, primary_key=True)
    id_nguoi_dung = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=False)
    loai = db.Column(db.Enum(LoaiThongBaoEnum), default=LoaiThongBaoEnum.info)
    tieu_de = db.Column(db.String(255), nullable=False)
    noi_dung = db.Column(db.Text, nullable=False)
    da_doc = db.Column(db.Boolean, default=False)
    thoi_gian_doc = db.Column(db.TIMESTAMP, nullable=True)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

# ============================================
# --- MỚI: MODEL 8: NHẬT KÝ HỆ THỐNG ---
# ============================================
class NhatKyHeThong(db.Model):
    __tablename__ = 'nhat_ky_he_thong'
    id = db.Column(db.Integer, primary_key=True)
    loai_log = db.Column(db.Enum(LoaiLogEnum), default=LoaiLogEnum.info)
    noi_dung = db.Column(db.Text, nullable=False)
    id_nguoi_dung = db.Column(db.Integer, db.ForeignKey('nguoi_dung.id'), nullable=True)
    ngay_tao = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())