"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : services/nguoi_lx_service.py
Mô tả     : Business logic cho quản lý hồ sơ người lái xe
            - CRUD hồ sơ
            - Tìm kiếm, lọc, phân trang
            - Thống kê
            - Kiểm tra nghiệp vụ
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

from typing   import Any, Optional
from datetime import datetime

from models.nguoi_lx_model import NguoiLX
from database.db_manager   import DatabaseManager
from services.logger_service import LoggerService


# ══════════════════════════════════════════════════════════
#  EXCEPTION TÙY CHỈNH
# ══════════════════════════════════════════════════════════

class HoSoError(Exception):
    """Lỗi nghiệp vụ liên quan tới hồ sơ."""
    pass


class HoSoValidationError(HoSoError):
    """Lỗi validate dữ liệu hồ sơ."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Lỗi validate: {'; '.join(errors)}")


class HoSoDuplicateError(HoSoError):
    """Lỗi trùng số hồ sơ (PRIMARY KEY)."""
    pass


class HoSoNotFoundError(HoSoError):
    """Không tìm thấy hồ sơ."""
    pass


# ══════════════════════════════════════════════════════════
#  SERVICE CLASS
# ══════════════════════════════════════════════════════════

class NguoiLXService:
    """
    Business logic layer cho quản lý hồ sơ người lái xe.

    Đóng vai trò trung gian giữa UI và Database:
    - Nhận dữ liệu từ UI → validate → gọi DatabaseManager
    - Trả kết quả về UI dưới dạng NguoiLX objects
    - Ghi log thao tác

    Sử dụng
    -------
    service = NguoiLXService(db_manager, logger)
    service.them_ho_so(data_dict)
    results = service.tim_kiem(ho_ten="Nguyễn")
    """

    def __init__(
        self,
        db_manager : DatabaseManager,
        logger     : Optional[LoggerService] = None
    ) -> None:
        """
        Parameters
        ----------
        db_manager : instance DatabaseManager đã connect
        logger     : LoggerService (optional)
        """
        self.db  = db_manager
        self.log = logger

    # ══════════════════════════════════════════════════════
    #  THÊM HỒ SƠ
    # ══════════════════════════════════════════════════════

    def them_ho_so(self, data: dict) -> NguoiLX:
        """
        Thêm mới 1 hồ sơ.

        Quy trình:
        1. Tạo NguoiLX object từ dict
        2. Tự động ghép HO_VA_TEN nếu thiếu
        3. Validate dữ liệu
        4. Kiểm tra trùng SO_HO_SO
        5. Insert vào DB
        6. Ghi log

        Parameters
        ----------
        data : dict chứa dữ liệu hồ sơ

        Returns
        -------
        NguoiLX object đã lưu thành công

        Raises
        ------
        HoSoValidationError : nếu dữ liệu không hợp lệ
        HoSoDuplicateError  : nếu SO_HO_SO đã tồn tại
        HoSoError           : lỗi khác
        """
        try:
            # ── Bước 1: Tạo object ────────────────────────
            nguoi = NguoiLX.from_dict(data)

            # ── Bước 2: Tự động ghép họ tên ───────────────
            nguoi = self._auto_fill(nguoi)

            # ── Bước 3: Validate ──────────────────────────
            errors = nguoi.validate()
            if errors:
                raise HoSoValidationError(errors)

            # ── Bước 4: Kiểm tra trùng ────────────────────
            existing = self.db.get_hoso_by_id(nguoi.SO_HO_SO)
            if existing:
                raise HoSoDuplicateError(
                    f"Số hồ sơ '{nguoi.SO_HO_SO}' đã tồn tại."
                )

            # ── Bước 5: Insert DB ─────────────────────────
            self.db.insert_hoso(nguoi.to_dict())

            # ── Bước 6: Log ───────────────────────────────
            self._log_info(
                action="Them",
                detail=(
                    f"SO_HO_SO={nguoi.SO_HO_SO}; "
                    f"HO_TEN={nguoi.HO_VA_TEN}; "
                    f"HANG={nguoi.HANG_GPLX}"
                )
            )

            return nguoi

        except (HoSoValidationError, HoSoDuplicateError):
            raise
        except Exception as exc:
            self._log_error(
                action="Them",
                detail=f"Loi them ho so: {exc}"
            )
            raise HoSoError(f"Lỗi thêm hồ sơ: {exc}") from exc

    def them_nhieu_ho_so(self, data_list: list[dict]) -> dict:
        """
        Thêm nhiều hồ sơ cùng lúc (dùng cho import).

        Parameters
        ----------
        data_list : list các dict hồ sơ

        Returns
        -------
        dict kết quả:
        {
            "success"   : int,   # số bản ghi thêm thành công
            "failed"    : int,   # số bản ghi thất bại
            "errors"    : list,  # chi tiết lỗi từng bản ghi
            "duplicates": list,  # danh sách SO_HO_SO bị trùng
        }
        """
        result = {
            "success"   : 0,
            "failed"    : 0,
            "errors"    : [],
            "duplicates": [],
        }

        for idx, data in enumerate(data_list):
            try:
                self.them_ho_so(data)
                result["success"] += 1
            except HoSoDuplicateError as exc:
                result["failed"] += 1
                result["duplicates"].append(data.get("SO_HO_SO", ""))
                result["errors"].append(
                    f"Dòng {idx + 1}: {exc}"
                )
            except HoSoValidationError as exc:
                result["failed"] += 1
                result["errors"].append(
                    f"Dòng {idx + 1}: {exc}"
                )
            except Exception as exc:
                result["failed"] += 1
                result["errors"].append(
                    f"Dòng {idx + 1}: Lỗi không xác định - {exc}"
                )

        self._log_info(
            action="ThemNhieu",
            detail=(
                f"Thanh cong: {result['success']}, "
                f"That bai: {result['failed']}"
            )
        )

        return result

    # ══════════════════════════════════════════════════════
    #  SỬA HỒ SƠ
    # ══════════════════════════════════════════════════════

    def sua_ho_so(self, so_ho_so: str, data: dict) -> NguoiLX:
        """
        Cập nhật hồ sơ theo SO_HO_SO.

        Quy trình:
        1. Kiểm tra hồ sơ tồn tại
        2. Merge dữ liệu cũ + mới
        3. Validate
        4. Update DB
        5. Ghi log (ghi rõ field thay đổi)

        Parameters
        ----------
        so_ho_so : số hồ sơ cần sửa
        data     : dict chứa các field cần cập nhật

        Returns
        -------
        NguoiLX object sau khi cập nhật

        Raises
        ------
        HoSoNotFoundError    : hồ sơ không tồn tại
        HoSoValidationError  : dữ liệu mới không hợp lệ
        """
        try:
            # ── Bước 1: Kiểm tra tồn tại ──────────────────
            existing = self.db.get_hoso_by_id(so_ho_so)
            if not existing:
                raise HoSoNotFoundError(
                    f"Không tìm thấy hồ sơ: '{so_ho_so}'"
                )

            # ── Bước 2: Merge dữ liệu ─────────────────────
            merged = dict(existing)
            changes = {}  # Lưu field thay đổi để ghi log

            for key, new_val in data.items():
                old_val = merged.get(key)
                if old_val != new_val:
                    changes[key] = {"old": old_val, "new": new_val}
                merged[key] = new_val

            if not changes:
                # Không có gì thay đổi
                return NguoiLX.from_dict(merged)

            # ── Bước 3: Validate ───────────────────────────
            nguoi_new = NguoiLX.from_dict(merged)
            nguoi_new = self._auto_fill(nguoi_new)
            errors    = nguoi_new.validate()
            if errors:
                raise HoSoValidationError(errors)

            # ── Bước 4: Update DB ──────────────────────────
            update_data = {k: data[k] for k in changes.keys() if k in data}
            self.db.update_hoso(so_ho_so, update_data)

            # ── Bước 5: Log chi tiết ───────────────────────
            changes_str = "; ".join([
                f"{k}: {v['old']} -> {v['new']}"
                for k, v in changes.items()
            ])
            self._log_info(
                action="Sua",
                detail=f"SO_HO_SO={so_ho_so}; {changes_str}"
            )

            return nguoi_new

        except (HoSoNotFoundError, HoSoValidationError):
            raise
        except Exception as exc:
            self._log_error(
                action="Sua",
                detail=f"Loi sua ho so {so_ho_so}: {exc}"
            )
            raise HoSoError(f"Lỗi sửa hồ sơ: {exc}") from exc

    # ══════════════════════════════════════════════════════
    #  XÓA HỒ SƠ
    # ══════════════════════════════════════════════════════

    def xoa_ho_so(self, so_ho_so: str) -> bool:
        """
        Xóa hồ sơ theo SO_HO_SO.

        Parameters
        ----------
        so_ho_so : số hồ sơ cần xóa

        Returns
        -------
        True nếu xóa thành công

        Raises
        ------
        HoSoNotFoundError : hồ sơ không tồn tại
        """
        try:
            # Lấy thông tin trước khi xóa (để ghi log)
            existing = self.db.get_hoso_by_id(so_ho_so)
            if not existing:
                raise HoSoNotFoundError(
                    f"Không tìm thấy hồ sơ: '{so_ho_so}'"
                )

            ho_ten = existing.get("HO_VA_TEN", "")

            result = self.db.delete_hoso(so_ho_so)

            self._log_info(
                action="Xoa",
                detail=f"SO_HO_SO={so_ho_so}; HO_TEN={ho_ten}"
            )

            return result

        except HoSoNotFoundError:
            raise
        except Exception as exc:
            self._log_error(
                action="Xoa",
                detail=f"Loi xoa ho so {so_ho_so}: {exc}"
            )
            raise HoSoError(f"Lỗi xóa hồ sơ: {exc}") from exc

    def xoa_nhieu_ho_so(self, ds_so_ho_so: list[str]) -> dict:
        """
        Xóa nhiều hồ sơ.

        Returns
        -------
        dict: {"success": int, "failed": int, "errors": list}
        """
        result = {
            "success": 0,
            "failed" : 0,
            "errors" : [],
        }

        for so_ho_so in ds_so_ho_so:
            try:
                self.xoa_ho_so(so_ho_so)
                result["success"] += 1
            except Exception as exc:
                result["failed"] += 1
                result["errors"].append(f"{so_ho_so}: {exc}")

        self._log_info(
            action="XoaNhieu",
            detail=(
                f"Thanh cong: {result['success']}, "
                f"That bai: {result['failed']}"
            )
        )
        return result

    # ══════════════════════════════════════════════════════
    #  TÌM KIẾM
    # ══════════════════════════════════════════════════════

    def tim_kiem(
        self,
        so_ho_so    : str = "",
        ho_ten      : str = "",
        so_cccd     : str = "",
        hang_gplx   : str = "",
        trang_thai  : str = "",
        ma_khoa_hoc : str = "",
        limit       : int = 1000,
        offset      : int = 0,
    ) -> list[NguoiLX]:
        """
        Tìm kiếm hồ sơ với nhiều điều kiện.

        Returns
        -------
        list[NguoiLX] kết quả tìm kiếm
        """
        try:
            rows = self.db.search_hoso(
                so_ho_so    = so_ho_so,
                ho_ten      = ho_ten,
                so_cccd     = so_cccd,
                hang_gplx   = hang_gplx,
                trang_thai  = trang_thai,
                ma_khoa_hoc = ma_khoa_hoc,
                limit       = limit,
                offset      = offset,
            )

            results = [NguoiLX.from_dict(row) for row in rows]

            self._log_info(
                action="TimKiem",
                detail=(
                    f"HoTen='{ho_ten}', HangGPLX='{hang_gplx}', "
                    f"Tim thay {len(results)} ban ghi"
                )
            )

            return results

        except Exception as exc:
            self._log_error(
                action="TimKiem",
                detail=f"Loi tim kiem: {exc}"
            )
            raise HoSoError(f"Lỗi tìm kiếm: {exc}") from exc

    def lay_ho_so(self, so_ho_so: str) -> Optional[NguoiLX]:
        """
        Lấy chi tiết 1 hồ sơ theo SO_HO_SO.

        Returns
        -------
        NguoiLX hoặc None
        """
        try:
            row = self.db.get_hoso_by_id(so_ho_so)
            if row:
                return NguoiLX.from_dict(row)
            return None
        except Exception as exc:
            self._log_error(
                action="LayHoSo",
                detail=f"Loi lay ho so {so_ho_so}: {exc}"
            )
            return None

    def lay_tat_ca(
        self,
        limit  : int = 1000,
        offset : int = 0
    ) -> list[NguoiLX]:
        """
        Lấy tất cả hồ sơ (có phân trang).

        Returns
        -------
        list[NguoiLX]
        """
        return self.tim_kiem(limit=limit, offset=offset)

    def dem_ho_so(self, **filters) -> int:
        """Đếm tổng số hồ sơ theo filter."""
        try:
            return self.db.count_hoso(**filters)
        except Exception:
            return 0

    # ══════════════════════════════════════════════════════
    #  THỐNG KÊ
    # ══════════════════════════════════════════════════════

    def thong_ke_tong_quan(self) -> dict:
        """
        Thống kê tổng quan về hồ sơ.

        Returns
        -------
        dict:
        {
            "tong_so"       : int,
            "theo_hang"     : {hang: count, ...},
            "theo_trang_thai": {trang_thai: count, ...},
            "theo_ket_qua"  : {ket_qua: count, ...},
        }
        """
        try:
            all_rows = self.db.search_hoso(limit=99999)

            stats = {
                "tong_so"         : len(all_rows),
                "theo_hang"       : {},
                "theo_trang_thai" : {},
                "theo_ket_qua"    : {},
            }

            for row in all_rows:
                # Theo hạng GPLX
                hang = row.get("HANG_GPLX", "Không rõ") or "Không rõ"
                stats["theo_hang"][hang] = (
                    stats["theo_hang"].get(hang, 0) + 1
                )

                # Theo trạng thái
                tt = row.get("TRANGTHAI", "Không rõ") or "Không rõ"
                stats["theo_trang_thai"][tt] = (
                    stats["theo_trang_thai"].get(tt, 0) + 1
                )

                # Theo kết quả
                kq = row.get("KET_QUA_SH", "Chưa có") or "Chưa có"
                stats["theo_ket_qua"][kq] = (
                    stats["theo_ket_qua"].get(kq, 0) + 1
                )

            return stats

        except Exception as exc:
            self._log_error(
                action="ThongKe",
                detail=f"Loi thong ke: {exc}"
            )
            return {
                "tong_so"         : 0,
                "theo_hang"       : {},
                "theo_trang_thai" : {},
                "theo_ket_qua"    : {},
            }

    def thong_ke_theo_khoa(self) -> dict:
        """
        Thống kê hồ sơ theo khóa học.

        Returns
        -------
        dict: {ma_khoa_hoc: {"tong": n, "dat": n, "khong_dat": n}, ...}
        """
        try:
            all_rows = self.db.search_hoso(limit=99999)
            stats = {}

            for row in all_rows:
                khoa = row.get("MA_KHOA_HOC", "Không rõ") or "Không rõ"
                if khoa not in stats:
                    stats[khoa] = {
                        "tong"      : 0,
                        "dat"       : 0,
                        "khong_dat" : 0,
                        "chua_thi"  : 0,
                    }

                stats[khoa]["tong"] += 1
                kq = str(row.get("KET_QUA_SH", "")).upper()
                if "DAT" in kq and "KHONG" not in kq:
                    stats[khoa]["dat"] += 1
                elif "KHONG" in kq:
                    stats[khoa]["khong_dat"] += 1
                else:
                    stats[khoa]["chua_thi"] += 1

            return stats

        except Exception as exc:
            self._log_error(
                action="ThongKeTheoKhoa",
                detail=f"Loi: {exc}"
            )
            return {}

    # ══════════════════════════════════════════════════════
    #  NGHIỆP VỤ ĐẶC THÙ
    # ══════════════════════════════════════════════════════

    def cap_nhat_ket_qua(
        self,
        so_ho_so       : str,
        kq_ly_thuyet   : str = None,
        kq_mo_phong    : str = None,
        kq_hinh        : str = None,
        kq_duong       : str = None,
        ket_qua_chung  : str = None,
    ) -> NguoiLX:
        """
        Cập nhật kết quả sát hạch cho 1 hồ sơ.

        Parameters
        ----------
        so_ho_so : số hồ sơ
        kq_*     : kết quả từng phần ("Đạt" / "Không đạt")
        ket_qua_chung : kết quả tổng hợp

        Returns
        -------
        NguoiLX đã cập nhật
        """
        update_data = {}

        if kq_ly_thuyet is not None:
            update_data["KQ_SH_LYTHUYET"] = kq_ly_thuyet
        if kq_mo_phong is not None:
            update_data["KQ_SH_MOPHONG"] = kq_mo_phong
        if kq_hinh is not None:
            update_data["KQ_SH_HINH"] = kq_hinh
        if kq_duong is not None:
            update_data["KQ_SH_DUONG"] = kq_duong
        if ket_qua_chung is not None:
            update_data["KET_QUA_SH"] = ket_qua_chung

        if not update_data:
            raise HoSoError("Không có dữ liệu kết quả để cập nhật.")

        return self.sua_ho_so(so_ho_so, update_data)

    def cap_nhat_trang_thai(
        self,
        so_ho_so   : str,
        trang_thai : str
    ) -> NguoiLX:
        """
        Cập nhật trạng thái hồ sơ.

        Parameters
        ----------
        so_ho_so   : số hồ sơ
        trang_thai : mã trạng thái mới

        Returns
        -------
        NguoiLX đã cập nhật
        """
        valid_tt = {
            "MOI", "CHO_XU_LY", "DA_DUYET",
            "DA_THI", "DAT", "KHONG_DAT",
            "HUY", "TAM_HOAN",
        }

        if trang_thai.upper() not in valid_tt:
            raise HoSoValidationError(
                [f"Trạng thái '{trang_thai}' không hợp lệ."]
            )

        return self.sua_ho_so(
            so_ho_so,
            {"TRANGTHAI": trang_thai.upper()}
        )

    def kiem_tra_ho_so_hop_le(self, so_ho_so: str) -> dict:
        """
        Kiểm tra toàn diện tính hợp lệ của 1 hồ sơ.
        Dùng trước khi cho phép dự thi.

        Returns
        -------
        dict:
        {
            "is_valid"  : bool,
            "warnings"  : list[str],
            "errors"    : list[str],
        }
        """
        result = {
            "is_valid"  : True,
            "warnings"  : [],
            "errors"    : [],
        }

        nguoi = self.lay_ho_so(so_ho_so)
        if not nguoi:
            result["is_valid"] = False
            result["errors"].append(
                f"Không tìm thấy hồ sơ: {so_ho_so}"
            )
            return result

        # Validate cơ bản
        val_errors = nguoi.validate()
        if val_errors:
            result["errors"].extend(val_errors)
            result["is_valid"] = False

        # Kiểm tra ảnh chân dung
        if not nguoi.ANH_CHAN_DUNG:
            result["warnings"].append("Chưa có ảnh chân dung.")

        # Kiểm tra giấy CNSK
        if not nguoi.GIAY_CNSK:
            result["warnings"].append("Chưa có giấy CN sức khỏe.")

        # Kiểm tra số báo danh
        if not nguoi.SO_BAO_DANH:
            result["warnings"].append("Chưa có số báo danh.")

        # Kiểm tra nội dung sát hạch
        if not nguoi.NOI_DUNG_SH:
            result["warnings"].append("Chưa xác định nội dung sát hạch.")

        # Kiểm tra trạng thái
        if nguoi.TRANGTHAI:
            if nguoi.TRANGTHAI in ("HUY",):
                result["is_valid"] = False
                result["errors"].append("Hồ sơ đã bị HỦY.")

        return result

    # ══════════════════════════════════════════════════════
    #  LẤY DANH MỤC
    # ══════════════════════════════════════════════════════

    def lay_danh_sach_hang_gplx(self) -> list[str]:
        """Lấy danh sách hạng GPLX đang có trong DB."""
        try:
            rows = self.db._fetchall(
                "SELECT DISTINCT HANG_GPLX FROM NguoiLX_HoSo "
                "WHERE HANG_GPLX IS NOT NULL AND HANG_GPLX != '' "
                "ORDER BY HANG_GPLX"
            )
            return [r["HANG_GPLX"] for r in rows]
        except Exception:
            return []

    def lay_danh_sach_trang_thai(self) -> list[str]:
        """Lấy danh sách trạng thái đang có trong DB."""
        try:
            rows = self.db._fetchall(
                "SELECT DISTINCT TRANGTHAI FROM NguoiLX_HoSo "
                "WHERE TRANGTHAI IS NOT NULL AND TRANGTHAI != '' "
                "ORDER BY TRANGTHAI"
            )
            return [r["TRANGTHAI"] for r in rows]
        except Exception:
            return []

    def lay_danh_sach_khoa_hoc(self) -> list[str]:
        """Lấy danh sách khoá học đang có trong DB."""
        try:
            rows = self.db._fetchall(
                "SELECT DISTINCT MA_KHOA_HOC FROM NguoiLX_HoSo "
                "WHERE MA_KHOA_HOC IS NOT NULL AND MA_KHOA_HOC != '' "
                "ORDER BY MA_KHOA_HOC"
            )
            return [r["MA_KHOA_HOC"] for r in rows]
        except Exception:
            return []

    # ══════════════════════════════════════════════════════
    #  PRIVATE HELPERS
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _auto_fill(nguoi: NguoiLX) -> NguoiLX:
        """
        Tự động điền dữ liệu dẫn xuất:
        - HO_VA_TEN = HO_TEN_DEM + TEN (nếu chưa có)
        - HO_TEN_DEM + TEN từ HO_VA_TEN (nếu chưa có)
        """
        # Ghép họ tên
        if not nguoi.HO_VA_TEN:
            parts = []
            if nguoi.HO_TEN_DEM:
                parts.append(nguoi.HO_TEN_DEM.strip())
            if nguoi.TEN:
                parts.append(nguoi.TEN.strip())
            if parts:
                nguoi.HO_VA_TEN = " ".join(parts)

        # Tách họ tên đệm + tên
        if nguoi.HO_VA_TEN and not nguoi.TEN:
            parts = nguoi.HO_VA_TEN.strip().split()
            if len(parts) >= 2:
                nguoi.TEN = parts[-1]
                nguoi.HO_TEN_DEM = " ".join(parts[:-1])
            elif len(parts) == 1:
                nguoi.TEN = parts[0]

        return nguoi

    def _log_info(self, action: str, detail: str) -> None:
        """Ghi log INFO cho module HoSo."""
        if self.log:
            self.log.info(
                module="HoSo",
                action=action,
                detail=detail
            )

    def _log_error(self, action: str, detail: str) -> None:
        """Ghi log ERROR cho module HoSo."""
        if self.log:
            self.log.error(
                module="HoSo",
                action=action,
                detail=detail
            )

    def _log_warning(self, action: str, detail: str) -> None:
        """Ghi log WARNING cho module HoSo."""
        if self.log:
            self.log.warning(
                module="HoSo",
                action=action,
                detail=detail
            )