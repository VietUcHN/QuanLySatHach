"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : ui/tab_config.py
Mô tả     : Tab Cấu hình v1.0
            - Sub-tab 1: Cấu hình nội dung thi
            - Sub-tab 2: Quản lý DVHC (tích hợp SQLite)
            - Sub-tab 3: Quản lý Tài khoản & Phân quyền
            - Sub-tab 4: Nhật ký hệ thống (Logs)
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

from pathlib  import Path
from datetime import datetime
from typing   import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFileDialog,
    QTextEdit,
    QDateEdit,
    QSpinBox,
    QSpacerItem,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui  import QColor, QFont

from config.config_loader    import ConfigLoader
from database.db_manager     import DatabaseManager
from services.auth_service   import (
    AuthService,
    AccountError,
    PermissionDeniedError,
    PermissionInfo,
)
from services.logger_service import LoggerService


# ══════════════════════════════════════════════════════════
#  STYLESHEET
# ══════════════════════════════════════════════════════════

TAB_CONFIG_STYLE = """
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

QPushButton {
    padding: 7px 14px;
    border-radius: 5px;
    font-size: 10pt;
    font-weight: bold;
    border: none;
    min-width: 75px;
}
QPushButton#btnPrimary  { background-color: #1a237e; color: white; }
QPushButton#btnPrimary:hover { background-color: #283593; }
QPushButton#btnSuccess  { background-color: #4CAF50; color: white; }
QPushButton#btnSuccess:hover { background-color: #388E3C; }
QPushButton#btnDanger   { background-color: #F44336; color: white; }
QPushButton#btnDanger:hover  { background-color: #C62828; }
QPushButton#btnWarning  { background-color: #FF9800; color: white; }
QPushButton#btnWarning:hover { background-color: #E65100; }
QPushButton#btnInfo     { background-color: #2196F3; color: white; }
QPushButton#btnInfo:hover    { background-color: #1565C0; }
QPushButton:disabled    { background-color: #bdbdbd; color: #757575; }

QLineEdit, QComboBox, QSpinBox {
    padding: 6px 10px;
    border: 1px solid #c5cae9;
    border-radius: 4px;
    font-size: 10pt;
}
QLineEdit:focus { border: 2px solid #1a237e; }

QTableWidget {
    border: 1px solid #c5cae9;
    border-radius: 4px;
    gridline-color: #e0e0e0;
    font-size: 9pt;
    alternate-background-color: #fafafa;
}
QTableWidget::item:selected {
    background-color: #bbdefb;
    color: #0d47a1;
}
QHeaderView::section {
    background-color: #1a237e;
    color: #ffffff;
    padding: 5px;
    border: 1px solid #283593;
    font-size: 9pt;
    font-weight: bold;
}

QTextEdit#logViewer {
    font-family: Consolas, monospace;
    font-size: 9pt;
    border: 1px solid #c5cae9;
    border-radius: 4px;
    background-color: #263238;
    color: #e0e0e0;
}

QCheckBox { font-size: 10pt; }
"""


# ══════════════════════════════════════════════════════════
#  CLASS TAB CONFIG
# ══════════════════════════════════════════════════════════

class TabConfig(QWidget):
    """
    Tab Cấu hình v1.0 gồm 4 sub-tab:
    1. 📝 Nội dung thi
    2. 🏛️ Quản lý DVHC
    3. 👥 Tài khoản & Phân quyền
    4. 📋 Nhật ký
    """

    def __init__(
        self,
        config_loader : ConfigLoader,
        dvhc_service,                    # có thể None
        logger        : LoggerService,
        auth_service  : AuthService = None,
        db_manager    : DatabaseManager = None,
        parent        : QWidget = None,
    ) -> None:
        super().__init__(parent)

        self.config = config_loader
        self.dvhc   = dvhc_service
        self.logger = logger
        self.auth   = auth_service
        self.db     = db_manager

        # Lấy db từ parent (MainWindow) nếu chưa có
        if not self.db and parent and hasattr(parent, 'get_db_manager'):
            self.db = parent.get_db_manager()
        if not self.auth and parent and hasattr(parent, 'get_auth_service'):
            self.auth = parent.get_auth_service()

        self.setStyleSheet(TAB_CONFIG_STYLE)
        self._setup_ui()

        QTimer.singleShot(300, self._load_initial_data)

    # ══════════════════════════════════════════════════════
    #  SETUP UI
    # ══════════════════════════════════════════════════════

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self._sub_tabs = QTabWidget()

        # Sub-tab 1: Nội dung thi
        self._sub_tabs.addTab(
            self._create_noidung_panel(), "📝 Nội dung thi"
        )

        # Sub-tab 2: DVHC
        self._sub_tabs.addTab(
            self._create_dvhc_panel(), "🏛️ DVHC"
        )

        # Sub-tab 3: Tài khoản & Phân quyền
        self._sub_tabs.addTab(
            self._create_user_panel(), "👥 Tài khoản"
        )

        # Sub-tab 4: Nhật ký
        self._sub_tabs.addTab(
            self._create_log_panel(), "📋 Nhật ký"
        )

        # Phân quyền sub-tab
        if self.auth and self.auth.current_permission:
            perm = self.auth.current_permission
            self._sub_tabs.setTabEnabled(2, perm.has_menu("user"))

        main_layout.addWidget(self._sub_tabs)

    # ══════════════════════════════════════════════════════
    #  SUB-TAB 1: NỘI DUNG THI
    # ══════════════════════════════════════════════════════

    def _create_noidung_panel(self) -> QWidget:
        panel  = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # Toolbar
        tb = QHBoxLayout()
        self.btn_nd_add = QPushButton("➕ Thêm")
        self.btn_nd_add.setObjectName("btnSuccess")
        self.btn_nd_add.clicked.connect(self._on_nd_add)
        tb.addWidget(self.btn_nd_add)

        self.btn_nd_edit = QPushButton("✏️ Sửa")
        self.btn_nd_edit.setObjectName("btnInfo")
        self.btn_nd_edit.clicked.connect(self._on_nd_edit)
        tb.addWidget(self.btn_nd_edit)

        self.btn_nd_delete = QPushButton("🗑️ Xóa")
        self.btn_nd_delete.setObjectName("btnDanger")
        self.btn_nd_delete.clicked.connect(self._on_nd_delete)
        tb.addWidget(self.btn_nd_delete)

        tb.addSpacerItem(QSpacerItem(15, 0, QSizePolicy.Fixed))

        self.btn_nd_save = QPushButton("💾 Lưu JSON")
        self.btn_nd_save.setObjectName("btnPrimary")
        self.btn_nd_save.clicked.connect(self._on_nd_save)
        tb.addWidget(self.btn_nd_save)

        self.btn_nd_reload = QPushButton("🔄 Tải lại")
        self.btn_nd_reload.setObjectName("btnWarning")
        self.btn_nd_reload.clicked.connect(self._on_nd_reload)
        tb.addWidget(self.btn_nd_reload)

        tb.addStretch()
        layout.addLayout(tb)

        # Bảng
        self.tbl_noidung = QTableWidget()
        self.tbl_noidung.setColumnCount(6)
        self.tbl_noidung.setHorizontalHeaderLabels([
            "Mã", "Lý thuyết", "Mô phỏng", "Sa hình", "Đường", "Ghi chú"
        ])
        self.tbl_noidung.setAlternatingRowColors(True)
        self.tbl_noidung.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_noidung.setSelectionBehavior(QAbstractItemView.SelectRows)
        h = self.tbl_noidung.horizontalHeader()
        for i in range(5):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.Stretch)

        layout.addWidget(self.tbl_noidung, 1)
        return panel

    # ══════════════════════════════════════════════════════
    #  SUB-TAB 2: DVHC
    # ══════════════════════════════════════════════════════

    def _create_dvhc_panel(self) -> QWidget:
        panel  = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # Toolbar
        tb = QHBoxLayout()

        self.btn_dvhc_sync = QPushButton("🔄 Đồng bộ JSON → SQLite")
        self.btn_dvhc_sync.setObjectName("btnPrimary")
        self.btn_dvhc_sync.clicked.connect(self._on_dvhc_sync)
        tb.addWidget(self.btn_dvhc_sync)

        tb.addStretch()

        self.lbl_dvhc_stats = QLabel("")
        self.lbl_dvhc_stats.setStyleSheet(
            "font-size: 10pt; color: #1a237e; font-weight: bold;"
        )
        tb.addWidget(self.lbl_dvhc_stats)

        layout.addLayout(tb)

        # Bộ lọc
        fl = QHBoxLayout()
        fl.addWidget(QLabel("🔍 Tìm:"))
        self.txt_dvhc_search = QLineEdit()
        self.txt_dvhc_search.setPlaceholderText("Mã hoặc tên ĐVHC...")
        self.txt_dvhc_search.setMinimumWidth(200)
        fl.addWidget(self.txt_dvhc_search)

        fl.addWidget(QLabel("Loại:"))
        self.cmb_dvhc_loai = QComboBox()
        self.cmb_dvhc_loai.setMinimumWidth(180)
        self.cmb_dvhc_loai.addItem("-- Tất cả --", "")
        for loai in ["Thành phố trực thuộc Trung ương", "Tỉnh",
                      "Quận", "Huyện", "Thị xã",
                      "Thành phố thuộc tỉnh", "Phường", "Thị trấn", "Xã"]:
            self.cmb_dvhc_loai.addItem(loai, loai)
        fl.addWidget(self.cmb_dvhc_loai)

        btn_dvhc_search = QPushButton("🔍 Lọc")
        btn_dvhc_search.setObjectName("btnInfo")
        btn_dvhc_search.clicked.connect(self._on_dvhc_filter)
        fl.addWidget(btn_dvhc_search)
        fl.addStretch()
        layout.addLayout(fl)

        # Debounce
        self._dvhc_timer = QTimer()
        self._dvhc_timer.setSingleShot(True)
        self._dvhc_timer.setInterval(300)
        self._dvhc_timer.timeout.connect(self._on_dvhc_filter)
        self.txt_dvhc_search.textChanged.connect(
            lambda: self._dvhc_timer.start()
        )

        # Bảng
        self.tbl_dvhc = QTableWidget()
        self.tbl_dvhc.setColumnCount(6)
        self.tbl_dvhc.setHorizontalHeaderLabels([
            "Mã DVHC", "Tên", "Tên ngắn", "Tên đầy đủ", "Loại", "Mã DVQL"
        ])
        self.tbl_dvhc.setAlternatingRowColors(True)
        self.tbl_dvhc.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_dvhc.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_dvhc.setSortingEnabled(True)
        h = self.tbl_dvhc.horizontalHeader()
        h.setSectionResizeMode(3, QHeaderView.Stretch)

        layout.addWidget(self.tbl_dvhc, 1)
        return panel

    # ══════════════════════════════════════════════════════
    #  SUB-TAB 3: TÀI KHOẢN & PHÂN QUYỀN
    # ══════════════════════════════════════════════════════

    def _create_user_panel(self) -> QWidget:
        """
        Panel quản lý tài khoản và phân quyền.

        ┌─────────────────────────────────────────────────────┐
        │ [➕ Thêm TK] [🔑 Reset MK] [🔒 Khóa/Mở] [🗑️ Xóa] │
        ├─────────────────────────────────────────────────────┤
        │ ┌── Danh sách tài khoản ──────────────────────┐    │
        │ │ ID│Username│Họ tên│Role│Active│Created│Login │    │
        │ └─────────────────────────────────────────────┘    │
        ├─────────────────────────────────────────────────────┤
        │ ┌── Phân quyền Role đang chọn ────────────────┐    │
        │ │ □ Main  □ Import  □ Export  □ Đối sánh       │    │
        │ │ □ Config □ User                              │    │
        │ │ □ Add   □ Edit   □ Delete  □ Print           │    │
        │ │                        [💾 Lưu quyền]        │    │
        │ └─────────────────────────────────────────────┘    │
        └─────────────────────────────────────────────────────┘
        """
        panel  = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # ── Toolbar tài khoản ──────────────────────────────
        tb = QHBoxLayout()

        self.btn_user_add = QPushButton("➕ Thêm TK")
        self.btn_user_add.setObjectName("btnSuccess")
        self.btn_user_add.clicked.connect(self._on_user_add)
        tb.addWidget(self.btn_user_add)

        self.btn_user_reset = QPushButton("🔑 Reset MK")
        self.btn_user_reset.setObjectName("btnWarning")
        self.btn_user_reset.clicked.connect(self._on_user_reset_pw)
        tb.addWidget(self.btn_user_reset)

        self.btn_user_toggle = QPushButton("🔒 Khóa/Mở")
        self.btn_user_toggle.setObjectName("btnInfo")
        self.btn_user_toggle.clicked.connect(self._on_user_toggle)
        tb.addWidget(self.btn_user_toggle)

        self.btn_user_delete = QPushButton("🗑️ Xóa")
        self.btn_user_delete.setObjectName("btnDanger")
        self.btn_user_delete.clicked.connect(self._on_user_delete)
        tb.addWidget(self.btn_user_delete)

        tb.addStretch()
        layout.addLayout(tb)

        # ── Bảng tài khoản ─────────────────────────────────
        self.tbl_users = QTableWidget()
        self.tbl_users.setColumnCount(7)
        self.tbl_users.setHorizontalHeaderLabels([
            "ID", "Username", "Họ tên", "Vai trò",
            "Trạng thái", "Ngày tạo", "Đăng nhập cuối"
        ])
        self.tbl_users.setAlternatingRowColors(True)
        self.tbl_users.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_users.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_users.setSelectionMode(QAbstractItemView.SingleSelection)
        h = self.tbl_users.horizontalHeader()
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(6, QHeaderView.Stretch)
        self.tbl_users.setColumnWidth(0, 40)
        self.tbl_users.setColumnWidth(1, 120)
        self.tbl_users.setColumnWidth(3, 100)
        self.tbl_users.setColumnWidth(4, 90)
        self.tbl_users.setColumnWidth(5, 120)

        self.tbl_users.itemSelectionChanged.connect(
            self._on_user_selected
        )

        layout.addWidget(self.tbl_users)

        # ── Phân quyền ─────────────────────────────────────
        self.grp_perm = QGroupBox("🔐 Phân quyền cho vai trò đang chọn")
        perm_layout = QVBoxLayout(self.grp_perm)

        # Dòng 1: Menu permissions
        menu_row = QHBoxLayout()
        menu_row.addWidget(QLabel("Menu:"))
        self.chk_menu_main     = QCheckBox("Main")
        self.chk_menu_import   = QCheckBox("Import")
        self.chk_menu_export   = QCheckBox("Export")
        self.chk_menu_doisanh  = QCheckBox("Đối sánh")
        self.chk_menu_config   = QCheckBox("Cấu hình")
        self.chk_menu_user     = QCheckBox("User")

        for chk in [self.chk_menu_main, self.chk_menu_import,
                     self.chk_menu_export, self.chk_menu_doisanh,
                     self.chk_menu_config, self.chk_menu_user]:
            menu_row.addWidget(chk)
        menu_row.addStretch()
        perm_layout.addLayout(menu_row)

        # Dòng 2: Action permissions
        action_row = QHBoxLayout()
        action_row.addWidget(QLabel("Thao tác:"))
        self.chk_can_add    = QCheckBox("Thêm")
        self.chk_can_edit   = QCheckBox("Sửa")
        self.chk_can_delete = QCheckBox("Xóa")
        self.chk_can_print  = QCheckBox("In")

        for chk in [self.chk_can_add, self.chk_can_edit,
                     self.chk_can_delete, self.chk_can_print]:
            action_row.addWidget(chk)
        action_row.addStretch()

        self.btn_save_perm = QPushButton("💾 Lưu quyền")
        self.btn_save_perm.setObjectName("btnPrimary")
        self.btn_save_perm.clicked.connect(self._on_save_permission)
        action_row.addWidget(self.btn_save_perm)

        perm_layout.addLayout(action_row)

        # Label role đang chọn
        self.lbl_perm_role = QLabel("Chọn 1 tài khoản để xem/sửa quyền.")
        self.lbl_perm_role.setStyleSheet(
            "font-size: 9pt; color: #666; font-style: italic;"
        )
        perm_layout.addWidget(self.lbl_perm_role)

        layout.addWidget(self.grp_perm)

        return panel

    # ══════════════════════════════════════════════════════
    #  SUB-TAB 4: NHẬT KÝ
    # ══════════════════════════════════════════════════════

    def _create_log_panel(self) -> QWidget:
        panel  = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # Toolbar
        tb = QHBoxLayout()
        self.btn_log_refresh = QPushButton("🔄 Tải lại")
        self.btn_log_refresh.setObjectName("btnPrimary")
        self.btn_log_refresh.clicked.connect(self._on_log_refresh)
        tb.addWidget(self.btn_log_refresh)

        self.btn_log_export = QPushButton("📊 Xuất Excel")
        self.btn_log_export.setObjectName("btnSuccess")
        self.btn_log_export.clicked.connect(self._on_log_export)
        tb.addWidget(self.btn_log_export)

        self.btn_log_clear = QPushButton("🗑️ Xóa cũ")
        self.btn_log_clear.setObjectName("btnDanger")
        self.btn_log_clear.clicked.connect(self._on_log_clear)
        tb.addWidget(self.btn_log_clear)

        tb.addStretch()

        self.lbl_log_count = QLabel("")
        self.lbl_log_count.setStyleSheet(
            "font-size: 10pt; color: #1a237e; font-weight: bold;"
        )
        tb.addWidget(self.lbl_log_count)
        layout.addLayout(tb)

        # Bộ lọc
        fl = QHBoxLayout()
        fl.addWidget(QLabel("Từ:"))
        self.date_log_from = QDateEdit()
        self.date_log_from.setCalendarPopup(True)
        self.date_log_from.setDisplayFormat("dd/MM/yyyy")
        self.date_log_from.setDate(QDate.currentDate().addDays(-30))
        fl.addWidget(self.date_log_from)

        fl.addWidget(QLabel("Đến:"))
        self.date_log_to = QDateEdit()
        self.date_log_to.setCalendarPopup(True)
        self.date_log_to.setDisplayFormat("dd/MM/yyyy")
        self.date_log_to.setDate(QDate.currentDate())
        fl.addWidget(self.date_log_to)

        fl.addWidget(QLabel("Module:"))
        self.cmb_log_module = QComboBox()
        self.cmb_log_module.setMinimumWidth(100)
        self.cmb_log_module.addItem("-- Tất cả --", "")
        for m in ["System","Auth","HoSo","IE","DVHC","Config","Log","Display","InitDB"]:
            self.cmb_log_module.addItem(m, m)
        fl.addWidget(self.cmb_log_module)

        fl.addWidget(QLabel("Level:"))
        self.cmb_log_level = QComboBox()
        self.cmb_log_level.addItem("-- Tất cả --", "")
        self.cmb_log_level.addItem("INFO", "INFO")
        self.cmb_log_level.addItem("WARNING", "WARNING")
        self.cmb_log_level.addItem("ERROR", "ERROR")
        fl.addWidget(self.cmb_log_level)

        fl.addWidget(QLabel("Từ khoá:"))
        self.txt_log_kw = QLineEdit()
        self.txt_log_kw.setPlaceholderText("Tìm...")
        self.txt_log_kw.setMaximumWidth(150)
        fl.addWidget(self.txt_log_kw)

        btn_log_filter = QPushButton("🔍 Lọc")
        btn_log_filter.setObjectName("btnInfo")
        btn_log_filter.clicked.connect(self._on_log_filter)
        fl.addWidget(btn_log_filter)

        layout.addLayout(fl)

        # Bảng log
        self.tbl_log = QTableWidget()
        self.tbl_log.setColumnCount(6)
        self.tbl_log.setHorizontalHeaderLabels([
            "Thời gian", "Level", "User", "Module", "Action", "Chi tiết"
        ])
        self.tbl_log.setAlternatingRowColors(True)
        self.tbl_log.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_log.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_log.setWordWrap(True)
        h = self.tbl_log.horizontalHeader()
        for i in range(5):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.Stretch)

        layout.addWidget(self.tbl_log, 1)
        return panel

    # ══════════════════════════════════════════════════════
    #  LOAD DỮ LIỆU BAN ĐẦU
    # ══════════════════════════════════════════════════════

    def _load_initial_data(self) -> None:
        self._load_noidung_table()
        self._load_dvhc_table()
        self._load_users_table()
        self._on_log_refresh()

    # ══════════════════════════════════════════════════════
    #  NỘI DUNG THI
    # ══════════════════════════════════════════════════════

    def _load_noidung_table(self) -> None:
        items = self.config.noidung_list
        self.tbl_noidung.setRowCount(len(items))
        for ri, item in enumerate(items):
            self.tbl_noidung.setItem(ri, 0, self._center(str(item.get("MA_NOI_DUNG",""))))
            for ci, f in enumerate(["LY_THUYET","MO_PHONG","HINH","DUONG"], 1):
                val = item.get(f, False)
                cell = QTableWidgetItem("✓" if val else "✗")
                cell.setTextAlignment(Qt.AlignCenter)
                cell.setForeground(QColor("#1B5E20" if val else "#B71C1C"))
                cell.setBackground(QColor("#E8F5E9" if val else "#FFEBEE"))
                ft = QFont(); ft.setBold(True); ft.setPointSize(12); cell.setFont(ft)
                self.tbl_noidung.setItem(ri, ci, cell)
            self.tbl_noidung.setItem(ri, 5, QTableWidgetItem(str(item.get("GHI_CHU",""))))

    def _on_nd_add(self) -> None:
        dialog = NoiDungDialog(mode="add", parent=self)
        if dialog.exec() == QDialog.Accepted:
            if self.config.add_noidung_item(dialog.get_data()):
                self._load_noidung_table()
            else:
                QMessageBox.warning(self, "Lỗi", "Mã đã tồn tại.")

    def _on_nd_edit(self) -> None:
        r = self.tbl_noidung.currentRow()
        if r < 0: return
        ma = self.tbl_noidung.item(r, 0).text()
        item = self.config.get_noidung_by_ma(ma)
        if not item: return
        dialog = NoiDungDialog(mode="edit", data=item, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.config.update_noidung_item(ma, dialog.get_data())
            self._load_noidung_table()

    def _on_nd_delete(self) -> None:
        r = self.tbl_noidung.currentRow()
        if r < 0: return
        ma = self.tbl_noidung.item(r, 0).text()
        if QMessageBox.question(self, "Xóa", f"Xóa mã '{ma}'?") == QMessageBox.Yes:
            self.config.delete_noidung_item(ma)
            self._load_noidung_table()

    def _on_nd_save(self) -> None:
        try:
            self.config.save_noidung(backup=True)
            QMessageBox.information(self, "OK", "Đã lưu!")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_nd_reload(self) -> None:
        try:
            self.config.load_noidung()
            self._load_noidung_table()
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))

    # ══════════════════════════════════════════════════════
    #  DVHC
    # ══════════════════════════════════════════════════════

    def _load_dvhc_table(self, keyword: str = "", loai: str = "") -> None:
        if not self.db:
            return
        try:
            sql = "SELECT * FROM dvhc WHERE 1=1"
            params = []
            if keyword:
                sql += " AND (CAST(MA_DVHC AS TEXT) LIKE ? OR TEN_DVHC LIKE ? OR TENDAYDU LIKE ?)"
                lk = f"%{keyword}%"
                params.extend([lk, lk, lk])
            if loai:
                sql += " AND LOAIDVHC = ?"
                params.append(loai)
            sql += " ORDER BY MA_DVHC LIMIT 2000"

            rows = self.db._fetchall(sql, tuple(params))
            self.tbl_dvhc.setSortingEnabled(False)
            self.tbl_dvhc.setRowCount(len(rows))

            for ri, row in enumerate(rows):
                fields = ["MA_DVHC","TEN_DVHC","TENNGANGON","TENDAYDU","LOAIDVHC","MA_DVQL"]
                for ci, f in enumerate(fields):
                    val = str(row.get(f, "") or "")
                    item = QTableWidgetItem(val)
                    if ci in (0, 5):
                        item.setTextAlignment(Qt.AlignCenter)
                    self.tbl_dvhc.setItem(ri, ci, item)

            self.tbl_dvhc.setSortingEnabled(True)
            self.lbl_dvhc_stats.setText(f"Hiển thị: {len(rows)} ĐVHC")
        except Exception:
            pass

    def _on_dvhc_filter(self) -> None:
        kw   = self.txt_dvhc_search.text().strip()
        loai = self.cmb_dvhc_loai.currentData() or ""
        self._load_dvhc_table(kw, loai)

    def _on_dvhc_sync(self) -> None:
        """Đồng bộ dvhc.json → bảng dvhc trong SQLite."""
        if not self.config.is_dvhc_loaded:
            QMessageBox.warning(self, "Lỗi", "Chưa load dvhc.json.")
            return

        data = self.config.dvhc_data
        reply = QMessageBox.question(
            self, "Đồng bộ",
            f"Đồng bộ {len(data)} bản ghi ĐVHC vào SQLite?\n"
            f"Dữ liệu cũ sẽ bị xóa.",
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.db._execute("DELETE FROM dvhc")
            sql = "INSERT INTO dvhc (MA_DVHC,MA_DVQL,MA_DV,TEN_DVHC,TENNGANGON,TENDAYDU,LOAIDVHC) VALUES (?,?,?,?,?,?,?)"
            rows = [(d.get("MA_DVHC"),d.get("MA_DVQL"),d.get("MA_DV"),
                      d.get("TEN_DVHC"),d.get("TENNGANGON"),d.get("TENDAYDU"),
                      d.get("LOAIDVHC")) for d in data]
            with self.db._lock:
                self.db._conn.executemany(sql, rows)
            self.db.commit()

            self._load_dvhc_table()
            QMessageBox.information(self, "OK", f"Đồng bộ {len(rows)} ĐVHC!")
            self.logger.info(module="DVHC", action="Sync", detail=f"{len(rows)} ban ghi")
        except Exception as exc:
            self.db.rollback()
            QMessageBox.critical(self, "Lỗi", str(exc))

    # ══════════════════════════════════════════════════════
    #  TÀI KHOẢN & PHÂN QUYỀN
    # ══════════════════════════════════════════════════════

    def _load_users_table(self) -> None:
        """Load danh sách tài khoản."""
        if not self.auth:
            return
        try:
            accounts = self.auth.get_all_accounts()
            self.tbl_users.setRowCount(len(accounts))

            for ri, acc in enumerate(accounts):
                # ID
                self.tbl_users.setItem(ri, 0, self._center(str(acc.get("id",""))))

                # Username
                self.tbl_users.setItem(ri, 1, QTableWidgetItem(acc.get("username","")))

                # Họ tên
                self.tbl_users.setItem(ri, 2, QTableWidgetItem(acc.get("full_name","")))

                # Role
                role_item = QTableWidgetItem(acc.get("role_name",""))
                role_item.setTextAlignment(Qt.AlignCenter)
                if acc.get("role_name") == "admin":
                    role_item.setForeground(QColor("#B71C1C"))
                    ft = QFont(); ft.setBold(True); role_item.setFont(ft)
                self.tbl_users.setItem(ri, 3, role_item)

                # Trạng thái
                active = acc.get("is_active", 0)
                status_item = QTableWidgetItem("✅ Active" if active else "🔒 Locked")
                status_item.setTextAlignment(Qt.AlignCenter)
                if not active:
                    status_item.setForeground(QColor("#B71C1C"))
                    status_item.setBackground(QColor("#FFEBEE"))
                else:
                    status_item.setForeground(QColor("#1B5E20"))
                    status_item.setBackground(QColor("#E8F5E9"))
                self.tbl_users.setItem(ri, 4, status_item)

                # Ngày tạo
                self.tbl_users.setItem(ri, 5, QTableWidgetItem(acc.get("created_at","")))

                # Login cuối
                self.tbl_users.setItem(ri, 6, QTableWidgetItem(acc.get("last_login","") or "---"))

        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", f"Lỗi load users:\n{exc}")

    def _get_selected_account_id(self) -> Optional[int]:
        r = self.tbl_users.currentRow()
        if r < 0:
            return None
        item = self.tbl_users.item(r, 0)
        try:
            return int(item.text()) if item else None
        except (ValueError, TypeError):
            return None

    def _on_user_selected(self) -> None:
        """Khi chọn tài khoản → load permission của role."""
        acc_id = self._get_selected_account_id()
        if not acc_id or not self.auth:
            return

        acc = self.auth.get_account_by_id(acc_id)
        if not acc:
            return

        role_id   = acc.get("role_id", 0)
        role_name = acc.get("role_name", "")
        username  = acc.get("username", "")

        self.lbl_perm_role.setText(
            f"Quyền của: {username} (Role: {role_name}, ID={role_id})"
        )

        # Load permission
        perm = self.auth.get_permission_for_role(role_id)
        if perm:
            self.chk_menu_main.setChecked(perm.menu_main == 1)
            self.chk_menu_import.setChecked(perm.menu_import == 1)
            self.chk_menu_export.setChecked(perm.menu_export == 1)
            self.chk_menu_doisanh.setChecked(perm.menu_doi_sanh == 1)
            self.chk_menu_config.setChecked(perm.menu_config == 1)
            self.chk_menu_user.setChecked(perm.menu_user == 1)
            self.chk_can_add.setChecked(perm.can_add == 1)
            self.chk_can_edit.setChecked(perm.can_edit == 1)
            self.chk_can_delete.setChecked(perm.can_delete == 1)
            self.chk_can_print.setChecked(perm.can_print == 1)

    def _on_save_permission(self) -> None:
        """Lưu thay đổi phân quyền."""
        acc_id = self._get_selected_account_id()
        if not acc_id or not self.auth:
            QMessageBox.information(self, "Thông báo", "Chọn 1 tài khoản.")
            return

        acc = self.auth.get_account_by_id(acc_id)
        if not acc:
            return
        role_id = acc.get("role_id", 0)

        perms = {
            "menu_main"     : 1 if self.chk_menu_main.isChecked() else 0,
            "menu_import"   : 1 if self.chk_menu_import.isChecked() else 0,
            "menu_export"   : 1 if self.chk_menu_export.isChecked() else 0,
            "menu_doi_sanh" : 1 if self.chk_menu_doisanh.isChecked() else 0,
            "menu_config"   : 1 if self.chk_menu_config.isChecked() else 0,
            "menu_user"     : 1 if self.chk_menu_user.isChecked() else 0,
            "can_add"       : 1 if self.chk_can_add.isChecked() else 0,
            "can_edit"      : 1 if self.chk_can_edit.isChecked() else 0,
            "can_delete"    : 1 if self.chk_can_delete.isChecked() else 0,
            "can_print"     : 1 if self.chk_can_print.isChecked() else 0,
        }

        try:
            self.auth.update_permission(role_id, perms)
            QMessageBox.information(self, "OK", "Đã lưu phân quyền!")
            self.logger.info(
                module="Config", action="SavePermission",
                detail=f"role_id={role_id}"
            )
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))

    def _on_user_add(self) -> None:
        """Thêm tài khoản mới."""
        dialog = AddUserDialog(auth_service=self.auth, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._load_users_table()

    def _on_user_reset_pw(self) -> None:
        """Reset mật khẩu."""
        acc_id = self._get_selected_account_id()
        if not acc_id:
            QMessageBox.information(self, "Thông báo", "Chọn 1 tài khoản.")
            return

        reply = QMessageBox.question(
            self, "Reset mật khẩu",
            f"Reset mật khẩu tài khoản ID={acc_id} về '123456'?",
        )
        if reply == QMessageBox.Yes:
            try:
                self.auth.reset_password(acc_id, "123456")
                QMessageBox.information(self, "OK", "Đã reset MK → '123456'")
            except Exception as exc:
                QMessageBox.warning(self, "Lỗi", str(exc))

    def _on_user_toggle(self) -> None:
        """Khóa / mở khóa tài khoản."""
        acc_id = self._get_selected_account_id()
        if not acc_id:
            return
        try:
            self.auth.toggle_account(acc_id)
            self._load_users_table()
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))

    def _on_user_delete(self) -> None:
        """Xóa tài khoản."""
        acc_id = self._get_selected_account_id()
        if not acc_id:
            return
        reply = QMessageBox.question(
            self, "Xóa",
            f"Xóa tài khoản ID={acc_id}?\nKhông thể hoàn tác!",
        )
        if reply == QMessageBox.Yes:
            try:
                self.auth.delete_account(acc_id)
                self._load_users_table()
            except Exception as exc:
                QMessageBox.warning(self, "Lỗi", str(exc))

    # ══════════════════════════════════════════════════════
    #  NHẬT KÝ
    # ══════════════════════════════════════════════════════

    def _on_log_refresh(self) -> None:
        records = self.logger.read_all()
        self._display_logs(records)

    def _on_log_filter(self) -> None:
        records = self.logger.filter_logs(
            date_from = self.date_log_from.date().toString("yyyy-MM-dd"),
            date_to   = self.date_log_to.date().toString("yyyy-MM-dd"),
            module    = self.cmb_log_module.currentData() or None,
            level     = self.cmb_log_level.currentData() or None,
            keyword   = self.txt_log_kw.text().strip() or None,
        )
        self._display_logs(records)

    def _display_logs(self, records: list[dict]) -> None:
        records = list(reversed(records))
        self.tbl_log.setRowCount(len(records))

        styles = {
            "INFO"    : ("#E3F2FD", "#0D47A1"),
            "WARNING" : ("#FFF3E0", "#E65100"),
            "ERROR"   : ("#FFEBEE", "#B71C1C"),
        }

        for ri, rec in enumerate(records):
            level = rec.get("level", "").upper().strip()
            bg, fg = styles.get(level, ("#FAFAFA", "#333"))

            fields = [
                rec.get("timestamp",""), level,
                rec.get("user",""), rec.get("module",""),
                rec.get("action",""), rec.get("detail",""),
            ]
            for ci, val in enumerate(fields):
                item = QTableWidgetItem(str(val).strip())
                item.setBackground(QColor(bg))
                item.setForeground(QColor(fg))
                if ci in (1, 2, 3):
                    item.setTextAlignment(Qt.AlignCenter)
                if level == "ERROR":
                    ft = QFont(); ft.setBold(True); item.setFont(ft)
                self.tbl_log.setItem(ri, ci, item)

        self.tbl_log.verticalHeader().setDefaultSectionSize(28)
        self.lbl_log_count.setText(f"📋 {len(records)} bản ghi")

    def _on_log_export(self) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "Xuất log", f"NhatKy_{ts}.xlsx", "Excel (*.xlsx)",
        )
        if path:
            if self.logger.export_to_excel(path):
                QMessageBox.information(self, "OK", f"Xuất log: {path}")
            else:
                QMessageBox.warning(self, "Lỗi", "Không xuất được.")

    def _on_log_clear(self) -> None:
        if QMessageBox.question(self, "Xóa", "Xóa log > 30 ngày?") == QMessageBox.Yes:
            n = self.logger.clear_old_logs(30)
            QMessageBox.information(self, "OK", f"Đã xóa {n} dòng.")
            self._on_log_refresh()

    # ══════════════════════════════════════════════════════
    #  TIỆN ÍCH
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _center(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item


# ══════════════════════════════════════════════════════════
#  DIALOG NỘI DUNG THI
# ══════════════════════════════════════════════════════════

class NoiDungDialog(QDialog):
    def __init__(self, mode="add", data=None, parent=None):
        super().__init__(parent)
        self._mode = mode
        self.setWindowTitle("Thêm nội dung" if mode=="add" else "Sửa nội dung")
        self.setMinimumWidth(380)
        f = QFormLayout(self)
        f.setSpacing(12)
        f.setContentsMargins(20,20,20,20)

        self.txt_ma = QLineEdit()
        if mode == "edit": self.txt_ma.setReadOnly(True)
        f.addRow("Mã:", self.txt_ma)

        self.chk_lt = QCheckBox("Lý thuyết")
        self.chk_mp = QCheckBox("Mô phỏng")
        self.chk_h  = QCheckBox("Sa hình")
        self.chk_d  = QCheckBox("Đường")
        for c in [self.chk_lt,self.chk_mp,self.chk_h,self.chk_d]:
            f.addRow("", c)

        self.txt_gc = QLineEdit()
        f.addRow("Ghi chú:", self.txt_gc)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

        if data:
            self.txt_ma.setText(str(data.get("MA_NOI_DUNG","")))
            self.chk_lt.setChecked(data.get("LY_THUYET",False))
            self.chk_mp.setChecked(data.get("MO_PHONG",False))
            self.chk_h.setChecked(data.get("HINH",False))
            self.chk_d.setChecked(data.get("DUONG",False))
            self.txt_gc.setText(data.get("GHI_CHU",""))

    def get_data(self):
        return {
            "MA_NOI_DUNG": self.txt_ma.text().strip(),
            "LY_THUYET": self.chk_lt.isChecked(),
            "MO_PHONG": self.chk_mp.isChecked(),
            "HINH": self.chk_h.isChecked(),
            "DUONG": self.chk_d.isChecked(),
            "GHI_CHU": self.txt_gc.text().strip(),
        }


# ══════════════════════════════════════════════════════════
#  DIALOG THÊM TÀI KHOẢN
# ══════════════════════════════════════════════════════════

class AddUserDialog(QDialog):
    """Dialog thêm tài khoản mới."""

    def __init__(self, auth_service: AuthService, parent=None):
        super().__init__(parent)
        self._auth = auth_service
        self.setWindowTitle("Thêm tài khoản")
        self.setMinimumWidth(420)

        f = QFormLayout(self)
        f.setSpacing(12)
        f.setContentsMargins(25, 25, 25, 25)

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Tên đăng nhập (unique)")
        f.addRow("Username *:", self.txt_username)

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Tối thiểu 4 ký tự")
        f.addRow("Mật khẩu *:", self.txt_password)

        self.txt_fullname = QLineEdit()
        self.txt_fullname.setPlaceholderText("Họ và tên")
        f.addRow("Họ tên:", self.txt_fullname)

        self.cmb_role = QComboBox()
        roles = self._auth.get_all_roles()
        for r in roles:
            self.cmb_role.addItem(
                f"{r.role_name} - {r.description}", r.id
            )
        f.addRow("Vai trò:", self.cmb_role)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_create)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.Ok).setText("💾 Tạo")
        f.addRow(bb)

    def _on_create(self) -> None:
        username = self.txt_username.text().strip()
        password = self.txt_password.text()
        fullname = self.txt_fullname.text().strip()
        role_id  = self.cmb_role.currentData()

        if not username or not password:
            QMessageBox.warning(self, "Lỗi", "Nhập đầy đủ Username + MK.")
            return

        try:
            self._auth.create_account(
                username=username,
                password=password,
                full_name=fullname,
                role_id=role_id,
            )
            QMessageBox.information(
                self, "OK", f"Tạo tài khoản '{username}' thành công!"
            )
            self.accept()
        except AccountError as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))