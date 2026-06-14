"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : services/display_service.py
Mô tả     : Dịch vụ hiển thị thống kê kết quả sát hạch v1.0
            - Bảng 1: Import KQ (load từ ho_so_sh)
            - Bảng 2: Nhập KQ (load từ nhap_kqsh)
            - Mỗi bảng: Chưa Thi / Đã Thi / Đạt / Không Đạt / %
            - 5 dòng: Lý Thuyết / Mô Phỏng / Hình / Đường / Tổng
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================

Bảng hiển thị:
┌──────────────────────────────────────────────────────────────────────┐
│                        Hiển thị kết quả                              │
├──────────────────────────────────────────────────────────────────────┤
│ Import KQ      │ Chưa Thi │ Đã Thi │  Đạt  │ Không Đạt │ Phần trăm│
│ Lý Thuyết:     │    50    │   75   │  60   │    15     │  80.0%   │
│ Mô Phỏng:      │    80    │   45   │  40   │     5     │  88.9%   │
│ Hình:           │    30    │   95   │  80   │    15     │  84.2%   │
│ Đường:          │    60    │   65   │  55   │    10     │  84.6%   │
│ Tổng:           │    20    │  105   │  90   │    15     │  85.7%   │
├──────────────────────────────────────────────────────────────────────┤
│ Nhập KQ        │ Chưa Thi │ Đã Thi │  Đạt  │ Không Đạt │ Phần trăm│
│ Lý Thuyết:     │    55    │   70   │  58   │    12     │  82.9%   │
│ Mô Phỏng:      │    85    │   40   │  38   │     2     │  95.0%   │
│ Hình:           │    35    │   90   │  78   │    12     │  86.7%   │
│ Đường:          │    65    │   60   │  52   │     8     │  86.7%   │
│ Tổng:           │    25    │  100   │  88   │    12     │  88.0%   │
└──────────────────────────────────────────────────────────────────────┘
"""

from typing   import Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

from database.db_manager     import DatabaseManager
from services.logger_service import LoggerService


# ══════════════════════════════════════════════════════════
#  HẰNG SỐ KẾT QUẢ
# ══════════════════════════════════════════════════════════

# Giá trị coi là "Đạt"
DAT_VALUES: set[str] = {
    "Đạt", "đạt", "Dat", "dat", "DAT",
    "D", "d", "1", "Pass", "pass",
}

# Giá trị coi là "Không đạt"
KHONG_DAT_VALUES: set[str] = {
    "Không đạt", "không đạt", "Khong dat", "khong dat",
    "KHONG DAT", "KD", "kd", "0", "Fail", "fail",
}

# Giá trị coi là "Chưa thi" (rỗng / None)
CHUA_THI_VALUES: set[str] = {
    "", "Chưa thi", "chua thi", "Chua thi",
    "CT", "ct", "N/A", "n/a",
}

# Nguồn dữ liệu
SOURCE_IMPORT = "import"   # Từ bảng ho_so_sh
SOURCE_NHAP   = "nhap"     # Từ bảng nhap_kqsh


# ══════════════════════════════════════════════════════════
#  DATACLASS: THỐNG KÊ 1 PHẦN THI
# ══════════════════════════════════════════════════════════

@dataclass
class PhanThiStats:
    """
    Thống kê 1 phần thi (LT / MP / H / Đ / Tổng).

    Attributes
    ----------
    ten        : tên phần thi
    tong_so    : tổng số hồ sơ
    chua_thi   : chưa thi
    da_thi     : đã thi (đạt + không đạt)
    dat        : đạt
    khong_dat  : không đạt
    phan_tram  : % đạt / đã thi
    """
    ten       : str   = ""
    tong_so   : int   = 0
    chua_thi  : int   = 0
    da_thi    : int   = 0
    dat       : int   = 0
    khong_dat : int   = 0
    phan_tram : float = 0.0

    def tinh_phan_tram(self) -> None:
        """Tính % đạt / đã thi."""
        if self.da_thi > 0:
            self.phan_tram = round(
                (self.dat / self.da_thi) * 100, 1
            )
        else:
            self.phan_tram = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def phan_tram_str(self) -> str:
        """Chuỗi hiển thị phần trăm."""
        if self.da_thi > 0:
            return f"{self.phan_tram}%"
        return "---"

    @property
    def chi_tiet_str(self) -> str:
        """Chuỗi chi tiết: Đạt/Đã thi."""
        if self.da_thi > 0:
            return f"{self.dat}/{self.da_thi}"
        return "---"

    def __repr__(self) -> str:
        return (
            f"PhanThiStats('{self.ten}': "
            f"CT={self.chua_thi}, DT={self.da_thi}, "
            f"D={self.dat}, KD={self.khong_dat}, "
            f"%={self.phan_tram})"
        )


# ══════════════════════════════════════════════════════════
#  DATACLASS: TỔNG HỢP 1 NGUỒN (IMPORT hoặc NHẬP)
# ══════════════════════════════════════════════════════════

@dataclass
class BangKetQua:
    """
    Tổng hợp thống kê 1 nguồn (Import KQ hoặc Nhập KQ).

    Gồm 5 phần: LT, MP, H, Đ, Tổng.
    """
    source_name : str = ""          # "Import KQ" hoặc "Nhập KQ"
    source_type : str = ""          # "import" hoặc "nhap"
    ly_thuyet   : PhanThiStats = field(default_factory=lambda: PhanThiStats("Lý Thuyết"))
    mo_phong    : PhanThiStats = field(default_factory=lambda: PhanThiStats("Mô Phỏng"))
    hinh        : PhanThiStats = field(default_factory=lambda: PhanThiStats("Hình"))
    duong       : PhanThiStats = field(default_factory=lambda: PhanThiStats("Đường"))
    tong        : PhanThiStats = field(default_factory=lambda: PhanThiStats("Tổng"))
    tong_ho_so  : int = 0

    @property
    def all_parts(self) -> list[PhanThiStats]:
        """List 5 phần: LT, MP, H, Đ, Tổng."""
        return [
            self.ly_thuyet,
            self.mo_phong,
            self.hinh,
            self.duong,
            self.tong,
        ]

    def to_dict(self) -> dict:
        return {
            "source_name" : self.source_name,
            "source_type" : self.source_type,
            "tong_ho_so"  : self.tong_ho_so,
            "ly_thuyet"   : self.ly_thuyet.to_dict(),
            "mo_phong"    : self.mo_phong.to_dict(),
            "hinh"        : self.hinh.to_dict(),
            "duong"       : self.duong.to_dict(),
            "tong"        : self.tong.to_dict(),
        }

    def to_table_rows(self) -> list[dict]:
        """
        Chuyển thành list 5 dòng cho bảng hiển thị.

        Mỗi dòng:
        {
            "ten"       : "Lý Thuyết",
            "chua_thi"  : 50,
            "da_thi"    : 75,
            "dat"       : 60,
            "khong_dat" : 15,
            "phan_tram" : 80.0,
            "phan_tram_str": "80.0%",
            "chi_tiet"  : "60/75",
        }
        """
        rows = []
        for part in self.all_parts:
            rows.append({
                "ten"           : part.ten,
                "chua_thi"      : part.chua_thi,
                "da_thi"        : part.da_thi,
                "dat"           : part.dat,
                "khong_dat"     : part.khong_dat,
                "phan_tram"     : part.phan_tram,
                "phan_tram_str" : part.phan_tram_str,
                "chi_tiet"      : part.chi_tiet_str,
            })
        return rows


# ══════════════════════════════════════════════════════════
#  DATACLASS: TỔNG HỢP CẢ 2 BẢNG
# ══════════════════════════════════════════════════════════

@dataclass
class TongHopHienThi:
    """
    Tổng hợp cả 2 bảng: Import KQ + Nhập KQ.
    Dùng cho widget hiển thị trên tab Main.
    """
    import_kq  : BangKetQua = field(
        default_factory=lambda: BangKetQua(
            source_name="Import KQ", source_type=SOURCE_IMPORT
        )
    )
    nhap_kq    : BangKetQua = field(
        default_factory=lambda: BangKetQua(
            source_name="Nhập KQ", source_type=SOURCE_NHAP
        )
    )
    tong_ho_so : int = 0
    ma_ky_sh   : str = ""

    def to_dict(self) -> dict:
        return {
            "tong_ho_so" : self.tong_ho_so,
            "ma_ky_sh"   : self.ma_ky_sh,
            "import_kq"  : self.import_kq.to_dict(),
            "nhap_kq"    : self.nhap_kq.to_dict(),
        }


# ══════════════════════════════════════════════════════════
#  CLASS DISPLAY SERVICE
# ══════════════════════════════════════════════════════════

class DisplayService:
    """
    Dịch vụ tính toán và hiển thị kết quả sát hạch v2.0.

    2 nguồn dữ liệu:
    - Import KQ : từ bảng ho_so_sh (cột KQ_SH_*)
    - Nhập KQ   : từ bảng nhap_kqsh (cột NHAP_KQ*)

    Sử dụng
    -------
    svc = DisplayService(db_manager, logger)

    # Thống kê toàn bộ
    result = svc.thong_ke_ket_qua()

    # Thống kê theo kỳ SH
    result = svc.thong_ke_ket_qua(ma_ky_sh="KSH001")

    # Thống kê theo hạng
    result = svc.thong_ke_ket_qua(hang_gplx="B2")

    # Lấy dữ liệu cho bảng Import KQ
    import_rows = result.import_kq.to_table_rows()

    # Lấy dữ liệu cho bảng Nhập KQ
    nhap_rows = result.nhap_kq.to_table_rows()
    """

    def __init__(
        self,
        db_manager : DatabaseManager,
        logger     : Optional[LoggerService] = None,
    ) -> None:
        self.db  = db_manager
        self.log = logger

    # ══════════════════════════════════════════════════════
    #  THỐNG KÊ CHÍNH
    # ══════════════════════════════════════════════════════

    def thong_ke_ket_qua(
        self,
        ma_ky_sh    : str = "",
        hang_gplx   : str = "",
        ma_khoa_hoc : str = "",
    ) -> TongHopHienThi:
        """
        Thống kê kết quả sát hạch từ 2 nguồn.

        Parameters
        ----------
        ma_ky_sh    : lọc theo mã kỳ sát hạch
        hang_gplx   : lọc theo hạng GPLX
        ma_khoa_hoc : lọc theo mã khóa học

        Returns
        -------
        TongHopHienThi chứa 2 bảng: import_kq + nhap_kq
        """
        try:
            result = TongHopHienThi(ma_ky_sh=ma_ky_sh)

            # ── Lấy dữ liệu Import KQ (ho_so_sh) ─────────
            import_data = self._query_import_kq(
                ma_ky_sh, hang_gplx, ma_khoa_hoc
            )
            result.import_kq = self._tinh_bang_ket_qua(
                data        = import_data,
                source_name = "Import KQ",
                source_type = SOURCE_IMPORT,
                field_lt    = "KQ_SH_LYTHUYET",
                field_mp    = "KQ_SH_MOPHONG",
                field_h     = "KQ_SH_HINH",
                field_d     = "KQ_SH_DUONG",
                field_tong  = "KET_QUA_SH",
            )

            # ── Lấy dữ liệu Nhập KQ (nhap_kqsh) ──────────
            nhap_data = self._query_nhap_kq(
                ma_ky_sh, hang_gplx, ma_khoa_hoc
            )
            result.nhap_kq = self._tinh_bang_ket_qua(
                data        = nhap_data,
                source_name = "Nhập KQ",
                source_type = SOURCE_NHAP,
                field_lt    = "NHAP_KQLT",
                field_mp    = "NHAP_KQMP",
                field_h     = "NHAP_KQH",
                field_d     = "NHAP_KQD",
                field_tong  = "KETQUA_NHAP",
            )

            # Tổng hồ sơ
            result.tong_ho_so = max(
                result.import_kq.tong_ho_so,
                result.nhap_kq.tong_ho_so
            )

            self._log_info(
                "ThongKeKetQua",
                f"KySH={ma_ky_sh or 'ALL'}; Hang={hang_gplx or 'ALL'}; "
                f"TongHS={result.tong_ho_so}; "
                f"Import_DaThi={result.import_kq.tong.da_thi}; "
                f"Nhap_DaThi={result.nhap_kq.tong.da_thi}"
            )

            return result

        except Exception as exc:
            self._log_error("ThongKeKetQua", f"Loi: {exc}")
            return TongHopHienThi()

    # ══════════════════════════════════════════════════════
    #  QUERY DỮ LIỆU
    # ══════════════════════════════════════════════════════

    def _query_import_kq(
        self,
        ma_ky_sh: str = "",
        hang_gplx: str = "",
        ma_khoa_hoc: str = "",
    ) -> list[dict]:
        """
        Query bảng ho_so_sh (Import KQ).

        Trả về list dict với các cột KQ_SH_*.
        """
        sql = """
        SELECT h.MA_DK,
               h.KQ_SH_LYTHUYET,
               h.KQ_SH_MOPHONG,
               h.KQ_SH_HINH,
               h.KQ_SH_DUONG,
               h.KET_QUA_SH,
               h.HANG_GPLX,
               h.MA_KY_SH
        FROM ho_so_sh h
        WHERE 1=1
        """
        params = []

        if ma_ky_sh:
            sql += " AND h.MA_KY_SH = ?"
            params.append(ma_ky_sh)
        if hang_gplx:
            sql += " AND h.HANG_GPLX = ?"
            params.append(hang_gplx)
        if ma_khoa_hoc:
            sql += " AND h.MA_KHOA_HOC = ?"
            params.append(ma_khoa_hoc)

        return self.db._fetchall(sql, tuple(params))

    def _query_nhap_kq(
        self,
        ma_ky_sh: str = "",
        hang_gplx: str = "",
        ma_khoa_hoc: str = "",
    ) -> list[dict]:
        """
        Query bảng nhap_kqsh (Nhập KQ).

        JOIN ho_so_sh để lọc theo hạng / kỳ SH / khóa học.
        """
        sql = """
        SELECT nk.MA_DK,
               nk.NHAP_KQLT,
               nk.NHAP_KQMP,
               nk.NHAP_KQH,
               nk.NHAP_KQD,
               nk.KETQUA_NHAP,
               nk.TAPHOSO,
               nk.TRANGTHAI,
               h.HANG_GPLX,
               h.MA_KY_SH
        FROM nhap_kqsh nk
        LEFT JOIN ho_so_sh h ON nk.MA_DK = h.MA_DK
        WHERE 1=1
        """
        params = []

        if ma_ky_sh:
            sql += " AND h.MA_KY_SH = ?"
            params.append(ma_ky_sh)
        if hang_gplx:
            sql += " AND h.HANG_GPLX = ?"
            params.append(hang_gplx)
        if ma_khoa_hoc:
            sql += " AND h.MA_KHOA_HOC = ?"
            params.append(ma_khoa_hoc)

        return self.db._fetchall(sql, tuple(params))

    # ══════════════════════════════════════════════════════
    #  TÍNH TOÁN
    # ══════════════════════════════════════════════════════

    def _tinh_bang_ket_qua(
        self,
        data        : list[dict],
        source_name : str,
        source_type : str,
        field_lt    : str,
        field_mp    : str,
        field_h     : str,
        field_d     : str,
        field_tong  : str,
    ) -> BangKetQua:
        """
        Tính thống kê 5 phần thi từ dữ liệu.

        Parameters
        ----------
        data        : list[dict] từ query
        source_name : "Import KQ" hoặc "Nhập KQ"
        source_type : "import" hoặc "nhap"
        field_lt    : tên cột Lý thuyết trong dict
        field_mp    : tên cột Mô phỏng
        field_h     : tên cột Hình
        field_d     : tên cột Đường
        field_tong  : tên cột Kết quả chung

        Returns
        -------
        BangKetQua đã tính toán xong
        """
        bang = BangKetQua(
            source_name = source_name,
            source_type = source_type,
            tong_ho_so  = len(data),
        )

        for row in data:
            # Lý Thuyết
            self._dem_ket_qua(
                bang.ly_thuyet,
                row.get(field_lt)
            )

            # Mô Phỏng
            self._dem_ket_qua(
                bang.mo_phong,
                row.get(field_mp)
            )

            # Hình
            self._dem_ket_qua(
                bang.hinh,
                row.get(field_h)
            )

            # Đường
            self._dem_ket_qua(
                bang.duong,
                row.get(field_d)
            )

            # Tổng (Kết quả chung)
            self._dem_ket_qua(
                bang.tong,
                row.get(field_tong)
            )

        # Tính phần trăm
        for part in bang.all_parts:
            part.tong_so = bang.tong_ho_so
            part.tinh_phan_tram()

        return bang

    # ══════════════════════════════════════════════════════
    #  THỐNG KÊ THEO BỘ LỌC
    # ══════════════════════════════════════════════════════

    def thong_ke_theo_hang(
        self, ma_ky_sh: str = "",
    ) -> dict[str, TongHopHienThi]:
        """
        Thống kê cho từng hạng GPLX.

        Returns
        -------
        dict: {hang_gplx: TongHopHienThi, ...}
        """
        try:
            rows = self.db._fetchall(
                """
                SELECT DISTINCT HANG_GPLX FROM ho_so_sh
                WHERE HANG_GPLX IS NOT NULL AND HANG_GPLX != ''
                ORDER BY HANG_GPLX
                """
            )

            result = {}
            for row in rows:
                hang = row["HANG_GPLX"]
                result[hang] = self.thong_ke_ket_qua(
                    ma_ky_sh  = ma_ky_sh,
                    hang_gplx = hang,
                )

            return result

        except Exception as exc:
            self._log_error("ThongKeTheoHang", f"Loi: {exc}")
            return {}

    def thong_ke_theo_ky_sh(self) -> dict[str, TongHopHienThi]:
        """
        Thống kê cho từng kỳ sát hạch.

        Returns
        -------
        dict: {ma_ky_sh: TongHopHienThi, ...}
        """
        try:
            rows = self.db._fetchall(
                """
                SELECT DISTINCT MA_KY_SH FROM ho_so_sh
                WHERE MA_KY_SH IS NOT NULL AND MA_KY_SH != ''
                ORDER BY MA_KY_SH
                """
            )

            result = {}
            for row in rows:
                ky = row["MA_KY_SH"]
                result[ky] = self.thong_ke_ket_qua(ma_ky_sh=ky)

            return result

        except Exception as exc:
            self._log_error("ThongKeTheoKy", f"Loi: {exc}")
            return {}

    # ══════════════════════════════════════════════════════
    #  DANH SÁCH CHO COMBOBOX LỌC
    # ══════════════════════════════════════════════════════

    def lay_danh_sach_ky_sh(self) -> list[dict]:
        """Lấy danh sách kỳ SH cho ComboBox lọc."""
        try:
            return self.db._fetchall(
                """
                SELECT MAKYSH, NGAYSH, TONGSODK
                FROM ky_sh
                ORDER BY MAKYSH
                """
            )
        except Exception:
            return []

    def lay_danh_sach_hang_gplx(self) -> list[str]:
        """Lấy danh sách hạng GPLX đang có."""
        try:
            rows = self.db._fetchall(
                """
                SELECT DISTINCT HANG_GPLX FROM ho_so_sh
                WHERE HANG_GPLX IS NOT NULL AND HANG_GPLX != ''
                ORDER BY HANG_GPLX
                """
            )
            return [r["HANG_GPLX"] for r in rows]
        except Exception:
            return []

    # ══════════════════════════════════════════════════════
    #  SO SÁNH IMPORT KQ VS NHẬP KQ
    # ══════════════════════════════════════════════════════

    def so_sanh_import_nhap(
        self,
        ma_ky_sh  : str = "",
        hang_gplx : str = "",
    ) -> dict:
        """
        So sánh kết quả giữa Import KQ và Nhập KQ.

        Returns
        -------
        dict:
        {
            "tong_ho_so" : int,
            "khop"       : int,   # số hồ sơ có KQ giống nhau
            "khac"       : int,   # số hồ sơ có KQ khác nhau
            "chi_tiet"   : list[dict],  # danh sách khác biệt
        }
        """
        try:
            sql = """
            SELECT h.MA_DK,
                   n.HO_VA_TEN,
                   h.KET_QUA_SH    AS import_kq,
                   nk.KETQUA_NHAP  AS nhap_kq,
                   h.KQ_SH_LYTHUYET AS import_lt,
                   nk.NHAP_KQLT     AS nhap_lt,
                   h.KQ_SH_MOPHONG  AS import_mp,
                   nk.NHAP_KQMP     AS nhap_mp,
                   h.KQ_SH_HINH     AS import_h,
                   nk.NHAP_KQH      AS nhap_h,
                   h.KQ_SH_DUONG    AS import_d,
                   nk.NHAP_KQD      AS nhap_d
            FROM ho_so_sh h
            JOIN nhap_kqsh nk ON h.MA_DK = nk.MA_DK
            JOIN nguoi_lx n ON h.MA_DK = n.MA_DK
            WHERE 1=1
            """
            params = []
            if ma_ky_sh:
                sql += " AND h.MA_KY_SH = ?"
                params.append(ma_ky_sh)
            if hang_gplx:
                sql += " AND h.HANG_GPLX = ?"
                params.append(hang_gplx)

            rows = self.db._fetchall(sql, tuple(params))

            khop = 0
            khac = 0
            chi_tiet = []

            for row in rows:
                import_tong = (row.get("import_kq") or "").strip()
                nhap_tong   = (row.get("nhap_kq") or "").strip()

                # So sánh từng phần
                differences = []
                for label, ik, nk in [
                    ("LT", row.get("import_lt",""), row.get("nhap_lt","")),
                    ("MP", row.get("import_mp",""), row.get("nhap_mp","")),
                    ("H",  row.get("import_h",""),  row.get("nhap_h","")),
                    ("Đ",  row.get("import_d",""),  row.get("nhap_d","")),
                ]:
                    ik_val = (ik or "").strip()
                    nk_val = (nk or "").strip()
                    if ik_val and nk_val and ik_val != nk_val:
                        differences.append(
                            f"{label}: Import='{ik_val}' ≠ Nhập='{nk_val}'"
                        )

                if import_tong == nhap_tong and not differences:
                    khop += 1
                else:
                    khac += 1
                    chi_tiet.append({
                        "MA_DK"      : row.get("MA_DK", ""),
                        "HO_VA_TEN"  : row.get("HO_VA_TEN", ""),
                        "import_kq"  : import_tong,
                        "nhap_kq"    : nhap_tong,
                        "khac_biet"  : "; ".join(differences) if differences else f"Tổng: '{import_tong}' ≠ '{nhap_tong}'",
                    })

            result = {
                "tong_ho_so" : len(rows),
                "khop"       : khop,
                "khac"       : khac,
                "chi_tiet"   : chi_tiet,
            }

            self._log_info(
                "SoSanh",
                f"So sanh Import vs Nhap: "
                f"Tong={len(rows)}, Khop={khop}, Khac={khac}"
            )

            return result

        except Exception as exc:
            self._log_error("SoSanh", f"Loi: {exc}")
            return {
                "tong_ho_so": 0, "khop": 0,
                "khac": 0, "chi_tiet": [],
            }

    # ══════════════════════════════════════════════════════
    #  XUẤT BÁO CÁO TEXT
    # ══════════════════════════════════════════════════════

    def xuat_bao_cao_text(
        self,
        result : TongHopHienThi,
        title  : str = "BÁO CÁO KẾT QUẢ SÁT HẠCH",
    ) -> str:
        """
        Xuất thống kê dạng text cho console / TextEdit.
        """
        sep = "─" * 75
        lines = [
            f"  {title}",
            f"  Tổng số hồ sơ: {result.tong_ho_so}",
            f"  Kỳ sát hạch : {result.ma_ky_sh or 'Tất cả'}",
            f"  Thời gian    : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            sep,
        ]

        # Bảng Import KQ
        lines.append(
            self._format_bang_text(result.import_kq)
        )

        lines.append(sep)

        # Bảng Nhập KQ
        lines.append(
            self._format_bang_text(result.nhap_kq)
        )

        lines.append(sep)
        return "\n".join(lines)

    def _format_bang_text(self, bang: BangKetQua) -> str:
        """Format 1 bảng kết quả dạng text."""
        header = (
            f"  {'':14} │ {'Chưa Thi':>9} │ {'Đã Thi':>8} │ "
            f"{'Đạt':>6} │ {'K.Đạt':>7} │ {'%':>8}"
        )

        lines = [
            f"  ■ {bang.source_name}",
            header,
            f"  {'─'*14}─┼{'─'*10}─┼{'─'*9}─┼{'─'*7}─┼{'─'*8}─┼{'─'*9}",
        ]

        for part in bang.all_parts:
            pct = part.phan_tram_str
            lines.append(
                f"  {part.ten + ':':<14} │ {part.chua_thi:>9} │ "
                f"{part.da_thi:>8} │ {part.dat:>6} │ "
                f"{part.khong_dat:>7} │ {pct:>8}"
            )

        return "\n".join(lines)

    # ══════════════════════════════════════════════════════
    #  PRIVATE: ĐẾM KẾT QUẢ
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _dem_ket_qua(
        phan_thi : PhanThiStats,
        ket_qua  : Optional[str],
    ) -> None:
        """
        Đếm 1 hồ sơ vào Chưa thi / Đạt / Không đạt.

        Quy tắc:
        - None / rỗng / CHUA_THI_VALUES → chưa thi
        - DAT_VALUES → đã thi + đạt
        - Còn lại → đã thi + không đạt
        """
        val = str(ket_qua or "").strip()

        if not val or val in CHUA_THI_VALUES:
            phan_thi.chua_thi += 1
        elif val in DAT_VALUES:
            phan_thi.da_thi += 1
            phan_thi.dat    += 1
        else:
            phan_thi.da_thi    += 1
            phan_thi.khong_dat += 1

    # ══════════════════════════════════════════════════════
    #  PRIVATE: LOG
    # ══════════════════════════════════════════════════════

    def _log_info(self, action: str, detail: str) -> None:
        if self.log:
            self.log.info(
                module="Display", action=action, detail=detail
            )

    def _log_error(self, action: str, detail: str) -> None:
        if self.log:
            self.log.error(
                module="Display", action=action, detail=detail
            )