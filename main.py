"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : main.py
Mô tả     : Entry point v1.0
            - Khởi tạo hệ thống (DB 8 bảng mới)
            - Hiển thị LoginDialog trước
            - Nếu đăng nhập thành công → MainWindow
            - Nếu đăng xuất từ MainWindow → Quay lại LoginDialog
            - Hỗ trợ Splash Screen trong quá trình khởi tạo
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

import sys
from pathlib  import Path
from datetime import datetime

# ─── PySide6 ─────────────────────────────────────────────
from PySide6.QtWidgets import (
    QApplication, QMessageBox, QSplashScreen, QDialog
)
from PySide6.QtCore    import Qt, QTimer
from PySide6.QtGui     import QPixmap, QFont, QPainter, QColor, QLinearGradient

# ─── Database & Services ─────────────────────────────────
from database.db_manager  import DatabaseManager
from database.init_db     import initialize_database
from services.logger_service import LoggerService
from services.auth_service   import AuthService

# ─── UI ──────────────────────────────────────────────────
from ui.main_window import MainWindow, LoginDialog


# ══════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════

ROOT_DIR = Path(__file__).resolve().parent

# Các đường dẫn mặc định
DB_PATH     = ROOT_DIR / "database" / "nguoi_lx.db"
CONFIG_PATH = ROOT_DIR / "config"   / "Config_noidung.json"
DVHC_PATH   = ROOT_DIR / "config"   / "dvhc.json"
LOG_PATH    = ROOT_DIR / "logs"     / "log.txt"


# ══════════════════════════════════════════════════════════
#  TIỆN ÍCH
# ══════════════════════════════════════════════════════════

def ensure_directories() -> None:
    """Tạo các thư mục cần thiết."""
    dirs = [
        ROOT_DIR / "database",
        ROOT_DIR / "config",
        ROOT_DIR / "logs",
        ROOT_DIR / "resources" / "icons",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def _build_splash_pixmap() -> QPixmap:
    """Tạo ảnh splash screen."""
    pix = QPixmap(600, 350)
    painter = QPainter(pix)

    gradient = QLinearGradient(0, 0, 0, 350)
    gradient.setColorAt(0.0, QColor("#1a237e"))
    gradient.setColorAt(1.0, QColor("#283593"))
    from PySide6.QtCore import QRect
    painter.fillRect(QRect(0, 0, 600, 350), gradient)

    painter.setPen(QColor("#ffffff"))
    font_title = QFont("Segoe UI", 18, QFont.Bold)
    painter.setFont(font_title)
    painter.drawText(
        QRect(0, 80, 600, 60),
        Qt.AlignCenter,
        "QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX"
    )

    font_sub = QFont("Segoe UI", 11)
    painter.setFont(font_sub)
    painter.setPen(QColor("#90caf9"))
    painter.drawText(
        QRect(0, 150, 600, 40),
        Qt.AlignCenter,
        "Phiên bản 2.0.0"
    )

    font_info = QFont("Segoe UI", 9)
    painter.setFont(font_info)
    painter.setPen(QColor("#b0bec5"))
    painter.drawText(
        QRect(0, 300, 600, 30),
        Qt.AlignCenter,
        "Đang khởi tạo hệ thống..."
    )

    painter.end()
    return pix


# ══════════════════════════════════════════════════════════
#  KHỞI TẠO HỆ THỐNG
# ══════════════════════════════════════════════════════════

def initialize_system(splash: QSplashScreen = None):
    """
    Khởi tạo toàn bộ hệ thống.

    Returns
    -------
    (db_manager, logger) nếu thành công
    None nếu thất bại
    """
    # ── 1. Logger ───────────────────────────────────────
    if splash:
        splash.showMessage(
            "Đang khởi tạo logger...",
            Qt.AlignBottom | Qt.AlignCenter,
            Qt.white
        )

    logger = LoggerService(
        log_file=str(LOG_PATH),
        user="system"
    )
    logger.info(
        module="System",
        action="Start",
        detail="Khoi dong phan mem v2.0.0"
    )

    # ── 2. Database ─────────────────────────────────────
    if splash:
        splash.showMessage(
            "Đang kết nối database...",
            Qt.AlignBottom | Qt.AlignCenter,
            Qt.white
        )

    try:
        db_manager = DatabaseManager(
            db_path=str(DB_PATH),
            logger=logger
        )
        db_manager.connect()

        # Kiểm tra và khởi tạo bảng nếu chưa có
        # (init_db sẽ tạo 8 bảng: account, role, permission, dvhc, ky_sh, nguoi_lx, ho_so_sh, nhap_kqsh)
        initialize_database(db_manager, logger)

    except Exception as exc:
        logger.error(
            module="System",
            action="InitDB",
            detail=f"Loi: {exc}"
        )
        QMessageBox.critical(
            None,
            "Lỗi khởi tạo",
            f"Không thể khởi tạo database:\n{exc}\n\n"
            f"Kiểm tra file: {DB_PATH}"
        )
        return None, None

    return db_manager, logger


# ══════════════════════════════════════════════════════════
#  CHẠY LOGIN DIALOG
# ══════════════════════════════════════════════════════════

def run_login(auth_service: AuthService, logger: LoggerService):
    """
    Hiển thị dialog đăng nhập.

    Returns
    -------
    UserInfo nếu đăng nhập thành công
    None nếu thoát
    """
    dialog = LoginDialog(
        auth_service=auth_service,
        parent=None
    )

    if dialog.exec() == QDialog.Accepted:
        return dialog.user_info
    return None


# ══════════════════════════════════════════════════════════
#  CHẠY MAIN WINDOW
# ══════════════════════════════════════════════════════════

def run_main_window(
    db_manager,
    logger,
    auth_service,
):
    """
    Hiển thị cửa sổ chính và chờ đến khi đóng.

    Returns
    -------
    True  : nếu user đăng xuất (cần quay lại login)
    False : nếu user thoát hoàn toàn
    """
    # Tạo MainWindow
    main_window = MainWindow(
        db_path      = str(DB_PATH),
        config_path  = str(CONFIG_PATH),
        dvhc_path    = str(DVHC_PATH),
        logger       = logger,
        auth_service = auth_service,
    )

    # Hiển thị maximized
    main_window.showMaximized()

    # Chạy event loop
    # Lấy QApplication instance hiện tại
    app = QApplication.instance()
    if app:
        app.exec()

    # Kiểm tra xem user có yêu cầu đăng xuất không
    # (Thuộc tính này được set trong MainWindow._on_logout)
    if hasattr(main_window, '_logout_requested') and main_window._logout_requested:
        return True  # Quay lại login

    return False  # Thoát hoàn toàn


# ══════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════

def main():
    """Hàm chính."""
    # ── Tạo QApplication ────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("Quản lý dữ liệu sát hạch GPLX")
    app.setApplicationVersion("1.0.0")
    app.setFont(QFont("Segoe UI", 10))

    # ── Tạo thư mục ─────────────────────────────────────
    ensure_directories()

    # ── Splash Screen ───────────────────────────────────
    splash = QSplashScreen(_build_splash_pixmap(), Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    # ── Khởi tạo hệ thống ───────────────────────────────
    db_manager, logger = initialize_system(splash)

    if db_manager is None:
        sys.exit(1)

    # ── Tạo AuthService ────────────────────────────────
    auth_service = AuthService(
        db_manager=db_manager,
        logger=logger
    )

    # Đóng splash sau khi init xong
    splash.finish(None)

    # ── Vòng lặp chính: Login → Main → (Logout → Login) ──
    while True:
        # Hiển thị Login Dialog
        user = run_login(auth_service, logger)

        if user is None:
            # User đóng login dialog → thoát
            logger.info(
                module="System",
                action="Exit",
                detail="User dong dang nhap, thoat."
            )
            break

        # Đăng nhập thành công, chạy MainWindow
        restart_login = run_main_window(
            db_manager   = db_manager,
            logger       = logger,
            auth_service = auth_service,
        )

        if not restart_login:
            # Thoát hoàn toàn
            break

        # Nếu restart_login = True (user đã đăng xuất)
        # Tiếp tục vòng lặp, hiển thị lại LoginDialog
        auth_service.logout()
        logger.user = "system"  # Reset logger user
        print("Đăng xuất thành công. Quay lại màn hình đăng nhập...")

    # ── Dọn dẹp ─────────────────────────────────────────
    try:
        db_manager.close()
    except Exception:
        pass

    sys.exit(0)


# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()