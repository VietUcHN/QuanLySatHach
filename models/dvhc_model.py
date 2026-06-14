"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : models/dvhc_model.py
Mô tả     : Model dữ liệu Đơn vị hành chính (DVHC)
            - Dataclass đại diện bản ghi DM_DVHC
            - Validate dữ liệu
            - Chuyển đổi dict ↔ object
            - QAbstractTableModel cho QTableView
            - SortFilterProxyModel
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, fields
from typing      import Any, Optional

from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Signal,
)


# ══════════════════════════════════════════════════════════
#  HẰNG SỐ
# ══════════════════════════════════════════════════════════

# Các loại đơn vị hành chính hợp lệ
VALID_LOAI_DVHC: list[str] = [
    "Thành phố trực thuộc Trung ương",
    "Tỉnh",
    "Quận",
    "Huyện",
    "Thị xã",
    "Thành phố thuộc tỉnh",
    "Thành phố thuộc thành phố",
    "Phường",
    "Thị trấn",
    "Xã",
]

# Nhóm cấp hành chính
CAP_TINH: list[str] = [
    "Thành phố trực thuộc Trung ương",
    "Tỉnh",
]
CAP_HUYEN: list[str] = [
    "Quận",
    "Huyện",
    "Thị xã",
    "Thành phố thuộc tỉnh",
    "Thành phố thuộc thành phố",
]
CAP_XA: list[str] = [
    "Phường",
    "Thị trấn",
    "Xã",
]


# ══════════════════════════════════════════════════════════
#  DATACLASS: ĐƠN VỊ HÀNH CHÍNH
# ══════════════════════════════════════════════════════════

@dataclass
class DVHC:
    """
    Đại diện 1 bản ghi trong bảng DM_DVHC.

    Tên field khớp 100% tên cột trong SQLite và dvhc.json.
    """
    MA_DVHC    : Optional[int] = None   # PRIMARY KEY
    MA_DVQL    : Optional[int] = None   # Mã đơn vị quản lý (cấp trên)
    MA_DV      : Optional[int] = None   # Mã đơn vị nội bộ
    TEN_DVHC   : Optional[str] = None   # Tên ngắn
    TENNGANGON : Optional[str] = None   # Tên ngang gọn
    TENDAYDU   : Optional[str] = None   # Tên đầy đủ
    LOAIDVHC   : Optional[str] = None   # Loại: Tỉnh/Huyện/Xã...

    # ──────────────────────────────────────────────────────
    #  CHUYỂN ĐỔI
    # ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        Chuyển object → dict, bỏ field None.
        Dùng cho INSERT/UPDATE SQL.
        """
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_full_dict(self) -> dict:
        """Chuyển object → dict bao gồm cả field None."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> DVHC:
        """
        Tạo instance từ dict.
        Chỉ lấy key khớp tên field dataclass.
        Tự ép kiểu MA_DVHC sang int.
        """
        valid_fields = {f.name for f in fields(cls)}
        filtered     = {}

        for k, v in data.items():
            if k not in valid_fields:
                continue
            # Ép kiểu MA_DVHC, MA_DVQL, MA_DV sang int
            if k in ("MA_DVHC", "MA_DVQL", "MA_DV") and v is not None:
                try:
                    filtered[k] = int(v)
                except (ValueError, TypeError):
                    filtered[k] = v
            else:
                filtered[k] = v

        return cls(**filtered)

    @classmethod
    def from_json_item(cls, item: dict) -> DVHC:
        """
        Tạo instance từ 1 phần tử trong dvhc.json.
        Alias của from_dict() nhưng thêm normalize tên field.
        """
        # Normalize key về uppercase để tránh lỗi casing
        normalized = {k.upper(): v for k, v in item.items()}
        return cls.from_dict(normalized)

    @classmethod
    def get_field_names(cls) -> list[str]:
        """Lấy danh sách tên tất cả field."""
        return [f.name for f in fields(cls)]

    # ──────────────────────────────────────────────────────
    #  VALIDATE
    # ──────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """
        Kiểm tra tính hợp lệ của bản ghi DVHC.

        Returns
        -------
        list[str] danh sách lỗi, rỗng = hợp lệ
        """
        errors = []

        # MA_DVHC bắt buộc (PRIMARY KEY)
        if self.MA_DVHC is None:
            errors.append("Mã DVHC (MA_DVHC) không được để trống.")
        else:
            try:
                ma = int(self.MA_DVHC)
                if ma <= 0:
                    errors.append(
                        f"Mã DVHC ({ma}) phải là số nguyên dương."
                    )
            except (ValueError, TypeError):
                errors.append(
                    f"Mã DVHC '{self.MA_DVHC}' phải là số nguyên."
                )

        # TEN_DVHC bắt buộc
        if not self.TEN_DVHC or not str(self.TEN_DVHC).strip():
            errors.append("Tên DVHC (TEN_DVHC) không được để trống.")
        else:
            if len(str(self.TEN_DVHC).strip()) > 255:
                errors.append(
                    "Tên DVHC không được vượt quá 255 ký tự."
                )

        # LOAIDVHC kiểm tra giá trị hợp lệ
        if self.LOAIDVHC:
            if self.LOAIDVHC not in VALID_LOAI_DVHC:
                errors.append(
                    f"Loại DVHC '{self.LOAIDVHC}' không hợp lệ. "
                    f"Hợp lệ: {', '.join(VALID_LOAI_DVHC)}"
                )

        # MA_DVQL: nếu có thì phải là số nguyên dương
        if self.MA_DVQL is not None:
            try:
                ma_dvql = int(self.MA_DVQL)
                if ma_dvql < 0:
                    errors.append("Mã DVQL phải là số nguyên không âm.")
            except (ValueError, TypeError):
                errors.append(
                    f"Mã DVQL '{self.MA_DVQL}' phải là số nguyên."
                )

        return errors

    # ──────────────────────────────────────────────────────
    #  TIỆN ÍCH
    # ──────────────────────────────────────────────────────

    def get_cap_hanh_chinh(self) -> str:
        """
        Xác định cấp hành chính từ LOAIDVHC.

        Returns
        -------
        "Tỉnh/TP" | "Huyện/Quận" | "Xã/Phường" | "Khác"
        """
        if not self.LOAIDVHC:
            return "Khác"
        if self.LOAIDVHC in CAP_TINH:
            return "Tỉnh/TP"
        if self.LOAIDVHC in CAP_HUYEN:
            return "Huyện/Quận"
        if self.LOAIDVHC in CAP_XA:
            return "Xã/Phường"
        return "Khác"

    def get_ten_display(self) -> str:
        """
        Lấy tên hiển thị tốt nhất:
        Ưu tiên TENDAYDU → TENNGANGON → TEN_DVHC.
        """
        return (
            self.TENDAYDU
            or self.TENNGANGON
            or self.TEN_DVHC
            or str(self.MA_DVHC or "")
        )

    def is_cap_tinh(self) -> bool:
        return self.LOAIDVHC in CAP_TINH

    def is_cap_huyen(self) -> bool:
        return self.LOAIDVHC in CAP_HUYEN

    def is_cap_xa(self) -> bool:
        return self.LOAIDVHC in CAP_XA

    def __repr__(self) -> str:
        return (
            f"DVHC(MA={self.MA_DVHC}, "
            f"TEN='{self.TEN_DVHC}', "
            f"LOAI='{self.LOAIDVHC}')"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DVHC):
            return False
        return self.MA_DVHC == other.MA_DVHC

    def __hash__(self) -> int:
        return hash(self.MA_DVHC)


# ══════════════════════════════════════════════════════════
#  CÁC CỘT HIỂN THỊ TRÊN TABLE VIEW
# ══════════════════════════════════════════════════════════

# Mỗi tuple = (field_name, header_label, width)
DVHC_DISPLAY_COLUMNS: list[tuple[str, str, int]] = [
    ("MA_DVHC",    "Mã DVHC",    80),
    ("TEN_DVHC",   "Tên DVHC",   180),
    ("TENNGANGON", "Tên ngắn",   150),
    ("TENDAYDU",   "Tên đầy đủ", 250),
    ("LOAIDVHC",   "Loại",       150),
    ("MA_DVQL",    "Mã DVQL",    80),
]


# ══════════════════════════════════════════════════════════
#  QT TABLE MODEL
# ══════════════════════════════════════════════════════════

class DVHCTableModel(QAbstractTableModel):
    """
    Model cung cấp dữ liệu DVHC cho QTableView.

    Tính năng:
    - Hiển thị các cột theo DVHC_DISPLAY_COLUMNS
    - Tô màu theo cấp hành chính
    - Hỗ trợ sắp xếp
    - Signal khi dữ liệu thay đổi
    """

    # Signal phát ra khi dữ liệu được cập nhật
    data_changed_signal = Signal()

    # Màu nền theo cấp hành chính
    CAP_COLORS: dict[str, str] = {
        "Tỉnh/TP"     : "#E3F2FD",   # xanh nhạt
        "Huyện/Quận"  : "#F3E5F5",   # tím nhạt
        "Xã/Phường"   : "#F1F8E9",   # xanh lá nhạt
        "Khác"         : "#FAFAFA",   # trắng xám
    }

    # Màu chữ cấp tỉnh (bold hơn)
    CAP_FONT_COLORS: dict[str, str] = {
        "Tỉnh/TP"     : "#0D47A1",   # xanh đậm
        "Huyện/Quận"  : "#6A1B9A",   # tím đậm
        "Xã/Phường"   : "#1B5E20",   # xanh lá đậm
        "Khác"         : "#212121",   # đen
    }

    def __init__(
        self,
        data    : list[DVHC] = None,
        columns : list[tuple[str, str, int]] = None,
        parent  = None
    ) -> None:
        """
        Parameters
        ----------
        data    : danh sách DVHC objects
        columns : cấu hình cột [(field, header, width), ...]
        """
        super().__init__(parent)
        self._data    : list[DVHC]               = data or []
        self._columns : list[tuple[str, str, int]] = columns or DVHC_DISPLAY_COLUMNS

    # ──────────────────────────────────────────────────────
    #  OVERRIDE QAbstractTableModel
    # ──────────────────────────────────────────────────────

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._columns)

    def data(
        self,
        index: QModelIndex,
        role : int = Qt.DisplayRole
    ) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._data):
            return None
        if col < 0 or col >= len(self._columns):
            return None

        dvhc       = self._data[row]
        field_name = self._columns[col][0]
        value      = getattr(dvhc, field_name, None)
        cap        = dvhc.get_cap_hanh_chinh()

        # ── DisplayRole ────────────────────────────────────
        if role == Qt.DisplayRole:
            if value is None:
                return ""
            return str(value)

        # ── BackgroundRole: tô màu theo cấp ───────────────
        if role == Qt.BackgroundRole:
            color_hex = self.CAP_COLORS.get(cap, "#FAFAFA")
            from PySide6.QtGui import QColor
            return QColor(color_hex)

        # ── ForegroundRole: màu chữ theo cấp ──────────────
        if role == Qt.ForegroundRole:
            color_hex = self.CAP_FONT_COLORS.get(cap, "#212121")
            from PySide6.QtGui import QColor
            return QColor(color_hex)

        # ── FontRole: in đậm cấp Tỉnh/TP ──────────────────
        if role == Qt.FontRole:
            if cap == "Tỉnh/TP":
                from PySide6.QtGui import QFont
                font = QFont()
                font.setBold(True)
                return font

        # ── TextAlignmentRole ──────────────────────────────
        if role == Qt.TextAlignmentRole:
            if field_name in ("MA_DVHC", "MA_DVQL", "MA_DV"):
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        # ── ToolTipRole ────────────────────────────────────
        if role == Qt.ToolTipRole:
            parts = [
                f"Mã DVHC   : {dvhc.MA_DVHC or ''}",
                f"Tên       : {dvhc.TEN_DVHC or ''}",
                f"Tên đầy đủ: {dvhc.TENDAYDU or ''}",
                f"Loại      : {dvhc.LOAIDVHC or ''}",
                f"Cấp       : {cap}",
                f"Mã DVQL   : {dvhc.MA_DVQL or ''}",
            ]
            return "\n".join(parts)

        # ── UserRole: trả object gốc ───────────────────────
        if role == Qt.UserRole:
            return dvhc

        return None

    def headerData(
        self,
        section     : int,
        orientation : Qt.Orientation,
        role        : int = Qt.DisplayRole
    ) -> Any:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if 0 <= section < len(self._columns):
                    return self._columns[section][1]
            elif orientation == Qt.Vertical:
                return str(section + 1)

        # Header nền màu
        if role == Qt.BackgroundRole and orientation == Qt.Horizontal:
            from PySide6.QtGui import QColor
            return QColor("#1a237e")

        if role == Qt.ForegroundRole and orientation == Qt.Horizontal:
            from PySide6.QtGui import QColor
            return QColor("#ffffff")

        return None

    # ──────────────────────────────────────────────────────
    #  PUBLIC API
    # ──────────────────────────────────────────────────────

    def set_data(self, data: list[DVHC]) -> None:
        """Thay đổi toàn bộ dữ liệu và refresh bảng."""
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()
        self.data_changed_signal.emit()

    def append_row(self, dvhc: DVHC) -> None:
        """Thêm 1 dòng cuối bảng."""
        row = len(self._data)
        self.beginInsertRows(QModelIndex(), row, row)
        self._data.append(dvhc)
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

    def update_row(self, row: int, dvhc: DVHC) -> bool:
        """Cập nhật 1 dòng theo index."""
        if 0 <= row < len(self._data):
            self._data[row] = dvhc
            left  = self.index(row, 0)
            right = self.index(row, self.columnCount() - 1)
            self.dataChanged.emit(left, right)
            self.data_changed_signal.emit()
            return True
        return False

    def get_item(self, row: int) -> Optional[DVHC]:
        """Lấy DVHC object theo index dòng."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def get_all_data(self) -> list[DVHC]:
        """Lấy toàn bộ dữ liệu."""
        return self._data.copy()

    def get_column_widths(self) -> list[int]:
        """Lấy danh sách độ rộng cột."""
        return [col[2] for col in self._columns]

    def find_by_ma_dvhc(self, ma_dvhc: int) -> Optional[int]:
        """
        Tìm index dòng theo MA_DVHC.

        Returns
        -------
        row index hoặc None nếu không tìm thấy
        """
        for i, item in enumerate(self._data):
            if item.MA_DVHC == ma_dvhc:
                return i
        return None

    def get_stats(self) -> dict:
        """
        Thống kê số lượng theo cấp hành chính.

        Returns
        -------
        dict: {"Tỉnh/TP": n, "Huyện/Quận": n, "Xã/Phường": n, "Khác": n}
        """
        stats = {"Tỉnh/TP": 0, "Huyện/Quận": 0, "Xã/Phường": 0, "Khác": 0}
        for item in self._data:
            cap = item.get_cap_hanh_chinh()
            stats[cap] = stats.get(cap, 0) + 1
        return stats

    def get_all_loai(self) -> list[str]:
        """Lấy danh sách LOAIDVHC không trùng."""
        loai_set = set()
        for item in self._data:
            if item.LOAIDVHC:
                loai_set.add(item.LOAIDVHC)
        return sorted(loai_set)

    def clear(self) -> None:
        """Xóa toàn bộ dữ liệu."""
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()
        self.data_changed_signal.emit()

    # ──────────────────────────────────────────────────────
    #  IMPORT TỪ DVHC SERVICE
    # ──────────────────────────────────────────────────────

    def load_from_dicts(self, dict_list: list[dict]) -> int:
        """
        Load dữ liệu từ list[dict] (từ JSON hoặc SQLite).

        Returns
        -------
        Số bản ghi đã load
        """
        objects = []
        for item in dict_list:
            try:
                obj = DVHC.from_dict(item)
                objects.append(obj)
            except Exception:
                continue  # Bỏ qua bản ghi lỗi

        self.set_data(objects)
        return len(objects)


# ══════════════════════════════════════════════════════════
#  SORT / FILTER PROXY MODEL
# ══════════════════════════════════════════════════════════

class DVHCSortFilterModel(QSortFilterProxyModel):
    """
    Proxy model hỗ trợ:
    - Sắp xếp theo cột
    - Lọc theo mã, tên, loại DVHC
    - Tìm kiếm tức thời
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Bộ lọc
        self._filter_ma_dvhc  : str = ""
        self._filter_ten      : str = ""
        self._filter_loai     : str = ""
        self._filter_keyword  : str = ""   # Tìm toàn bộ

        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)

    # ──────────────────────────────────────────────────────
    #  SET FILTER
    # ──────────────────────────────────────────────────────

    def set_filter_ma(self, value: str) -> None:
        self._filter_ma_dvhc = value.strip().lower()
        self.invalidateFilter()

    def set_filter_ten(self, value: str) -> None:
        self._filter_ten = value.strip().lower()
        self.invalidateFilter()

    def set_filter_loai(self, value: str) -> None:
        self._filter_loai = value.strip()
        self.invalidateFilter()

    def set_filter_keyword(self, value: str) -> None:
        """Tìm kiếm toàn bộ field (Mã + Tên + Loại)."""
        self._filter_keyword = value.strip().lower()
        self.invalidateFilter()

    def clear_all_filters(self) -> None:
        """Xóa toàn bộ bộ lọc."""
        self._filter_ma_dvhc = ""
        self._filter_ten     = ""
        self._filter_loai    = ""
        self._filter_keyword = ""
        self.invalidateFilter()

    # ──────────────────────────────────────────────────────
    #  OVERRIDE
    # ──────────────────────────────────────────────────────

    def filterAcceptsRow(
        self,
        source_row   : int,
        source_parent: QModelIndex
    ) -> bool:
        """
        Xác định 1 dòng có thỏa mãn tất cả bộ lọc không.
        Tất cả điều kiện kết hợp AND.
        """
        model = self.sourceModel()
        if not model:
            return True

        item = model.get_item(source_row)
        if not item:
            return True

        # ── Lọc mã DVHC ───────────────────────────────────
        if self._filter_ma_dvhc:
            val = str(item.MA_DVHC or "").lower()
            if self._filter_ma_dvhc not in val:
                return False

        # ── Lọc tên ───────────────────────────────────────
        if self._filter_ten:
            searchable = " ".join([
                str(item.TEN_DVHC   or ""),
                str(item.TENNGANGON or ""),
                str(item.TENDAYDU   or ""),
            ]).lower()
            if self._filter_ten not in searchable:
                return False

        # ── Lọc loại (chính xác) ──────────────────────────
        if self._filter_loai:
            val = str(item.LOAIDVHC or "")
            if val != self._filter_loai:
                return False

        # ── Tìm toàn bộ keyword ───────────────────────────
        if self._filter_keyword:
            kw = self._filter_keyword
            searchable = " ".join([
                str(item.MA_DVHC    or ""),
                str(item.TEN_DVHC   or ""),
                str(item.TENNGANGON or ""),
                str(item.TENDAYDU   or ""),
                str(item.LOAIDVHC   or ""),
                str(item.MA_DVQL    or ""),
            ]).lower()
            if kw not in searchable:
                return False

        return True

    def lessThan(
        self,
        left : QModelIndex,
        right: QModelIndex
    ) -> bool:
        """Override sắp xếp tùy chỉnh."""
        model = self.sourceModel()
        if not model:
            return False

        col_name = (
            DVHC_DISPLAY_COLUMNS[left.column()][0]
            if left.column() < len(DVHC_DISPLAY_COLUMNS)
            else ""
        )

        left_data  = model.data(left,  Qt.DisplayRole)
        right_data = model.data(right, Qt.DisplayRole)

        # Cột số: so sánh int
        if col_name in ("MA_DVHC", "MA_DVQL", "MA_DV"):
            try:
                return int(left_data or 0) < int(right_data or 0)
            except (ValueError, TypeError):
                pass

        # Mặc định: so sánh chuỗi
        return str(left_data or "").lower() < str(right_data or "").lower()


# ══════════════════════════════════════════════════════════
#  TIỆN ÍCH
# ══════════════════════════════════════════════════════════

def dvhc_list_from_dicts(dict_list: list[dict]) -> list[DVHC]:
    """
    Chuyển list[dict] thành list[DVHC].
    Dùng khi load từ JSON hoặc SQLite.

    Parameters
    ----------
    dict_list : list các dict từ json.load() hoặc db._fetchall()

    Returns
    -------
    list[DVHC]
    """
    result = []
    for item in dict_list:
        try:
            result.append(DVHC.from_dict(item))
        except Exception:
            continue
    return result


def dvhc_list_to_dicts(dvhc_list: list[DVHC]) -> list[dict]:
    """
    Chuyển list[DVHC] thành list[dict].
    Dùng khi lưu vào JSON hoặc SQLite.
    """
    return [item.to_full_dict() for item in dvhc_list]


def build_dvhc_tree(dvhc_list: list[DVHC]) -> dict:
    """
    Xây dựng cây phân cấp DVHC theo MA_DVQL.

    Returns
    -------
    dict dạng:
    {
        ma_dvhc: {
            "item"    : DVHC,
            "children": [DVHC, ...]
        }
    }
    """
    # Index tất cả theo mã
    by_ma    : dict[int, DVHC]        = {}
    children : dict[int, list[DVHC]] = {}

    for dvhc in dvhc_list:
        if dvhc.MA_DVHC:
            by_ma[dvhc.MA_DVHC] = dvhc
        parent = dvhc.MA_DVQL
        if parent:
            if parent not in children:
                children[parent] = []
            children[parent].append(dvhc)

    # Xây dựng dict kết quả
    tree = {}
    for ma, dvhc in by_ma.items():
        tree[ma] = {
            "item"     : dvhc,
            "children" : children.get(ma, [])
        }
    return tree