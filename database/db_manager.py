"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : database/db_manager.py
Mô tả     : Quản lý kết nối và thao tác SQLite
            - Thread-safe (dùng threading.Lock)
            - Hỗ trợ transaction
            - Tích hợp LoggerService
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

import sqlite3
import threading
from datetime import datetime
from pathlib  import Path
from typing   import Any, Optional


# ══════════════════════════════════════════════════════════
#  SQL SCHEMA (theo đúng thiết kế section 5, 6)
# ══════════════════════════════════════════════════════════

SQL_CREATE_TABLE_HOSO = """
CREATE TABLE IF NOT EXISTS NguoiLX_HoSo (
    SO_TT INTEGER,
    MA_DK TEXT,
    HO_TEN_DEM TEXT,
    TEN TEXT,
    HO_VA_TEN TEXT,
    GIOI_TINH TEXT,
    NGAY_SINH DATE,
    MA_QUOC_TICH TEXT,
    NOI_CT TEXT,
    NOI_CT_MA_DVHC TEXT,
    NOI_CT_MA_DVQL TEXT,
    SO_CMT TEXT,
    SO_HO_SO TEXT PRIMARY KEY,
    MA_KY_SH TEXT,
    SO_BAO_DANH INTEGER,
    MA_CSDT TEXT,
    MA_TTSH TEXT,
    MA_SO_GTVT TEXT,
    GIAY_CNSK TEXT,
    HANG_GPLX TEXT,
    SO_GPLX_DA_CO TEXT,
    HANG_GPLX_DA_CO TEXT,
    DVQL_GPLX_DACO TEXT,
    NGAY_HH_GPLX_DACO DATE,
    SO_NAM_LAIXE INTEGER,
    SO_KM_ANTOAN INTEGER,
    SO_GIAY_CNTN TEXT,
    SO_CCN TEXT,
    NOI_DUNG_SH TEXT,
    LY_DO_SH TEXT,
    KET_QUA_SH TEXT,
    KQ_SH_LYTHUYET TEXT,
    KQ_SH_MOPHONG TEXT,
    KQ_SH_HINH TEXT,
    KQ_SH_DUONG TEXT,
    GHI_CHU_SH TEXT,
    ANH_CHAN_DUNG TEXT,
    NGAY_TT_GPLX_DACO TEXT,
    MA_KHOA_HOC TEXT,
    SO_QD_SH TEXT,
    NGAY_QD_SH DATE,
    NGUOI_QD_SH TEXT,
    CHAT_LUONG_ANH TEXT,
    LYTHUYETKT TEXT,
    MOPHONGKT TEXT,
    HINHKT TEXT,
    DUONGKT TEXT,
    KETQUAKT TEXT,
    TAPHOSO TEXT,
    TRANGTHAI TEXT
);
"""

SQL_CREATE_TABLE_DVHC = """
CREATE TABLE IF NOT EXISTS DM_DVHC (
    MA_DVHC INTEGER PRIMARY KEY,
    MA_DVQL INTEGER,
    MA_DV INTEGER,
    TEN_DVHC TEXT,
    TENNGANGON TEXT,
    TENDAYDU TEXT,
    LOAIDVHC TEXT
);
"""

SQL_CREATE_INDEXES = """
-- Index tìm kiếm nhanh trên bảng hồ sơ
CREATE INDEX IF NOT EXISTS idx_hoso_sohoso ON NguoiLX_HoSo(SO_HO_SO);
CREATE INDEX IF NOT EXISTS idx_hoso_hoten   ON NguoiLX_HoSo(HO_VA_TEN);
CREATE INDEX IF NOT EXISTS idx_hoso_cccd    ON NguoiLX_HoSo(SO_CMT);
CREATE INDEX IF NOT EXISTS idx_hoso_hang    ON NguoiLX_HoSo(HANG_GPLX);
CREATE INDEX IF NOT EXISTS idx_hoso_trangthai ON NguoiLX_HoSo(TRANGTHAI);
CREATE INDEX IF NOT EXISTS idx_hoso_khoahoc ON NguoiLX_HoSo(MA_KHOA_HOC);

-- Index DVHC
CREATE INDEX IF NOT EXISTS idx_dvhc_ten ON DM_DVHC(TEN_DVHC);
CREATE INDEX IF NOT EXISTS idx_dvhc_loai ON DM_DVHC(LOAIDVHC);
"""


# ══════════════════════════════════════════════════════════
#  CLASS DATABASE MANAGER
# ══════════════════════════════════════════════════════════

class DatabaseManager:
    """
    Quản lý kết nối SQLite và các thao tác CRUD.

    Tính năng
    ---------
    - Thread-safe: mọi thao tác DB đều được khóa bằng threading.Lock
    - Transaction: hỗ trợ begin/commit/rollback thủ công
    - Logging: tích hợp ghi log qua LoggerService
    - Schema: tự động tạo bảng và index nếu chưa tồn tại
    """

    def __init__(
        self,
        db_path : str,
        logger  : Optional[Any] = None
    ) -> None:
        """
        Parameters
        ----------
        db_path : đường dẫn file .db (tuyệt đối hoặc tương đối)
        logger  : instance của LoggerService (optional)
        """
        self.db_path : Path             = Path(db_path)
        self.logger  : Optional[Any]    = logger
        self._conn   : Optional[sqlite3.Connection] = None
        self._lock   : threading.Lock   = threading.Lock()

        # Đảm bảo thư mục tồn tại
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    # ══════════════════════════════════════════════════════
    #  KẾT NỐI CƠ BẢN
    # ══════════════════════════════════════════════════════

    def connect(self) -> None:
        """
        Mở kết nối tới SQLite.
        Bật foreign keys và row_factory = sqlite3.Row.
        """
        with self._lock:
            if self._conn is not None:
                return  # Đã kết nối

            try:
                # check_same_thread=False cho phép dùng trong multi-thread (GUI)
                self._conn = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False,
                    timeout=10.0  # chờ 10s nếu DB bị khóa
                )
                self._conn.row_factory = sqlite3.Row
                # Bật foreign key constraint
                self._conn.execute("PRAGMA foreign_keys = ON")
                # Tối ưu performance
                self._conn.execute("PRAGMA journal_mode = WAL")
                self._conn.execute("PRAGMA synchronous = NORMAL")

                if self.logger:
                    self.logger.info(
                        module="Database",
                        action="Connect",
                        detail=f"Ket noi SQLite: {self.db_path.name}"
                    )
            except sqlite3.Error as exc:
                if self.logger:
                    self.logger.error(
                        module="Database",
                        action="Connect",
                        detail=f"Loi ket noi DB: {exc}"
                    )
                raise RuntimeError(f"Không thể kết nối database: {exc}") from exc

    def close(self) -> None:
        """Đóng kết nối SQLite."""
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                    if self.logger:
                        self.logger.info(
                            module="Database",
                            action="Disconnect",
                            detail="Dong ket noi SQLite"
                        )
                except sqlite3.Error as exc:
                    if self.logger:
                        self.logger.error(
                            module="Database",
                            action="Disconnect",
                            detail=f"Loi dong ket noi: {exc}"
                        )
                finally:
                    self._conn = None

    def is_connected(self) -> bool:
        """Kiểm tra trạng thái kết nối."""
        return self._conn is not None

    # ══════════════════════════════════════════════════════
    #  KHỞI TẠO BẢNG
    # ══════════════════════════════════════════════════════

    def initialize_tables(self) -> None:
        """
        Tạo bảng và index nếu chưa tồn tại.
        Nên gọi hàm này một lần khi khởi động app (trong init_db.py).
        """
        self._execute_script(SQL_CREATE_TABLE_HOSO)
        self._execute_script(SQL_CREATE_TABLE_DVHC)
        self._execute_script(SQL_CREATE_INDEXES)

        if self.logger:
            self.logger.info(
                module="Database",
                action="InitSchema",
                detail="Da tao bang NguoiLX_HoSo va DM_DVHC"
            )

    # ══════════════════════════════════════════════════════
    #  TRANSACTION
    # ══════════════════════════════════════════════════════

    def begin_transaction(self) -> None:
        """Bắt đầu transaction thủ công."""
        with self._lock:
            self._conn.execute("BEGIN")

    def commit(self) -> None:
        """Commit transaction."""
        with self._lock:
            self._conn.commit()

    def rollback(self) -> None:
        """Rollback transaction."""
        with self._lock:
            self._conn.rollback()

    # ══════════════════════════════════════════════════════
    #  CRUD - NGƯỜI LÁI XE / HỒ SƠ
    # ══════════════════════════════════════════════════════

    def insert_hoso(self, data: dict) -> int:
        """
        Thêm mới hồ sơ.

        Parameters
        ----------
        data : dict chứa dữ liệu hồ sơ (key phải khớp tên cột)

        Returns
        -------
        lastrowid (int)

        Raises
        ------
        sqlite3.IntegrityError : nếu SO_HO_SO bị trùng (PRIMARY KEY)
        """
        if not data:
            raise ValueError("Dữ liệu rỗng")

        # Loại bỏ key rỗng để tránh lỗi cột không tồn tại
        data = {k: v for k, v in data.items() if v is not None}

        cols   = ", ".join(data.keys())
        vals   = ", ".join(["?" for _ in data])
        sql    = f"INSERT INTO NguoiLX_HoSo ({cols}) VALUES ({vals})"

        with self._lock:
            try:
                cursor = self._conn.execute(sql, tuple(data.values()))
                self._conn.commit()
                row_id = cursor.lastrowid

                if self.logger:
                    self.logger.info(
                        module="HoSo",
                        action="Them",
                        detail=f"SO_HO_SO={data.get('SO_HO_SO')}; "
                               f"HO_TEN={data.get('HO_VA_TEN')}"
                    )
                return row_id
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                if self.logger:
                    self.logger.error(
                        module="HoSo",
                        action="Them",
                        detail=f"Trung SO_HO_SO: {exc}"
                    )
                raise
            except sqlite3.Error as exc:
                self._conn.rollback()
                if self.logger:
                    self.logger.error(
                        module="HoSo",
                        action="Them",
                        detail=f"Loi SQL: {exc}"
                    )
                raise

    def update_hoso(self, so_ho_so: str, data: dict) -> bool:
        """
        Cập nhật hồ sơ theo SO_HO_SO (PRIMARY KEY).

        Returns
        -------
        True nếu có ít nhất 1 dòng được cập nhật
        """
        if not so_ho_so or not data:
            return False

        # Không cho phép cập nhật SO_HO_SO chính nó
        data.pop("SO_HO_SO", None)

        set_clause = ", ".join([f"{k}=?" for k in data.keys()])
        sql        = f"UPDATE NguoiLX_HoSo SET {set_clause} WHERE SO_HO_SO=?"
        params     = tuple(data.values()) + (so_ho_so,)

        with self._lock:
            try:
                cursor = self._conn.execute(sql, params)
                self._conn.commit()
                updated = cursor.rowcount > 0

                if updated and self.logger:
                    self.logger.info(
                        module="HoSo",
                        action="Sua",
                        detail=f"SO_HO_SO={so_ho_so}; "
                               f"Cap nhat: {list(data.keys())}"
                    )
                return updated
            except sqlite3.Error as exc:
                self._conn.rollback()
                if self.logger:
                    self.logger.error(
                        module="HoSo",
                        action="Sua",
                        detail=f"SO_HO_SO={so_ho_so}; Loi: {exc}"
                    )
                raise

    def delete_hoso(self, so_ho_so: str) -> bool:
        """Xóa hồ sơ theo SO_HO_SO."""
        sql = "DELETE FROM NguoiLX_HoSo WHERE SO_HO_SO=?"

        with self._lock:
            try:
                cursor = self._conn.execute(sql, (so_ho_so,))
                self._conn.commit()
                deleted = cursor.rowcount > 0

                if deleted and self.logger:
                    self.logger.info(
                        module="HoSo",
                        action="Xoa",
                        detail=f"SO_HO_SO={so_ho_so}"
                    )
                return deleted
            except sqlite3.Error as exc:
                self._conn.rollback()
                if self.logger:
                    self.logger.error(
                        module="HoSo",
                        action="Xoa",
                        detail=f"SO_HO_SO={so_ho_so}; Loi: {exc}"
                    )
                raise

    def get_hoso_by_id(self, so_ho_so: str) -> Optional[dict]:
        """Lấy chi tiết một hồ sơ."""
        sql = "SELECT * FROM NguoiLX_HoSo WHERE SO_HO_SO=?"
        rows = self._fetchall(sql, (so_ho_so,))
        return rows[0] if rows else None

    def search_hoso(
        self,
        so_ho_so    : str = "",
        ho_ten      : str = "",
        so_cccd     : str = "",
        hang_gplx   : str = "",
        trang_thai  : str = "",
        ma_khoa_hoc : str = "",
        limit       : int = 1000,
        offset      : int = 0
    ) -> list[dict]:
        """
        Tìm kiếm hồ sơ với nhiều điều kiện (LIKE cho text).

        Parameters
        ----------
        limit  : giới hạn số kết quả (mặc định 1000 để tránh quá tải)
        offset : phân trang
        """
        conditions = []
        params     = []

        if so_ho_so:
            conditions.append("SO_HO_SO LIKE ?")
            params.append(f"%{so_ho_so}%")
        if ho_ten:
            conditions.append("HO_VA_TEN LIKE ?")
            params.append(f"%{ho_ten}%")
        if so_cccd:
            conditions.append("SO_CMT LIKE ?")  # CCCD lưu ở SO_CMT
            params.append(f"%{so_cccd}%")
        if hang_gplx:
            conditions.append("HANG_GPLX = ?")
            params.append(hang_gplx)
        if trang_thai:
            conditions.append("TRANGTHAI = ?")
            params.append(trang_thai)
        if ma_khoa_hoc:
            conditions.append("MA_KHOA_HOC = ?")
            params.append(ma_khoa_hoc)

        sql = "SELECT * FROM NguoiLX_HoSo"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY SO_TT DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return self._fetchall(sql, tuple(params))

    def count_hoso(self, **filters) -> int:
        """Đếm số lượng hồ sơ theo bộ lọc (tương tự search)."""
        # Tạm thời dùng cách đơn giản: lấy len() của search
        # Hoặc viết lại SQL SELECT COUNT(*)
        # Ở đây viết lại để tối ưu
        conditions = []
        params     = []

        if filters.get("so_ho_so"):
            conditions.append("SO_HO_SO LIKE ?")
            params.append(f"%{filters['so_ho_so']}%")
        if filters.get("ho_ten"):
            conditions.append("HO_VA_TEN LIKE ?")
            params.append(f"%{filters['ho_ten']}%")
        # ... thêm các filter khác nếu cần đếm chính xác

        sql = "SELECT COUNT(*) as total FROM NguoiLX_HoSo"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        row = self._fetchone(sql, tuple(params))
        return row["total"] if row else 0

    # ══════════════════════════════════════════════════════
    #  CRUD - DVHC
    # ══════════════════════════════════════════════════════

    def sync_dvhc(self, dvhc_list: list[dict]) -> tuple[int, int]:
        """
        Đồng bộ toàn bộ danh mục DVHC từ JSON vào SQLite.
        Chiến lược: Xóa hết → Chèn mới (nhanh nhất cho danh mục đồng nhất).

        Parameters
        ----------
        dvhc_list : list[dict] từ file dvhc.json

        Returns
        -------
        (so_ban_ghi_xoa, so_ban_ghi_them)
        """
        if not dvhc_list:
            return (0, 0)

        with self._lock:
            try:
                self.begin_transaction()

                # Đếm cũ
                cur = self._conn.execute("SELECT COUNT(*) FROM DM_DVHC")
                old_count = cur.fetchone()[0]

                # Xóa cũ
                self._conn.execute("DELETE FROM DM_DVHC")

                # Chèn mới bằng executemany (nhanh)
                sql = """
                INSERT INTO DM_DVHC 
                (MA_DVHC, MA_DVQL, MA_DV, TEN_DVHC, TENNGANGON, TENDAYDU, LOAIDVHC)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                # Chuẩn hóa dữ liệu đầu vào
                rows = []
                for item in dvhc_list:
                    rows.append((
                        item.get("MA_DVHC"),
                        item.get("MA_DVQL"),
                        item.get("MA_DV"),
                        item.get("TEN_DVHC"),
                        item.get("TENNGANGON"),
                        item.get("TENDAYDU"),
                        item.get("LOAIDVHC"),
                    ))

                self._conn.executemany(sql, rows)
                self.commit()

                new_count = len(rows)

                if self.logger:
                    self.logger.info(
                        module="DVHC",
                        action="DongBoSQLite",
                        detail=f"Da xoa {old_count} cu, them {new_count} moi"
                    )
                return (old_count, new_count)

            except sqlite3.Error as exc:
                self.rollback()
                if self.logger:
                    self.logger.error(
                        module="DVHC",
                        action="DongBoSQLite",
                        detail=f"Loi dong bo: {exc}"
                    )
                raise

    def get_dvhc_all(self) -> list[dict]:
        """Lấy toàn bộ danh mục DVHC."""
        return self._fetchall("SELECT * FROM DM_DVHC ORDER BY MA_DVHC")

    def get_dvhc_by_ma(self, ma_dvhc: int) -> Optional[dict]:
        """Lấy DVHC theo mã."""
        rows = self._fetchall(
            "SELECT * FROM DM_DVHC WHERE MA_DVHC=?", (ma_dvhc,)
        )
        return rows[0] if rows else None

    def search_dvhc(
        self,
        keyword: str = "",
        loai   : str = "",
        limit  : int = 500
    ) -> list[dict]:
        """Tìm kiếm DVHC theo tên hoặc mã."""
        sql    = "SELECT * FROM DM_DVHC WHERE 1=1"
        params = []

        if keyword:
            sql += " AND (MA_DVHC LIKE ? OR TEN_DVHC LIKE ? OR TENDAYDU LIKE ?)"
            like = f"%{keyword}%"
            params.extend([like, like, like])

        if loai:
            sql += " AND LOAIDVHC = ?"
            params.append(loai)

        sql += f" LIMIT {limit}"
        return self._fetchall(sql, tuple(params))

    # ══════════════════════════════════════════════════════
    #  TIỆN ÍCH INTERNAL
    # ══════════════════════════════════════════════════════

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute đơn giản (đã có lock)."""
        with self._lock:
            return self._conn.execute(sql, params)

    def _execute_script(self, sql_script: str) -> None:
        """Thực thi nhiều câu SQL (CREATE TABLE...)."""
        with self._lock:
            self._conn.executescript(sql_script)

    def _fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        """Trả về list[dict]."""
        with self._lock:
            cursor = self._conn.execute(sql, params)
            rows   = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def _fetchone(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """Trả về một dict hoặc None."""
        with self._lock:
            cursor = self._conn.execute(sql, params)
            row    = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        """Chuyển sqlite3.Row thành dict thuần."""
        return {key: row[key] for key in row.keys()}

    # ══════════════════════════════════════════════════════
    #  BACKUP & MAINTENANCE
    # ══════════════════════════════════════════════════════

    def backup_to(self, backup_path: str) -> bool:
        """
        Tạo bản sao lưu database (online backup).
        Dùng SQLite backup API.
        """
        try:
            with self._lock:
                # Mở kết nối đích
                dest = sqlite3.connect(backup_path)
                with dest:
                    self._conn.backup(dest)
                dest.close()

            if self.logger:
                self.logger.info(
                    module="Database",
                    action="Backup",
                    detail=f"Sao luu thanh cong: {backup_path}"
                )
            return True
        except sqlite3.Error as exc:
            if self.logger:
                self.logger.error(
                    module="Database",
                    action="Backup",
                    detail=f"Loi sao luu: {exc}"
                )
            return False

    def vacuum(self) -> None:
        """Dọn dẹp và tối ưu kích thước file DB."""
        with self._lock:
            self._conn.execute("VACUUM")

    def get_stats(self) -> dict:
        """Thống kê nhanh số lượng bản ghi."""
        stats = {}
        try:
            with self._lock:
                # Hồ sơ
                cur = self._conn.execute(
                    "SELECT COUNT(*) FROM NguoiLX_HoSo"
                )
                stats["total_hoso"] = cur.fetchone()[0]

                # DVHC
                cur = self._conn.execute("SELECT COUNT(*) FROM DM_DVHC")
                stats["total_dvhc"] = cur.fetchone()[0]

                # Kích thước file
                stats["db_size_mb"] = round(
                    self.db_path.stat().st_size / (1024*1024), 2
                )
        except Exception:
            stats = {"total_hoso": 0, "total_dvhc": 0, "db_size_mb": 0}
        return stats

    def __enter__(self):
        """Context manager: with DatabaseManager(...) as db:"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Tự động đóng kết nối khi ra khỏi with."""
        self.close()