"""
============================================================
File      : database/init_db.py
Mô tả     : Khởi tạo database 9 bảng
Phiên bản : 1.0.0
============================================================
"""

import hashlib
from datetime import datetime
from typing import Optional, Any


SCHEMA_VERSION = 3

# ═══════════════════════════════════════
#  SQL TẠO BẢNG
# ═══════════════════════════════════════

SQL_CREATE_VERSION = """
CREATE TABLE IF NOT EXISTS db_version (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    version     INTEGER NOT NULL,
    applied_at  TEXT NOT NULL,
    description TEXT
);
"""

SQL_CREATE_ROLE = """
CREATE TABLE IF NOT EXISTS role (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name   TEXT UNIQUE NOT NULL,
    description TEXT
);
"""

SQL_CREATE_ACCOUNT = """
CREATE TABLE IF NOT EXISTS account (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    full_name      TEXT,
    role_id        INTEGER,
    is_active      INTEGER DEFAULT 1,
    created_at     TEXT,
    last_login     TEXT,
    FOREIGN KEY (role_id) REFERENCES role(id)
);
"""

SQL_CREATE_PERMISSION = """
CREATE TABLE IF NOT EXISTS permission (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id         INTEGER UNIQUE,
    menu_main       INTEGER DEFAULT 0,
    menu_import     INTEGER DEFAULT 0,
    menu_export     INTEGER DEFAULT 0,
    menu_doi_sanh   INTEGER DEFAULT 0,
    menu_config     INTEGER DEFAULT 0,
    menu_user       INTEGER DEFAULT 0,
    can_add         INTEGER DEFAULT 0,
    can_edit        INTEGER DEFAULT 0,
    can_delete      INTEGER DEFAULT 0,
    can_print       INTEGER DEFAULT 0,
    FOREIGN KEY (role_id) REFERENCES role(id)
);
"""

SQL_CREATE_DVHC = """
CREATE TABLE IF NOT EXISTS dvhc (
    MA_DVHC     INTEGER PRIMARY KEY,
    MA_DVQL     INTEGER,
    MA_DV       INTEGER,
    TEN_DVHC    TEXT,
    TENNGANGON  TEXT,
    TENDAYDU    TEXT,
    LOAIDVHC    TEXT
);
"""

SQL_CREATE_KY_SH = """
CREATE TABLE IF NOT EXISTS ky_sh (
    MAKYSH              TEXT PRIMARY KEY,
    MATTSH              TEXT,
    NGAYSH              TEXT,
    GIOSH               INTEGER,
    SOQD                TEXT,
    NGAYQD              TEXT,
    NGUOIQD             TEXT,
    CHUTICH_HDSH        TEXT,
    PHOCHUTICH_HDSH     TEXT,
    UV_GD_TTSH          TEXT,
    UV_TOTRUONG         TEXT,
    UV_THUKY            TEXT,
    TONGSODK            TEXT
);
"""

SQL_CREATE_NGUOI_LX = """
CREATE TABLE IF NOT EXISTS nguoi_lx (
    SO_TT               INTEGER,
    MA_DK               TEXT PRIMARY KEY,
    HO_TEN_DEM          TEXT,
    TEN                 TEXT,
    HO_VA_TEN           TEXT,
    GIOI_TINH           TEXT,
    NGAY_SINH           TEXT,
    MA_QUOC_TICH        TEXT,
    NOI_CT              TEXT,
    NOI_CT_MA_DVHC      TEXT,
    NOI_CT_MA_DVQL      TEXT,
    SO_CMT              TEXT
);
"""

SQL_CREATE_HO_SO_SH = """
CREATE TABLE IF NOT EXISTS ho_so_sh (
    MA_DK               TEXT PRIMARY KEY,
    SO_HO_SO            TEXT,
    MA_KY_SH            TEXT,
    SO_BAO_DANH         TEXT,
    MA_CSDT             TEXT,
    MA_TTSH             TEXT,
    MA_SO_GTVT          TEXT,
    GIAY_CNSK           TEXT,
    HANG_GPLX           TEXT,
    SO_GPLX_DA_CO       TEXT,
    HANG_GPLX_DA_CO     TEXT,
    DVQL_GPLX_DACO      TEXT,
    NGAY_HH_GPLX_DACO   TEXT,
    SO_NAM_LAIXE        TEXT,
    SO_KM_ANTOAN        TEXT,
    SO_GIAY_CNTN        TEXT,
    SO_CCN              TEXT,
    NOI_DUNG_SH         TEXT,
    LY_DO_SH            TEXT,
    KET_QUA_SH          TEXT,
    KQ_SH_LYTHUYET      TEXT,
    KQ_SH_MOPHONG       TEXT,
    KQ_SH_HINH          TEXT,
    KQ_SH_DUONG         TEXT,
    GHI_CHU_SH          TEXT,
    ANH_CHAN_DUNG        TEXT,
    NGAY_TT_GPLX_DACO   TEXT,
    MA_KHOA_HOC         TEXT,
    SO_QD_SH            TEXT,
    NGAY_QD_SH          TEXT,
    NGUOI_QD_SH         TEXT,
    CHAT_LUONG_ANH      TEXT,
    FOREIGN KEY (MA_DK) REFERENCES nguoi_lx(MA_DK),
    FOREIGN KEY (MA_KY_SH) REFERENCES ky_sh(MAKYSH)
);
"""

SQL_CREATE_NHAP_KQSH = """
CREATE TABLE IF NOT EXISTS nhap_kqsh (
    MA_DK           TEXT PRIMARY KEY,
    NHAP_KQLT       TEXT,
    NHAP_KQMP       TEXT,
    NHAP_KQH        TEXT,
    NHAP_KQD        TEXT,
    KETQUA_NHAP     TEXT,
    TAPHOSO         TEXT,
    TRANGTHAI       TEXT,
    FOREIGN KEY (MA_DK) REFERENCES nguoi_lx(MA_DK)
);
"""

SQL_CREATE_CONFIG_NOIDUNG = """
CREATE TABLE IF NOT EXISTS config_noidung (
    MA_NOIDUNG  TEXT PRIMARY KEY,
    LT          INTEGER DEFAULT 0,
    MP          INTEGER DEFAULT 0,
    H           INTEGER DEFAULT 0,
    D           INTEGER DEFAULT 0,
    MO_TA       TEXT
);
"""

SQL_CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_nguoi_lx_hoten  ON nguoi_lx(HO_VA_TEN);
CREATE INDEX IF NOT EXISTS idx_nguoi_lx_cmt    ON nguoi_lx(SO_CMT);
CREATE INDEX IF NOT EXISTS idx_hoso_kysh       ON ho_so_sh(MA_KY_SH);
CREATE INDEX IF NOT EXISTS idx_hoso_hang       ON ho_so_sh(HANG_GPLX);
CREATE INDEX IF NOT EXISTS idx_hoso_sohoso     ON ho_so_sh(SO_HO_SO);
CREATE INDEX IF NOT EXISTS idx_dvhc_ten        ON dvhc(TEN_DVHC);
CREATE INDEX IF NOT EXISTS idx_dvhc_loai       ON dvhc(LOAIDVHC);
CREATE INDEX IF NOT EXISTS idx_nhap_madk       ON nhap_kqsh(MA_DK);
CREATE INDEX IF NOT EXISTS idx_account_user    ON account(username);
"""


# ═══════════════════════════════════════
#  DỮ LIỆU MẪU
# ═══════════════════════════════════════

SAMPLE_ROLES = [
    (1, "admin",    "Quản trị viên - Toàn quyền"),
    (2, "manager",  "Quản lý - Xem, sửa, xuất"),
    (3, "operator", "Nhân viên nhập liệu"),
    (4, "viewer",   "Chỉ xem"),
]

SAMPLE_PERMISSIONS = [
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    (2, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1),
    (3, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0),
    (4, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0),
]

SAMPLE_NOIDUNG = [
    ("1",  1, 0, 1, 0, "LT+H lần đầu A1"),
    ("2",  1, 0, 0, 0, "Chỉ LT"),
    ("3",  1, 0, 1, 0, "LT+H"),
    ("4",  1, 0, 1, 1, "LT+H+D"),
    ("5",  0, 0, 1, 1, "H+D"),
    ("6",  0, 0, 0, 1, "Chỉ D"),
    ("7",  0, 0, 1, 0, "Chỉ H"),
    ("8",  0, 0, 1, 0, "H (miễn LT ô tô)"),
    ("9",  0, 0, 1, 0, "H (miễn LT xe máy)"),
    ("11", 1, 1, 1, 1, "LT+MP+H+D lần đầu"),
    ("12", 1, 1, 1, 1, "LT+MP+H+D thi lại"),
    ("13", 0, 1, 1, 1, "MP+H+D"),
    ("14", 1, 1, 0, 0, "LT+MP"),
    ("15", 0, 1, 0, 1, "MP+D"),
    ("16", 0, 1, 0, 0, "Chỉ MP"),
    ("17", 0, 1, 1, 0, "MP+H"),
    ("18", 1, 0, 0, 1, "LT+D"),
    ("19", 1, 1, 0, 1, "LT+MP+D"),
    ("20", 1, 1, 1, 0, "LT+MP+H"),
]


# ═══════════════════════════════════════
#  TIỆN ÍCH
# ═══════════════════════════════════════

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _log(logger, action, detail):
    if logger:
        logger.info(module="InitDB", action=action, detail=detail)


def _log_error(logger, action, detail):
    if logger:
        logger.error(module="InitDB", action=action, detail=detail)


def _record_version(db_manager, version, description=""):
    db_manager._execute(
        "INSERT INTO db_version (version, applied_at, description) VALUES (?, ?, ?)",
        (version, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), description)
    )
    db_manager.commit()


def _get_current_version(db_manager):
    try:
        row = db_manager._fetchone(
            "SELECT version FROM db_version ORDER BY id DESC LIMIT 1"
        )
        return row["version"] if row else 0
    except Exception:
        return 0


def _get_existing_tables(db_manager):
    rows = db_manager._fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [r["name"] for r in rows]


# ═══════════════════════════════════════
#  INSERT DỮ LIỆU MẪU
# ═══════════════════════════════════════

def _insert_sample_roles(db_manager):
    sql = "INSERT OR IGNORE INTO role (id, role_name, description) VALUES (?, ?, ?)"
    with db_manager._lock:
        db_manager._conn.executemany(sql, SAMPLE_ROLES)
        db_manager._conn.commit()


def _insert_sample_permissions(db_manager):
    sql = """
    INSERT OR IGNORE INTO permission
    (role_id, menu_main, menu_import, menu_export, menu_doi_sanh,
     menu_config, menu_user, can_add, can_edit, can_delete, can_print)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with db_manager._lock:
        db_manager._conn.executemany(sql, SAMPLE_PERMISSIONS)
        db_manager._conn.commit()


def _insert_admin_account(db_manager):
    sql = """
    INSERT OR IGNORE INTO account
    (username, password_hash, full_name, role_id, is_active, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    with db_manager._lock:
        db_manager._conn.execute(sql, (
            "admin",
            hash_password("admin123"),
            "Quản trị viên",
            1,
            1,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        db_manager._conn.commit()


def _insert_sample_noidung(db_manager):
    sql = """
    INSERT OR IGNORE INTO config_noidung
    (MA_NOIDUNG, LT, MP, H, D, MO_TA)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    with db_manager._lock:
        db_manager._conn.executemany(sql, SAMPLE_NOIDUNG)
        db_manager._conn.commit()


# ═══════════════════════════════════════
#  HÀM KHỞI TẠO CHÍNH
# ═══════════════════════════════════════

def initialize_database(db_manager, logger=None):
    """
    Khởi tạo 9 bảng + dữ liệu mẫu.

    Thứ tự:
    1. db_version
    2. role, account, permission
    3. dvhc
    4. ky_sh
    5. nguoi_lx, ho_so_sh, nhap_kqsh
    6. config_noidung
    7. indexes
    8. dữ liệu mẫu
    9. ghi version
    """
    try:
        _log(logger, "InitDB", "Bat dau khoi tao database v2.1...")

        # 1
        db_manager._execute_script(SQL_CREATE_VERSION)
        _log(logger, "InitDB", "Tao bang db_version")

        # 2
        db_manager._execute_script(SQL_CREATE_ROLE)
        db_manager._execute_script(SQL_CREATE_ACCOUNT)
        db_manager._execute_script(SQL_CREATE_PERMISSION)
        _log(logger, "InitDB", "Tao bang role, account, permission")

        # 3
        db_manager._execute_script(SQL_CREATE_DVHC)
        _log(logger, "InitDB", "Tao bang dvhc")

        # 4
        db_manager._execute_script(SQL_CREATE_KY_SH)
        _log(logger, "InitDB", "Tao bang ky_sh")

        # 5
        db_manager._execute_script(SQL_CREATE_NGUOI_LX)
        db_manager._execute_script(SQL_CREATE_HO_SO_SH)
        db_manager._execute_script(SQL_CREATE_NHAP_KQSH)
        _log(logger, "InitDB", "Tao bang nguoi_lx, ho_so_sh, nhap_kqsh")

        # 6
        db_manager._execute_script(SQL_CREATE_CONFIG_NOIDUNG)
        _log(logger, "InitDB", "Tao bang config_noidung")

        # 7
        db_manager._execute_script(SQL_CREATE_INDEXES)
        _log(logger, "InitDB", "Tao indexes")

        # 8
        _insert_sample_roles(db_manager)
        _insert_sample_permissions(db_manager)
        _insert_admin_account(db_manager)
        _insert_sample_noidung(db_manager)
        _log(logger, "InitDB", "Chen du lieu mau")

        # 9
        _record_version(db_manager, SCHEMA_VERSION, "Init v2.1 (9 bang)")
        _log(logger, "InitDB", f"Version: v{SCHEMA_VERSION}")

        _log(logger, "InitDB", "HOAN TAT!")
        return True

    except Exception as exc:
        _log_error(logger, "InitDB", f"LOI: {exc}")
        raise RuntimeError(f"Lỗi khởi tạo database: {exc}") from exc


# ═══════════════════════════════════════
#  KIỂM TRA
# ═══════════════════════════════════════

def verify_schema(db_manager):
    required = [
        "db_version", "role", "account", "permission",
        "dvhc", "ky_sh", "nguoi_lx", "ho_so_sh", "nhap_kqsh",
        "config_noidung",
    ]
    existing = _get_existing_tables(db_manager)
    missing = [t for t in required if t not in existing]
    return (len(missing) == 0, missing)


def get_database_info(db_manager):
    info = {
        "schema_version": _get_current_version(db_manager),
        "tables": _get_existing_tables(db_manager),
        "record_counts": {},
        "db_size_mb": 0,
        "db_path": str(db_manager.db_path),
    }
    for table in info["tables"]:
        try:
            row = db_manager._fetchone(f"SELECT COUNT(*) as cnt FROM {table}")
            info["record_counts"][table] = row["cnt"] if row else 0
        except Exception:
            info["record_counts"][table] = -1
    try:
        info["db_size_mb"] = round(db_manager.db_path.stat().st_size / (1024 * 1024), 2)
    except Exception:
        pass
    return info


def check_database_integrity(db_manager):
    try:
        result = db_manager._fetchall("PRAGMA integrity_check")
        if result and result[0].get("integrity_check") == "ok":
            return True, "Database OK."
        return False, str(result)
    except Exception as exc:
        return False, f"Lỗi: {exc}"