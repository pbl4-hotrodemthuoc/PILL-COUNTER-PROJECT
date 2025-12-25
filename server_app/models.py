# File: server_app/models.py
# Phiên bản hoàn thiện, kết hợp cấu trúc CSDL đầy đủ và các hàm logic nghiệp vụ.

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, text
from .extensions import db 
import enum
import datetime
from .extensions import db

# Khởi tạo đối tượng SQLAlchemy để các model có thể kế thừa
#db = SQLAlchemy()

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
    ten_benh_nhan = db.Column(db.String(100), nullable=True)
    thoi_gian_bat_dau = db.Column(db.DateTime, nullable=True)
    thoi_gian_ket_thuc = db.Column(db.DateTime, nullable=True)
    thoi_gian_xu_ly_ms = db.Column(db.BigInteger, nullable=True)  # Thời gian xử lý (mili giây)
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
    trang_thai_khop = db.Column(db.Enum(TrangThaiKhopChiTietEnum), nullable=True) # Khớp/Thừa/Thiếu
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
    """Hàm này sẽ được gọi bởi lệnh 'flask seed-db' để tạo dữ liệu ban đầu đa dạng và thực tế."""
    
    if NguoiDung.query.first():
        print("CSDL đã có dữ liệu. Bỏ qua việc tạo dữ liệu mẫu.")
        return

    print("Đang xóa dữ liệu cũ và tạo dữ liệu mẫu...")
    
    db.session.execute(text('SET FOREIGN_KEY_CHECKS = 0;'))
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.execute(text('SET FOREIGN_KEY_CHECKS = 1;'))

    # ============================================
    # TẠO NGƯỜI DÙNG (1 ADMIN + 5 DƯỢC SĨ)
    # ============================================
    admin = NguoiDung(
        ten_dang_nhap='admin', ho_ten='Quản trị viên', vai_tro=VaiTroEnum.admin,
        email='admin@demthuoc.com', so_dien_thoai='0901234567', gioi_tinh=GioiTinhEnum.male
    )
    admin.set_password('admin123')
    
    # SỬA LỖI LOGIC: Tách riêng các trường thống kê để tránh lỗi khi dùng **
    duoc_si_list_data = [
        {'ten_dang_nhap': 'duocsi1', 'ho_ten': 'Nguyễn Thị An', 'email': 'nguyenthian@demthuoc.com', 'so_dien_thoai': '0912345678', 'ca_lam_viec': CaLamViecEnum.morning, 'gioi_tinh': GioiTinhEnum.female},
        {'ten_dang_nhap': 'duocsi2', 'ho_ten': 'Trần Văn Bình', 'email': 'tranvanbinh@demthuoc.com', 'so_dien_thoai': '0923456789', 'ca_lam_viec': CaLamViecEnum.afternoon, 'gioi_tinh': GioiTinhEnum.male},
        {'ten_dang_nhap': 'duocsi3', 'ho_ten': 'Lê Thị Cẩm', 'email': 'lethicam@demthuoc.com', 'so_dien_thoai': '0934567890', 'ca_lam_viec': CaLamViecEnum.evening, 'gioi_tinh': GioiTinhEnum.female},
        {'ten_dang_nhap': 'duocsi4', 'ho_ten': 'Phạm Minh Đức', 'email': 'phamminhduc@demthuoc.com', 'so_dien_thoai': '0945678901', 'ca_lam_viec': CaLamViecEnum.fulltime, 'gioi_tinh': GioiTinhEnum.male},
        {'ten_dang_nhap': 'duocsi5', 'ho_ten': 'Võ Thị Em', 'email': 'vothiem@demthuoc.com', 'so_dien_thoai': '0956789012', 'ca_lam_viec': CaLamViecEnum.morning, 'gioi_tinh': GioiTinhEnum.female}
    ]
    
    danh_sach_duoc_si_obj = []
    for data in duoc_si_list_data:
        ds = NguoiDung(
            ten_dang_nhap=data['ten_dang_nhap'], ho_ten=data['ho_ten'], email=data['email'],
            so_dien_thoai=data['so_dien_thoai'], ca_lam_viec=data['ca_lam_viec'], 
            gioi_tinh=data['gioi_tinh'], vai_tro=VaiTroEnum.pharmacist
        )
        ds.set_password('duocsi123')
        danh_sach_duoc_si_obj.append(ds)
    
    db.session.add(admin)
    db.session.add_all(danh_sach_duoc_si_obj)
    db.session.flush() # Gửi các thay đổi đến DB để lấy ID
    # ============================================
    # TẠO THIẾT BỊ
    # ============================================
    thiet_bi = ThietBi(
        id=1, 
        ma_thiet_bi='Pi-01',
        ten_thiet_bi='Thiết bị đếm thuốc chính',
        trang_thai=TrangThaiThietBiEnum.online,
        tong_don_da_dem=576
    )
    db.session.add(thiet_bi)
    
    # ============================================
    # TẠO LOẠI THUỐC (13 LOẠI)
    # ============================================
    thuoc_list_data = [
        {'ten_thuoc': 'Paracetamol 500mg', 'ma_thuoc': 'PARA500', 'ton_kho_uoc_tinh': 1250, 'nguong_canh_bao': 500, 'tong_luong_da_dem': 3450, 'so_lan_duoc_dem': 125},
        {'ten_thuoc': 'Amoxicillin 250mg', 'ma_thuoc': 'AMOX250', 'ton_kho_uoc_tinh': 380, 'nguong_canh_bao': 500, 'tong_luong_da_dem': 1890, 'so_lan_duoc_dem': 78},
        {'ten_thuoc': 'Vitamin C 100mg', 'ma_thuoc': 'VITC100', 'ton_kho_uoc_tinh': 850, 'nguong_canh_bao': 300, 'tong_luong_da_dem': 2340, 'so_lan_duoc_dem': 98},
        {'ten_thuoc': 'Ibuprofen 400mg', 'ma_thuoc': 'IBU400', 'ton_kho_uoc_tinh': 620, 'nguong_canh_bao': 400, 'tong_luong_da_dem': 1560, 'so_lan_duoc_dem': 65},
        {'ten_thuoc': 'Aspirin 100mg', 'ma_thuoc': 'ASP100', 'ton_kho_uoc_tinh': 920, 'nguong_canh_bao': 600, 'tong_luong_da_dem': 2780, 'so_lan_duoc_dem': 115},
        {'ten_thuoc': 'Omeprazole 20mg', 'ma_thuoc': 'OME20', 'ton_kho_uoc_tinh': 540, 'nguong_canh_bao': 300, 'tong_luong_da_dem': 1340, 'so_lan_duoc_dem': 56},
        {'ten_thuoc': 'Cetirizine 10mg', 'ma_thuoc': 'CETI10', 'ton_kho_uoc_tinh': 730, 'nguong_canh_bao': 400, 'tong_luong_da_dem': 1820, 'so_lan_duoc_dem': 73},
        {'ten_thuoc': 'Metformin 500mg', 'ma_thuoc': 'MET500', 'ton_kho_uoc_tinh': 1100, 'nguong_canh_bao': 700, 'tong_luong_da_dem': 3120, 'so_lan_duoc_dem': 134},
        {'ten_thuoc': 'Losartan 50mg', 'ma_thuoc': 'LOS50', 'ton_kho_uoc_tinh': 460, 'nguong_canh_bao': 300, 'tong_luong_da_dem': 980, 'so_lan_duoc_dem': 42},
        {'ten_thuoc': 'Atorvastatin 20mg', 'ma_thuoc': 'ATO20', 'ton_kho_uoc_tinh': 680, 'nguong_canh_bao': 400, 'tong_luong_da_dem': 1450, 'so_lan_duoc_dem': 61},
        {'ten_thuoc': 'Amlodipine 5mg', 'ma_thuoc': 'AML5', 'ton_kho_uoc_tinh': 870, 'nguong_canh_bao': 500, 'tong_luong_da_dem': 2240, 'so_lan_duoc_dem': 89},
        {'ten_thuoc': 'Clopidogrel 75mg', 'ma_thuoc': 'CLO75', 'ton_kho_uoc_tinh': 320, 'nguong_canh_bao': 250, 'tong_luong_da_dem': 780, 'so_lan_duoc_dem': 34},
        {'ten_thuoc': 'Vitamin D3 1000IU', 'ma_thuoc': 'VITD1000', 'ton_kho_uoc_tinh': 950, 'nguong_canh_bao': 400, 'tong_luong_da_dem': 2560, 'so_lan_duoc_dem': 102}
    ]
    
    danh_sach_thuoc = []
    for thuoc_data in thuoc_list_data:
        danh_sach_thuoc.append(LoaiThuoc(**thuoc_data))
    db.session.add_all(danh_sach_thuoc)
    
    db.session.commit()
    print("✅ Đã tạo 1 admin, 5 dược sĩ, 1 thiết bị, và 13 loại thuốc.")

    # ============================================
    # TẠO ĐơN THUỐC (10 ĐƠN)
    # ============================================
    don_thuoc_list = []
    import random
    from datetime import datetime, timedelta
    
    trang_thai_don_choices = [TrangThaiDonEnum.completed] * 7 + [TrangThaiDonEnum.error] * 2 + [TrangThaiDonEnum.pending]
    trang_thai_khop_choices = [TrangThaiKhopDonEnum.perfect] * 5 + [TrangThaiKhopDonEnum.partial] * 3 + [TrangThaiKhopDonEnum.mismatch] * 2
    
    for i in range(1, 11):
        thoi_gian_tao = datetime.utcnow() - timedelta(days=random.randint(1, 30))
        trang_thai = random.choice(trang_thai_don_choices)
        
        don = DonThuoc(
            ma_don_thuoc=f'DT{datetime.now().year}{i:04d}',
            id_duoc_si=random.choice(danh_sach_duoc_si).id,
            id_thiet_bi=1,
            thoi_gian_tao_don=thoi_gian_tao,
            thoi_gian_bat_dau=thoi_gian_tao + timedelta(minutes=2) if trang_thai != TrangThaiDonEnum.pending else None,
            thoi_gian_ket_thuc=thoi_gian_tao + timedelta(minutes=random.randint(5, 15)) if trang_thai == TrangThaiDonEnum.completed else None,
            thoi_gian_xu_ly_ms=random.randint(180000, 900000) if trang_thai == TrangThaiDonEnum.completed else None,  # Random 3-15 phút in ms
            tong_so_loai_thuoc=random.randint(2, 5),
            tong_vien_yeu_cau=random.randint(50, 200),
            tong_vien_dem_duoc=random.randint(48, 200) if trang_thai != TrangThaiDonEnum.pending else 0,
            trang_thai_don=trang_thai,
            trang_thai_khop=random.choice(trang_thai_khop_choices) if trang_thai == TrangThaiDonEnum.completed else None,
            ghi_chu_duoc_si=f'Ghi chú đơn {i}' if random.random() > 0.5 else None
        )
        don_thuoc_list.append(don)
    
    db.session.add_all(don_thuoc_list)
    db.session.commit()
    print("✅ Đã tạo 10 đơn thuốc mẫu.")

    # ============================================
    # TẠO CHI TIẾT ĐƠN THUỐC (MỖI ĐƠN 2-5 LOẠI THUỐC)
    # ============================================
    chi_tiet_list = []
    trang_thai_khop_ct = [TrangThaiKhopChiTietEnum.match] * 6 + [TrangThaiKhopChiTietEnum.over, TrangThaiKhopChiTietEnum.under] * 2
    
    for don in don_thuoc_list:
        so_loai = random.randint(2, 5)
        cac_thuoc = random.sample(danh_sach_thuoc, so_loai)
        
        for thuoc in cac_thuoc:
            sl_yeu_cau = random.randint(10, 50)
            trang_thai_khop_item = random.choice(trang_thai_khop_ct)
            
            if trang_thai_khop_item == TrangThaiKhopChiTietEnum.match:
                sl_dem = sl_yeu_cau
                chenh_lech = 0
            elif trang_thai_khop_item == TrangThaiKhopChiTietEnum.over:
                sl_dem = sl_yeu_cau + random.randint(1, 3)
                chenh_lech = sl_dem - sl_yeu_cau
            else:
                sl_dem = sl_yeu_cau - random.randint(1, 3)
                chenh_lech = sl_dem - sl_yeu_cau
            
            chi_tiet = ChiTietDonThuoc(
                id_don_thuoc=don.id,
                id_loai_thuoc=thuoc.id,
                so_luong_yeu_cau=sl_yeu_cau,
                so_luong_dem_duoc=sl_dem if don.trang_thai_don != TrangThaiDonEnum.pending else None,
                do_tin_cay=round(random.uniform(95.0, 99.9), 2) if don.trang_thai_don == TrangThaiDonEnum.completed else None,
                thoi_gian_nhan_dien_ms=random.randint(1200, 3500) if don.trang_thai_don == TrangThaiDonEnum.completed else None,
                trang_thai_khop=trang_thai_khop_item if don.trang_thai_don == TrangThaiDonEnum.completed else None,
                chenh_lech=chenh_lech if don.trang_thai_don == TrangThaiDonEnum.completed else None
            )
            chi_tiet_list.append(chi_tiet)
    
    db.session.add_all(chi_tiet_list)
    db.session.commit()
    print("✅ Đã tạo chi tiết cho các đơn thuốc.")

    # ============================================
    # TẠO BÁO CÁO SỰ CỐ (10 BÁO CÁO)
    # ============================================
    bao_cao_list = []
    loai_su_co_choices = [LoaiSuCoEnum.drug_defect, LoaiSuCoEnum.device_error, LoaiSuCoEnum.other]
    trang_thai_su_co_choices = [TrangThaiSuCoEnum.resolved] * 5 + [TrangThaiSuCoEnum.reviewing] * 3 + [TrangThaiSuCoEnum.pending] * 2
    
    for i in range(10):
        loai = random.choice(loai_su_co_choices)
        trang_thai_sc = random.choice(trang_thai_su_co_choices)
        
        mo_ta_map = {
            LoaiSuCoEnum.drug_defect: f'Phát hiện viên thuốc bị vỡ/méo trong lô {random.randint(1000, 9999)}',
            LoaiSuCoEnum.device_error: f'Thiết bị gặp lỗi kết nối hoặc camera không hoạt động',
            LoaiSuCoEnum.other: f'Vấn đề khác: {random.choice(["Lỗi phần mềm", "Sự cố điện", "Cần bảo trì"])}'
        }
        
        bao_cao = BaoCaoSuCo(
            id_nguoi_bao_cao=random.choice(danh_sach_duoc_si).id,
            loai_su_co=loai,
            id_don_thuoc=random.choice(don_thuoc_list).id if random.random() > 0.3 else None,
            mo_ta=mo_ta_map[loai],
            trang_thai=trang_thai_sc,
            phan_hoi_admin=f'Đã xử lý sự cố {i+1}' if trang_thai_sc == TrangThaiSuCoEnum.resolved else None,
            ngay_xu_ly=datetime.utcnow() - timedelta(days=random.randint(1, 5)) if trang_thai_sc == TrangThaiSuCoEnum.resolved else None
        )
        bao_cao_list.append(bao_cao)
    
    db.session.add_all(bao_cao_list)
    db.session.commit()
    print("✅ Đã tạo 10 báo cáo sự cố.")

    # ============================================
    # TẠO THÔNG BÁO (10 THÔNG BÁO)
    # ============================================
    thong_bao_list = []
    loai_tb_choices = [LoaiThongBaoEnum.info, LoaiThongBaoEnum.warning, LoaiThongBaoEnum.error, LoaiThongBaoEnum.success]
    
    noi_dung_map = {
        LoaiThongBaoEnum.info: [
            'Hệ thống đã cập nhật phiên bản mới',
            'Lịch bảo trì định kỳ vào cuối tuần',
            'Đã thêm tính năng xuất báo cáo Excel'
        ],
        LoaiThongBaoEnum.warning: [
            'Tồn kho thuốc Paracetamol sắp hết, cần nhập thêm',
            'Thiết bị cần được hiệu chuẩn lại',
            'Có 3 đơn thuốc cần xử lý khẩn cấp'
        ],
        LoaiThongBaoEnum.error: [
            'Lỗi kết nối với thiết bị đếm thuốc',
            'Không thể tải dữ liệu đơn thuốc',
            'Hệ thống gặp sự cố nghiêm trọng'
        ],
        LoaiThongBaoEnum.success: [
            'Đã hoàn thành đơn thuốc DT20240055 thành công',
            'Báo cáo tháng đã được gửi đi',
            'Đồng bộ dữ liệu thành công'
        ]
    }
    
    for i in range(10):
        loai_tb = random.choice(loai_tb_choices)
        noi_dung = random.choice(noi_dung_map[loai_tb])
        da_doc = random.random() > 0.4
        
        thong_bao = ThongBao(
            id_nguoi_dung=random.choice(danh_sach_duoc_si + [admin]).id,
            loai=loai_tb,
            tieu_de=f'Thông báo {loai_tb.value} #{i+1}',
            noi_dung=noi_dung,
            da_doc=da_doc,
            thoi_gian_doc=datetime.utcnow() - timedelta(hours=random.randint(1, 48)) if da_doc else None,
            ngay_tao=datetime.utcnow() - timedelta(days=random.randint(0, 7))
        )
        thong_bao_list.append(thong_bao)
    
    db.session.add_all(thong_bao_list)
    db.session.commit()
    print("✅ Đã tạo 10 thông báo.")

    # ============================================
    # TẠO NHẬT KÝ HỆ THỐNG (10 LOG)
    # ============================================
    log_list = []
    loai_log_choices = [LoaiLogEnum.info, LoaiLogEnum.warning, LoaiLogEnum.error]
    
    noi_dung_log = {
        LoaiLogEnum.info: [
            'Người dùng đăng nhập thành công',
            'Tạo đơn thuốc mới',
            'Cập nhật thông tin thuốc',
            'Xuất báo cáo thống kê',
            'Đồng bộ dữ liệu với thiết bị'
        ],
        LoaiLogEnum.warning: [
            'Thời gian xử lý đơn vượt quá ngưỡng',
            'Phát hiện sai lệch trong kết quả đếm',
            'Kết nối không ổn định với thiết bị'
        ],
        LoaiLogEnum.error: [
            'Lỗi khi kết nối cơ sở dữ liệu',
            'Thiết bị không phản hồi',
            'Lỗi xử lý hình ảnh từ camera'
        ]
    }
    
    for i in range(10):
        loai_log = random.choice(loai_log_choices)
        
        log = NhatKyHeThong(
            loai_log=loai_log,
            noi_dung=random.choice(noi_dung_log[loai_log]),
            id_nguoi_dung=random.choice(danh_sach_duoc_si + [admin]).id if random.random() > 0.2 else None,
            ngay_tao=datetime.utcnow() - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))
        )
        log_list.append(log)
    
    db.session.add_all(log_list)
    db.session.commit()
    print("✅ Đã tạo 10 nhật ký hệ thống.")

    print("\n" + "="*60)
    print("🎉 HOÀN TẤT KHỞI TẠO DỮ LIỆU MẪU!")
    print("="*60)
    print(f"✓ 1 Admin + 5 Dược sĩ")
    print(f"✓ 13 Loại thuốc")
    print(f"✓ 10 Đơn thuốc + Chi tiết")
    print(f"✓ 10 Báo cáo sự cố")
    print(f"✓ 10 Thông báo")
    print(f"✓ 10 Nhật ký hệ thống")
    print("="*60)