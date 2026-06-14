"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : config/config_loader.py
Mô tả     : Load và quản lý file cấu hình JSON
            - Config_noidung.json : cấu hình nội dung thi
            - dvhc.json           : danh mục đơn vị hành chính
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

import json
import shutil
from pathlib  import Path
from datetime import datetime
from typing   import Any


# ══════════════════════════════════════════════════════════
#  CLASS CONFIG LOADER
# ══════════════════════════════════════════════════════════

class ConfigLoader:
    """
    Quản lý toàn bộ file cấu hình JSON của hệ thống.

    Chức năng
    ---------
    - Load Config_noidung.json  → dict nội dung thi
    - Load dvhc.json            → list đơn vị hành chính
    - Lưu lại JSON sau khi sửa
    - Tạo file mẫu khi chưa có
    - Backup file trước khi ghi đè
    - Validate dữ liệu cơ bản

    Sử dụng
    -------
    loader = ConfigLoader("config/Config_noidung.json")
    loader.load_noidung()
    data = loader.noidung_data          # dict
    loader.load_dvhc("config/dvhc.json")
    dvhc = loader.dvhc_data             # list[dict]
    """

    # ── Cấu trúc mặc định Config_noidung.json ─────────────
    DEFAULT_NOIDUNG: dict = {
        "meta": {
            "version"    : "1.0.0",
            "created_at" : "",
            "updated_at" : "",
            "description": "Cấu hình nội dung thi sát hạch GPLX"
        },
        "noi_dung_thi": [
            {
                "MA_NOI_DUNG" : "1",
                "LY_THUYET"   : True,
                "MO_PHONG"    : False,
                "HINH"        : True,
                "DUONG"       : False,
                "GHI_CHU"     : "Lý thuyết và Sa hình"
            },
            {
                "MA_NOI_DUNG" : "4",
                "LY_THUYET"   : True,
                "MO_PHONG"    : False,
                "HINH"        : True,
                "DUONG"       : True,
                "GHI_CHU"     : "Lý thuyết, Sa hình và Đường trường"
            },
            {
                "MA_NOI_DUNG" : "11",
                "LY_THUYET"   : True,
                "MO_PHONG"    : True,
                "HINH"        : True,
                "DUONG"       : True,
                "GHI_CHU"     : "Đầy đủ tất cả các phần thi"
            }
        ]
    }

    # ── Các field bắt buộc của mỗi bản ghi noi_dung_thi ──
    REQUIRED_NOIDUNG_FIELDS: list[str] = [
        "MA_NOI_DUNG",
        "LY_THUYET",
        "MO_PHONG",
        "HINH",
        "DUONG",
    ]

    # ── Các field bắt buộc của mỗi bản ghi DVHC ──────────
    REQUIRED_DVHC_FIELDS: list[str] = [
        "MA_DVHC",
        "TEN_DVHC",
    ]

    def __init__(self, noidung_path: str = "") -> None:
        """
        Parameters
        ----------
        noidung_path : đường dẫn tới Config_noidung.json
                       (có thể để rỗng, load sau bằng load_noidung)
        """
        self._noidung_path : Path            = Path(noidung_path) if noidung_path else Path()
        self._dvhc_path    : Path            = Path()

        self._noidung_data : dict            = {}
        self._dvhc_data    : list[dict]      = []

        self._noidung_loaded : bool          = False
        self._dvhc_loaded    : bool          = False

        # Load ngay nếu có đường dẫn và file tồn tại
        if noidung_path and self._noidung_path.exists():
            self.load_noidung()

    # ══════════════════════════════════════════════════════
    #  PROPERTIES
    # ══════════════════════════════════════════════════════

    @property
    def noidung_data(self) -> dict:
        """Toàn bộ dict Config_noidung.json."""
        return self._noidung_data

    @property
    def noidung_list(self) -> list[dict]:
        """Chỉ lấy list noi_dung_thi từ config."""
        return self._noidung_data.get("noi_dung_thi", [])

    @property
    def dvhc_data(self) -> list[dict]:
        """Toàn bộ list dvhc.json."""
        return self._dvhc_data

    @property
    def is_noidung_loaded(self) -> bool:
        return self._noidung_loaded

    @property
    def is_dvhc_loaded(self) -> bool:
        return self._dvhc_loaded

    @property
    def noidung_path(self) -> str:
        return str(self._noidung_path)

    @property
    def dvhc_path(self) -> str:
        return str(self._dvhc_path)

    # ══════════════════════════════════════════════════════
    #  LOAD CONFIG_NOIDUNG.JSON
    # ══════════════════════════════════════════════════════

    def load_noidung(self, path: str = "") -> dict:
        """
        Load file Config_noidung.json.

        Parameters
        ----------
        path : đường dẫn file, để rỗng dùng path đã khởi tạo

        Returns
        -------
        dict dữ liệu đã load

        Raises
        ------
        FileNotFoundError : nếu file không tồn tại
        ValueError        : nếu JSON không hợp lệ
        """
        if path:
            self._noidung_path = Path(path)

        if not self._noidung_path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file: {self._noidung_path}"
            )

        raw = self._read_json(self._noidung_path)

        # Validate cơ bản
        errors = self._validate_noidung(raw)
        if errors:
            raise ValueError(
                f"Config_noidung.json có lỗi:\n" + "\n".join(errors)
            )

        self._noidung_data    = raw
        self._noidung_loaded  = True
        return self._noidung_data

    def save_noidung(
        self,
        data         : dict  = None,
        backup       : bool  = True,
        path         : str   = ""
    ) -> bool:
        """
        Lưu dữ liệu nội dung thi vào Config_noidung.json.

        Parameters
        ----------
        data   : dict cần lưu, None = lưu self._noidung_data
        backup : True = tạo bản backup trước khi ghi đè
        path   : đường dẫn tùy chỉnh, rỗng = dùng path gốc

        Returns
        -------
        True nếu thành công
        """
        save_path  = Path(path) if path else self._noidung_path
        save_data  = data if data is not None else self._noidung_data

        if not save_data:
            raise ValueError("Không có dữ liệu để lưu.")

        # Cập nhật timestamp
        if "meta" not in save_data:
            save_data["meta"] = {}
        save_data["meta"]["updated_at"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Validate trước khi lưu
        errors = self._validate_noidung(save_data)
        if errors:
            raise ValueError(
                "Dữ liệu không hợp lệ:\n" + "\n".join(errors)
            )

        # Backup file cũ
        if backup and save_path.exists():
            self._backup_file(save_path)

        # Ghi JSON
        self._write_json(save_path, save_data)

        # Cập nhật cache
        self._noidung_data   = save_data
        self._noidung_loaded = True
        return True

    def update_noidung_item(
        self,
        ma_noi_dung : str,
        new_values  : dict
    ) -> bool:
        """
        Cập nhật một bản ghi nội dung thi theo mã.

        Parameters
        ----------
        ma_noi_dung : mã nội dung cần sửa
        new_values  : dict các field cần cập nhật

        Returns
        -------
        True nếu tìm thấy và cập nhật, False nếu không tìm thấy
        """
        items = self._noidung_data.get("noi_dung_thi", [])
        for i, item in enumerate(items):
            if str(item.get("MA_NOI_DUNG", "")) == str(ma_noi_dung):
                items[i].update(new_values)
                return True
        return False

    def add_noidung_item(self, item: dict) -> bool:
        """
        Thêm mới một bản ghi nội dung thi.

        Returns
        -------
        True nếu thêm thành công, False nếu mã đã tồn tại
        """
        # Kiểm tra trùng mã
        existing_codes = [
            str(x.get("MA_NOI_DUNG", ""))
            for x in self._noidung_data.get("noi_dung_thi", [])
        ]
        if str(item.get("MA_NOI_DUNG", "")) in existing_codes:
            return False

        if "noi_dung_thi" not in self._noidung_data:
            self._noidung_data["noi_dung_thi"] = []

        self._noidung_data["noi_dung_thi"].append(item)
        return True

    def delete_noidung_item(self, ma_noi_dung: str) -> bool:
        """
        Xóa một bản ghi nội dung thi theo mã.

        Returns
        -------
        True nếu xóa thành công, False nếu không tìm thấy
        """
        items = self._noidung_data.get("noi_dung_thi", [])
        before = len(items)
        self._noidung_data["noi_dung_thi"] = [
            x for x in items
            if str(x.get("MA_NOI_DUNG", "")) != str(ma_noi_dung)
        ]
        return len(self._noidung_data["noi_dung_thi"]) < before

    def get_noidung_by_ma(self, ma_noi_dung: str) -> dict | None:
        """Lấy một bản ghi nội dung thi theo mã."""
        for item in self._noidung_data.get("noi_dung_thi", []):
            if str(item.get("MA_NOI_DUNG", "")) == str(ma_noi_dung):
                return item
        return None

    # ══════════════════════════════════════════════════════
    #  LOAD DVHC.JSON
    # ══════════════════════════════════════════════════════

    def load_dvhc(self, path: str = "") -> list[dict]:
        """
        Load file dvhc.json.

        Parameters
        ----------
        path : đường dẫn file dvhc.json

        Returns
        -------
        list[dict] dữ liệu DVHC

        Raises
        ------
        FileNotFoundError : nếu file không tồn tại
        ValueError        : nếu JSON không hợp lệ
        """
        if path:
            self._dvhc_path = Path(path)

        if not self._dvhc_path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file: {self._dvhc_path}"
            )

        raw = self._read_json(self._dvhc_path)

        # dvhc.json có thể là list hoặc dict có key "dvhc"
        if isinstance(raw, list):
            data = raw
        elif isinstance(raw, dict):
            # Thử tìm key chứa list
            data = (
                raw.get("dvhc")
                or raw.get("data")
                or raw.get("DM_DVHC")
                or []
            )
        else:
            raise ValueError("dvhc.json phải là list hoặc dict.")

        # Validate mẫu
        errors = self._validate_dvhc(data)
        if errors:
            raise ValueError(
                "dvhc.json có lỗi:\n" + "\n".join(errors)
            )

        self._dvhc_data    = data
        self._dvhc_loaded  = True
        return self._dvhc_data

    def save_dvhc(
        self,
        data   : list[dict] = None,
        backup : bool       = True,
        path   : str        = ""
    ) -> bool:
        """
        Lưu dữ liệu DVHC vào dvhc.json.

        Parameters
        ----------
        data   : list cần lưu, None = lưu self._dvhc_data
        backup : True = tạo bản backup trước khi ghi đè
        path   : đường dẫn tùy chỉnh

        Returns
        -------
        True nếu thành công
        """
        save_path = Path(path) if path else self._dvhc_path
        save_data = data if data is not None else self._dvhc_data

        if save_data is None:
            raise ValueError("Không có dữ liệu DVHC để lưu.")

        if backup and save_path.exists():
            self._backup_file(save_path)

        self._write_json(save_path, save_data)

        self._dvhc_data   = save_data
        self._dvhc_loaded = True
        return True

    def get_dvhc_by_ma(self, ma_dvhc: Any) -> dict | None:
        """Tìm DVHC theo mã."""
        for item in self._dvhc_data:
            if str(item.get("MA_DVHC", "")) == str(ma_dvhc):
                return item
        return None

    def search_dvhc(
        self,
        keyword   : str = "",
        loai_dvhc : str = "",
    ) -> list[dict]:
        """
        Tìm kiếm DVHC theo từ khoá và loại.

        Parameters
        ----------
        keyword   : từ khoá tìm trong TEN_DVHC / TENDAYDU / MA_DVHC
        loai_dvhc : lọc theo LOAIDVHC (Tỉnh / Huyện / Xã ...)

        Returns
        -------
        list[dict] kết quả tìm kiếm
        """
        result = self._dvhc_data

        if loai_dvhc:
            result = [
                x for x in result
                if x.get("LOAIDVHC", "").lower() == loai_dvhc.lower()
            ]

        if keyword:
            kw = keyword.lower()
            result = [
                x for x in result
                if (
                    kw in str(x.get("MA_DVHC",    "")).lower() or
                    kw in str(x.get("TEN_DVHC",   "")).lower() or
                    kw in str(x.get("TENDAYDU",   "")).lower() or
                    kw in str(x.get("TENNGANGON", "")).lower()
                )
            ]

        return result

    def get_all_loai_dvhc(self) -> list[str]:
        """Lấy danh sách các loại DVHC không trùng."""
        loai_set = set()
        for item in self._dvhc_data:
            loai = item.get("LOAIDVHC", "").strip()
            if loai:
                loai_set.add(loai)
        return sorted(loai_set)

    # ══════════════════════════════════════════════════════
    #  TẠO FILE MẪU
    # ══════════════════════════════════════════════════════

    @staticmethod
    def create_default_noidung(path: str) -> None:
        """
        Tạo file Config_noidung.json mẫu tại đường dẫn chỉ định.

        Parameters
        ----------
        path : đường dẫn file cần tạo
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        default = dict(ConfigLoader.DEFAULT_NOIDUNG)
        default["meta"]["created_at"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        default["meta"]["updated_at"] = default["meta"]["created_at"]

        ConfigLoader._write_json(p, default)

    @staticmethod
    def create_default_dvhc(path: str) -> None:
        """
        Tạo file dvhc.json mẫu (rỗng) tại đường dẫn chỉ định.

        Parameters
        ----------
        path : đường dẫn file cần tạo
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        ConfigLoader._write_json(p, [])

    # ══════════════════════════════════════════════════════
    #  VALIDATE
    # ══════════════════════════════════════════════════════

    def _validate_noidung(self, data: dict) -> list[str]:
        """
        Kiểm tra tính hợp lệ của Config_noidung.json.

        Returns
        -------
        list[str] danh sách lỗi, rỗng = hợp lệ
        """
        errors = []

        if not isinstance(data, dict):
            errors.append("Config_noidung.json phải là object JSON (dict).")
            return errors

        items = data.get("noi_dung_thi", [])

        if not isinstance(items, list):
            errors.append("Trường 'noi_dung_thi' phải là array.")
            return errors

        # Kiểm tra từng bản ghi
        seen_codes = set()
        for idx, item in enumerate(items):
            # Kiểm tra field bắt buộc
            for field in self.REQUIRED_NOIDUNG_FIELDS:
                if field not in item:
                    errors.append(
                        f"Bản ghi #{idx + 1}: thiếu trường '{field}'."
                    )

            # Kiểm tra trùng mã
            ma = str(item.get("MA_NOI_DUNG", ""))
            if ma in seen_codes:
                errors.append(
                    f"Bản ghi #{idx + 1}: MA_NOI_DUNG='{ma}' bị trùng."
                )
            seen_codes.add(ma)

            # Kiểm tra kiểu bool
            for bool_field in ["LY_THUYET", "MO_PHONG", "HINH", "DUONG"]:
                val = item.get(bool_field)
                if val is not None and not isinstance(val, bool):
                    errors.append(
                        f"Bản ghi #{idx + 1}: "
                        f"'{bool_field}' phải là true/false."
                    )

        return errors

    def _validate_dvhc(self, data: list) -> list[str]:
        """
        Kiểm tra tính hợp lệ của dvhc.json.

        Returns
        -------
        list[str] danh sách lỗi, rỗng = hợp lệ
        """
        errors = []

        if not isinstance(data, list):
            errors.append("dvhc.json phải là array JSON (list).")
            return errors

        # Chỉ kiểm tra 5 bản ghi đầu (tránh chậm với file lớn)
        sample = data[:5]
        for idx, item in enumerate(sample):
            if not isinstance(item, dict):
                errors.append(f"Bản ghi #{idx + 1} không phải object.")
                continue
            for field in self.REQUIRED_DVHC_FIELDS:
                if field not in item:
                    errors.append(
                        f"Bản ghi #{idx + 1}: thiếu trường '{field}'."
                    )

        return errors

    # ══════════════════════════════════════════════════════
    #  TIỆN ÍCH ĐỌC / GHI JSON
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _read_json(path: Path) -> Any:
        """
        Đọc file JSON, trả về object Python.

        Raises
        ------
        ValueError : nếu JSON không hợp lệ
        """
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"File '{path.name}' không phải JSON hợp lệ: {exc}"
            ) from exc

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        """
        Ghi object Python ra file JSON (UTF-8, indent=2).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _backup_file(path: Path) -> Path:
        """
        Tạo bản sao backup của file trước khi ghi đè.

        Tên backup: <tên_file>_backup_YYYYMMDD_HHMMSS<.ext>

        Returns
        -------
        Path của file backup
        """
        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.stem}_backup_{timestamp}{path.suffix}"
        backup_path = path.with_name(backup_name)
        shutil.copy2(path, backup_path)
        return backup_path

    # ══════════════════════════════════════════════════════
    #  THÔNG TIN
    # ══════════════════════════════════════════════════════

    def summary(self) -> dict:
        """
        Trả về tóm tắt trạng thái của ConfigLoader.

        Returns
        -------
        dict thông tin tóm tắt
        """
        return {
            "noidung_path"    : str(self._noidung_path),
            "noidung_loaded"  : self._noidung_loaded,
            "noidung_count"   : len(self.noidung_list),
            "dvhc_path"       : str(self._dvhc_path),
            "dvhc_loaded"     : self._dvhc_loaded,
            "dvhc_count"      : len(self._dvhc_data),
        }

    def __repr__(self) -> str:
        s = self.summary()
        return (
            f"ConfigLoader("
            f"noidung={s['noidung_count']} items, "
            f"dvhc={s['dvhc_count']} items)"
        )