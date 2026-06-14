"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : models/nguoi_lx_model.py
Mô tả     : Model dữ liệu hồ sơ người lái xe
            - Dataclass đại diện bản ghi NguoiLX_HoSo
            - Validate dữ liệu
            - Chuyển đổi dict ↔ object
            - Hỗ trợ QTableView thông qua QAbstractTableModel
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields
from datetime    import date, datetime
from typing      import Any, Optional

from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Signal,
)


# ══════════════════════════════════════════════════════════
#  DATACLASS: HỒ SƠ NGƯỜI LÁI XE
# ══════════════════════════════════════════════════════════

@dataclass
class NguoiLX:
    """
    Đại diện 1 bản ghi trong bảng NguoiLX_HoSo.

    Tất cả field đều optional (cho phép khởi tạo rỗng).
    Tên field khớp 100% tên cột trong SQLite.
    """
    SO_TT               : Optional[int]  = None
    MA_DK                : Optional[str]  = None
    HO_TEN_DEM           : Optional[str]  = None
    TEN                  : Optional[str]  = None
    HO_VA_TEN            : Optional[str]  = None
    GIOI_TINH            : Optional[str]  = None
    NGAY_SINH            : Optional[str]  = None  # "YYYY-MM-DD"
    MA_QUOC_TICH         : Optional[str]  = None
    NOI_CT               : Optional[str]  = None
    NOI_CT_MA_DVHC       : Optional[str]  = None
    NOI_CT_MA_DVQL       : Optional[str]  = None
    SO_CMT               : Optional[str]  = None
    SO_HO_SO             : Optional[str]  = None
    MA_KY_SH             : Optional[str]  = None
    SO_BAO_DANH          : Optional[int]  = None
    MA_CSDT              : Optional[str]  = None
    MA_TTSH              : Optional[str]  = None
    MA_SO_GTVT           : Optional[str]  = None
    GIAY_CNSK            : Optional[str]  = None
    HANG_GPLX            : Optional[str]  = None
    SO_GPLX_DA_CO        : Optional[str]  = None
    HANG_GPLX_DA_CO      : Optional[str]  = None
    DVQL_GPLX_DACO       : Optional[str]  = None
    NGAY_HH_GPLX_DACO   : Optional[str]  = None
    SO_NAM_LAIXE         : Optional[int]  = None
    SO_KM_ANTOAN         : Optional[int]  = None
    SO_GIAY_CNTN         : Optional[str]  = None
    SO_CCN               : Optional[str]  = None
    NOI_DUNG_SH          : Optional[str]  = None
    LY_DO_SH             : Optional[str]  = None
    KET_QUA_SH           : Optional[str]  = None
    KQ_SH_LYTHUYET       : Optional[str]  = None
    KQ_SH_MOPHONG        : Optional[str]  = None
    KQ_SH_HINH           : Optional[str]  = None
    KQ_SH_DUONG          : Optional[str]  = None
    GHI_CHU_SH           : Optional[str]  = None
    ANH_CHAN_DUNG         : Optional[str]  = None
    NGAY_TT_GPLX_DACO   : Optional[str]  = None
    MA_KHOA_HOC          : Optional[str]  = None
    SO_QD_SH             : Optional[str]  = None
    NGAY_QD_SH           : Optional[str]  = None
    NGUOI_QD_SH          : Optional[str]  = None
    CHAT_LUONG_ANH       : Optional[str]  = None
    LYTHUYETKT           : Optional[str]  = None
    MOPHONGKT            : Optional[str]  = None
    HINHKT               : Optional[str]  = None
    DUONGKT              : Optional[str]  = None
    KETQUAKT             : Optional[str]  = None
    TAPHOSO              : Optional[str]  = None
    TRANGTHAI            : Optional[str]  = None

    # ──────────────────────────────────────────────────────
    #  CHUYỂN ĐỔI
    # ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        Chuyển object thành dict (key = tên cột SQLite).
        Loại bỏ các field có giá trị None.
        """
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_full_dict(self) -> dict:
        """Chuyển object thành dict bao gồm cả field None."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> NguoiLX:
        """
        Tạo instance từ dict.
        Chỉ lấy các key khớp tên field của dataclass.
        """
        valid_fields = {f.name for f in fields(cls)}
        filtered     = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def get_field_names(cls) -> list[str]:
        """Lấy danh sách tên tất cả field."""
        return [f.name for f in fields(cls)]

    # ──────────────────────────────────────────────────────
    #  VALIDATE
    # ──────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """
        Kiểm tra tính hợp lệ của dữ liệu.

        Returns
        -------
        list[str] danh sách lỗi, rỗng = hợp lệ
        """
        errors = []

        # SO_HO_SO bắt buộc (PRIMARY KEY)
        if not self.SO_HO_SO or not str(self.SO_HO_SO).strip():
            errors.append("Số hồ sơ (SO_HO_SO) không được để trống.")

        # HO_VA_TEN bắt buộc
        if not self.HO_VA_TEN or not str(self.HO_VA_TEN).strip():
            errors.append("Họ và tên (HO_VA_TEN) không được để trống.")

        # NGAY_SINH kiểm tra định dạng
        if self.NGAY_SINH:
            if not self._is_valid_date(self.NGAY_SINH):
                errors.append(
                    f"Ngày sinh '{self.NGAY_SINH}' không đúng định dạng "
                    f"(YYYY-MM-DD)."
                )
            else:
                # Kiểm tra tuổi hợp lý (15 - 100)
                age = self._calc_age(self.NGAY_SINH)
                if age is not None:
                    if age < 15:
                        errors.append(
                            f"Tuổi ({age}) phải từ 15 trở lên."
                        )
                    elif age > 100:
                        errors.append(
                            f"Tuổi ({age}) không hợp lý (> 100)."
                        )

        # SO_CMT (CCCD) kiểm tra format
        if self.SO_CMT:
            cmt = str(self.SO_CMT).strip()
            if not cmt.isdigit():
                errors.append("Số CCCD phải là số.")
            elif len(cmt) not in (9, 12):
                errors.append(
                    f"Số CCCD '{cmt}' phải có 9 hoặc 12 chữ số."
                )

        # HANG_GPLX kiểm tra giá trị hợp lệ
        valid_hang = {"A1", "A2", "A3", "A4", "B1", "B2", "C", "D", "E", "F", "FB2", "FC", "FD", "FE"}
        if self.HANG_GPLX:
            if self.HANG_GPLX.upper() not in valid_hang:
                errors.append(
                    f"Hạng GPLX '{self.HANG_GPLX}' không hợp lệ. "
                    f"Hợp lệ: {', '.join(sorted(valid_hang))}"
                )

        # GIOI_TINH
        if self.GIOI_TINH:
            if self.GIOI_TINH not in ("Nam", "Nữ", "Khác", "nam", "nữ", "khác"):
                errors.append(
                    f"Giới tính '{self.GIOI_TINH}' không hợp lệ "
                    f"(Nam/Nữ/Khác)."
                )

        # SO_BAO_DANH phải > 0
        if self.SO_BAO_DANH is not None:
            if not isinstance(self.SO_BAO_DANH, int) or self.SO_BAO_DANH < 0:
                errors.append("Số báo danh phải là số nguyên >= 0.")

        # NGAY_QD_SH kiểm tra định dạng
        if self.NGAY_QD_SH:
            if not self._is_valid_date(self.NGAY_QD_SH):
                errors.append(
                    f"Ngày QĐ sát hạch '{self.NGAY_QD_SH}' không đúng "
                    f"định dạng (YYYY-MM-DD)."
                )

        # NGAY_HH_GPLX_DACO kiểm tra định dạng
        if self.NGAY_HH_GPLX_DACO:
            if not self._is_valid_date(self.NGAY_HH_GPLX_DACO):
                errors.append(
                    f"Ngày hết hạn GPLX '{self.NGAY_HH_GPLX_DACO}' "
                    f"không đúng định dạng."
                )

        return errors

    # ──────────────────────────────────────────────────────
    #  TIỆN ÍCH
    # ──────────────────────────────────────────────────────

    def get_display_name(self) -> str:
        """Lấy tên hiển thị: HO_VA_TEN hoặc ghép HO_TEN_DEM + TEN."""
        if self.HO_VA_TEN:
            return self.HO_VA_TEN.strip()
        parts = []
        if self.HO_TEN_DEM:
            parts.append(self.HO_TEN_DEM.strip())
        if self.TEN:
            parts.append(self.TEN.strip())
        return " ".join(parts)

    def get_ngay_sinh_display(self) -> str:
        """Chuyển NGAY_SINH sang DD/MM/YYYY để hiển thị."""
        if not self.NGAY_SINH:
            return ""
        try:
            dt = datetime.strptime(str(self.NGAY_SINH)[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(self.NGAY_SINH)

    def get_ket_qua_display(self) -> str:
        """Hiển thị kết quả sát hạch dạng tóm tắt."""
        parts = []
        if self.KQ_SH_LYTHUYET:
            parts.append(f"LT:{self.KQ_SH_LYTHUYET}")
        if self.KQ_SH_MOPHONG:
            parts.append(f"MP:{self.KQ_SH_MOPHONG}")
        if self.KQ_SH_HINH:
            parts.append(f"H:{self.KQ_SH_HINH}")
        if self.KQ_SH_DUONG:
            parts.append(f"Đ:{self.KQ_SH_DUONG}")
        return " | ".join(parts) if parts else ""

    # ──────────────────────────────────────────────────────
    #  PRIVATE HELPERS
    # ──────────────────────────────────────────────────────

    @staticmethod
    def _is_valid_date(value: str) -> bool:
        """Kiểm tra chuỗi có đúng format YYYY-MM-DD không."""
        try:
            datetime.strptime(str(value)[:10], "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _calc_age(date_str: str) -> Optional[int]:
        """Tính tuổi từ ngày sinh (YYYY-MM-DD)."""
        try:
            born  = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
            today = date.today()
            age   = today.year - born.year
            if (today.month, today.day) < (born.month, born.day):
                age -= 1
            return age
        except (ValueError, TypeError):
            return None

    def __repr__(self) -> str:
        return (
            f"NguoiLX(SO_HO_SO='{self.SO_HO_SO}', "
            f"HO_VA_TEN='{self.HO_VA_TEN}', "
            f"HANG_GPLX='{self.HANG_GPLX}')"
        )


# ══════════════════════════════════════════════════════════
#  CÁC CỘT HIỂN THỊ TRÊN TABLE VIEW
# ══════════════════════════════════════════════════════════

# Mỗi tuple = (field_name, header_label, width)
DISPLAY_COLUMNS: list[tuple[str, str, int]] = [
    ("SO_TT",          "STT",            50),
    ("MA_DK",          "Mã đăng ký",    120),
    ("HO_VA_TEN",      "Họ và tên",     200),
    ("NGAY_SINH",      "Ngày sinh",     100),
    ("SO_CMT",         "CCCD",          130),
    ("HANG_GPLX",      "Hạng GPLX",     80),
    ("SO_BAO_DANH",    "Số báo danh",   100),
    ("KET_QUA_SH",     "Kết quả",       100),
    ("TRANGTHAI",      "Trạng thái",    100),
]


# ══════════════════════════════════════════════════════════
#  QT TABLE MODEL
# ══════════════════════════════════════════════════════════

class NguoiLXTableModel(QAbstractTableModel):
    """
    Model cung cấp dữ liệu cho QTableView.

    Tính năng:
    - Hiển thị các cột theo DISPLAY_COLUMNS
    - Tô màu theo trạng thái
    - Hỗ trợ sắp xếp (sort)
    - Signal thông báo khi dữ liệu thay đổi
    """

    # Signal phát ra khi dữ liệu được cập nhật
    data_changed_signal = Signal()

    # Bảng màu cho trạng thái
    STATUS_COLORS: dict[str, str] = {
        "MOI"        : "#2196F3",   # xanh dương
        "CHO_XU_LY" : "#FF9800",   # cam
        "DA_DUYET"   : "#4CAF50",   # xanh lá
        "DA_THI"     : "#9C27B0",   # tím
        "DAT"        : "#009688",   # xanh lục
        "KHONG_DAT"  : "#F44336",   # đỏ
        "HUY"        : "#607D8B",   # xám
        "TAM_HOAN"   : "#795548",   # nâu
    }

    def __init__(
        self,
        data    : list[NguoiLX] = None,
        columns : list[tuple[str, str, int]] = None,
        parent  = None
    ) -> None:
        """
        Parameters
        ----------
        data    : danh sách NguoiLX objects
        columns : cấu hình cột [(field, header, width), ...]
        """
        super().__init__(parent)
        self._data    : list[NguoiLX] = data or []
        self._columns : list[tuple[str, str, int]] = columns or DISPLAY_COLUMNS

    # ──────────────────────────────────────────────────────
    #  OVERRIDE QAbstractTableModel
    # ──────────────────────────────────────────────────────

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._data):
            return None
        if col < 0 or col >= len(self._columns):
            return None

        nguoi_lx   = self._data[row]
        field_name = self._columns[col][0]
        value      = getattr(nguoi_lx, field_name, None)

        # ── DisplayRole: giá trị hiển thị ─────────────────
        if role == Qt.DisplayRole:
            # Xử lý đặc biệt cho một số cột
            if field_name == "SO_TT":
                return row + 1  # STT tự động

            if field_name == "NGAY_SINH":
                return nguoi_lx.get_ngay_sinh_display()

            if value is None:
                return ""
            return str(value)

        # ── ForegroundRole: màu chữ theo trạng thái ───────
        if role == Qt.ForegroundRole:
            if field_name == "TRANGTHAI" and value:
                from PySide6.QtGui import QColor
                color_hex = self.STATUS_COLORS.get(str(value).upper(), None)
                if color_hex:
                    return QColor(color_hex)

        # ── BackgroundRole: tô nền nhạt cho dòng Đạt/Không đạt ──
        if role == Qt.BackgroundRole:
            trang_thai = getattr(nguoi_lx, "TRANGTHAI", "")
            if trang_thai:
                tt = str(trang_thai).upper()
                from PySide6.QtGui import QColor
                if tt == "DAT":
                    return QColor("#E8F5E9")   # xanh nhạt
                elif tt == "KHONG_DAT":
                    return QColor("#FFEBEE")   # đỏ nhạt

        # ── TextAlignmentRole ──────────────────────────────
        if role == Qt.TextAlignmentRole:
            if field_name in ("SO_TT", "SO_BAO_DANH"):
                return Qt.AlignCenter
            if field_name == "HANG_GPLX":
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        # ── ToolTipRole: tooltip chi tiết ──────────────────
        if role == Qt.ToolTipRole:
            parts = [
                f"Số hồ sơ: {nguoi_lx.SO_HO_SO or ''}",
                f"Họ tên: {nguoi_lx.get_display_name()}",
                f"CCCD: {nguoi_lx.SO_CMT or ''}",
                f"Hạng: {nguoi_lx.HANG_GPLX or ''}",
                f"Trạng thái: {nguoi_lx.TRANGTHAI or ''}",
            ]
            return "\n".join(parts)

        # ── UserRole: trả object gốc để truy xuất nhanh ───
        if role == Qt.UserRole:
            return nguoi_lx

        return None

    def headerData(
        self,
        section  : int,
        orientation: Qt.Orientation,
        role     : int = Qt.DisplayRole
    ) -> Any:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if 0 <= section < len(self._columns):
                    return self._columns[section][1]  # header label
            elif orientation == Qt.Vertical:
                return str(section + 1)
        return None

    # ──────────────────────────────────────────────────────
    #  PUBLIC API
    # ──────────────────────────────────────────────────────

    def set_data(self, data: list[NguoiLX]) -> None:
        """Thay đổi toàn bộ dữ liệu và refresh bảng."""
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()
        self.data_changed_signal.emit()

    def append_row(self, nguoi_lx: NguoiLX) -> None:
        """Thêm 1 dòng cuối bảng."""
        row = len(self._data)
        self.beginInsertRows(QModelIndex(), row, row)
        self._data.append(nguoi_lx)
        self.endInsertRows()
        self.data_changed_signal.emit()

    def remove_row(self, row: int) -> bool:
        """Xóa 1 dòng theo index."""
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._data.pop(row)
            self.endRemoveRows()
            self.data_changed_signal.emit()
            return True
        return False

    def update_row(self, row: int, nguoi_lx: NguoiLX) -> bool:
        """Cập nhật 1 dòng theo index."""
        if 0 <= row < len(self._data):
            self._data[row] = nguoi_lx
            left  = self.index(row, 0)
            right = self.index(row, self.columnCount() - 1)
            self.dataChanged.emit(left, right)
            self.data_changed_signal.emit()
            return True
        return False

    def get_item(self, row: int) -> Optional[NguoiLX]:
        """Lấy NguoiLX object theo index dòng."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def get_all_data(self) -> list[NguoiLX]:
        """Lấy toàn bộ dữ liệu."""
        return self._data.copy()

    def get_column_widths(self) -> list[int]:
        """Lấy danh sách độ rộng cột."""
        return [col[2] for col in self._columns]

    def find_by_so_ho_so(self, so_ho_so: str) -> Optional[int]:
        """
        Tìm index dòng theo SO_HO_SO.

        Returns
        -------
        row index hoặc None nếu không tìm thấy
        """
        for i, item in enumerate(self._data):
            if item.SO_HO_SO == so_ho_so:
                return i
        return None

    def clear(self) -> None:
        """Xóa toàn bộ dữ liệu."""
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()
        self.data_changed_signal.emit()


# ══════════════════════════════════════════════════════════
#  SORT / FILTER PROXY MODEL
# ══════════════════════════════════════════════════════════

class NguoiLXSortFilterModel(QSortFilterProxyModel):
    """
    Proxy model hỗ trợ:
    - Sắp xếp theo cột
    - Lọc theo nhiều tiêu chí
    - Tìm kiếm tức thời (filter text)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Bộ lọc
        self._filter_so_ho_so   : str = ""
        self._filter_ho_ten     : str = ""
        self._filter_cccd       : str = ""
        self._filter_hang_gplx  : str = ""
        self._filter_trang_thai : str = ""

        # Không phân biệt hoa thường
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)

    # ──────────────────────────────────────────────────────
    #  SET FILTER
    # ──────────────────────────────────────────────────────

    def set_filter_so_ho_so(self, value: str) -> None:
        self._filter_so_ho_so = value.strip().lower()
        self.invalidateFilter()

    def set_filter_ho_ten(self, value: str) -> None:
        self._filter_ho_ten = value.strip().lower()
        self.invalidateFilter()

    def set_filter_cccd(self, value: str) -> None:
        self._filter_cccd = value.strip().lower()
        self.invalidateFilter()

    def set_filter_hang_gplx(self, value: str) -> None:
        self._filter_hang_gplx = value.strip()
        self.invalidateFilter()

    def set_filter_trang_thai(self, value: str) -> None:
        self._filter_trang_thai = value.strip()
        self.invalidateFilter()

    def clear_all_filters(self) -> None:
        """Xóa toàn bộ bộ lọc."""
        self._filter_so_ho_so   = ""
        self._filter_ho_ten     = ""
        self._filter_cccd       = ""
        self._filter_hang_gplx  = ""
        self._filter_trang_thai = ""
        self.invalidateFilter()

    # ──────────────────────────────────────────────────────
    #  OVERRIDE filterAcceptsRow
    # ──────────────────────────────────────────────────────

    def filterAcceptsRow(
        self,
        source_row   : int,
        source_parent: QModelIndex
    ) -> bool:
        """
        Xác định 1 dòng có thỏa mãn tất cả bộ lọc không.
        Phải thỏa TẤT CẢ điều kiện (AND).
        """
        model = self.sourceModel()
        if not model:
            return True

        item = model.get_item(source_row)
        if not item:
            return True

        # Lọc số hồ sơ
        if self._filter_so_ho_so:
            val = str(item.SO_HO_SO or "").lower()
            if self._filter_so_ho_so not in val:
                return False

        # Lọc họ tên
        if self._filter_ho_ten:
            val = str(item.HO_VA_TEN or "").lower()
            if self._filter_ho_ten not in val:
                return False

        # Lọc CCCD
        if self._filter_cccd:
            val = str(item.SO_CMT or "").lower()
            if self._filter_cccd not in val:
                return False

        # Lọc hạng GPLX (so sánh chính xác)
        if self._filter_hang_gplx:
            val = str(item.HANG_GPLX or "")
            if val != self._filter_hang_gplx:
                return False

        # Lọc trạng thái (so sánh chính xác)
        if self._filter_trang_thai:
            val = str(item.TRANGTHAI or "")
            if val != self._filter_trang_thai:
                return False

        return True

    def lessThan(
        self,
        left : QModelIndex,
        right: QModelIndex
    ) -> bool:
        """Override sắp xếp tuỳ chỉnh cho cột số."""
        model = self.sourceModel()
        if not model:
            return False

        col_name = DISPLAY_COLUMNS[left.column()][0] if left.column() < len(DISPLAY_COLUMNS) else ""

        left_data  = model.data(left,  Qt.DisplayRole)
        right_data = model.data(right, Qt.DisplayRole)

        # Cột số: so sánh dạng số
        if col_name in ("SO_TT", "SO_BAO_DANH"):
            try:
                return int(left_data or 0) < int(right_data or 0)
            except (ValueError, TypeError):
                pass

        # Cột ngày: so sánh dạng ngày
        if col_name == "NGAY_SINH":
            try:
                l_date = datetime.strptime(str(left_data),  "%d/%m/%Y")
                r_date = datetime.strptime(str(right_data), "%d/%m/%Y")
                return l_date < r_date
            except (ValueError, TypeError):
                pass

        # Mặc định: so sánh chuỗi
        return str(left_data or "").lower() < str(right_data or "").lower()