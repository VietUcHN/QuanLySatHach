"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : services/dvhc_service.py
Mô tả     : Business logic cho quản lý đơn vị hành chính
            - CRUD DVHC
            - Đồng bộ JSON ↔ SQLite
            - Tìm kiếm, lọc, phân cấp
            - Thống kê
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

from typing import Any, Optional

from models.dvhc_model       import (
    DVHC,
    dvhc_list_from_dicts,
    dvhc_list_to_dicts,
    build_dvhc_tree,
    VALID_LOAI_DVHC,
    CAP_TINH,
    CAP_HUYEN,
    CAP_XA,
)
from config.config_loader    import ConfigLoader
from database.db_manager     import DatabaseManager
from services.logger_service import LoggerService


# ══════════════════════════════════════════════════════════
#  EXCEPTION TÙY CHỈNH
# ══════════════════════════════════════════════════════════

class DVHCError(Exception):
    """Lỗi nghiệp vụ liên quan tới DVHC."""
    pass


class DVHCValidationError(DVHCError):
    """Lỗi validate dữ liệu DVHC."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Lỗi validate: {'; '.join(errors)}")


class DVHCDuplicateError(DVHCError):
    """Lỗi trùng mã DVHC."""
    pass


class DVHCNotFoundError(DVHCError):
    """Không tìm thấy DVHC."""
    pass


# ══════════════════════════════════════════════════════════
#  SERVICE CLASS
# ══════════════════════════════════════════════════════════

class DVHCService:
    """
    Business logic layer cho quản lý đơn vị hành chính.

    Chức năng chính:
    - CRUD trên dvhc.json (nguồn chính)
    - Đồng bộ dữ liệu JSON → SQLite
    - Tìm kiếm, lọc theo mã / tên / loại / cấp
    - Xây dựng cây phân cấp DVHC
    - Thống kê

    Luồng dữ liệu:
    ┌──────────┐     load      ┌──────────────┐
    │ dvhc.json│ ──────────── →│ ConfigLoader  │
    └──────────┘               └──────────────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │  DVHCService  │
                               └──────────────┘
                                      │
                             sync     │    search
                               ▼      │       ▼
                          ┌────────┐  │  ┌────────┐
                          │ SQLite │  │  │   UI   │
                          └────────┘  │  └────────┘

    Sử dụng
    -------
    service = DVHCService(config_loader, db_manager, logger)
    service.load_from_json()
    results = service.tim_kiem(keyword="Hà Nội")
    service.dong_bo_sqlite()
    """

    def __init__(
        self,
        config_loader : ConfigLoader,
        db_manager    : DatabaseManager,
        logger        : Optional[LoggerService] = None
    ) -> None:
        """
        Parameters
        ----------
        config_loader : instance ConfigLoader đã load dvhc.json
        db_manager    : instance DatabaseManager đã connect
        logger        : LoggerService (optional)
        """
        self.config = config_loader
        self.db     = db_manager
        self.log    = logger

        # Cache danh sách DVHC objects (đã parse từ JSON)
        self._dvhc_list : list[DVHC] = []
        self._loaded    : bool       = False

    # ══════════════════════════════════════════════════════
    #  PROPERTIES
    # ══════════════════════════════════════════════════════

    @property
    def dvhc_list(self) -> list[DVHC]:
        """Trả về danh sách DVHC hiện tại trong cache."""
        return self._dvhc_list

    @property
    def is_loaded(self) -> bool:
        """Kiểm tra đã load dữ liệu chưa."""
        return self._loaded

    @property
    def total_count(self) -> int:
        """Tổng số bản ghi DVHC."""
        return len(self._dvhc_list)

    # ══════════════════════════════════════════════════════
    #  LOAD DỮ LIỆU
    # ══════════════════════════════════════════════════════

    def load_from_json(self, path: str = "") -> int:
        """
        Load dữ liệu DVHC từ file dvhc.json.

        Parameters
        ----------
        path : đường dẫn file (rỗng = dùng path trong ConfigLoader)

        Returns
        -------
        Số bản ghi đã load

        Raises
        ------
        DVHCError : nếu không load được
        """
        try:
            if path:
                raw_list = self.config.load_dvhc(path)
            else:
                raw_list = self.config.dvhc_data

            if not raw_list:
                self._log_warning(
                    action="LoadJSON",
                    detail="dvhc.json rong hoac chua load."
                )
                self._dvhc_list = []
                self._loaded    = True
                return 0

            self._dvhc_list = dvhc_list_from_dicts(raw_list)
            self._loaded    = True

            self._log_info(
                action="LoadJSON",
                detail=f"Da load {len(self._dvhc_list)} ban ghi DVHC tu JSON"
            )

            return len(self._dvhc_list)

        except Exception as exc:
            self._log_error(
                action="LoadJSON",
                detail=f"Loi load dvhc.json: {exc}"
            )
            raise DVHCError(f"Lỗi load DVHC từ JSON: {exc}") from exc

    def load_from_sqlite(self) -> int:
        """
        Load dữ liệu DVHC từ bảng DM_DVHC trong SQLite.

        Returns
        -------
        Số bản ghi đã load
        """
        try:
            rows = self.db.get_dvhc_all()
            self._dvhc_list = dvhc_list_from_dicts(rows)
            self._loaded    = True

            self._log_info(
                action="LoadSQLite",
                detail=f"Da load {len(self._dvhc_list)} ban ghi DVHC tu SQLite"
            )

            return len(self._dvhc_list)

        except Exception as exc:
            self._log_error(
                action="LoadSQLite",
                detail=f"Loi load DVHC tu SQLite: {exc}"
            )
            raise DVHCError(f"Lỗi load DVHC từ SQLite: {exc}") from exc

    # ══════════════════════════════════════════════════════
    #  ĐỒNG BỘ JSON ↔ SQLITE
    # ══════════════════════════════════════════════════════

    def dong_bo_sqlite(self) -> dict:
        """
        Đồng bộ dữ liệu từ JSON cache → bảng DM_DVHC trong SQLite.

        Chiến lược: Xóa hết bảng cũ → INSERT toàn bộ từ cache.

        Returns
        -------
        dict:
        {
            "old_count" : int,   # số bản ghi cũ bị xóa
            "new_count" : int,   # số bản ghi mới chèn
            "success"   : bool,
        }
        """
        try:
            if not self._dvhc_list:
                raise DVHCError(
                    "Không có dữ liệu DVHC trong cache để đồng bộ. "
                    "Hãy load_from_json() trước."
                )

            # Chuyển list DVHC → list dict cho sync
            dict_list = dvhc_list_to_dicts(self._dvhc_list)

            old_count, new_count = self.db.sync_dvhc(dict_list)

            self._log_info(
                action="DongBoSQLite",
                detail=(
                    f"Dong bo hoan tat: "
                    f"Xoa {old_count} cu, them {new_count} moi"
                )
            )

            return {
                "old_count" : old_count,
                "new_count" : new_count,
                "success"   : True,
            }

        except Exception as exc:
            self._log_error(
                action="DongBoSQLite",
                detail=f"Loi dong bo: {exc}"
            )
            raise DVHCError(f"Lỗi đồng bộ DVHC: {exc}") from exc

    def dong_bo_nguoc(self) -> int:
        """
        Đồng bộ ngược: SQLite → JSON file.
        Load từ SQLite → lưu lại dvhc.json.

        Returns
        -------
        Số bản ghi đã lưu
        """
        try:
            # Load từ SQLite
            self.load_from_sqlite()

            # Lưu ra JSON
            dict_list = dvhc_list_to_dicts(self._dvhc_list)
            self.config.save_dvhc(dict_list)

            self._log_info(
                action="DongBoNguoc",
                detail=f"Da luu {len(self._dvhc_list)} ban ghi DVHC ra JSON"
            )

            return len(self._dvhc_list)

        except Exception as exc:
            self._log_error(
                action="DongBoNguoc",
                detail=f"Loi dong bo nguoc: {exc}"
            )
            raise DVHCError(f"Lỗi đồng bộ ngược: {exc}") from exc

    # ══════════════════════════════════════════════════════
    #  CRUD
    # ══════════════════════════════════════════════════════

    def them_dvhc(self, data: dict) -> DVHC:
        """
        Thêm mới 1 đơn vị hành chính.

        Quy trình:
        1. Tạo DVHC object
        2. Validate
        3. Kiểm tra trùng MA_DVHC
        4. Thêm vào cache
        5. Ghi log

        Parameters
        ----------
        data : dict chứa dữ liệu DVHC

        Returns
        -------
        DVHC object đã thêm

        Raises
        ------
        DVHCValidationError : dữ liệu không hợp lệ
        DVHCDuplicateError  : mã DVHC đã tồn tại
        """
        try:
            # ── Bước 1: Tạo object ────────────────────────
            dvhc = DVHC.from_dict(data)

            # ── Bước 2: Validate ──────────────────────────
            errors = dvhc.validate()
            if errors:
                raise DVHCValidationError(errors)

            # ── Bước 3: Kiểm tra trùng ────────────────────
            existing = self.tim_theo_ma(dvhc.MA_DVHC)
            if existing:
                raise DVHCDuplicateError(
                    f"Mã DVHC '{dvhc.MA_DVHC}' đã tồn tại: "
                    f"'{existing.TEN_DVHC}'"
                )

            # ── Bước 4: Thêm vào cache ────────────────────
            self._dvhc_list.append(dvhc)

            # ── Bước 5: Log ───────────────────────────────
            self._log_info(
                action="Them",
                detail=(
                    f"MA_DVHC={dvhc.MA_DVHC}; "
                    f"TEN={dvhc.TEN_DVHC}; "
                    f"LOAI={dvhc.LOAIDVHC}"
                )
            )

            return dvhc

        except (DVHCValidationError, DVHCDuplicateError):
            raise
        except Exception as exc:
            self._log_error(
                action="Them",
                detail=f"Loi them DVHC: {exc}"
            )
            raise DVHCError(f"Lỗi thêm DVHC: {exc}") from exc

    def sua_dvhc(self, ma_dvhc: int, data: dict) -> DVHC:
        """
        Cập nhật 1 đơn vị hành chính theo mã.

        Parameters
        ----------
        ma_dvhc : mã DVHC cần sửa
        data    : dict chứa field cần cập nhật

        Returns
        -------
        DVHC object sau khi cập nhật

        Raises
        ------
        DVHCNotFoundError   : không tìm thấy
        DVHCValidationError : dữ liệu không hợp lệ
        """
        try:
            # Tìm trong cache
            idx = self._find_index(ma_dvhc)
            if idx is None:
                raise DVHCNotFoundError(
                    f"Không tìm thấy DVHC với mã: {ma_dvhc}"
                )

            old_dvhc = self._dvhc_list[idx]

            # Merge dữ liệu cũ + mới
            merged = old_dvhc.to_full_dict()
            changes = {}

            for key, new_val in data.items():
                old_val = merged.get(key)
                if old_val != new_val:
                    changes[key] = {"old": old_val, "new": new_val}
                merged[key] = new_val

            if not changes:
                return old_dvhc  # Không thay đổi

            # Validate
            new_dvhc = DVHC.from_dict(merged)
            errors   = new_dvhc.validate()
            if errors:
                raise DVHCValidationError(errors)

            # Cập nhật cache
            self._dvhc_list[idx] = new_dvhc

            # Log chi tiết thay đổi
            changes_str = "; ".join([
                f"{k}: {v['old']} -> {v['new']}"
                for k, v in changes.items()
            ])
            self._log_info(
                action="Sua",
                detail=f"MA_DVHC={ma_dvhc}; {changes_str}"
            )

            return new_dvhc

        except (DVHCNotFoundError, DVHCValidationError):
            raise
        except Exception as exc:
            self._log_error(
                action="Sua",
                detail=f"Loi sua DVHC {ma_dvhc}: {exc}"
            )
            raise DVHCError(f"Lỗi sửa DVHC: {exc}") from exc

    def xoa_dvhc(self, ma_dvhc: int) -> bool:
        """
        Xóa 1 đơn vị hành chính theo mã.

        Parameters
        ----------
        ma_dvhc : mã DVHC cần xóa

        Returns
        -------
        True nếu xóa thành công

        Raises
        ------
        DVHCNotFoundError : không tìm thấy
        DVHCError         : có DVHC con phụ thuộc
        """
        try:
            # Tìm trong cache
            idx = self._find_index(ma_dvhc)
            if idx is None:
                raise DVHCNotFoundError(
                    f"Không tìm thấy DVHC với mã: {ma_dvhc}"
                )

            dvhc = self._dvhc_list[idx]

            # Kiểm tra có DVHC con không
            children = self._get_children(ma_dvhc)
            if children:
                raise DVHCError(
                    f"Không thể xóa DVHC '{dvhc.TEN_DVHC}' "
                    f"vì có {len(children)} đơn vị con phụ thuộc."
                )

            # Xóa khỏi cache
            self._dvhc_list.pop(idx)

            # Log
            self._log_info(
                action="Xoa",
                detail=(
                    f"MA_DVHC={ma_dvhc}; "
                    f"TEN={dvhc.TEN_DVHC}; "
                    f"LOAI={dvhc.LOAIDVHC}"
                )
            )

            return True

        except (DVHCNotFoundError, DVHCError):
            raise
        except Exception as exc:
            self._log_error(
                action="Xoa",
                detail=f"Loi xoa DVHC {ma_dvhc}: {exc}"
            )
            raise DVHCError(f"Lỗi xóa DVHC: {exc}") from exc

    # ══════════════════════════════════════════════════════
    #  LƯU JSON
    # ══════════════════════════════════════════════════════

    def luu_json(self, path: str = "") -> bool:
        """
        Lưu toàn bộ DVHC cache ra file dvhc.json.
        Tự động tạo backup trước khi ghi đè.

        Parameters
        ----------
        path : đường dẫn tùy chỉnh, rỗng = dùng path gốc

        Returns
        -------
        True nếu lưu thành công
        """
        try:
            dict_list = dvhc_list_to_dicts(self._dvhc_list)
            self.config.save_dvhc(dict_list, backup=True, path=path)

            self._log_info(
                action="LuuJSON",
                detail=f"Da luu {len(self._dvhc_list)} ban ghi DVHC ra JSON"
            )

            return True

        except Exception as exc:
            self._log_error(
                action="LuuJSON",
                detail=f"Loi luu JSON: {exc}"
            )
            raise DVHCError(f"Lỗi lưu DVHC JSON: {exc}") from exc

    # ══════════════════════════════════════════════════════
    #  TÌM KIẾM
    # ══════════════════════════════════════════════════════

    def tim_kiem(
        self,
        keyword   : str = "",
        loai_dvhc : str = "",
        cap       : str = "",
        limit     : int = 500,
    ) -> list[DVHC]:
        """
        Tìm kiếm DVHC trong cache.

        Parameters
        ----------
        keyword   : từ khoá tìm trong mã / tên / tên đầy đủ
        loai_dvhc : lọc theo LOAIDVHC (chính xác)
        cap       : lọc theo cấp: "tinh", "huyen", "xa"
        limit     : giới hạn kết quả

        Returns
        -------
        list[DVHC] kết quả
        """
        result = self._dvhc_list

        # ── Lọc cấp ───────────────────────────────────────
        if cap:
            cap_lower = cap.lower()
            if cap_lower == "tinh":
                result = [d for d in result if d.is_cap_tinh()]
            elif cap_lower == "huyen":
                result = [d for d in result if d.is_cap_huyen()]
            elif cap_lower == "xa":
                result = [d for d in result if d.is_cap_xa()]

        # ── Lọc loại ──────────────────────────────────────
        if loai_dvhc:
            result = [
                d for d in result
                if d.LOAIDVHC == loai_dvhc
            ]

        # ── Lọc keyword ───────────────────────────────────
        if keyword:
            kw = keyword.lower()
            filtered = []
            for d in result:
                searchable = " ".join([
                    str(d.MA_DVHC    or ""),
                    str(d.TEN_DVHC   or ""),
                    str(d.TENNGANGON or ""),
                    str(d.TENDAYDU   or ""),
                ]).lower()
                if kw in searchable:
                    filtered.append(d)
            result = filtered

        # ── Giới hạn ──────────────────────────────────────
        return result[:limit]

    def tim_theo_ma(self, ma_dvhc: int) -> Optional[DVHC]:
        """
        Tìm DVHC theo mã (trong cache).

        Returns
        -------
        DVHC hoặc None
        """
        if ma_dvhc is None:
            return None
        for d in self._dvhc_list:
            if d.MA_DVHC == int(ma_dvhc):
                return d
        return None

    def tim_theo_ten(self, ten: str) -> list[DVHC]:
        """
        Tìm DVHC theo tên (LIKE).

        Returns
        -------
        list[DVHC]
        """
        if not ten:
            return []
        kw = ten.lower()
        return [
            d for d in self._dvhc_list
            if kw in str(d.TEN_DVHC or "").lower()
            or kw in str(d.TENDAYDU or "").lower()
        ]

    # ══════════════════════════════════════════════════════
    #  PHÂN CẤP
    # ══════════════════════════════════════════════════════

    def lay_danh_sach_tinh(self) -> list[DVHC]:
        """Lấy tất cả đơn vị cấp Tỉnh/TP trực thuộc TW."""
        return [d for d in self._dvhc_list if d.is_cap_tinh()]

    def lay_danh_sach_huyen(
        self,
        ma_tinh: int = None
    ) -> list[DVHC]:
        """
        Lấy danh sách cấp Huyện/Quận.

        Parameters
        ----------
        ma_tinh : mã tỉnh cha (MA_DVQL), None = tất cả

        Returns
        -------
        list[DVHC] cấp huyện
        """
        result = [d for d in self._dvhc_list if d.is_cap_huyen()]
        if ma_tinh is not None:
            result = [d for d in result if d.MA_DVQL == int(ma_tinh)]
        return result

    def lay_danh_sach_xa(
        self,
        ma_huyen: int = None
    ) -> list[DVHC]:
        """
        Lấy danh sách cấp Xã/Phường.

        Parameters
        ----------
        ma_huyen : mã huyện cha (MA_DVQL), None = tất cả

        Returns
        -------
        list[DVHC] cấp xã
        """
        result = [d for d in self._dvhc_list if d.is_cap_xa()]
        if ma_huyen is not None:
            result = [d for d in result if d.MA_DVQL == int(ma_huyen)]
        return result

    def lay_dvhc_con(self, ma_dvhc: int) -> list[DVHC]:
        """
        Lấy tất cả DVHC con trực tiếp (MA_DVQL = ma_dvhc).

        Returns
        -------
        list[DVHC] danh sách con
        """
        return self._get_children(ma_dvhc)

    def lay_cay_dvhc(self) -> dict:
        """
        Xây dựng cây phân cấp toàn bộ DVHC.

        Returns
        -------
        dict dạng {ma: {"item": DVHC, "children": [...]}, ...}
        """
        return build_dvhc_tree(self._dvhc_list)

    def lay_duong_dan_dvhc(self, ma_dvhc: int) -> list[DVHC]:
        """
        Lấy đường dẫn phân cấp từ DVHC đến gốc (Xã → Huyện → Tỉnh).

        Parameters
        ----------
        ma_dvhc : mã DVHC cần tìm đường dẫn

        Returns
        -------
        list[DVHC] từ gốc (Tỉnh) đến lá, hoặc rỗng nếu không tìm thấy

        Ví dụ:
        [Tỉnh Hà Nội, Quận Ba Đình, Phường Phúc Xạ]
        """
        path    = []
        current = self.tim_theo_ma(ma_dvhc)
        visited = set()  # Tránh vòng lặp vô hạn

        while current and current.MA_DVHC not in visited:
            visited.add(current.MA_DVHC)
            path.insert(0, current)  # Chèn đầu → gốc ở đầu list
            if current.MA_DVQL:
                current = self.tim_theo_ma(current.MA_DVQL)
            else:
                break

        return path

    # ══════════════════════════════════════════════════════
    #  THỐNG KÊ
    # ══════════════════════════════════════════════════════

    def thong_ke(self) -> dict:
        """
        Thống kê tổng quan DVHC.

        Returns
        -------
        dict:
        {
            "tong_so"       : int,
            "theo_cap"      : {cap: count, ...},
            "theo_loai"     : {loai: count, ...},
            "so_tinh"       : int,
            "so_huyen"      : int,
            "so_xa"         : int,
        }
        """
        stats = {
            "tong_so"  : len(self._dvhc_list),
            "theo_cap" : {
                "Tỉnh/TP"    : 0,
                "Huyện/Quận" : 0,
                "Xã/Phường"  : 0,
                "Khác"        : 0,
            },
            "theo_loai": {},
        }

        for d in self._dvhc_list:
            # Theo cấp
            cap = d.get_cap_hanh_chinh()
            stats["theo_cap"][cap] = stats["theo_cap"].get(cap, 0) + 1

            # Theo loại
            loai = d.LOAIDVHC or "Không rõ"
            stats["theo_loai"][loai] = stats["theo_loai"].get(loai, 0) + 1

        stats["so_tinh"]  = stats["theo_cap"]["Tỉnh/TP"]
        stats["so_huyen"] = stats["theo_cap"]["Huyện/Quận"]
        stats["so_xa"]    = stats["theo_cap"]["Xã/Phường"]

        return stats

    def lay_danh_sach_loai(self) -> list[str]:
        """Lấy danh sách LOAIDVHC không trùng."""
        loai_set = set()
        for d in self._dvhc_list:
            if d.LOAIDVHC:
                loai_set.add(d.LOAIDVHC)
        return sorted(loai_set)

    # ══════════════════════════════════════════════════════
    #  KIỂM TRA
    # ══════════════════════════════════════════════════════

    def kiem_tra_toan_ven(self) -> dict:
        """
        Kiểm tra toàn vẹn dữ liệu DVHC.

        Returns
        -------
        dict:
        {
            "is_valid"        : bool,
            "trung_ma"        : list[int],   # mã bị trùng
            "ma_dvql_loi"     : list[int],   # MA_DVQL trỏ đến mã không tồn tại
            "loai_khong_hop_le": list[dict],  # bản ghi có LOAIDVHC không hợp lệ
        }
        """
        result = {
            "is_valid"         : True,
            "trung_ma"         : [],
            "ma_dvql_loi"      : [],
            "loai_khong_hop_le": [],
        }

        # Kiểm tra trùng mã
        seen_ma = set()
        for d in self._dvhc_list:
            if d.MA_DVHC in seen_ma:
                result["trung_ma"].append(d.MA_DVHC)
                result["is_valid"] = False
            seen_ma.add(d.MA_DVHC)

        # Kiểm tra MA_DVQL trỏ đúng
        all_ma = {d.MA_DVHC for d in self._dvhc_list}
        for d in self._dvhc_list:
            if d.MA_DVQL and d.MA_DVQL not in all_ma:
                result["ma_dvql_loi"].append(d.MA_DVHC)
                result["is_valid"] = False

        # Kiểm tra LOAIDVHC hợp lệ
        for d in self._dvhc_list:
            if d.LOAIDVHC and d.LOAIDVHC not in VALID_LOAI_DVHC:
                result["loai_khong_hop_le"].append({
                    "MA_DVHC"  : d.MA_DVHC,
                    "TEN_DVHC" : d.TEN_DVHC,
                    "LOAIDVHC" : d.LOAIDVHC,
                })
                result["is_valid"] = False

        return result

    def so_sanh_json_sqlite(self) -> dict:
        """
        So sánh dữ liệu giữa JSON cache và SQLite.

        Returns
        -------
        dict:
        {
            "json_count"    : int,
            "sqlite_count"  : int,
            "matched"       : bool,
            "chi_co_json"   : list[int],   # mã chỉ có trong JSON
            "chi_co_sqlite" : list[int],   # mã chỉ có trong SQLite
        }
        """
        try:
            # Lấy mã từ JSON cache
            json_ma = {d.MA_DVHC for d in self._dvhc_list if d.MA_DVHC}

            # Lấy mã từ SQLite
            sqlite_rows = self.db.get_dvhc_all()
            sqlite_ma   = {
                row.get("MA_DVHC")
                for row in sqlite_rows
                if row.get("MA_DVHC")
            }

            chi_co_json   = sorted(json_ma - sqlite_ma)
            chi_co_sqlite = sorted(sqlite_ma - json_ma)

            return {
                "json_count"    : len(json_ma),
                "sqlite_count"  : len(sqlite_ma),
                "matched"       : len(chi_co_json) == 0 and len(chi_co_sqlite) == 0,
                "chi_co_json"   : chi_co_json,
                "chi_co_sqlite" : chi_co_sqlite,
            }

        except Exception as exc:
            self._log_error(
                action="SoSanh",
                detail=f"Loi so sanh JSON vs SQLite: {exc}"
            )
            return {
                "json_count"    : len(self._dvhc_list),
                "sqlite_count"  : 0,
                "matched"       : False,
                "chi_co_json"   : [],
                "chi_co_sqlite" : [],
            }

    # ══════════════════════════════════════════════════════
    #  PRIVATE HELPERS
    # ══════════════════════════════════════════════════════

    def _find_index(self, ma_dvhc: int) -> Optional[int]:
        """Tìm index trong cache theo mã DVHC."""
        for i, d in enumerate(self._dvhc_list):
            if d.MA_DVHC == int(ma_dvhc):
                return i
        return None

    def _get_children(self, ma_dvhc: int) -> list[DVHC]:
        """Lấy danh sách DVHC con trực tiếp."""
        return [
            d for d in self._dvhc_list
            if d.MA_DVQL == int(ma_dvhc)
        ]

    def _log_info(self, action: str, detail: str) -> None:
        if self.log:
            self.log.info(module="DVHC", action=action, detail=detail)

    def _log_error(self, action: str, detail: str) -> None:
        if self.log:
            self.log.error(module="DVHC", action=action, detail=detail)

    def _log_warning(self, action: str, detail: str) -> None:
        if self.log:
            self.log.warning(module="DVHC", action=action, detail=detail)