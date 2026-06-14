"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : ui/main_window.py
Mô tả     : Cửa sổ chính v1.0
            - Tích hợp AuthService (đăng nhập + phân quyền)
            - MenuBar / StatusBar theo quyền
            - Quản lý kết nối services mới
            - 3 tab: Main / IE / Cấu hình
            - Dialog đăng nhập khi khởi động
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

from pathlib  import Path
from datetime import datetime
from typing   import Optional

from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QStatusBar,
    QLabel,
    QMessageBox,
    QFileDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QCheckBox,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui  import QAction, QFont, QCloseEvent, QIcon

from config.config_loader       import ConfigLoader
from database.db_manager        import DatabaseManager
from database.init_db           import (
    initialize_database,
    get_database_info,
    check_database_integrity,
)
from services.logger_service    import LoggerService
from services.auth_service      import (
    AuthService,
    LoginError,
    PermissionDeniedError,
)
from services.ie_service        import IEService
from services.display_service   import DisplayService

from ui.tab_main   import TabMain
from ui.tab_ie     import TabIE
from ui.tab_config import TabConfig


# ══════════════════════════════════════════════════════════
#  STYLESHEET
# ══════════════════════════════════════════════════════════

MAIN_STYLESHEET = """
QMainWindow {
    background-color: #f5f5f5;
}

QTabWidget::pane {
    border: 1px solid #cccccc;
    background-color: #ffffff;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #e0e0e0;
    color: #333333;
    padding: 10px 25px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 11pt;
    font-weight: bold;
    min-width: 120px;
}

QTabBar::tab:selected {
    background-color: #1a237e;
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #bbdefb;
    color: #0d47a1;
}

QTabBar::tab:disabled {
    background-color: #e0e0e0;
    color: #999999;
}

QMenuBar {
    background-color: #1a237e;
    color: #ffffff;
    padding: 2px;
    font-size: 10pt;
}

QMenuBar::item {
    padding: 6px 15px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #283593;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    padding: 5px;
}

QMenu::item {
    padding: 8px 30px;
    color: #333333;
}

QMenu::item:selected {
    background-color: #e3f2fd;
    color: #0d47a1;
}

QMenu::item:disabled {
    color: #aaaaaa;
}

QMenu::separator {
    height: 1px;
    background: #e0e0e0;
    margin: 3px 10px;
}

QStatusBar {
    background-color: #1a237e;
    color: #ffffff;
    font-size: 9pt;
    padding: 3px;
}

QStatusBar::item {
    border: none;
}
"""


# ══════════════════════════════════════════════════════════
#  DIALOG ĐĂNG NHẬP
# ══════════════════════════════════════════════════════════

LOGIN_DIALOG_STYLE = """
QDialog {
    background-color: #ffffff;
}

QLabel#lblTitle {
    font-size: 16pt;
    font-weight: bold;
    color: #1a237e;
    padding: 10px;
}

QLabel#lblSubtitle {
    font-size: 9pt;
    color: #666666;
    padding-bottom: 10px;
}

QLineEdit {
    padding: 10px 12px;
    border: 2px solid #c5cae9;
    border-radius: 6px;
    font-size: 11pt;
    min-width: 280px;
}

QLineEdit:focus {
    border: 2px solid #1a237e;
}

QPushButton#btnLogin {
    background-color: #1a237e;
    color: white;
    padding: 10px 30px;
    border-radius: 6px;
    font-size: 11pt;
    font-weight: bold;
    min-width: 120px;
}

QPushButton#btnLogin:hover {
    background-color: #283593;
}

QPushButton#btnCancel {
    background-color: #e0e0e0;
    color: #333333;
    padding: 10px 30px;
    border-radius: 6px;
    font-size: 11pt;
    min-width: 100px;
}

QPushButton#btnCancel:hover {
    background-color: #bdbdbd;
}

QLabel#lblError {
    color: #B71C1C;
    font-size: 10pt;
    font-weight: bold;
    padding: 5px;
}
"""


class LoginDialog(QDialog):
    """
    Dialog đăng nhập khi khởi động phần mềm.

    ┌────────────────────────────────────┐
    │    QUẢN LÝ SÁT HẠCH GPLX         │
    │    Đăng nhập hệ thống             │
    │                                    │
    │  Tên đăng nhập: [____________]     │
    │  Mật khẩu:      [____________]     │
    │  □ Hiện mật khẩu                   │
    │                                    │
    │  ⚠️ Sai mật khẩu!                  │
    │                                    │
    │      [Đăng nhập]  [Thoát]          │
    └────────────────────────────────────┘
    """

    def __init__(
        self,
        auth_service : AuthService,
        parent       : QWidget = None,
    ) -> None:
        super().__init__(parent)
        self._auth = auth_service
        self._user_info = None

        self.setWindowTitle("Đăng nhập")
        self.setFixedSize(420, 380)
        self.setStyleSheet(LOGIN_DIALOG_STYLE)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint
        )

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(30, 20, 30, 20)

        # Tiêu đề
        lbl_title = QLabel("QUẢN LÝ SÁT HẠCH GPLX")
        lbl_title.setObjectName("lblTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Đăng nhập hệ thống")
        lbl_sub.setObjectName("lblSubtitle")
        lbl_sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_sub)

        layout.addSpacing(10)

        # Form
        form = QFormLayout()
        form.setSpacing(12)

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Nhập tên đăng nhập...")
        self.txt_username.setText("admin")
        form.addRow("Tên đăng nhập:", self.txt_username)

        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Nhập mật khẩu...")
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.returnPressed.connect(self._on_login)
        form.addRow("Mật khẩu:", self.txt_password)

        layout.addLayout(form)

        # Hiện mật khẩu
        self.chk_show_pw = QCheckBox("Hiện mật khẩu")
        self.chk_show_pw.setStyleSheet("font-size: 9pt; color: #666;")
        self.chk_show_pw.toggled.connect(self._toggle_password)
        layout.addWidget(self.chk_show_pw)

        # Label lỗi
        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("lblError")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        layout.addSpacing(10)

        # Nút
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        from PySide6.QtWidgets import QPushButton

        self.btn_login = QPushButton("🔐  Đăng nhập")
        self.btn_login.setObjectName("btnLogin")
        self.btn_login.clicked.connect(self._on_login)
        btn_layout.addWidget(self.btn_login)

        self.btn_cancel = QPushButton("Thoát")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

        # Focus username
        self.txt_username.setFocus()
        self.txt_username.selectAll()

    def _toggle_password(self, checked: bool) -> None:
        if checked:
            self.txt_password.setEchoMode(QLineEdit.Normal)
        else:
            self.txt_password.setEchoMode(QLineEdit.Password)

    def _on_login(self) -> None:
        """Xử lý đăng nhập."""
        username = self.txt_username.text().strip()
        password = self.txt_password.text()

        if not username or not password:
            self._show_error("Vui lòng nhập đầy đủ thông tin.")
            return

        try:
            self._user_info = self._auth.login(username, password)
            self.accept()

        except LoginError as exc:
            self._show_error(str(exc))
            self.txt_password.setFocus()
            self.txt_password.selectAll()

    def _show_error(self, message: str) -> None:
        self.lbl_error.setText(f"⚠️ {message}")
        self.lbl_error.setVisible(True)

    @property
    def user_info(self):
        return self._user_info


# ══════════════════════════════════════════════════════════
#  CLASS MAIN WINDOW
# ══════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    """
    Cửa sổ chính v1.0.

    Tính năng:
    - Tích hợp AuthService (đăng nhập + phân quyền)
    - Tab bị ẩn/disable nếu không có quyền
    - Menu action disable theo permission
    - StatusBar hiển thị user + role
    - Sử dụng CSDL mới (8 bảng)
    """

    def __init__(
        self,
        db_path     : str,
        config_path : str,
        dvhc_path   : str,
        logger      : LoggerService,
        auth_service: AuthService,
        parent      : QWidget = None,
    ) -> None:
        super().__init__(parent)

        self._db_path     = db_path
        self._config_path = config_path
        self._dvhc_path   = dvhc_path
        self._logger      = logger
        self._auth        = auth_service

        # ── Khởi tạo services ─────────────────────────────
        self._init_services()

        # ── Thiết lập UI ──────────────────────────────────
        self._setup_window()
        self._setup_menubar()
        self._setup_tabs()
        self._setup_statusbar()

        # ── Stylesheet ────────────────────────────────────
        self.setStyleSheet(MAIN_STYLESHEET)

        # ── Timer đồng hồ ─────────────────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_clock)
        self._timer.start(1000)

        # ── Áp dụng phân quyền ────────────────────────────
        self._apply_permissions()
        self._update_status_info()

    # ══════════════════════════════════════════════════════
    #  KHỞI TẠO SERVICES
    # ══════════════════════════════════════════════════════

    def _init_services(self) -> None:
        """Khởi tạo services phù hợp CSDL mới."""

        # ConfigLoader
        self._config_loader = ConfigLoader(self._config_path)
        try:
            self._config_loader.load_noidung()
        except Exception:
            ConfigLoader.create_default_noidung(self._config_path)
            self._config_loader.load_noidung()

        try:
            self._config_loader.load_dvhc(self._dvhc_path)
        except Exception:
            pass

        # DatabaseManager
        self._db_manager = DatabaseManager(
            db_path=self._db_path, logger=self._logger,
        )
        self._db_manager.connect()

        # IEService (hợp nhất import/export, dùng db trực tiếp)
        self._ie_service = IEService(
            db_manager=self._db_manager,
            logger=self._logger,
        )

        # DisplayService
        self._display_service = DisplayService(
            db_manager=self._db_manager,
            logger=self._logger,
        )

    # ══════════════════════════════════════════════════════
    #  THIẾT LẬP CỬA SỔ
    # ══════════════════════════════════════════════════════

    def _setup_window(self) -> None:
        user = self._auth.current_user
        role = user.role_name if user else ""
        name = user.full_name if user else ""

        self.setWindowTitle(
            f"Quản lý dữ liệu sát hạch GPLX v1.0  ─  "
            f"{name} ({role})"
        )
        self.setMinimumSize(1200, 700)

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.setGeometry(
                geo.x() + (geo.width()  - 1400) // 2,
                geo.y() + (geo.height() - 850)  // 2,
                1400, 850,
            )

    # ══════════════════════════════════════════════════════
    #  MENU BAR
    # ══════════════════════════════════════════════════════

    def _setup_menubar(self) -> None:
        menubar = self.menuBar()

        # ── Menu Hệ thống ─────────────────────────────────
        menu_system = menubar.addMenu("  Hệ thống  ")

        self.act_backup = QAction("Sao lưu Database", self)
        self.act_backup.triggered.connect(self._on_backup_db)
        menu_system.addAction(self.act_backup)

        self.act_vacuum = QAction("Tối ưu Database", self)
        self.act_vacuum.triggered.connect(self._on_vacuum_db)
        menu_system.addAction(self.act_vacuum)

        menu_system.addSeparator()

        self.act_db_info = QAction("Thông tin Database", self)
        self.act_db_info.triggered.connect(self._on_db_info)
        menu_system.addAction(self.act_db_info)

        self.act_integrity = QAction("Kiểm tra toàn vẹn", self)
        self.act_integrity.triggered.connect(self._on_check_integrity)
        menu_system.addAction(self.act_integrity)

        menu_system.addSeparator()

        self.act_change_pw = QAction("Đổi mật khẩu", self)
        self.act_change_pw.triggered.connect(self._on_change_password)
        menu_system.addAction(self.act_change_pw)

        self.act_logout = QAction("Đăng xuất", self)
        self.act_logout.triggered.connect(self._on_logout)
        menu_system.addAction(self.act_logout)

        menu_system.addSeparator()

        act_exit = QAction("Thoát", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        menu_system.addAction(act_exit)

        # ── Menu Dữ liệu ─────────────────────────────────
        menu_data = menubar.addMenu("  Dữ liệu  ")

        self.act_import_xml = QAction("Import XML", self)
        self.act_import_xml.setShortcut("Ctrl+I")
        self.act_import_xml.triggered.connect(self._on_import_xml)
        menu_data.addAction(self.act_import_xml)

        menu_data.addSeparator()

        self.act_export_excel = QAction("Export Excel", self)
        self.act_export_excel.setShortcut("Ctrl+E")
        self.act_export_excel.triggered.connect(self._on_export_excel)
        menu_data.addAction(self.act_export_excel)

        self.act_export_csv = QAction("Export CSV", self)
        self.act_export_csv.triggered.connect(self._on_export_csv)
        menu_data.addAction(self.act_export_csv)

        self.act_export_pdf = QAction("Export PDF", self)
        self.act_export_pdf.triggered.connect(self._on_export_pdf)
        menu_data.addAction(self.act_export_pdf)

        # ── Menu Trợ giúp ─────────────────────────────────
        menu_help = menubar.addMenu("  Trợ giúp  ")

        act_about = QAction("Về phần mềm", self)
        act_about.triggered.connect(self._on_about)
        menu_help.addAction(act_about)

        act_shortcuts = QAction("Phím tắt", self)
        act_shortcuts.triggered.connect(self._on_shortcuts)
        menu_help.addAction(act_shortcuts)

    # ══════════════════════════════════════════════════════
    #  TAB WIDGET
    # ══════════════════════════════════════════════════════

    def _setup_tabs(self) -> None:
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabPosition(QTabWidget.North)
        self._tab_widget.setMovable(False)
        self._tab_widget.setDocumentMode(True)

        # Tab 0: Main
        self._tab_main = TabMain(
            db_manager      = self._db_manager,
            display_service = self._display_service,
            auth_service    = self._auth,
            logger          = self._logger,
            parent          = self,
        )
        self._tab_widget.addTab(self._tab_main, "  📋  Main  ")

        # Tab 1: IE
        self._tab_ie = TabIE(
            ie_service       = self._ie_service,
            nguoi_lx_service = None,  # IE dùng db trực tiếp
            logger           = self._logger,
            parent           = self,
        )
        self._tab_widget.addTab(self._tab_ie, "  📥  Import/Export  ")

        # Tab 2: Cấu hình
        self._tab_config = TabConfig(
            config_loader = self._config_loader,
            dvhc_service  = None,
            logger        = self._logger,
            parent        = self,
        )
        self._tab_widget.addTab(self._tab_config, "  ⚙  Cấu hình  ")

        # Signal
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tab_widget)

    # ══════════════════════════════════════════════════════
    #  STATUS BAR
    # ══════════════════════════════════════════════════════

    def _setup_statusbar(self) -> None:
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

        # DB info
        self._lbl_db_info = QLabel()
        self._lbl_db_info.setStyleSheet(
            "color: #90caf9; font-size: 9pt; padding: 0 10px;"
        )
        self._statusbar.addWidget(self._lbl_db_info)

        # Status
        self._lbl_status = QLabel("Sẵn sàng")
        self._lbl_status.setStyleSheet(
            "color: #ffffff; font-size: 9pt; padding: 0 10px;"
        )
        self._statusbar.addWidget(self._lbl_status, 1)

        # Đồng hồ
        self._lbl_clock = QLabel()
        self._lbl_clock.setStyleSheet(
            "color: #b0bec5; font-size: 9pt; padding: 0 10px;"
        )
        self._statusbar.addPermanentWidget(self._lbl_clock)

        # User + Role
        user = self._auth.current_user
        user_text = (
            f"👤 {user.full_name} ({user.role_name})"
            if user else "👤 ---"
        )
        self._lbl_user = QLabel(user_text)
        self._lbl_user.setStyleSheet(
            "color: #90caf9; font-size: 9pt; padding: 0 10px;"
        )
        self._statusbar.addPermanentWidget(self._lbl_user)

    # ══════════════════════════════════════════════════════
    #  PHÂN QUYỀN
    # ══════════════════════════════════════════════════════

    def _apply_permissions(self) -> None:
        """
        Áp dụng phân quyền lên menu + tab.
        Ẩn/disable các thành phần không có quyền.
        """
        perm = self._auth.current_permission
        if not perm:
            return

        # ── Tab ────────────────────────────────────────────
        # Tab Main (luôn hiện nếu có menu_main)
        self._tab_widget.setTabEnabled(0, perm.has_menu("main"))

        # Tab IE: cần import HOẶC export
        ie_enabled = (
            perm.has_menu("import") or perm.has_menu("export")
        )
        self._tab_widget.setTabEnabled(1, ie_enabled)

        # Tab Cấu hình
        self._tab_widget.setTabEnabled(2, perm.has_menu("config"))

        # ── Menu actions ───────────────────────────────────
        # Import
        self.act_import_xml.setEnabled(perm.has_menu("import"))

        # Export
        export_ok = perm.has_menu("export")
        self.act_export_excel.setEnabled(export_ok)
        self.act_export_csv.setEnabled(export_ok)
        self.act_export_pdf.setEnabled(export_ok)

        # DB maintenance (chỉ admin/manager)
        is_admin = perm.has_menu("config")
        self.act_backup.setEnabled(is_admin)
        self.act_vacuum.setEnabled(is_admin)
        self.act_integrity.setEnabled(is_admin)

        self._logger.info(
            module="System",
            action="ApplyPermissions",
            detail=f"User={self._auth.current_username}; "
                   f"Role={self._auth.current_role}; "
                   f"Perm={perm}"
        )

    # ══════════════════════════════════════════════════════
    #  CẬP NHẬT TRẠNG THÁI
    # ══════════════════════════════════════════════════════

    def _update_clock(self) -> None:
        now = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self._lbl_clock.setText(f"🕐 {now}")

    def _update_status_info(self) -> None:
        try:
            stats = self._db_manager.get_stats()
            # Đếm thêm các bảng mới
            try:
                nguoi_count = self._db_manager._fetchone(
                    "SELECT COUNT(*) as cnt FROM nguoi_lx"
                )
                hoso_count = self._db_manager._fetchone(
                    "SELECT COUNT(*) as cnt FROM ho_so_sh"
                )
                n = nguoi_count["cnt"] if nguoi_count else 0
                h = hoso_count["cnt"] if hoso_count else 0
            except Exception:
                n, h = 0, 0

            self._lbl_db_info.setText(
                f"💾 NguoiLX: {n} | HoSo: {h} | "
                f"DB: {stats.get('db_size_mb', 0)} MB"
            )
        except Exception:
            self._lbl_db_info.setText("💾 DB: ---")

    def show_status_message(
        self, message: str, timeout: int = 5000
    ) -> None:
        self._lbl_status.setText(message)
        if timeout > 0:
            QTimer.singleShot(
                timeout,
                lambda: self._lbl_status.setText("Sẵn sàng")
            )

    # ══════════════════════════════════════════════════════
    #  SỰ KIỆN TAB
    # ══════════════════════════════════════════════════════

    def _on_tab_changed(self, index: int) -> None:
        tab_names = ["Main", "IE", "CauHinh"]
        name = tab_names[index] if index < len(tab_names) else ""
        self.show_status_message(f"Tab: {name}")
        self._update_status_info()

        if index == 0:
            self._tab_main.refresh_data()

    # ══════════════════════════════════════════════════════
    #  MENU ACTIONS
    # ══════════════════════════════════════════════════════

    def _on_backup_db(self) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "Sao lưu Database",
            f"nguoi_lx_backup_{ts}.db",
            "SQLite Database (*.db)",
        )
        if not path:
            return

        if self._db_manager.backup_to(path):
            self.show_status_message(
                f"✅ Sao lưu: {Path(path).name}"
            )
            QMessageBox.information(
                self, "Sao lưu", f"Thành công!\nFile: {path}"
            )
        else:
            QMessageBox.warning(self, "Lỗi", "Không thể sao lưu.")

    def _on_vacuum_db(self) -> None:
        reply = QMessageBox.question(
            self, "Tối ưu",
            "Tối ưu database?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                self._db_manager.vacuum()
                self._update_status_info()
                QMessageBox.information(
                    self, "OK", "Tối ưu hoàn tất!"
                )
            except Exception as exc:
                QMessageBox.warning(
                    self, "Lỗi", f"Lỗi:\n{exc}"
                )

    def _on_db_info(self) -> None:
        try:
            info = get_database_info(self._db_manager)
            msg = (
                f"📁 Path: {info.get('db_path', '')}\n"
                f"📊 Schema: v{info.get('schema_version', 0)}\n"
                f"💾 Size: {info.get('db_size_mb', 0)} MB\n\n"
                f"📋 Bảng:\n"
            )
            for t, c in info.get("record_counts", {}).items():
                msg += f"   • {t}: {c}\n"
            QMessageBox.information(self, "DB Info", msg)
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))

    def _on_check_integrity(self) -> None:
        ok, msg = check_database_integrity(self._db_manager)
        if ok:
            QMessageBox.information(self, "OK", f"✅ {msg}")
        else:
            QMessageBox.warning(self, "⚠️", msg)

    def _on_change_password(self) -> None:
        """Dialog đổi mật khẩu."""
        dialog = ChangePasswordDialog(
            auth_service=self._auth, parent=self
        )
        dialog.exec()

    def _on_logout(self) -> None:
        """Đăng xuất → đóng cửa sổ → main.py sẽ hiện lại LoginDialog."""
        reply = QMessageBox.question(
            self, "Đăng xuất",
            "Bạn có chắc muốn đăng xuất?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._auth.logout()
            self.close()

    def _on_import_xml(self) -> None:
        self._tab_widget.setCurrentIndex(1)
        self._tab_ie.trigger_import_excel()

    def _on_export_excel(self) -> None:
        self._tab_widget.setCurrentIndex(1)
        self._tab_ie.trigger_export_excel()

    def _on_export_csv(self) -> None:
        self._tab_widget.setCurrentIndex(1)
        self._tab_ie.trigger_export_csv()

    def _on_export_pdf(self) -> None:
        self._tab_widget.setCurrentIndex(1)
        self._tab_ie.trigger_export_pdf()

    def _on_about(self) -> None:
        QMessageBox.about(
            self, "Về phần mềm",
            "<h2>Quản lý dữ liệu sát hạch GPLX</h2>"
            "<p><b>Phiên bản:</b> 1.0.0</p>"
            "<p><b>Ngôn ngữ:</b> Python 3.13+ / PySide6</p>"
            "<p><b>Database:</b> SQLite (8 bảng)</p>"
            "<p><b>CSDL:</b> account, role, permission, dvhc, "
            "ky_sh, nguoi_lx, ho_so_sh, nhap_kqsh</p>"
            "<hr><p><i>© 2026</i></p>"
        )

    def _on_shortcuts(self) -> None:
        QMessageBox.information(
            self, "Phím tắt",
            "<table cellpadding='5'>"
            "<tr><td><b>Ctrl+I</b></td><td>Import XML</td></tr>"
            "<tr><td><b>Ctrl+E</b></td><td>Export Excel</td></tr>"
            "<tr><td><b>Ctrl+Q</b></td><td>Thoát</td></tr>"
            "<tr><td><b>F5</b></td><td>Làm mới</td></tr>"
            "</table>"
        )

    # ══════════════════════════════════════════════════════
    #  ĐÓNG CỬA SỔ
    # ══════════════════════════════════════════════════════

    def closeEvent(self, event: QCloseEvent) -> None:
        reply = QMessageBox.question(
            self, "Thoát",
            "Bạn có chắc muốn thoát?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                self._db_manager.close()
            except Exception:
                pass

            self._logger.info(
                module="System",
                action="Shutdown",
                detail=f"User={self._auth.current_username} dong phan mem."
            )
            event.accept()
        else:
            event.ignore()

    # ══════════════════════════════════════════════════════
    #  PUBLIC API
    # ══════════════════════════════════════════════════════

    def get_auth_service(self) -> AuthService:
        return self._auth

    def get_db_manager(self) -> DatabaseManager:
        return self._db_manager

    def get_ie_service(self) -> IEService:
        return self._ie_service

    def get_display_service(self) -> DisplayService:
        return self._display_service

    def get_logger(self) -> LoggerService:
        return self._logger

    def refresh_all(self) -> None:
        self._tab_main.refresh_data()
        self._update_status_info()


# ══════════════════════════════════════════════════════════
#  DIALOG ĐỔI MẬT KHẨU
# ══════════════════════════════════════════════════════════

class ChangePasswordDialog(QDialog):
    """Dialog đổi mật khẩu."""

    def __init__(
        self,
        auth_service: AuthService,
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)
        self._auth = auth_service

        self.setWindowTitle("Đổi mật khẩu")
        self.setFixedSize(400, 280)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        self.txt_old = QLineEdit()
        self.txt_old.setEchoMode(QLineEdit.Password)
        self.txt_old.setPlaceholderText("Mật khẩu hiện tại")
        layout.addRow("Mật khẩu cũ:", self.txt_old)

        self.txt_new = QLineEdit()
        self.txt_new.setEchoMode(QLineEdit.Password)
        self.txt_new.setPlaceholderText("Mật khẩu mới (tối thiểu 4 ký tự)")
        layout.addRow("Mật khẩu mới:", self.txt_new)

        self.txt_confirm = QLineEdit()
        self.txt_confirm.setEchoMode(QLineEdit.Password)
        self.txt_confirm.setPlaceholderText("Nhập lại mật khẩu mới")
        layout.addRow("Xác nhận:", self.txt_confirm)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self._on_change)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def _on_change(self) -> None:
        old_pw  = self.txt_old.text()
        new_pw  = self.txt_new.text()
        confirm = self.txt_confirm.text()

        if not old_pw or not new_pw:
            QMessageBox.warning(
                self, "Lỗi", "Vui lòng nhập đầy đủ."
            )
            return

        if new_pw != confirm:
            QMessageBox.warning(
                self, "Lỗi", "Mật khẩu xác nhận không khớp."
            )
            return

        try:
            user = self._auth.current_user
            if user:
                self._auth.change_password(
                    user.id, old_pw, new_pw
                )
                QMessageBox.information(
                    self, "OK", "Đổi mật khẩu thành công!"
                )
                self.accept()
        except Exception as exc:
            QMessageBox.warning(
                self, "Lỗi", str(exc)
            )