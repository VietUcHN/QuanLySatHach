"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : services/ie_service.py
Mô tả     : Dịch vụ Import / Export hợp nhất (v1.0)
            - Import XML theo cấu trúc SAT_HACH
            - Import Excel (.xlsx), CSV (.csv)
            - Export Excel, CSV, PDF
            - Phù hợp CSDL mới: ky_sh, nguoi_lx, ho_so_sh
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================

Cấu trúc XML:
SAT_HACH
├── HEADER
├── DATA
│   ├── KY_SH
│   └── NGUOI_LXS
│       └── NGUOI_LX (nhiều)
│           └── HO_SO
└── Signature
"""

import os
import xml.etree.ElementTree as ET
from pathlib  import Path
from typing   import Any, Optional
from datetime import datetime

import pandas as pd

from database.db_manager      import DatabaseManager
from services.logger_service  import LoggerService


# ══════════════════════════════════════════════════════════
#  EXCEPTION
# ══════════════════════════════════════════════════════════

class ImportError_(Exception):
    """Lỗi import chung."""
    pass


class ImportFileError(ImportError_):
    """Lỗi đọc file."""
    pass


class ImportXMLError(ImportError_):
    """Lỗi cấu trúc XML."""
    pass


class ImportValidationError(ImportError_):
    """Lỗi validate dữ liệu."""
    def __init__(self, errors: list[dict]) -> None:
        self.errors = errors
        super().__init__(f"{len(errors)} lỗi khi kiểm tra dữ liệu.")


class ExportError(Exception):
    """Lỗi export."""
    pass


# ══════════════════════════════════════════════════════════
#  CẤU HÌNH CỘT EXPORT
# ══════════════════════════════════════════════════════════

FULL_EXPORT_COLUMNS: list[tuple[str, str, int]] = [
    ("SO_TT",           "STT",              6),
    ("MA_DK",           "Mã ĐK",          12),
    ("HO_VA_TEN",       "Họ và tên",       25),
    ("NGAY_SINH",       "Ngày sinh",       12),
    ("GIOI_TINH",       "Giới tính",        9),
    ("SO_CMT",          "Số CCCD",         15),
    ("NOI_CT",          "Nơi cư trú",     30),
    ("SO_HO_SO",        "Số hồ sơ",       15),
    ("MA_KY_SH",        "Mã kỳ SH",       12),
    ("SO_BAO_DANH",     "Số báo danh",    12),
    ("HANG_GPLX",       "Hạng GPLX",      10),
    ("NOI_DUNG_SH",     "Nội dung SH",    12),
    ("KQ_SH_LYTHUYET",  "KQ Lý thuyết",   12),
    ("KQ_SH_MOPHONG",   "KQ Mô phỏng",    12),
    ("KQ_SH_HINH",      "KQ Hình",        10),
    ("KQ_SH_DUONG",     "KQ Đường",       10),
    ("KET_QUA_SH",      "Kết quả SH",     12),
    ("MA_KHOA_HOC",     "Mã khóa học",    12),
    ("GHI_CHU_SH",      "Ghi chú",        20),
]

SHORT_EXPORT_COLUMNS: list[tuple[str, str, int]] = [
    ("SO_TT",           "STT",              6),
    ("MA_DK",           "Mã ĐK",          12),
    ("HO_VA_TEN",       "Họ và tên",       25),
    ("NGAY_SINH",       "Ngày sinh",       12),
    ("SO_CMT",          "Số CCCD",         15),
    ("HANG_GPLX",       "Hạng GPLX",      10),
    ("SO_BAO_DANH",     "SBD",             8),
    ("KET_QUA_SH",      "Kết quả",        12),
]

# ══════════════════════════════════════════════════════════
#  EXCEL STYLE
# ══════════════════════════════════════════════════════════

COLOR_HEADER_BG   = "#1a237e"
COLOR_HEADER_FONT = "#ffffff"

RESULT_BG_COLORS = {
    "đạt"       : "#C8E6C9",
    "dat"       : "#C8E6C9",
    "không đạt" : "#FFCDD2",
    "khong dat" : "#FFCDD2",
}


# ══════════════════════════════════════════════════════════
#  MAPPING CỘT CHO EXCEL/CSV IMPORT
# ══════════════════════════════════════════════════════════

COLUMN_MAPPING_NGUOI_LX: dict[str, str] = {
    "stt": "SO_TT", "số tt": "SO_TT", "so_tt": "SO_TT",
    "mã đăng ký": "MA_DK", "ma dk": "MA_DK", "ma_dk": "MA_DK",
    "họ tên đệm": "HO_TEN_DEM", "ho_ten_dem": "HO_TEN_DEM",
    "tên": "TEN", "ten": "TEN",
    "họ và tên": "HO_VA_TEN", "ho va ten": "HO_VA_TEN", "ho_va_ten": "HO_VA_TEN",
    "giới tính": "GIOI_TINH", "gioi_tinh": "GIOI_TINH",
    "ngày sinh": "NGAY_SINH", "ngay_sinh": "NGAY_SINH",
    "số cmt": "SO_CMT", "cccd": "SO_CMT", "so_cmt": "SO_CMT",
    "nơi cư trú": "NOI_CT", "noi_ct": "NOI_CT",
}

COLUMN_MAPPING_HO_SO: dict[str, str] = {
    "số hồ sơ": "SO_HO_SO", "so_ho_so": "SO_HO_SO",
    "hạng gplx": "HANG_GPLX", "hang_gplx": "HANG_GPLX",
    "số báo danh": "SO_BAO_DANH", "so_bao_danh": "SO_BAO_DANH",
    "kết quả": "KET_QUA_SH", "ket_qua_sh": "KET_QUA_SH",
    "kq lý thuyết": "KQ_SH_LYTHUYET", "kq_sh_lythuyet": "KQ_SH_LYTHUYET",
    "kq mô phỏng": "KQ_SH_MOPHONG", "kq_sh_mophong": "KQ_SH_MOPHONG",
    "kq hình": "KQ_SH_HINH", "kq_sh_hinh": "KQ_SH_HINH",
    "kq đường": "KQ_SH_DUONG", "kq_sh_duong": "KQ_SH_DUONG",
    "nội dung sh": "NOI_DUNG_SH", "noi_dung_sh": "NOI_DUNG_SH",
    "mã kỳ sh": "MA_KY_SH", "ma_ky_sh": "MA_KY_SH",
    "mã khóa học": "MA_KHOA_HOC", "ma_khoa_hoc": "MA_KHOA_HOC",
    "ghi chú": "GHI_CHU_SH", "ghi_chu_sh": "GHI_CHU_SH",
    "trạng thái": "TRANGTHAI", "trangthai": "TRANGTHAI",
}


# ══════════════════════════════════════════════════════════
#  CLASS IE SERVICE
# ══════════════════════════════════════════════════════════

class IEService:
    """
    Dịch vụ Import / Export hợp nhất v2.0.

    Import XML:
    - Đọc file XML theo cấu trúc SAT_HACH
    - Parse KY_SH → bảng ky_sh
    - Parse NGUOI_LX → bảng nguoi_lx
    - Parse HO_SO → bảng ho_so_sh
    - Tự tạo bản ghi nhap_kqsh rỗng

    Import Excel/CSV: (giữ tương thích)
    - Đọc, mapping cột, kiểm tra lỗi, lưu DB

    Export: Excel, CSV, PDF
    """

    SUPPORTED_FORMATS = [".xml", ".xlsx", ".csv"]
    MAX_ROWS = 50000

    def __init__(
        self,
        db_manager : DatabaseManager,
        logger     : Optional[LoggerService] = None,
    ) -> None:
        self.db  = db_manager
        self.log = logger

        # ── Import cache ───────────────────────────────────
        self._file_path    : str  = ""
        self._file_info    : dict = {}
        self._errors       : list[dict] = []

        # XML cache
        self._xml_ky_sh    : Optional[dict] = None
        self._xml_nguoi_lx : list[dict] = []
        self._xml_ho_so    : list[dict] = []
        self._xml_header   : dict = {}

        # Excel/CSV cache
        self._raw_df       : Optional[pd.DataFrame] = None
        self._mapped_df    : Optional[pd.DataFrame] = None

    # ══════════════════════════════════════════════════════
    #  PROPERTIES
    # ══════════════════════════════════════════════════════

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def file_info(self) -> dict:
        return self._file_info

    @property
    def errors(self) -> list[dict]:
        return self._errors

    @property
    def row_count(self) -> int:
        """Số bản ghi người lái xe đã đọc."""
        if self._xml_nguoi_lx:
            return len(self._xml_nguoi_lx)
        if self._mapped_df is not None:
            return len(self._mapped_df)
        return 0

    @property
    def xml_ky_sh(self) -> Optional[dict]:
        return self._xml_ky_sh

    @property
    def xml_nguoi_lx(self) -> list[dict]:
        return self._xml_nguoi_lx

    @property
    def xml_ho_so(self) -> list[dict]:
        return self._xml_ho_so

    # ══════════════════════════════════════════════════════
    #  ═══════════════ IMPORT XML ══════════════════════════
    # ══════════════════════════════════════════════════════

    def doc_file_xml(self, file_path: str) -> dict:
        """
        Đọc file XML theo cấu trúc SAT_HACH.

        Cấu trúc:
        SAT_HACH
        ├── HEADER
        ├── DATA
        │   ├── KY_SH
        │   └── NGUOI_LXS
        │       └── NGUOI_LX (nhiều)
        │           └── HO_SO
        └── Signature

        Returns
        -------
        dict: {
            "header"   : dict,
            "ky_sh"    : dict,
            "nguoi_lx" : list[dict],  # mỗi dict chứa cả HO_SO
            "total"    : int,
        }
        """
        try:
            path = Path(file_path)
            self._file_path = str(path)

            if not path.exists():
                raise ImportFileError(f"File không tồn tại: {file_path}")

            if path.suffix.lower() != ".xml":
                raise ImportFileError("File phải có định dạng .xml")

            if path.stat().st_size == 0:
                raise ImportFileError("File rỗng (0 bytes).")

            # ── Parse XML ──────────────────────────────────
            tree = ET.parse(str(path))
            root = tree.getroot()

            # Xử lý namespace nếu có
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"

            # ── Parse HEADER ───────────────────────────────
            self._xml_header = self._parse_element_to_dict(
                root.find(f"{ns}HEADER") or root.find("HEADER")
            )

            # ── Parse DATA ─────────────────────────────────
            data_elem = (
                root.find(f"{ns}DATA")
                or root.find("DATA")
                or root
            )

            # ── Parse KY_SH ───────────────────────────────
            ky_sh_elem = (
                data_elem.find(f"{ns}KY_SH")
                or data_elem.find("KY_SH")
            )
            self._xml_ky_sh = self._parse_element_to_dict(
                ky_sh_elem
            ) if ky_sh_elem is not None else {}

            # ── Parse NGUOI_LXS ────────────────────────────
            nguoi_lxs_elem = (
                data_elem.find(f"{ns}NGUOI_LXS")
                or data_elem.find("NGUOI_LXS")
                or data_elem
            )

            self._xml_nguoi_lx = []
            self._xml_ho_so    = []

            nguoi_lx_elems = (
                nguoi_lxs_elem.findall(f"{ns}NGUOI_LX")
                or nguoi_lxs_elem.findall("NGUOI_LX")
            )

            for idx, nlx_elem in enumerate(nguoi_lx_elems):
                # Parse thông tin người lái xe
                nguoi_data = self._parse_element_to_dict(
                    nlx_elem, exclude_children=["HO_SO"]
                )
                nguoi_data["_index"] = idx + 1

                # Parse HO_SO (con của NGUOI_LX)
                hoso_elem = (
                    nlx_elem.find(f"{ns}HO_SO")
                    or nlx_elem.find("HO_SO")
                )
                hoso_data = {}
                if hoso_elem is not None:
                    hoso_data = self._parse_element_to_dict(hoso_elem)

                # Gắn MA_DK vào hồ sơ
                ma_dk = nguoi_data.get("MA_DK", "")
                hoso_data["MA_DK"] = ma_dk

                self._xml_nguoi_lx.append(nguoi_data)
                self._xml_ho_so.append(hoso_data)

            # ── File info ──────────────────────────────────
            self._file_info = {
                "file_name"  : path.name,
                "file_size"  : path.stat().st_size,
                "file_type"  : ".xml",
                "total_rows" : len(self._xml_nguoi_lx),
                "ky_sh"      : self._xml_ky_sh.get("MAKYSH", ""),
            }

            self._log_info(
                "DocXML",
                f"Da doc XML: {path.name}; "
                f"KySH={self._xml_ky_sh.get('MAKYSH', '')}; "
                f"SoNguoi={len(self._xml_nguoi_lx)}"
            )

            return {
                "header"   : self._xml_header,
                "ky_sh"    : self._xml_ky_sh,
                "nguoi_lx" : self._xml_nguoi_lx,
                "ho_so"    : self._xml_ho_so,
                "total"    : len(self._xml_nguoi_lx),
            }

        except (ImportFileError, ImportXMLError):
            raise
        except ET.ParseError as exc:
            self._log_error("DocXML", f"XML parse error: {exc}")
            raise ImportXMLError(
                f"File XML không hợp lệ:\n{exc}"
            ) from exc
        except Exception as exc:
            self._log_error("DocXML", f"Loi: {exc}")
            raise ImportFileError(f"Lỗi đọc XML: {exc}") from exc

    def kiem_tra_xml(self) -> list[dict]:
        """
        Kiểm tra dữ liệu XML đã đọc trước khi lưu.

        Returns
        -------
        list[dict] danh sách lỗi
        """
        self._errors = []

        if not self._xml_nguoi_lx:
            self._errors.append({
                "row": 0, "column": "", "type": "NO_DATA",
                "message": "Không có dữ liệu NGUOI_LX.",
                "severity": "error",
            })
            return self._errors

        # Kiểm tra KY_SH
        if not self._xml_ky_sh or not self._xml_ky_sh.get("MAKYSH"):
            self._errors.append({
                "row": 0, "column": "MAKYSH", "type": "MISSING_KY_SH",
                "message": "Thiếu thông tin kỳ sát hạch (MAKYSH).",
                "severity": "warning",
            })

        # Kiểm tra từng NGUOI_LX
        seen_ma_dk = set()
        for idx, nguoi in enumerate(self._xml_nguoi_lx):
            row_num = idx + 1
            ma_dk = nguoi.get("MA_DK", "").strip()

            # MA_DK bắt buộc
            if not ma_dk:
                self._errors.append({
                    "row": row_num, "column": "MA_DK",
                    "type": "MISSING_FIELD",
                    "message": f"Dòng {row_num}: Thiếu MA_DK.",
                    "severity": "error",
                })
                continue

            # Trùng MA_DK trong file
            if ma_dk in seen_ma_dk:
                self._errors.append({
                    "row": row_num, "column": "MA_DK",
                    "type": "DUPLICATE_FILE",
                    "message": f"Dòng {row_num}: MA_DK='{ma_dk}' bị trùng trong file.",
                    "severity": "error",
                })
            seen_ma_dk.add(ma_dk)

            # Trùng MA_DK trong DB
            existing = self.db._fetchone(
                "SELECT MA_DK FROM nguoi_lx WHERE MA_DK = ?",
                (ma_dk,)
            )
            if existing:
                self._errors.append({
                    "row": row_num, "column": "MA_DK",
                    "type": "DUPLICATE_DB",
                    "message": f"Dòng {row_num}: MA_DK='{ma_dk}' đã tồn tại trong DB.",
                    "severity": "warning",
                })

            # HO_VA_TEN
            ho_ten = nguoi.get("HO_VA_TEN", "").strip()
            if not ho_ten:
                self._errors.append({
                    "row": row_num, "column": "HO_VA_TEN",
                    "type": "MISSING_FIELD",
                    "message": f"Dòng {row_num}: Thiếu HO_VA_TEN (MA_DK={ma_dk}).",
                    "severity": "warning",
                })

        self._log_info(
            "KiemTraXML",
            f"Kiem tra {len(self._xml_nguoi_lx)} ban ghi; "
            f"Loi={self._count_errors()}; "
            f"CanhBao={self._count_warnings()}"
        )

        return self._errors

    def luu_xml_database(
        self,
        skip_errors     : bool = True,
        update_existing : bool = False,
    ) -> dict:
        """
        Lưu dữ liệu XML vào database.

        Thứ tự:
        1. Lưu ky_sh
        2. Lưu nguoi_lx (từng bản ghi)
        3. Lưu ho_so_sh (từng bản ghi)
        4. Tạo nhap_kqsh rỗng cho mỗi MA_DK

        Returns
        -------
        dict kết quả
        """
        result = {
            "total": len(self._xml_nguoi_lx),
            "success": 0, "failed": 0, "updated": 0,
            "skipped": 0, "errors": [],
            "ky_sh_saved": False,
        }

        if not self._xml_nguoi_lx:
            raise ImportError_("Không có dữ liệu để lưu.")

        try:
            # ── 1. Lưu KY_SH ──────────────────────────────
            if self._xml_ky_sh and self._xml_ky_sh.get("MAKYSH"):
                self._save_ky_sh(self._xml_ky_sh, update_existing)
                result["ky_sh_saved"] = True

            # ── 2+3+4. Lưu từng NGUOI_LX + HO_SO + NHAP ──
            for idx in range(len(self._xml_nguoi_lx)):
                nguoi = self._xml_nguoi_lx[idx]
                hoso  = self._xml_ho_so[idx] if idx < len(self._xml_ho_so) else {}
                ma_dk = nguoi.get("MA_DK", "").strip()
                row_num = idx + 1

                if not ma_dk:
                    if skip_errors:
                        result["skipped"] += 1
                        continue
                    result["failed"] += 1
                    result["errors"].append(f"Dòng {row_num}: Thiếu MA_DK")
                    continue

                try:
                    # Kiểm tra tồn tại
                    existing = self.db._fetchone(
                        "SELECT MA_DK FROM nguoi_lx WHERE MA_DK = ?",
                        (ma_dk,)
                    )

                    if existing:
                        if update_existing:
                            self._update_nguoi_lx(nguoi)
                            self._update_ho_so_sh(hoso)
                            result["updated"] += 1
                        else:
                            if skip_errors:
                                result["skipped"] += 1
                            else:
                                result["failed"] += 1
                                result["errors"].append(
                                    f"Dòng {row_num}: MA_DK='{ma_dk}' đã tồn tại."
                                )
                    else:
                        self._insert_nguoi_lx(nguoi)
                        self._insert_ho_so_sh(hoso)
                        self._insert_nhap_kqsh(ma_dk)
                        result["success"] += 1

                except Exception as exc:
                    result["failed"] += 1
                    result["errors"].append(f"Dòng {row_num}: {exc}")
                    if not skip_errors:
                        continue

            self.db.commit()

            self._log_info(
                "ImportXML",
                f"Import XML: Tong={result['total']}; "
                f"OK={result['success']}; Update={result['updated']}; "
                f"Fail={result['failed']}; Skip={result['skipped']}"
            )

            return result

        except ImportError_:
            raise
        except Exception as exc:
            self.db.rollback()
            self._log_error("ImportXML", f"Loi luu DB: {exc}")
            raise ImportError_(f"Lỗi lưu database: {exc}") from exc

    # ──────────────────────────────────────────────────────
    #  XML: INSERT / UPDATE HELPERS
    # ──────────────────────────────────────────────────────

    def _save_ky_sh(self, data: dict, update: bool = False) -> None:
        """Lưu kỳ sát hạch."""
        ma_ky = data.get("MAKYSH", "")
        if not ma_ky:
            return

        existing = self.db._fetchone(
            "SELECT MAKYSH FROM ky_sh WHERE MAKYSH = ?", (ma_ky,)
        )

        fields = [
            "MAKYSH", "MATTSH", "NGAYSH", "GIOSH", "SOQD",
            "NGAYQD", "NGUOIQD", "CHUTICH_HDSH", "PHOCHUTICH_HDSH",
            "UV_GD_TTSH", "UV_TOTRUONG", "UV_THUKY", "TONGSODK",
        ]

        if existing and update:
            sets = ", ".join([f"{f} = ?" for f in fields if f != "MAKYSH"])
            vals = [data.get(f, "") for f in fields if f != "MAKYSH"]
            vals.append(ma_ky)
            self.db._execute(
                f"UPDATE ky_sh SET {sets} WHERE MAKYSH = ?",
                tuple(vals)
            )
        elif not existing:
            cols = ", ".join(fields)
            qs   = ", ".join(["?" for _ in fields])
            vals = [data.get(f, "") for f in fields]
            self.db._execute(
                f"INSERT INTO ky_sh ({cols}) VALUES ({qs})",
                tuple(vals)
            )

    def _insert_nguoi_lx(self, data: dict) -> None:
        """Insert bản ghi nguoi_lx."""
        fields = [
            "SO_TT", "MA_DK", "HO_TEN_DEM", "TEN", "HO_VA_TEN",
            "GIOI_TINH", "NGAY_SINH", "MA_QUOC_TICH",
            "NOI_CT", "NOI_CT_MA_DVHC", "NOI_CT_MA_DVQL", "SO_CMT",
        ]
        cols = ", ".join(fields)
        qs   = ", ".join(["?" for _ in fields])
        vals = [data.get(f, "") for f in fields]

        self.db._execute(
            f"INSERT INTO nguoi_lx ({cols}) VALUES ({qs})",
            tuple(vals)
        )

    def _update_nguoi_lx(self, data: dict) -> None:
        """Update bản ghi nguoi_lx theo MA_DK."""
        fields = [
            "SO_TT", "HO_TEN_DEM", "TEN", "HO_VA_TEN",
            "GIOI_TINH", "NGAY_SINH", "MA_QUOC_TICH",
            "NOI_CT", "NOI_CT_MA_DVHC", "NOI_CT_MA_DVQL", "SO_CMT",
        ]
        sets = ", ".join([f"{f} = ?" for f in fields])
        vals = [data.get(f, "") for f in fields]
        vals.append(data.get("MA_DK", ""))

        self.db._execute(
            f"UPDATE nguoi_lx SET {sets} WHERE MA_DK = ?",
            tuple(vals)
        )

    def _insert_ho_so_sh(self, data: dict) -> None:
        """Insert bản ghi ho_so_sh."""
        fields = [
            "MA_DK", "SO_HO_SO", "MA_KY_SH", "SO_BAO_DANH",
            "MA_CSDT", "MA_TTSH", "MA_SO_GTVT", "GIAY_CNSK",
            "HANG_GPLX", "SO_GPLX_DA_CO", "HANG_GPLX_DA_CO",
            "DVQL_GPLX_DACO", "NGAY_HH_GPLX_DACO",
            "SO_NAM_LAIXE", "SO_KM_ANTOAN", "SO_GIAY_CNTN",
            "SO_CCN", "NOI_DUNG_SH", "LY_DO_SH",
            "KET_QUA_SH", "KQ_SH_LYTHUYET", "KQ_SH_MOPHONG",
            "KQ_SH_HINH", "KQ_SH_DUONG", "GHI_CHU_SH",
            "ANH_CHAN_DUNG", "NGAY_TT_GPLX_DACO", "MA_KHOA_HOC",
            "SO_QD_SH", "NGAY_QD_SH", "NGUOI_QD_SH", "CHAT_LUONG_ANH",
        ]

        # Gắn MA_KY_SH từ ky_sh nếu hồ sơ chưa có
        if not data.get("MA_KY_SH") and self._xml_ky_sh:
            data["MA_KY_SH"] = self._xml_ky_sh.get("MAKYSH", "")

        cols = ", ".join(fields)
        qs   = ", ".join(["?" for _ in fields])
        vals = [data.get(f, "") for f in fields]

        self.db._execute(
            f"INSERT INTO ho_so_sh ({cols}) VALUES ({qs})",
            tuple(vals)
        )

    def _update_ho_so_sh(self, data: dict) -> None:
        """Update bản ghi ho_so_sh theo MA_DK."""
        fields = [
            "SO_HO_SO", "MA_KY_SH", "SO_BAO_DANH",
            "MA_CSDT", "MA_TTSH", "MA_SO_GTVT", "GIAY_CNSK",
            "HANG_GPLX", "SO_GPLX_DA_CO", "HANG_GPLX_DA_CO",
            "DVQL_GPLX_DACO", "NGAY_HH_GPLX_DACO",
            "SO_NAM_LAIXE", "SO_KM_ANTOAN", "SO_GIAY_CNTN",
            "SO_CCN", "NOI_DUNG_SH", "LY_DO_SH",
            "KET_QUA_SH", "KQ_SH_LYTHUYET", "KQ_SH_MOPHONG",
            "KQ_SH_HINH", "KQ_SH_DUONG", "GHI_CHU_SH",
            "ANH_CHAN_DUNG", "NGAY_TT_GPLX_DACO", "MA_KHOA_HOC",
            "SO_QD_SH", "NGAY_QD_SH", "NGUOI_QD_SH", "CHAT_LUONG_ANH",
        ]
        sets = ", ".join([f"{f} = ?" for f in fields])
        vals = [data.get(f, "") for f in fields]
        vals.append(data.get("MA_DK", ""))

        self.db._execute(
            f"UPDATE ho_so_sh SET {sets} WHERE MA_DK = ?",
            tuple(vals)
        )

    def _insert_nhap_kqsh(self, ma_dk: str) -> None:
        """Tạo bản ghi nhap_kqsh rỗng cho MA_DK."""
        existing = self.db._fetchone(
            "SELECT MA_DK FROM nhap_kqsh WHERE MA_DK = ?",
            (ma_dk,)
        )
        if not existing:
            self.db._execute(
                """
                INSERT INTO nhap_kqsh
                (MA_DK, NHAP_KQLT, NHAP_KQMP, NHAP_KQH, NHAP_KQD,
                 KETQUA_NHAP, TAPHOSO, TRANGTHAI)
                VALUES (?, '', '', '', '', '', '', '')
                """,
                (ma_dk,)
            )

    # ──────────────────────────────────────────────────────
    #  XML: PREVIEW
    # ──────────────────────────────────────────────────────

    def preview_xml(self, max_rows: int = 20) -> list[dict]:
        """Xem trước dữ liệu XML đã đọc."""
        result = []
        for idx, nguoi in enumerate(self._xml_nguoi_lx[:max_rows]):
            hoso = self._xml_ho_so[idx] if idx < len(self._xml_ho_so) else {}
            row = {
                "STT"        : idx + 1,
                "MA_DK"      : nguoi.get("MA_DK", ""),
                "HO_VA_TEN"  : nguoi.get("HO_VA_TEN", ""),
                "NGAY_SINH"  : nguoi.get("NGAY_SINH", ""),
                "SO_CMT"     : nguoi.get("SO_CMT", ""),
                "HANG_GPLX"  : hoso.get("HANG_GPLX", ""),
                "SO_BAO_DANH": hoso.get("SO_BAO_DANH", ""),
                "KET_QUA_SH" : hoso.get("KET_QUA_SH", ""),
            }
            result.append(row)
        return result

    # ══════════════════════════════════════════════════════
    #  ═══════════════ IMPORT EXCEL/CSV ════════════════════
    # ══════════════════════════════════════════════════════

    def doc_file(
        self, file_path: str,
        sheet_name: Any = 0, header_row: int = 0,
        encoding: str = "utf-8",
    ) -> pd.DataFrame:
        """Đọc file Excel hoặc CSV (giữ tương thích cũ)."""
        try:
            path = Path(file_path)
            self._file_path = str(path)

            if not path.exists():
                raise ImportFileError(f"File không tồn tại: {file_path}")

            ext = path.suffix.lower()
            if ext == ".xml":
                self.doc_file_xml(file_path)
                # Chuyển sang DataFrame cho preview
                self._mapped_df = pd.DataFrame(self.preview_xml(99999))
                return self._mapped_df

            if ext not in [".xlsx", ".csv"]:
                raise ImportFileError(f"Không hỗ trợ: {ext}")

            if ext == ".xlsx":
                df = pd.read_excel(path, sheet_name=sheet_name,
                                   header=header_row, engine="openpyxl", dtype=str)
            else:
                df = self._read_csv(str(path), header_row, encoding)

            df.dropna(how="all", inplace=True)
            df.reset_index(drop=True, inplace=True)

            if df.empty:
                raise ImportFileError("File không chứa dữ liệu.")
            if len(df) > self.MAX_ROWS:
                raise ImportFileError(f"Quá {self.MAX_ROWS} dòng.")

            self._raw_df = df.copy()
            self._file_info = {
                "file_name": path.name, "file_size": path.stat().st_size,
                "file_type": ext, "total_rows": len(df),
                "total_cols": len(df.columns),
            }

            # Mapping cột
            all_mapping = {**COLUMN_MAPPING_NGUOI_LX, **COLUMN_MAPPING_HO_SO}
            rn = {}
            for col in df.columns:
                n = str(col).strip().lower()
                if n in all_mapping:
                    rn[col] = all_mapping[n]
            self._mapped_df = df.rename(columns=rn)

            self._log_info("DocFile",
                           f"Doc file: {path.name}; Dong={len(df)}")
            return self._mapped_df

        except ImportFileError:
            raise
        except Exception as exc:
            self._log_error("DocFile", f"Loi: {exc}")
            raise ImportFileError(f"Lỗi đọc file: {exc}") from exc

    @staticmethod
    def _read_csv(path, header_row=0, encoding="utf-8"):
        for enc in [encoding, "utf-8-sig", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(path, header=header_row, encoding=enc, dtype=str)
                df.dropna(how="all", inplace=True)
                df.reset_index(drop=True, inplace=True)
                return df
            except UnicodeDecodeError:
                continue
        raise ImportFileError("Không đọc được CSV.")

    def preview(self, max_rows: int = 20) -> list[dict]:
        """Preview cho Excel/CSV."""
        if self._xml_nguoi_lx:
            return self.preview_xml(max_rows)
        if self._mapped_df is not None:
            return self._mapped_df.head(max_rows).fillna("").to_dict(orient="records")
        return []

    def lay_cot_chua_map(self) -> list[str]:
        if self._raw_df is None:
            return []
        all_mapping = {**COLUMN_MAPPING_NGUOI_LX, **COLUMN_MAPPING_HO_SO}
        return [
            col for col in self._raw_df.columns
            if str(col).strip().lower() not in all_mapping
        ]

    def lay_cot_da_map(self) -> list[str]:
        if self._mapped_df is not None:
            return list(self._mapped_df.columns)
        return []

    # ══════════════════════════════════════════════════════
    #  ═══════════════ EXPORT ══════════════════════════════
    # ══════════════════════════════════════════════════════

    def _get_export_data(
        self,
        ma_khoa_hoc: str = "", hang_gplx: str = "",
        ket_qua: str = "", ma_ky_sh: str = "",
    ) -> list[dict]:
        """
        Lấy dữ liệu JOIN nguoi_lx + ho_so_sh cho export.
        """
        sql = """
        SELECT n.SO_TT, n.MA_DK, n.HO_VA_TEN, n.NGAY_SINH,
               n.GIOI_TINH, n.SO_CMT, n.NOI_CT,
               h.SO_HO_SO, h.MA_KY_SH, h.SO_BAO_DANH,
               h.HANG_GPLX, h.NOI_DUNG_SH,
               h.KQ_SH_LYTHUYET, h.KQ_SH_MOPHONG,
               h.KQ_SH_HINH, h.KQ_SH_DUONG,
               h.KET_QUA_SH, h.MA_KHOA_HOC, h.GHI_CHU_SH
        FROM nguoi_lx n
        LEFT JOIN ho_so_sh h ON n.MA_DK = h.MA_DK
        WHERE 1=1
        """
        params = []

        if hang_gplx:
            sql += " AND h.HANG_GPLX = ?"
            params.append(hang_gplx)
        if ma_khoa_hoc:
            sql += " AND h.MA_KHOA_HOC = ?"
            params.append(ma_khoa_hoc)
        if ket_qua:
            sql += " AND h.KET_QUA_SH LIKE ?"
            params.append(f"%{ket_qua}%")
        if ma_ky_sh:
            sql += " AND h.MA_KY_SH = ?"
            params.append(ma_ky_sh)

        sql += " ORDER BY n.SO_TT"
        return self.db._fetchall(sql, tuple(params))

    def export_excel(
        self, output_path: str,
        full_columns: bool = False, title: str = "",
        **filters,
    ) -> dict:
        """Xuất Excel có format."""
        try:
            data = self._get_export_data(**filters)
            if not data:
                return {"success": False, "file_path": output_path,
                        "total_rows": 0, "message": "Không có dữ liệu."}

            cols = FULL_EXPORT_COLUMNS if full_columns else SHORT_EXPORT_COLUMNS
            df   = self._build_export_df(data, cols)

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
                start_row = 2 if title else 0
                df.to_excel(writer, index=False, sheet_name="DuLieu",
                            startrow=start_row)

                wb = writer.book
                ws = writer.sheets["DuLieu"]

                if title:
                    tf = wb.add_format({"bold": True, "font_size": 14,
                                        "font_color": COLOR_HEADER_BG,
                                        "align": "center"})
                    ws.merge_range(0, 0, 0, len(cols)-1, title, tf)
                    inf = wb.add_format({"font_size": 9, "italic": True,
                                         "align": "center", "font_color": "#666"})
                    ws.merge_range(1, 0, 1, len(cols)-1,
                                   f"Ngày xuất: {datetime.now().strftime('%d/%m/%Y %H:%M')} "
                                   f"| Tổng: {len(df)}", inf)

                hf = wb.add_format({"bold": True, "bg_color": COLOR_HEADER_BG,
                                    "font_color": COLOR_HEADER_FONT, "border": 1,
                                    "align": "center", "text_wrap": True})
                hr = start_row
                for ci, (_, h, w) in enumerate(cols):
                    ws.write(hr, ci, h, hf)
                    ws.set_column(ci, ci, w)

                cf = wb.add_format({"border": 1, "font_size": 10})
                for ri in range(len(df)):
                    for ci in range(len(cols)):
                        v = df.iloc[ri, ci]
                        ws.write(hr+1+ri, ci, "" if pd.isna(v) else str(v), cf)

                ws.freeze_panes(hr+1, 0)
                ws.autofilter(hr, 0, hr+len(df), len(cols)-1)

            self._log_info("ExportExcel",
                           f"Xuat {len(data)} ban ghi: {Path(output_path).name}")
            return {"success": True, "file_path": output_path,
                    "total_rows": len(data),
                    "message": f"Xuất thành công {len(data)} hồ sơ."}

        except Exception as exc:
            self._log_error("ExportExcel", f"Loi: {exc}")
            raise ExportError(f"Lỗi xuất Excel: {exc}") from exc

    def export_csv(self, output_path: str, full_columns: bool = False, **filters) -> dict:
        """Xuất CSV."""
        try:
            data = self._get_export_data(**filters)
            if not data:
                return {"success": False, "file_path": output_path,
                        "total_rows": 0, "message": "Không có dữ liệu."}
            cols = FULL_EXPORT_COLUMNS if full_columns else SHORT_EXPORT_COLUMNS
            df = self._build_export_df(data, cols)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
            self._log_info("ExportCSV", f"Xuat {len(data)} ban ghi CSV")
            return {"success": True, "file_path": output_path,
                    "total_rows": len(data),
                    "message": f"Xuất thành công {len(data)} hồ sơ."}
        except Exception as exc:
            raise ExportError(f"Lỗi xuất CSV: {exc}") from exc

    def export_pdf(self, output_path: str, title: str = "", **filters) -> dict:
        """Xuất PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet

            data = self._get_export_data(**filters)
            if not data:
                return {"success": False, "file_path": output_path,
                        "total_rows": 0, "message": "Không có dữ liệu."}

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            pdf_cols = [("MA_DK","Mã ĐK"),("HO_VA_TEN","Họ tên"),
                        ("NGAY_SINH","Ngày sinh"),("SO_CMT","CCCD"),
                        ("HANG_GPLX","Hạng"),("SO_BAO_DANH","SBD"),
                        ("KET_QUA_SH","Kết quả")]
            headers = ["STT"] + [c[1] for c in pdf_cols]
            tdata = [headers]
            for i, row in enumerate(data, 1):
                r = [str(i)] + [str(row.get(c[0],"") or "") for c in pdf_cols]
                tdata.append(r)

            doc = SimpleDocTemplate(output_path, pagesize=landscape(A4),
                                    leftMargin=15*mm, rightMargin=15*mm,
                                    topMargin=15*mm, bottomMargin=15*mm)
            elements = []
            styles = getSampleStyleSheet()
            if title:
                elements.append(Paragraph(title, styles["Title"]))
                elements.append(Spacer(1, 10))

            cw = [15*mm,25*mm,55*mm,25*mm,30*mm,18*mm,18*mm,25*mm]
            table = Table(tdata, colWidths=cw, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor(COLOR_HEADER_BG)),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("FONTSIZE",(0,0),(-1,0),9),
                ("FONTSIZE",(0,1),(-1,-1),8),
                ("GRID",(0,0),(-1,-1),0.5,colors.grey),
                ("ALIGN",(0,0),(-1,0),"CENTER"),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ]))
            elements.append(table)
            doc.build(elements)

            self._log_info("ExportPDF", f"Xuat {len(data)} ban ghi PDF")
            return {"success": True, "file_path": output_path,
                    "total_rows": len(data),
                    "message": f"Xuất thành công {len(data)} hồ sơ."}
        except ImportError:
            raise ExportError("Cần cài: pip install reportlab")
        except Exception as exc:
            raise ExportError(f"Lỗi PDF: {exc}") from exc

    # ══════════════════════════════════════════════════════
    #  TIỆN ÍCH
    # ══════════════════════════════════════════════════════

    def _build_export_df(self, data: list[dict], columns) -> pd.DataFrame:
        fields = [c[0] for c in columns]
        headers = [c[1] for c in columns]
        rows = []
        for idx, row in enumerate(data, 1):
            r = {}
            for f, h in zip(fields, headers):
                if f == "SO_TT":
                    r[h] = idx
                else:
                    r[h] = row.get(f, "") or ""
            rows.append(r)
        return pd.DataFrame(rows, columns=headers)

    def get_suggested_filename(self, file_type="xlsx", hang_gplx="", ma_khoa_hoc=""):
        parts = ["DuLieu"]
        if hang_gplx: parts.append(hang_gplx)
        if ma_khoa_hoc: parts.append(ma_khoa_hoc)
        parts.append(datetime.now().strftime("%Y%m%d_%H%M%S"))
        return "_".join(parts) + f".{file_type}"

    def lay_thong_ke_loi(self) -> dict:
        stats = {"total_errors": 0, "total_warnings": 0, "by_type": {}}
        for e in self._errors:
            if e.get("severity") == "error": stats["total_errors"] += 1
            else: stats["total_warnings"] += 1
            t = e.get("type","")
            stats["by_type"][t] = stats["by_type"].get(t,0) + 1
        return stats

    def reset_import(self) -> None:
        """Xóa toàn bộ cache import."""
        self._file_path = ""
        self._file_info = {}
        self._errors = []
        self._xml_ky_sh = None
        self._xml_nguoi_lx = []
        self._xml_ho_so = []
        self._xml_header = {}
        self._raw_df = None
        self._mapped_df = None

    @staticmethod
    def _parse_element_to_dict(elem, exclude_children: list = None) -> dict:
        """Parse XML element thành dict (1 cấp)."""
        if elem is None:
            return {}
        result = {}
        exclude = set(exclude_children or [])
        for child in elem:
            tag = child.tag
            # Xử lý namespace
            if "}" in tag:
                tag = tag.split("}")[1]
            if tag in exclude:
                continue
            result[tag] = (child.text or "").strip()
        # Thêm attributes
        for k, v in elem.attrib.items():
            result[f"@{k}"] = v
        return result

    def _count_errors(self):
        return sum(1 for e in self._errors if e.get("severity")=="error")

    def _count_warnings(self):
        return sum(1 for e in self._errors if e.get("severity")=="warning")

    def _log_info(self, action, detail):
        if self.log: self.log.info(module="IE", action=action, detail=detail)

    def _log_error(self, action, detail):
        if self.log: self.log.error(module="IE", action=action, detail=detail)