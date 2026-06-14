"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : services/logger_service.py
Mô tả     : Module ghi nhật ký hệ thống và thao tác người dùng
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

import os
import threading
from datetime import datetime
from pathlib  import Path
from enum     import Enum


# ══════════════════════════════════════════════════════════
#  ENUM MỨC ĐỘ LOG
# ══════════════════════════════════════════════════════════

class LogLevel(Enum):
    """Các mức độ ghi log."""
    INFO    = "INFO"
    WARNING = "WARNING"
    ERROR   = "ERROR"


# ══════════════════════════════════════════════════════════
#  ENUM MODULE
# ══════════════════════════════════════════════════════════

class LogModule(Enum):
    """
    Các module trong hệ thống.
    Dùng để chuẩn hoá tên module khi ghi log.
    """
    SYSTEM  = "System"
    HOSO    = "HoSo"
    IE      = "IE"
    DVHC    = "DVHC"
    CONFIG  = "Config"
    LOG     = "Log"


# ══════════════════════════════════════════════════════════
#  CLASS LOGGER SERVICE
# ══════════════════════════════════════════════════════════

class LoggerService:
    """
    Dịch vụ ghi nhật ký hệ thống và thao tác người dùng.

    Định dạng mỗi dòng log:
    ─────────────────────────────────────────────────────
    [YYYY-MM-DD HH:MM:SS] | LEVEL=INFO | USER=admin |
    MODULE=HoSo | ACTION=Them |
    DETAIL=SO_HO_SO=HS000123; HO_TEN=Nguyen Van A
    ─────────────────────────────────────────────────────

    Đặc điểm:
    - Thread-safe (dùng threading.Lock)
    - Tự động tạo file log nếu chưa tồn tại
    - Tự động tạo thư mục logs/ nếu chưa có
    - Giới hạn kích thước file (auto rotate)
    - Hỗ trợ lọc theo level, module, ngày tháng
    """

    # Kích thước tối đa 1 file log (mặc định 5 MB)
    MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024

    def __init__(
        self,
        log_file : str  = "logs/log.txt",
        user     : str  = "unknown",
        max_size : int  = None,        # bytes, None = dùng MAX_FILE_SIZE_BYTES
    ) -> None:
        """
        Parameters
        ----------
        log_file : đường dẫn tới file log
        user     : tên người dùng hiện tại
        max_size : giới hạn kích thước file log (bytes)
        """
        self._log_path  = Path(log_file)
        self._user      = user
        self._max_size  = max_size if max_size else self.MAX_FILE_SIZE_BYTES
        self._lock      = threading.Lock()

        # Tạo thư mục nếu chưa có
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

        # Ghi dòng phân cách khi mở session mới
        self._write_session_separator()

    # ──────────────────────────────────────────────────────
    #  PUBLIC API
    # ──────────────────────────────────────────────────────

    def info(
        self,
        module : str,
        action : str,
        detail : str = ""
    ) -> None:
        """Ghi log mức INFO."""
        self._write(LogLevel.INFO, module, action, detail)

    def warning(
        self,
        module : str,
        action : str,
        detail : str = ""
    ) -> None:
        """Ghi log mức WARNING."""
        self._write(LogLevel.WARNING, module, action, detail)

    def error(
        self,
        module : str,
        action : str,
        detail : str = ""
    ) -> None:
        """Ghi log mức ERROR."""
        self._write(LogLevel.ERROR, module, action, detail)

    # ──────────────────────────────────────────────────────
    #  ĐỌC / LỌC LOG
    # ──────────────────────────────────────────────────────

    def read_all(self) -> list[dict]:
        """
        Đọc toàn bộ file log, trả về list các dict đã parse.

        Returns
        -------
        list[dict] với các key:
            timestamp, level, user, module, action, detail
        """
        if not self._log_path.exists():
            return []

        records = []
        with self._lock:
            with open(self._log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("=") or line.startswith("-"):
                        continue
                    parsed = self._parse_line(line)
                    if parsed:
                        records.append(parsed)
        return records

    def filter_logs(
        self,
        date_from : str  = None,   # "YYYY-MM-DD"
        date_to   : str  = None,   # "YYYY-MM-DD"
        module    : str  = None,
        level     : str  = None,
        keyword   : str  = None,
    ) -> list[dict]:
        """
        Lọc log theo các tiêu chí.

        Parameters
        ----------
        date_from : ngày bắt đầu (YYYY-MM-DD), None = không lọc
        date_to   : ngày kết thúc (YYYY-MM-DD), None = không lọc
        module    : tên module, None = tất cả
        level     : INFO / WARNING / ERROR, None = tất cả
        keyword   : từ khoá tìm trong DETAIL, None = tất cả

        Returns
        -------
        list[dict] đã lọc
        """
        all_records = self.read_all()
        result      = []

        # Chuyển ngày lọc sang datetime.date để so sánh
        dt_from = self._parse_date(date_from) if date_from else None
        dt_to   = self._parse_date(date_to)   if date_to   else None

        for rec in all_records:
            # ── Lọc ngày ──────────────────────────────────
            if dt_from or dt_to:
                rec_date = self._parse_date(rec.get("timestamp", "")[:10])
                if rec_date is None:
                    continue
                if dt_from and rec_date < dt_from:
                    continue
                if dt_to   and rec_date > dt_to:
                    continue

            # ── Lọc module ────────────────────────────────
            if module and rec.get("module", "").lower() != module.lower():
                continue

            # ── Lọc level ─────────────────────────────────
            if level and rec.get("level", "").upper() != level.upper():
                continue

            # ── Lọc keyword ───────────────────────────────
            if keyword:
                kw = keyword.lower()
                searchable = (
                    rec.get("detail",  "").lower() + " " +
                    rec.get("action",  "").lower() + " " +
                    rec.get("module",  "").lower()
                )
                if kw not in searchable:
                    continue

            result.append(rec)

        return result

    def clear_old_logs(self, keep_days: int = 30) -> int:
        """
        Xóa các dòng log cũ hơn `keep_days` ngày.

        Returns
        -------
        Số dòng đã xóa
        """
        from datetime import timedelta

        all_records  = self.read_all()
        cutoff       = datetime.now().date() - timedelta(days=keep_days)
        kept         = []
        removed_count= 0

        for rec in all_records:
            rec_date = self._parse_date(rec.get("timestamp", "")[:10])
            if rec_date and rec_date < cutoff:
                removed_count += 1
            else:
                kept.append(rec)

        # Ghi lại file chỉ với bản ghi còn giữ
        with self._lock:
            with open(self._log_path, "w", encoding="utf-8") as f:
                for rec in kept:
                    f.write(self._format_line(
                        timestamp = rec.get("timestamp", ""),
                        level     = rec.get("level",     "INFO"),
                        user      = rec.get("user",      "unknown"),
                        module    = rec.get("module",    ""),
                        action    = rec.get("action",    ""),
                        detail    = rec.get("detail",    ""),
                    ) + "\n")

        self.info(
            module="Log",
            action="ClearOldLogs",
            detail=f"Da xoa {removed_count} dong log cu hon {keep_days} ngay."
        )
        return removed_count

    def export_to_excel(self, output_path: str) -> bool:
        """
        Xuất toàn bộ log ra file Excel.

        Parameters
        ----------
        output_path : đường dẫn file .xlsx sẽ tạo

        Returns
        -------
        True nếu thành công, False nếu lỗi
        """
        try:
            import pandas as pd

            records = self.read_all()
            if not records:
                return False

            df = pd.DataFrame(records, columns=[
                "timestamp", "level", "user", "module", "action", "detail"
            ])

            # Đổi tên cột sang tiếng Việt
            df.columns = [
                "Thời gian", "Mức độ", "Người dùng",
                "Module", "Hành động", "Chi tiết"
            ]

            with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="NhatKy")

                # Định dạng Excel
                workbook  = writer.book
                worksheet = writer.sheets["NhatKy"]

                # Format header
                header_fmt = workbook.add_format({
                    "bold"    : True,
                    "bg_color": "#1a237e",
                    "font_color": "#ffffff",
                    "border"  : 1,
                    "align"   : "center",
                    "valign"  : "vcenter",
                })

                # Format dòng ERROR
                error_fmt = workbook.add_format({
                    "bg_color"  : "#ffebee",
                    "font_color": "#c62828",
                })

                # Format dòng WARNING
                warn_fmt = workbook.add_format({
                    "bg_color"  : "#fff8e1",
                    "font_color": "#e65100",
                })

                # Ghi lại header với format
                for col_num, col_name in enumerate(df.columns):
                    worksheet.write(0, col_num, col_name, header_fmt)

                # Độ rộng cột
                col_widths = [20, 10, 15, 12, 18, 60]
                for i, w in enumerate(col_widths):
                    worksheet.set_column(i, i, w)

                # Tô màu theo level
                for row_num, rec in enumerate(records, start=1):
                    lvl = rec.get("level", "").upper()
                    if lvl == "ERROR":
                        fmt = error_fmt
                    elif lvl == "WARNING":
                        fmt = warn_fmt
                    else:
                        fmt = None

                    if fmt:
                        for col_num in range(len(df.columns)):
                            val = list(rec.values())[col_num]
                            worksheet.write(row_num, col_num, val, fmt)

            self.info(
                module="Log",
                action="ExportExcel",
                detail=f"Xuat log ra Excel: {output_path}"
            )
            return True

        except Exception as exc:
            self.error(
                module="Log",
                action="ExportExcel",
                detail=f"Loi xuat Excel: {exc}"
            )
            return False

    # ──────────────────────────────────────────────────────
    #  THUỘC TÍNH
    # ──────────────────────────────────────────────────────

    @property
    def user(self) -> str:
        return self._user

    @user.setter
    def user(self, value: str) -> None:
        """Cập nhật tên người dùng (dùng khi login/logout)."""
        self._user = value

    @property
    def log_path(self) -> str:
        return str(self._log_path)

    # ──────────────────────────────────────────────────────
    #  PRIVATE METHODS
    # ──────────────────────────────────────────────────────

    def _write(
        self,
        level  : LogLevel,
        module : str,
        action : str,
        detail : str,
    ) -> None:
        """
        Ghi một dòng log vào file (thread-safe).
        Tự động rotate file nếu vượt kích thước giới hạn.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line      = self._format_line(
            timestamp = timestamp,
            level     = level.value,
            user      = self._user,
            module    = module,
            action    = action,
            detail    = detail,
        )

        with self._lock:
            # Kiểm tra kích thước file → rotate nếu cần
            if self._log_path.exists():
                if self._log_path.stat().st_size >= self._max_size:
                    self._rotate_log()

            # Ghi dòng log
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

        # In ra console (hỗ trợ debug khi phát triển)
        print(line)

    @staticmethod
    def _format_line(
        timestamp : str,
        level     : str,
        user      : str,
        module    : str,
        action    : str,
        detail    : str,
    ) -> str:
        """
        Tạo chuỗi log theo định dạng chuẩn.

        Ví dụ:
        [2026-06-12 15:30:12] | LEVEL=INFO | USER=admin |
        MODULE=HoSo | ACTION=Them |
        DETAIL=SO_HO_SO=HS000123; HO_TEN=Nguyen Van A
        """
        return (
            f"[{timestamp}] | "
            f"LEVEL={level:<7} | "
            f"USER={user:<15} | "
            f"MODULE={module:<10} | "
            f"ACTION={action:<20} | "
            f"DETAIL={detail}"
        )

    def _rotate_log(self) -> None:
        """
        Đổi tên file log cũ thành log_YYYYMMDD_HHMMSS.txt
        rồi bắt đầu file log mới.
        """
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated    = self._log_path.with_name(
            f"{self._log_path.stem}_{timestamp}.txt"
        )
        self._log_path.rename(rotated)

        # Ghi thông báo vào file mới
        with open(self._log_path, "w", encoding="utf-8") as f:
            f.write(
                f"# Log rotate tu: {rotated.name}\n"
                f"# Bat dau: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

    def _write_session_separator(self) -> None:
        """Ghi dòng phân cách đánh dấu session mới."""
        separator = (
            "\n" + "=" * 80 + "\n"
            f"  SESSION BAT DAU: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
            f"| USER: {self._user}\n"
            + "=" * 80 + "\n"
        )
        with self._lock:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(separator)

    @staticmethod
    def _parse_line(line: str) -> dict | None:
        """
        Parse một dòng log thành dict.

        Returns None nếu dòng không đúng định dạng.
        """
        try:
            # Định dạng: [timestamp] | LEVEL=... | USER=... | ...
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 6:
                return None

            # Lấy timestamp: [2026-06-12 15:30:12]
            raw_ts    = parts[0].strip()
            timestamp = raw_ts.strip("[]") if raw_ts.startswith("[") else ""

            def _extract(part: str, key: str) -> str:
                """Lấy giá trị sau dấu = của key."""
                prefix = f"{key}="
                if part.strip().startswith(prefix):
                    return part.strip()[len(prefix):].strip()
                return ""

            return {
                "timestamp" : timestamp,
                "level"     : _extract(parts[1], "LEVEL"),
                "user"      : _extract(parts[2], "USER"),
                "module"    : _extract(parts[3], "MODULE"),
                "action"    : _extract(parts[4], "ACTION"),
                "detail"    : _extract(parts[5], "DETAIL"),
            }
        except Exception:
            return None

    @staticmethod
    def _parse_date(date_str: str):
        """Parse chuỗi YYYY-MM-DD thành datetime.date, None nếu lỗi."""
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except Exception:
            return None