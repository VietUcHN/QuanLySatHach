"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : ui/tab_main.py
Mô tả     : Tab chính v1.0 - Quản lý hồ sơ + Hiển thị kết quả
            - Phần trên: Toolbar + Bộ lọc + Bảng danh sách
            - Phần dưới: 2 bảng thống kê (Import KQ + Nhập KQ)
            - Tích hợp AuthService phân quyền nút bấm
            - Dữ liệu JOIN nguoi_lx + ho_so_sh + nhap_kqsh
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================

Bố cục:
┌─────────────────────────────────────────────────────────────┐
│  [Thêm] [Sửa] [Xóa] [Làm mới]       Tổng: 125 hồ sơ      │
├─────────────────────────────────────────────────────────────┤
│  Bộ lọc: [Kỳ SH▼] [Hạng▼] [Họ tên___] [CCCD___] [🔍]     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │ STT│Mã ĐK│Họ tên│Ngày sinh│CCCD│Hạng│SBD│KQ│Nhập  │    │
│  │────│──────│──────│────────│────│────│───│──│──── │    │
│  │ 1  │DK001 │Ng A  │01/01   │012 │B2  │01 │Đ │Đ     │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  ┌─── Import KQ ──────────────────────────────────────┐    │
│  │      │Chưa Thi│Đã Thi│ Đạt │K.Đạt│  %   │         │    │
│  │ LT   │  50    │  75  │ 60  │ 15  │80.0% │         │    │
│  │ MP   │  80    │  45  │ 40  │  5  │88.9% │         │    │
│  │ H    │  30    │  95  │ 80  │ 15  │84.2% │         │    │
│  │ Đ    │  60    │  65  │ 55  │ 10  │84.6% │         │    │
│  │ Tổng │  20    │ 105  │ 90  │ 15  │85.7% │         │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─── Nhập KQ ────────────────────────────────────────┐    │
│  │      │Chưa Thi│Đã Thi│ Đạt │K.Đạt│  %   │         │    │
│  │ LT   │  55    │  70  │ 58  │ 12  │82.9% │         │    │
│  │ ...  │        │      │     │     │      │         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
"""

from typing   import Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLineEdit,
    QComboBox,
    QLabel,
    QMessageBox,
    QHeaderView,
    QAbstractItemView,
    QSpacerItem,
    QSizePolicy,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QDateEdit,
    QTextEdit,
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui  import QColor, QFont, QKeySequence, QShortcut

from database.db_manager       import DatabaseManager
from services.display_service  import DisplayService, TongHopHienThi, BangKetQua
from services.auth_service     import AuthService
from services.logger_service   import LoggerService


# ══════════════════════════════════════════════════════════
#  STYLESHEET
# ══════════════════════════════════════════════════════════

TAB_MAIN_STYLE = """
/* ── GroupBox ─────────────────────────────────────────── */
QGroupBox {
    font-size: 10pt;
    font-weight: bold;
    color: #1a237e;
    border: 1px solid #c5cae9;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 8px;
}

/* ── Nút bấm ─────────────────────────────────────────── */
QPushButton {
    padding: 7px 16px;
    border-radius: 5px;
    font-size: 10pt;
    font-weight: bold;
    border: none;
    min-width: 80px;
}
QPushButton#btnAdd    { background-color: #4CAF50; color: white; }
QPushButton#btnAdd:hover { background-color: #388E3C; }
QPushButton#btnEdit   { background-color: #2196F3; color: white; }
QPushButton#btnEdit:hover { background-color: #1565C0; }
QPushButton#btnDelete { background-color: #F44336; color: white; }
QPushButton#btnDelete:hover { background-color: #C62828; }
QPushButton#btnSearch { background-color: #FF9800; color: white; }
QPushButton#btnSearch:hover { background-color: #E65100; }
QPushButton#btnRefresh{ background-color: #607D8B; color: white; }
QPushButton#btnRefresh:hover { background-color: #37474F; }
QPushButton:disabled  { background-color: #bdbdbd; color: #757575; }

/* ── Input ────────────────────────────────────────────── */
QLineEdit, QComboBox {
    padding: 6px 10px;
    border: 1px solid #c5cae9;
    border-radius: 4px;
    font-size: 10pt;
}
QLineEdit:focus, QComboBox:focus {
    border: 2px solid #1a237e;
}

/* ── TableWidget ──────────────────────────────────────── */
QTableWidget {
    border: 1px solid #c5cae9;
    border-radius: 4px;
    gridline-color: #e0e0e0;
    font-size: 10pt;
    alternate-background-color: #fafafa;
    selection-background-color: #e3f2fd;
    selection-color: #0d47a1;
}
QTableWidget::item:selected {
    background-color: #bbdefb;
    color: #0d47a1;
}
QHeaderView::section {
    background-color: #1a237e;
    color: #ffffff;
    padding: 6px;
    border: 1px solid #283593;
    font-size: 10pt;
    font-weight: bold;
}

/* ── Bảng thống kê ────────────────────────────────────── */
QTableWidget#tblStats {
    font-size: 10pt;
    border: 1px solid #c5cae9;
    border-radius: 4px;
}
QTableWidget#tblStats QHeaderView::section {
    background-color: #283593;
    color: #ffffff;
    font-size: 9pt;
    font-weight: bold;
    padding: 5px;
}
"""


# ══════════════════════════════════════════════════════════
#  CỘT HIỂN THỊ DANH SÁCH
# ══════════════════════════════════════════════════════════

# (field_db, header_label, width, source_table)
DISPLAY_COLUMNS = [
    ("SO_TT",           "STT",         50,  "n"),
    ("MA_DK",           "Mã ĐK",     100,  "n"),
    ("HO_VA_TEN",       "Họ và tên",  200,  "n"),
    ("NGAY_SINH",       "Ngày sinh",  100,  "n"),
    ("SO_CMT",          "CCCD",       120,  "n"),
    ("HANG_GPLX",       "Hạng",        70,  "h"),
    ("SO_BAO_DANH",     "SBD",         70,  "h"),
    ("KET_QUA_SH",      "KQ Import",  100,  "h"),
    ("KETQUA_NHAP",     "KQ Nhập",    100,  "nk"),
    ("TRANGTHAI",       "Trạng thái",  90,  "nk"),
]

# Màu theo kết quả
KQ_COLORS = {
    "Đạt"       : ("#1B5E20", "#E8F5E9"),  # (font, bg)
    "đạt"       : ("#1B5E20", "#E8F5E9"),
    "Dat"       : ("#1B5E20", "#E8F5E9"),
    "Không đạt" : ("#B71C1C", "#FFEBEE"),
    "không đạt" : ("#B71C1C", "#FFEBEE"),
    "Khong dat" : ("#B71C1C", "#FFEBEE"),
}

# Màu cho bảng thống kê
STATS_HEADER_LABELS = ["", "Chưa Thi", "Đã Thi", "Đạt", "Không Đạt", "Phần trăm"]
STATS_ROW_LABELS    = ["Lý Thuyết", "Mô Phỏng", "Hình", "Đường", "Tổng"]


# ══════════════════════════════════════════════════════════
#  CLASS TAB MAIN
# ══════════════════════════════════════════════════════════

class TabMain(QWidget):
    """
    Tab chính v1.0 – Quản lý hồ sơ + Hiển thị kết quả.

    Cấu trúc:
    - Splitter dọc chia 2:
      + Trên: Toolbar + Filter + Bảng danh sách
      + Dưới: 2 bảng thống kê (Import KQ + Nhập KQ) nằm ngang
    """

    def __init__(
        self,
        db_manager      : DatabaseManager,
        display_service : DisplayService,
        auth_service    : AuthService,
        logger          : LoggerService,
        parent          : QWidget = None,
    ) -> None:
        super().__init__(parent)

        self.db      = db_manager
        self.display = display_service
        self.auth    = auth_service
        self.logger  = logger

        self.setStyleSheet(TAB_MAIN_STYLE)
        self._setup_ui()
        self._connect_signals()

        # Load lần đầu
        QTimer.singleShot(200, self.refresh_data)

    # ══════════════════════════════════════════════════════
    #  SETUP UI
    # ══════════════════════════════════════════════════════

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # Splitter: Danh sách (trên) + Thống kê (dưới)
        self._splitter = QSplitter(Qt.Vertical)

        # ── Phần trên: Danh sách ───────────────────────────
        self._splitter.addWidget(self._create_list_section())

        # ── Phần dưới: Thống kê ────────────────────────────
        self._splitter.addWidget(self._create_stats_section())

        self._splitter.setSizes([500, 300])
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, False)

        main_layout.addWidget(self._splitter, 1)

    # ══════════════════════════════════════════════════════
    #  PHẦN TRÊN: DANH SÁCH HỒ SƠ
    # ══════════════════════════════════════════════════════

    def _create_list_section(self) -> QWidget:
        """Tạo phần danh sách hồ sơ."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Toolbar
        layout.addLayout(self._create_toolbar())

        # Bộ lọc
        layout.addLayout(self._create_filter_row())

        # Bảng danh sách
        layout.addWidget(self._create_data_table(), 1)

        # Thanh info
        layout.addLayout(self._create_info_row())

        return widget

    # ──────────────────────────────────────────────────────
    #  TOOLBAR
    # ──────────────────────────────────────────────────────

    def _create_toolbar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(6)

        # Nút Thêm
        self.btn_add = QPushButton("➕ Thêm")
        self.btn_add.setObjectName("btnAdd")
        layout.addWidget(self.btn_add)

        # Nút Sửa
        self.btn_edit = QPushButton("✏️ Sửa")
        self.btn_edit.setObjectName("btnEdit")
        layout.addWidget(self.btn_edit)

        # Nút Xóa
        self.btn_delete = QPushButton("🗑️ Xóa")
        self.btn_delete.setObjectName("btnDelete")
        layout.addWidget(self.btn_delete)

        layout.addSpacerItem(
            QSpacerItem(15, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        )

        # Nút Làm mới
        self.btn_refresh = QPushButton("🔄 Làm mới")
        self.btn_refresh.setObjectName("btnRefresh")
        layout.addWidget(self.btn_refresh)

        layout.addStretch()

        # Label tổng
        self.lbl_total = QLabel("Tổng: 0 hồ sơ")
        self.lbl_total.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #1a237e;"
        )
        layout.addWidget(self.lbl_total)

        # ── Phân quyền nút ────────────────────────────────
        perm = self.auth.current_permission
        if perm:
            self.btn_add.setEnabled(perm.has_action("add"))
            self.btn_edit.setEnabled(perm.has_action("edit"))
            self.btn_delete.setEnabled(perm.has_action("delete"))

        return layout

    # ──────────────────────────────────────────────────────
    #  BỘ LỌC
    # ──────────────────────────────────────────────────────

    def _create_filter_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(8)

        # Kỳ SH
        layout.addWidget(QLabel("Kỳ SH:"))
        self.cmb_ky_sh = QComboBox()
        self.cmb_ky_sh.setMinimumWidth(130)
        self.cmb_ky_sh.addItem("-- Tất cả --", "")
        self._load_ky_sh_list()
        layout.addWidget(self.cmb_ky_sh)

        # Hạng GPLX
        layout.addWidget(QLabel("Hạng:"))
        self.cmb_hang = QComboBox()
        self.cmb_hang.setMinimumWidth(80)
        self.cmb_hang.addItem("-- Tất cả --", "")
        for h in ["A1", "A2", "B1", "B2", "C", "D", "E", "F"]:
            self.cmb_hang.addItem(h, h)
        layout.addWidget(self.cmb_hang)

        # Họ tên
        layout.addWidget(QLabel("Họ tên:"))
        self.txt_hoten = QLineEdit()
        self.txt_hoten.setPlaceholderText("Tìm họ tên...")
        self.txt_hoten.setMaximumWidth(180)
        layout.addWidget(self.txt_hoten)

        # CCCD
        layout.addWidget(QLabel("CCCD:"))
        self.txt_cccd = QLineEdit()
        self.txt_cccd.setPlaceholderText("Tìm CCCD...")
        self.txt_cccd.setMaximumWidth(140)
        layout.addWidget(self.txt_cccd)

        # Nút tìm
        self.btn_search = QPushButton("🔍 Tìm")
        self.btn_search.setObjectName("btnSearch")
        layout.addWidget(self.btn_search)

        layout.addStretch()
        return layout

    # ──────────────────────────────────────────────────────
    #  BẢNG DANH SÁCH
    # ──────────────────────────────────────────────────────

    def _create_data_table(self) -> QTableWidget:
        self.tbl_data = QTableWidget()
        self.tbl_data.setColumnCount(len(DISPLAY_COLUMNS))
        self.tbl_data.setHorizontalHeaderLabels(
            [c[1] for c in DISPLAY_COLUMNS]
        )
        self.tbl_data.setAlternatingRowColors(True)
        self.tbl_data.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_data.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_data.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_data.setSortingEnabled(True)
        self.tbl_data.verticalHeader().setDefaultSectionSize(32)
        self.tbl_data.verticalHeader().setVisible(False)

        # Độ rộng cột
        header = self.tbl_data.horizontalHeader()
        for i, (_, _, width, _) in enumerate(DISPLAY_COLUMNS):
            self.tbl_data.setColumnWidth(i, width)
        header.setStretchLastSection(True)

        # Double-click sửa
        self.tbl_data.doubleClicked.connect(self._on_edit_clicked)

        return self.tbl_data

    # ──────────────────────────────────────────────────────
    #  THANH INFO
    # ──────────────────────────────────────────────────────

    def _create_info_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("font-size: 9pt; color: #666;")
        layout.addWidget(self.lbl_info)

        layout.addStretch()

        self.lbl_selection = QLabel("")
        self.lbl_selection.setStyleSheet("font-size: 9pt; color: #666;")
        layout.addWidget(self.lbl_selection)

        return layout

    # ══════════════════════════════════════════════════════
    #  PHẦN DƯỚI: BẢNG THỐNG KÊ KẾT QUẢ
    # ══════════════════════════════════════════════════════

    def _create_stats_section(self) -> QWidget:
        """
        Tạo phần thống kê: 2 bảng nằm ngang.

        ┌────── Import KQ ──────┐  ┌────── Nhập KQ ────────┐
        │     │CT│ĐT│Đ │KĐ│ % │  │     │CT│ĐT│Đ │KĐ│ % │
        │ LT  │  │  │  │  │   │  │ LT  │  │  │  │  │   │
        │ MP  │  │  │  │  │   │  │ MP  │  │  │  │  │   │
        │ H   │  │  │  │  │   │  │ H   │  │  │  │  │   │
        │ Đ   │  │  │  │  │   │  │ Đ   │  │  │  │  │   │
        │ Tổng│  │  │  │  │   │  │ Tổng│  │  │  │  │   │
        └─────────────────────┘  └─────────────────────┘
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(10)

        # Bảng Import KQ
        layout.addWidget(
            self._create_stats_group("📊 Import KQ (từ Ho_so_SH)", "import")
        )

        # Bảng Nhập KQ
        layout.addWidget(
            self._create_stats_group("📝 Nhập KQ (từ Nhap_KQSH)", "nhap")
        )

        return widget

    def _create_stats_group(
        self, title: str, stats_type: str
    ) -> QGroupBox:
        """Tạo 1 GroupBox chứa bảng thống kê 5×6."""
        group  = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(5, 15, 5, 5)

        # Tạo bảng
        tbl = QTableWidget()
        tbl.setObjectName("tblStats")
        tbl.setRowCount(5)           # LT, MP, H, Đ, Tổng
        tbl.setColumnCount(6)        # Tên, CT, ĐT, Đ, KĐ, %
        tbl.setHorizontalHeaderLabels(STATS_HEADER_LABELS)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionMode(QAbstractItemView.NoSelection)
        tbl.verticalHeader().setVisible(False)
        tbl.verticalHeader().setDefaultSectionSize(30)

        # Độ rộng cột
        header = tbl.horizontalHeader()
        tbl.setColumnWidth(0, 80)    # Tên phần thi
        tbl.setColumnWidth(1, 70)    # Chưa Thi
        tbl.setColumnWidth(2, 65)    # Đã Thi
        tbl.setColumnWidth(3, 55)    # Đạt
        tbl.setColumnWidth(4, 80)    # Không Đạt
        header.setStretchLastSection(True)  # % co giãn

        # Điền tên dòng mặc định
        for row_idx, name in enumerate(STATS_ROW_LABELS):
            item = QTableWidgetItem(name)
            item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            if row_idx == 4:  # Dòng Tổng
                item.setBackground(QColor("#E8EAF6"))
            tbl.setItem(row_idx, 0, item)

            # Điền --- cho các cột còn lại
            for col in range(1, 6):
                cell = QTableWidgetItem("---")
                cell.setTextAlignment(Qt.AlignCenter)
                if row_idx == 4:
                    cell.setBackground(QColor("#E8EAF6"))
                    cell.setFont(QFont("Segoe UI", 10, QFont.Bold))
                tbl.setItem(row_idx, col, cell)

        layout.addWidget(tbl)

        # Lưu reference
        if stats_type == "import":
            self.tbl_stats_import = tbl
        else:
            self.tbl_stats_nhap = tbl

        return group

    # ══════════════════════════════════════════════════════
    #  KẾT NỐI SIGNAL
    # ══════════════════════════════════════════════════════

    def _connect_signals(self) -> None:
        self.btn_add.clicked.connect(self._on_add_clicked)
        self.btn_edit.clicked.connect(self._on_edit_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.btn_search.clicked.connect(self._on_search)

        # Debounce tìm kiếm
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._on_search)

        self.txt_hoten.textChanged.connect(lambda: self._debounce.start())
        self.txt_cccd.textChanged.connect(lambda: self._debounce.start())
        self.cmb_ky_sh.currentIndexChanged.connect(self._on_search)
        self.cmb_hang.currentIndexChanged.connect(self._on_search)

        # Selection
        self.tbl_data.itemSelectionChanged.connect(
            self._on_selection_changed
        )

        # Phím tắt
        QShortcut(QKeySequence(Qt.Key_Delete), self).activated.connect(
            self._on_delete_clicked
        )
        QShortcut(QKeySequence(Qt.Key_F5), self).activated.connect(
            self.refresh_data
        )

    # ══════════════════════════════════════════════════════
    #  LOAD / REFRESH DỮ LIỆU
    # ══════════════════════════════════════════════════════

    def refresh_data(self) -> None:
        """Load lại toàn bộ danh sách + thống kê."""
        self._load_data_table()
        self._load_stats()

    def _load_data_table(self) -> None:
        """Query và hiển thị danh sách hồ sơ."""
        try:
            # Lấy filter
            ma_ky_sh  = self.cmb_ky_sh.currentData() or ""
            hang_gplx = self.cmb_hang.currentData() or ""
            ho_ten    = self.txt_hoten.text().strip()
            cccd      = self.txt_cccd.text().strip()

            # Build SQL
            sql = """
            SELECT n.SO_TT, n.MA_DK, n.HO_VA_TEN, n.NGAY_SINH,
                   n.SO_CMT,
                   h.HANG_GPLX, h.SO_BAO_DANH, h.KET_QUA_SH,
                   nk.KETQUA_NHAP, nk.TRANGTHAI
            FROM nguoi_lx n
            LEFT JOIN ho_so_sh h ON n.MA_DK = h.MA_DK
            LEFT JOIN nhap_kqsh nk ON n.MA_DK = nk.MA_DK
            WHERE 1=1
            """
            params = []

            if ma_ky_sh:
                sql += " AND h.MA_KY_SH = ?"
                params.append(ma_ky_sh)
            if hang_gplx:
                sql += " AND h.HANG_GPLX = ?"
                params.append(hang_gplx)
            if ho_ten:
                sql += " AND n.HO_VA_TEN LIKE ?"
                params.append(f"%{ho_ten}%")
            if cccd:
                sql += " AND n.SO_CMT LIKE ?"
                params.append(f"%{cccd}%")

            sql += " ORDER BY n.SO_TT LIMIT 5000"

            rows = self.db._fetchall(sql, tuple(params))

            # Hiển thị
            self.tbl_data.setSortingEnabled(False)
            self.tbl_data.setRowCount(len(rows))

            for ri, row in enumerate(rows):
                for ci, (field, _, _, src) in enumerate(DISPLAY_COLUMNS):
                    value = row.get(field, "") or ""
                    if field == "SO_TT":
                        value = str(ri + 1)

                    item = QTableWidgetItem(str(value))

                    # Căn giữa một số cột
                    if field in ("SO_TT", "SO_BAO_DANH", "HANG_GPLX",
                                 "TRANGTHAI"):
                        item.setTextAlignment(Qt.AlignCenter)

                    # Tô màu kết quả
                    if field in ("KET_QUA_SH", "KETQUA_NHAP"):
                        colors = KQ_COLORS.get(str(value).strip())
                        if colors:
                            item.setForeground(QColor(colors[0]))
                            item.setBackground(QColor(colors[1]))
                            font = QFont()
                            font.setBold(True)
                            item.setFont(font)

                    self.tbl_data.setItem(ri, ci, item)

            self.tbl_data.setSortingEnabled(True)

            # Cập nhật info
            self.lbl_total.setText(f"Tổng: {len(rows)} hồ sơ")
            self.lbl_info.setText(f"Hiển thị: {len(rows)} hồ sơ")

        except Exception as exc:
            QMessageBox.warning(
                self, "Lỗi",
                f"Không tải được dữ liệu:\n{exc}"
            )

    def _load_stats(self) -> None:
        """Load thống kê Import KQ + Nhập KQ."""
        try:
            ma_ky_sh  = self.cmb_ky_sh.currentData() or ""
            hang_gplx = self.cmb_hang.currentData() or ""

            result = self.display.thong_ke_ket_qua(
                ma_ky_sh  = ma_ky_sh,
                hang_gplx = hang_gplx,
            )

            # Cập nhật bảng Import KQ
            self._fill_stats_table(
                self.tbl_stats_import,
                result.import_kq
            )

            # Cập nhật bảng Nhập KQ
            self._fill_stats_table(
                self.tbl_stats_nhap,
                result.nhap_kq
            )

        except Exception as exc:
            self.logger.error(
                module="TabMain",
                action="LoadStats",
                detail=f"Loi: {exc}"
            )

    def _fill_stats_table(
        self,
        tbl  : QTableWidget,
        bang : BangKetQua,
    ) -> None:
        """
        Điền dữ liệu thống kê vào bảng QTableWidget.

        Bảng 5 dòng × 6 cột:
        [Tên] [Chưa Thi] [Đã Thi] [Đạt] [Không Đạt] [%]
        """
        rows = bang.to_table_rows()

        for ri, row_data in enumerate(rows):
            is_tong = (ri == 4)  # Dòng Tổng

            # Cột 0: Tên (đã set sẵn khi tạo bảng)
            name_item = tbl.item(ri, 0)
            if name_item:
                if is_tong:
                    name_item.setBackground(QColor("#E8EAF6"))

            # Cột 1: Chưa Thi
            self._set_stats_cell(
                tbl, ri, 1,
                str(row_data["chua_thi"]),
                is_tong=is_tong,
            )

            # Cột 2: Đã Thi
            self._set_stats_cell(
                tbl, ri, 2,
                str(row_data["da_thi"]),
                is_tong=is_tong,
            )

            # Cột 3: Đạt
            self._set_stats_cell(
                tbl, ri, 3,
                str(row_data["dat"]),
                is_tong=is_tong,
                fg_color="#1B5E20" if row_data["dat"] > 0 else None,
            )

            # Cột 4: Không Đạt
            self._set_stats_cell(
                tbl, ri, 4,
                str(row_data["khong_dat"]),
                is_tong=is_tong,
                fg_color="#B71C1C" if row_data["khong_dat"] > 0 else None,
            )

            # Cột 5: Phần trăm
            pct_text = row_data["phan_tram_str"]
            pct_val  = row_data["phan_tram"]

            # Chọn màu nền theo % đạt
            if row_data["da_thi"] > 0:
                if pct_val >= 80:
                    bg = "#C8E6C9"  # xanh lá nhạt
                elif pct_val >= 50:
                    bg = "#FFF9C4"  # vàng nhạt
                else:
                    bg = "#FFCDD2"  # đỏ nhạt
            else:
                bg = None

            self._set_stats_cell(
                tbl, ri, 5,
                pct_text,
                is_tong=is_tong,
                bg_color=bg,
                bold=True,
            )

    @staticmethod
    def _set_stats_cell(
        tbl      : QTableWidget,
        row      : int,
        col      : int,
        text     : str,
        is_tong  : bool = False,
        fg_color : str  = None,
        bg_color : str  = None,
        bold     : bool = False,
    ) -> None:
        """Đặt giá trị + format cho 1 ô thống kê."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)

        font = QFont("Segoe UI", 10)
        if is_tong or bold:
            font.setBold(True)
        item.setFont(font)

        if is_tong and not bg_color:
            item.setBackground(QColor("#E8EAF6"))

        if fg_color:
            item.setForeground(QColor(fg_color))
        if bg_color:
            item.setBackground(QColor(bg_color))

        tbl.setItem(row, col, item)

    # ══════════════════════════════════════════════════════
    #  TÌM KIẾM
    # ══════════════════════════════════════════════════════

    def _on_search(self) -> None:
        """Áp dụng bộ lọc → load lại danh sách + thống kê."""
        self._load_data_table()
        self._load_stats()

    # ══════════════════════════════════════════════════════
    #  THÊM HỒ SƠ
    # ══════════════════════════════════════════════════════

    def _on_add_clicked(self) -> None:
        """Mở dialog thêm hồ sơ."""
        try:
            self.auth.require_action("add")
        except Exception as exc:
            QMessageBox.warning(self, "Phân quyền", str(exc))
            return

        dialog = HoSoDialog(
            mode="add", db_manager=self.db, parent=self
        )
        if dialog.exec() == QDialog.Accepted:
            data_nguoi, data_hoso = dialog.get_data()
            try:
                # Insert nguoi_lx
                self._insert_record("nguoi_lx", data_nguoi)
                # Insert ho_so_sh
                data_hoso["MA_DK"] = data_nguoi.get("MA_DK", "")
                self._insert_record("ho_so_sh", data_hoso)
                # Insert nhap_kqsh rỗng
                self.db._execute(
                    "INSERT OR IGNORE INTO nhap_kqsh (MA_DK) VALUES (?)",
                    (data_nguoi.get("MA_DK", ""),)
                )
                self.db.commit()

                self.logger.info(
                    module="HoSo", action="Them",
                    detail=f"MA_DK={data_nguoi.get('MA_DK')}"
                )
                self.refresh_data()
                self._notify_parent("✅ Thêm hồ sơ thành công.")
            except Exception as exc:
                self.db.rollback()
                QMessageBox.critical(self, "Lỗi", f"Lỗi thêm:\n{exc}")

    def on_add_clicked(self) -> None:
        """Public API cho MainWindow menu."""
        self._on_add_clicked()

    # ══════════════════════════════════════════════════════
    #  SỬA HỒ SƠ
    # ══════════════════════════════════════════════════════

    def _on_edit_clicked(self) -> None:
        try:
            self.auth.require_action("edit")
        except Exception as exc:
            QMessageBox.warning(self, "Phân quyền", str(exc))
            return

        ma_dk = self._get_selected_ma_dk()
        if not ma_dk:
            QMessageBox.information(self, "Thông báo", "Chọn 1 hồ sơ để sửa.")
            return

        # Load dữ liệu hiện tại
        nguoi = self.db._fetchone(
            "SELECT * FROM nguoi_lx WHERE MA_DK = ?", (ma_dk,)
        )
        hoso = self.db._fetchone(
            "SELECT * FROM ho_so_sh WHERE MA_DK = ?", (ma_dk,)
        )

        dialog = HoSoDialog(
            mode="edit", db_manager=self.db,
            nguoi_data=nguoi, hoso_data=hoso,
            parent=self,
        )
        if dialog.exec() == QDialog.Accepted:
            data_nguoi, data_hoso = dialog.get_data()
            try:
                self._update_record("nguoi_lx", data_nguoi, "MA_DK", ma_dk)
                self._update_record("ho_so_sh", data_hoso, "MA_DK", ma_dk)
                self.db.commit()

                self.logger.info(
                    module="HoSo", action="Sua",
                    detail=f"MA_DK={ma_dk}"
                )
                self.refresh_data()
                self._notify_parent("✅ Cập nhật thành công.")
            except Exception as exc:
                self.db.rollback()
                QMessageBox.critical(self, "Lỗi", f"Lỗi sửa:\n{exc}")

    # ══════════════════════════════════════════════════════
    #  XÓA HỒ SƠ
    # ══════════════════════════════════════════════════════

    def _on_delete_clicked(self) -> None:
        try:
            self.auth.require_action("delete")
        except Exception as exc:
            QMessageBox.warning(self, "Phân quyền", str(exc))
            return

        ma_dk = self._get_selected_ma_dk()
        if not ma_dk:
            QMessageBox.information(self, "Thông báo", "Chọn 1 hồ sơ để xóa.")
            return

        # Lấy tên để hiển thị
        row = self.db._fetchone(
            "SELECT HO_VA_TEN FROM nguoi_lx WHERE MA_DK = ?", (ma_dk,)
        )
        ho_ten = row.get("HO_VA_TEN", "") if row else ""

        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Xóa hồ sơ:\n\n"
            f"  Mã ĐK : {ma_dk}\n"
            f"  Họ tên : {ho_ten}\n\n"
            f"Xóa khỏi cả 3 bảng: nguoi_lx, ho_so_sh, nhap_kqsh.\n"
            f"Không thể hoàn tác!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                self.db._execute(
                    "DELETE FROM nhap_kqsh WHERE MA_DK = ?", (ma_dk,)
                )
                self.db._execute(
                    "DELETE FROM ho_so_sh WHERE MA_DK = ?", (ma_dk,)
                )
                self.db._execute(
                    "DELETE FROM nguoi_lx WHERE MA_DK = ?", (ma_dk,)
                )
                self.db.commit()

                self.logger.info(
                    module="HoSo", action="Xoa",
                    detail=f"MA_DK={ma_dk}; HO_TEN={ho_ten}"
                )
                self.refresh_data()
                self._notify_parent("✅ Đã xóa hồ sơ.")
            except Exception as exc:
                self.db.rollback()
                QMessageBox.critical(self, "Lỗi", f"Lỗi xóa:\n{exc}")

    # ══════════════════════════════════════════════════════
    #  TIỆN ÍCH
    # ══════════════════════════════════════════════════════

    def _get_selected_ma_dk(self) -> Optional[str]:
        """Lấy MA_DK của dòng đang chọn."""
        row = self.tbl_data.currentRow()
        if row < 0:
            return None
        item = self.tbl_data.item(row, 1)  # Cột MA_DK
        return item.text() if item else None

    def _on_selection_changed(self) -> None:
        ma_dk = self._get_selected_ma_dk()
        if ma_dk:
            # Lấy tên
            row_idx = self.tbl_data.currentRow()
            name_item = self.tbl_data.item(row_idx, 2)
            name = name_item.text() if name_item else ""
            self.lbl_selection.setText(f"Đang chọn: {ma_dk} - {name}")
        else:
            self.lbl_selection.setText("")

    def _insert_record(self, table: str, data: dict) -> None:
        """Insert dict vào bảng."""
        data = {k: v for k, v in data.items() if v}
        cols = ", ".join(data.keys())
        qs   = ", ".join(["?" for _ in data])
        self.db._execute(
            f"INSERT INTO {table} ({cols}) VALUES ({qs})",
            tuple(data.values())
        )

    def _update_record(
        self, table: str, data: dict, key_field: str, key_value: str
    ) -> None:
        """Update dict vào bảng theo key."""
        data = {k: v for k, v in data.items() if k != key_field}
        if not data:
            return
        sets = ", ".join([f"{k} = ?" for k in data.keys()])
        vals = list(data.values()) + [key_value]
        self.db._execute(
            f"UPDATE {table} SET {sets} WHERE {key_field} = ?",
            tuple(vals)
        )

    def _load_ky_sh_list(self) -> None:
        """Load danh sách kỳ SH vào ComboBox."""
        try:
            rows = self.db._fetchall(
                "SELECT MAKYSH, NGAYSH FROM ky_sh ORDER BY MAKYSH"
            )
            for r in rows:
                label = f"{r['MAKYSH']}"
                if r.get("NGAYSH"):
                    label += f" ({r['NGAYSH']})"
                self.cmb_ky_sh.addItem(label, r["MAKYSH"])
        except Exception:
            pass

    def _notify_parent(self, message: str) -> None:
        parent = self.parent()
        if parent and hasattr(parent, "show_status_message"):
            parent.show_status_message(message)


# ══════════════════════════════════════════════════════════
#  DIALOG THÊM / SỬA HỒ SƠ
# ══════════════════════════════════════════════════════════

DIALOG_STYLE = """
QDialog { background-color: #ffffff; }
QLabel { font-size: 10pt; }
QLineEdit, QComboBox, QDateEdit, QTextEdit {
    padding: 6px 8px; border: 1px solid #c5cae9;
    border-radius: 4px; font-size: 10pt;
}
QLineEdit:focus { border: 2px solid #1a237e; }
QTabBar::tab:selected { background: #1a237e; color: white; }
"""


class HoSoDialog(QDialog):
    """Dialog thêm / sửa hồ sơ (2 tab: Cá nhân + Hồ sơ SH)."""

    def __init__(
        self,
        mode        : str = "add",
        db_manager  : DatabaseManager = None,
        nguoi_data  : dict = None,
        hoso_data   : dict = None,
        parent      : QWidget = None,
    ) -> None:
        super().__init__(parent)
        self._mode  = mode
        self._db    = db_manager
        self._nguoi = nguoi_data or {}
        self._hoso  = hoso_data or {}

        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowTitle(
            "Thêm hồ sơ" if mode == "add"
            else f"Sửa hồ sơ: {self._nguoi.get('MA_DK', '')}"
        )
        self.setMinimumSize(700, 550)
        self._setup_ui()

        if mode == "edit":
            self._populate()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        from PySide6.QtWidgets import QTabWidget
        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_tab_nguoi(), "Thông tin cá nhân")
        self._tabs.addTab(self._create_tab_hoso(), "Hồ sơ sát hạch")
        layout.addWidget(self._tabs, 1)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        btn_box.button(QDialogButtonBox.Ok).setText("💾 Lưu")
        btn_box.button(QDialogButtonBox.Cancel).setText("❌ Hủy")
        layout.addWidget(btn_box)

    def _create_tab_nguoi(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setSpacing(10)
        f.setContentsMargins(20, 20, 20, 20)

        self.txt_ma_dk = QLineEdit()
        self.txt_ma_dk.setPlaceholderText("Mã đăng ký (bắt buộc)")
        if self._mode == "edit":
            self.txt_ma_dk.setReadOnly(True)
            self.txt_ma_dk.setStyleSheet("background: #f0f0f0;")
        f.addRow("Mã ĐK *:", self.txt_ma_dk)

        self.txt_ho_ten_dem = QLineEdit()
        f.addRow("Họ tên đệm:", self.txt_ho_ten_dem)

        self.txt_ten = QLineEdit()
        f.addRow("Tên:", self.txt_ten)

        self.txt_ho_va_ten = QLineEdit()
        self.txt_ho_va_ten.setPlaceholderText("Họ và tên đầy đủ")
        f.addRow("Họ và tên *:", self.txt_ho_va_ten)

        self.cmb_gioi_tinh = QComboBox()
        self.cmb_gioi_tinh.addItems(["", "Nam", "Nữ"])
        f.addRow("Giới tính:", self.cmb_gioi_tinh)

        self.txt_ngay_sinh = QLineEdit()
        self.txt_ngay_sinh.setPlaceholderText("DD/MM/YYYY")
        f.addRow("Ngày sinh:", self.txt_ngay_sinh)

        self.txt_cccd = QLineEdit()
        self.txt_cccd.setPlaceholderText("Số CCCD")
        f.addRow("Số CCCD:", self.txt_cccd)

        self.txt_noi_ct = QLineEdit()
        f.addRow("Nơi cư trú:", self.txt_noi_ct)

        return w

    def _create_tab_hoso(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setSpacing(10)
        f.setContentsMargins(20, 20, 20, 20)

        self.txt_so_ho_so = QLineEdit()
        f.addRow("Số hồ sơ:", self.txt_so_ho_so)

        self.cmb_hang = QComboBox()
        self.cmb_hang.addItem("", "")
        for h in ["A1","A2","B1","B2","C","D","E","F"]:
            self.cmb_hang.addItem(h, h)
        f.addRow("Hạng GPLX:", self.cmb_hang)

        self.txt_sbd = QLineEdit()
        f.addRow("Số báo danh:", self.txt_sbd)

        self.txt_ma_ky_sh = QLineEdit()
        f.addRow("Mã kỳ SH:", self.txt_ma_ky_sh)

        self.txt_noi_dung = QLineEdit()
        f.addRow("Nội dung SH:", self.txt_noi_dung)

        self.txt_ma_khoa = QLineEdit()
        f.addRow("Mã khóa học:", self.txt_ma_khoa)

        self.txt_ghi_chu = QTextEdit()
        self.txt_ghi_chu.setMaximumHeight(60)
        f.addRow("Ghi chú:", self.txt_ghi_chu)

        return w

    def _populate(self) -> None:
        """Điền dữ liệu khi sửa."""
        n = self._nguoi
        h = self._hoso

        self.txt_ma_dk.setText(n.get("MA_DK", ""))
        self.txt_ho_ten_dem.setText(n.get("HO_TEN_DEM", ""))
        self.txt_ten.setText(n.get("TEN", ""))
        self.txt_ho_va_ten.setText(n.get("HO_VA_TEN", ""))
        self.txt_ngay_sinh.setText(n.get("NGAY_SINH", ""))
        self.txt_cccd.setText(n.get("SO_CMT", ""))
        self.txt_noi_ct.setText(n.get("NOI_CT", ""))

        idx = self.cmb_gioi_tinh.findText(n.get("GIOI_TINH", ""))
        if idx >= 0:
            self.cmb_gioi_tinh.setCurrentIndex(idx)

        self.txt_so_ho_so.setText(h.get("SO_HO_SO", ""))
        self.txt_sbd.setText(h.get("SO_BAO_DANH", ""))
        self.txt_ma_ky_sh.setText(h.get("MA_KY_SH", ""))
        self.txt_noi_dung.setText(h.get("NOI_DUNG_SH", ""))
        self.txt_ma_khoa.setText(h.get("MA_KHOA_HOC", ""))
        self.txt_ghi_chu.setPlainText(h.get("GHI_CHU_SH", ""))

        idx_h = self.cmb_hang.findData(h.get("HANG_GPLX", ""))
        if idx_h >= 0:
            self.cmb_hang.setCurrentIndex(idx_h)

    def get_data(self) -> tuple[dict, dict]:
        """
        Thu thập dữ liệu từ form.

        Returns
        -------
        (nguoi_lx_dict, ho_so_sh_dict)
        """
        nguoi = {
            "MA_DK"       : self.txt_ma_dk.text().strip(),
            "HO_TEN_DEM"  : self.txt_ho_ten_dem.text().strip(),
            "TEN"         : self.txt_ten.text().strip(),
            "HO_VA_TEN"   : self.txt_ho_va_ten.text().strip(),
            "GIOI_TINH"   : self.cmb_gioi_tinh.currentText(),
            "NGAY_SINH"   : self.txt_ngay_sinh.text().strip(),
            "SO_CMT"      : self.txt_cccd.text().strip(),
            "NOI_CT"      : self.txt_noi_ct.text().strip(),
        }

        hoso = {
            "SO_HO_SO"    : self.txt_so_ho_so.text().strip(),
            "HANG_GPLX"   : self.cmb_hang.currentData() or "",
            "SO_BAO_DANH" : self.txt_sbd.text().strip(),
            "MA_KY_SH"    : self.txt_ma_ky_sh.text().strip(),
            "NOI_DUNG_SH" : self.txt_noi_dung.text().strip(),
            "MA_KHOA_HOC" : self.txt_ma_khoa.text().strip(),
            "GHI_CHU_SH"  : self.txt_ghi_chu.toPlainText().strip(),
        }

        return nguoi, hoso