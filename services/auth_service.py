"""
============================================================
PHẦN MỀM QUẢN LÝ DỮ LIỆU SÁT HẠCH GPLX
============================================================
File      : services/auth_service.py
Mô tả     : Dịch vụ xác thực và phân quyền người dùng
            - Đăng nhập / Đăng xuất
            - Quản lý tài khoản (CRUD)
            - Quản lý vai trò (Role)
            - Kiểm tra quyền truy cập (Permission)
            - Hash password SHA-256
Tác giả   : [ThienTon]
Phiên bản : 1.0.0
Ngày tạo  : 2026-06-12
============================================================
"""

import hashlib
from datetime import datetime
from typing   import Optional, Any
from dataclasses import dataclass, asdict, field

from database.db_manager     import DatabaseManager
from services.logger_service import LoggerService


# ══════════════════════════════════════════════════════════
#  DATACLASS
# ══════════════════════════════════════════════════════════

@dataclass
class UserInfo:
    """Thông tin người dùng đang đăng nhập."""
    id            : int    = 0
    username      : str    = ""
    full_name     : str    = ""
    role_id       : int    = 0
    role_name     : str    = ""
    is_active     : int    = 1
    created_at    : str    = ""
    last_login    : str    = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def __repr__(self) -> str:
        return (
            f"UserInfo(username='{self.username}', "
            f"role='{self.role_name}')"
        )


@dataclass
class PermissionInfo:
    """Thông tin quyền truy cập."""
    role_id         : int = 0
    menu_main       : int = 0
    menu_import     : int = 0
    menu_export     : int = 0
    menu_doi_sanh   : int = 0
    menu_config     : int = 0
    menu_user       : int = 0
    can_add         : int = 0
    can_edit        : int = 0
    can_delete      : int = 0
    can_print       : int = 0

    def has_menu(self, menu_name: str) -> bool:
        """
        Kiểm tra quyền truy cập menu.

        Parameters
        ----------
        menu_name : tên menu (main, import, export, doi_sanh, config, user)

        Returns
        -------
        True nếu có quyền
        """
        attr = f"menu_{menu_name}"
        return getattr(self, attr, 0) == 1

    def has_action(self, action: str) -> bool:
        """
        Kiểm tra quyền thao tác.

        Parameters
        ----------
        action : tên thao tác (add, edit, delete, print)

        Returns
        -------
        True nếu có quyền
        """
        attr = f"can_{action}"
        return getattr(self, attr, 0) == 1

    def to_dict(self) -> dict:
        return asdict(self)

    def __repr__(self) -> str:
        menus = []
        for m in ["main", "import", "export", "doi_sanh", "config", "user"]:
            if self.has_menu(m):
                menus.append(m)
        actions = []
        for a in ["add", "edit", "delete", "print"]:
            if self.has_action(a):
                actions.append(a)
        return (
            f"PermissionInfo(menus={menus}, actions={actions})"
        )


@dataclass
class RoleInfo:
    """Thông tin vai trò."""
    id          : int = 0
    role_name   : str = ""
    description : str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════
#  EXCEPTION
# ══════════════════════════════════════════════════════════

class AuthError(Exception):
    """Lỗi xác thực."""
    pass


class LoginError(AuthError):
    """Lỗi đăng nhập."""
    pass


class PermissionDeniedError(AuthError):
    """Không có quyền truy cập."""
    pass


class AccountError(AuthError):
    """Lỗi quản lý tài khoản."""
    pass


# ══════════════════════════════════════════════════════════
#  CLASS AUTH SERVICE
# ══════════════════════════════════════════════════════════

class AuthService:
    """
    Dịch vụ xác thực và phân quyền.

    Sử dụng
    -------
    auth = AuthService(db_manager, logger)

    # Đăng nhập
    user = auth.login("admin", "admin123")

    # Kiểm tra quyền
    if auth.check_permission("import"):
        ...

    # Quản lý tài khoản
    auth.create_account("user1", "pass123", "Nguyen Van A", role_id=3)
    """

    def __init__(
        self,
        db_manager : DatabaseManager,
        logger     : Optional[LoggerService] = None,
    ) -> None:
        self.db  = db_manager
        self.log = logger

        # Thông tin phiên đăng nhập hiện tại
        self._current_user       : Optional[UserInfo]       = None
        self._current_permission : Optional[PermissionInfo] = None
        self._is_logged_in       : bool = False

    # ══════════════════════════════════════════════════════
    #  PROPERTIES
    # ══════════════════════════════════════════════════════

    @property
    def current_user(self) -> Optional[UserInfo]:
        """Người dùng đang đăng nhập."""
        return self._current_user

    @property
    def current_permission(self) -> Optional[PermissionInfo]:
        """Quyền truy cập hiện tại."""
        return self._current_permission

    @property
    def is_logged_in(self) -> bool:
        """Kiểm tra đã đăng nhập chưa."""
        return self._is_logged_in

    @property
    def current_username(self) -> str:
        """Lấy username hiện tại."""
        if self._current_user:
            return self._current_user.username
        return "unknown"

    @property
    def current_role(self) -> str:
        """Lấy role name hiện tại."""
        if self._current_user:
            return self._current_user.role_name
        return ""

    # ══════════════════════════════════════════════════════
    #  ĐĂNG NHẬP / ĐĂNG XUẤT
    # ══════════════════════════════════════════════════════

    def login(self, username: str, password: str) -> UserInfo:
        """
        Đăng nhập hệ thống.

        Parameters
        ----------
        username : tên đăng nhập
        password : mật khẩu (plain text)

        Returns
        -------
        UserInfo nếu đăng nhập thành công

        Raises
        ------
        LoginError : sai username/password hoặc tài khoản bị khóa
        """
        try:
            # ── Kiểm tra username ──────────────────────────
            if not username or not password:
                raise LoginError("Tên đăng nhập và mật khẩu không được trống.")

            username = username.strip().lower()
            pw_hash  = self._hash_password(password)

            # ── Tìm tài khoản ──────────────────────────────
            row = self.db._fetchone(
                """
                SELECT a.*, r.role_name
                FROM account a
                LEFT JOIN role r ON a.role_id = r.id
                WHERE a.username = ?
                """,
                (username,)
            )

            if not row:
                self._log_warning(
                    "Login",
                    f"Dang nhap that bai: username='{username}' khong ton tai"
                )
                raise LoginError("Tên đăng nhập không tồn tại.")

            # ── Kiểm tra mật khẩu ─────────────────────────
            if row["password_hash"] != pw_hash:
                self._log_warning(
                    "Login",
                    f"Dang nhap that bai: username='{username}' sai mat khau"
                )
                raise LoginError("Mật khẩu không đúng.")

            # ── Kiểm tra trạng thái ───────────────────────
            if row["is_active"] != 1:
                self._log_warning(
                    "Login",
                    f"Dang nhap that bai: username='{username}' bi khoa"
                )
                raise LoginError(
                    "Tài khoản đã bị khóa. Liên hệ quản trị viên."
                )

            # ── Tạo UserInfo ───────────────────────────────
            self._current_user = UserInfo(
                id         = row["id"],
                username   = row["username"],
                full_name  = row["full_name"] or "",
                role_id    = row["role_id"] or 0,
                role_name  = row["role_name"] or "",
                is_active  = row["is_active"],
                created_at = row["created_at"] or "",
                last_login = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

            # ── Load permission ────────────────────────────
            self._current_permission = self._load_permission(
                self._current_user.role_id
            )

            self._is_logged_in = True

            # ── Cập nhật last_login ────────────────────────
            self.db._execute(
                "UPDATE account SET last_login = ? WHERE id = ?",
                (self._current_user.last_login, self._current_user.id)
            )
            self.db.commit()

            # ── Cập nhật logger username ───────────────────
            if self.log:
                self.log.user = self._current_user.username

            self._log_info(
                "Login",
                f"Dang nhap thanh cong: username='{username}', "
                f"role='{self._current_user.role_name}'"
            )

            return self._current_user

        except LoginError:
            raise
        except Exception as exc:
            self._log_error("Login", f"Loi dang nhap: {exc}")
            raise LoginError(f"Lỗi đăng nhập: {exc}") from exc

    def logout(self) -> None:
        """Đăng xuất hệ thống."""
        if self._current_user:
            self._log_info(
                "Logout",
                f"Dang xuat: username='{self._current_user.username}'"
            )

        self._current_user       = None
        self._current_permission = None
        self._is_logged_in       = False

        if self.log:
            self.log.user = "unknown"

    # ══════════════════════════════════════════════════════
    #  KIỂM TRA QUYỀN
    # ══════════════════════════════════════════════════════

    def check_permission(self, menu_name: str) -> bool:
        """
        Kiểm tra quyền truy cập menu.

        Parameters
        ----------
        menu_name : main, import, export, doi_sanh, config, user

        Returns
        -------
        True nếu có quyền
        """
        if not self._current_permission:
            return False
        return self._current_permission.has_menu(menu_name)

    def check_action(self, action: str) -> bool:
        """
        Kiểm tra quyền thao tác.

        Parameters
        ----------
        action : add, edit, delete, print

        Returns
        -------
        True nếu có quyền
        """
        if not self._current_permission:
            return False
        return self._current_permission.has_action(action)

    def require_permission(self, menu_name: str) -> None:
        """
        Yêu cầu quyền, raise nếu không có.

        Raises
        ------
        PermissionDeniedError
        """
        if not self.check_permission(menu_name):
            raise PermissionDeniedError(
                f"Bạn không có quyền truy cập: {menu_name}"
            )

    def require_action(self, action: str) -> None:
        """
        Yêu cầu quyền thao tác, raise nếu không có.

        Raises
        ------
        PermissionDeniedError
        """
        if not self.check_action(action):
            raise PermissionDeniedError(
                f"Bạn không có quyền: {action}"
            )

    def require_login(self) -> None:
        """
        Yêu cầu đã đăng nhập.

        Raises
        ------
        LoginError
        """
        if not self._is_logged_in:
            raise LoginError("Chưa đăng nhập. Vui lòng đăng nhập.")

    # ══════════════════════════════════════════════════════
    #  QUẢN LÝ TÀI KHOẢN
    # ══════════════════════════════════════════════════════

    def create_account(
        self,
        username  : str,
        password  : str,
        full_name : str = "",
        role_id   : int = 4,   # mặc định viewer
    ) -> int:
        """
        Tạo tài khoản mới.

        Returns
        -------
        account id

        Raises
        ------
        AccountError : trùng username hoặc dữ liệu không hợp lệ
        """
        try:
            if not username or not password:
                raise AccountError(
                    "Username và password không được trống."
                )

            username = username.strip().lower()

            if len(password) < 4:
                raise AccountError("Mật khẩu tối thiểu 4 ký tự.")

            # Kiểm tra trùng
            existing = self.db._fetchone(
                "SELECT id FROM account WHERE username = ?",
                (username,)
            )
            if existing:
                raise AccountError(
                    f"Username '{username}' đã tồn tại."
                )

            # Kiểm tra role_id hợp lệ
            role = self.db._fetchone(
                "SELECT id FROM role WHERE id = ?", (role_id,)
            )
            if not role:
                raise AccountError(
                    f"Role ID={role_id} không tồn tại."
                )

            # Insert
            pw_hash = self._hash_password(password)
            now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor = self.db._execute(
                """
                INSERT INTO account
                (username, password_hash, full_name, role_id, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (username, pw_hash, full_name, role_id, now)
            )
            self.db.commit()

            self._log_info(
                "CreateAccount",
                f"Tao tai khoan: username='{username}', role_id={role_id}"
            )

            return cursor.lastrowid

        except AccountError:
            raise
        except Exception as exc:
            self._log_error("CreateAccount", f"Loi: {exc}")
            raise AccountError(f"Lỗi tạo tài khoản: {exc}") from exc

    def update_account(
        self,
        account_id : int,
        full_name  : str = None,
        role_id    : int = None,
        is_active  : int = None,
    ) -> bool:
        """Cập nhật thông tin tài khoản."""
        try:
            updates = {}
            if full_name is not None:
                updates["full_name"] = full_name
            if role_id is not None:
                updates["role_id"] = role_id
            if is_active is not None:
                updates["is_active"] = is_active

            if not updates:
                return False

            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            params     = tuple(updates.values()) + (account_id,)

            self.db._execute(
                f"UPDATE account SET {set_clause} WHERE id = ?",
                params
            )
            self.db.commit()

            self._log_info(
                "UpdateAccount",
                f"Cap nhat account id={account_id}: {list(updates.keys())}"
            )
            return True

        except Exception as exc:
            self._log_error("UpdateAccount", f"Loi: {exc}")
            raise AccountError(f"Lỗi cập nhật: {exc}") from exc

    def change_password(
        self,
        account_id   : int,
        old_password : str,
        new_password : str,
    ) -> bool:
        """
        Đổi mật khẩu.

        Raises
        ------
        AccountError : mật khẩu cũ sai hoặc mới quá ngắn
        """
        try:
            if len(new_password) < 4:
                raise AccountError("Mật khẩu mới tối thiểu 4 ký tự.")

            # Kiểm tra mật khẩu cũ
            row = self.db._fetchone(
                "SELECT password_hash FROM account WHERE id = ?",
                (account_id,)
            )
            if not row:
                raise AccountError("Tài khoản không tồn tại.")

            if row["password_hash"] != self._hash_password(old_password):
                raise AccountError("Mật khẩu cũ không đúng.")

            # Cập nhật
            new_hash = self._hash_password(new_password)
            self.db._execute(
                "UPDATE account SET password_hash = ? WHERE id = ?",
                (new_hash, account_id)
            )
            self.db.commit()

            self._log_info(
                "ChangePassword",
                f"Doi mat khau account id={account_id}"
            )
            return True

        except AccountError:
            raise
        except Exception as exc:
            raise AccountError(f"Lỗi đổi mật khẩu: {exc}") from exc

    def reset_password(
        self,
        account_id   : int,
        new_password : str = "123456",
    ) -> bool:
        """
        Reset mật khẩu (bởi admin, không cần mật khẩu cũ).
        """
        try:
            new_hash = self._hash_password(new_password)
            self.db._execute(
                "UPDATE account SET password_hash = ? WHERE id = ?",
                (new_hash, account_id)
            )
            self.db.commit()

            self._log_info(
                "ResetPassword",
                f"Reset mat khau account id={account_id}"
            )
            return True

        except Exception as exc:
            raise AccountError(f"Lỗi reset mật khẩu: {exc}") from exc

    def delete_account(self, account_id: int) -> bool:
        """Xóa tài khoản (không cho xóa admin id=1)."""
        try:
            if account_id == 1:
                raise AccountError(
                    "Không thể xóa tài khoản admin mặc định."
                )

            row = self.db._fetchone(
                "SELECT username FROM account WHERE id = ?",
                (account_id,)
            )
            if not row:
                raise AccountError("Tài khoản không tồn tại.")

            self.db._execute(
                "DELETE FROM account WHERE id = ?", (account_id,)
            )
            self.db.commit()

            self._log_info(
                "DeleteAccount",
                f"Xoa account id={account_id}, username='{row['username']}'"
            )
            return True

        except AccountError:
            raise
        except Exception as exc:
            raise AccountError(f"Lỗi xóa tài khoản: {exc}") from exc

    def toggle_account(self, account_id: int) -> bool:
        """Khóa / mở khóa tài khoản."""
        try:
            if account_id == 1:
                raise AccountError(
                    "Không thể khóa tài khoản admin mặc định."
                )

            row = self.db._fetchone(
                "SELECT is_active FROM account WHERE id = ?",
                (account_id,)
            )
            if not row:
                raise AccountError("Tài khoản không tồn tại.")

            new_status = 0 if row["is_active"] == 1 else 1
            self.db._execute(
                "UPDATE account SET is_active = ? WHERE id = ?",
                (new_status, account_id)
            )
            self.db.commit()

            action = "Mo khoa" if new_status == 1 else "Khoa"
            self._log_info(
                "ToggleAccount",
                f"{action} account id={account_id}"
            )
            return True

        except AccountError:
            raise
        except Exception as exc:
            raise AccountError(f"Lỗi: {exc}") from exc

    # ══════════════════════════════════════════════════════
    #  TRUY VẤN TÀI KHOẢN
    # ══════════════════════════════════════════════════════

    def get_all_accounts(self) -> list[dict]:
        """Lấy danh sách tất cả tài khoản."""
        return self.db._fetchall(
            """
            SELECT a.id, a.username, a.full_name, a.role_id,
                   r.role_name, a.is_active, a.created_at, a.last_login
            FROM account a
            LEFT JOIN role r ON a.role_id = r.id
            ORDER BY a.id
            """
        )

    def get_account_by_id(self, account_id: int) -> Optional[dict]:
        """Lấy thông tin 1 tài khoản."""
        return self.db._fetchone(
            """
            SELECT a.*, r.role_name
            FROM account a
            LEFT JOIN role r ON a.role_id = r.id
            WHERE a.id = ?
            """,
            (account_id,)
        )

    def get_all_roles(self) -> list[RoleInfo]:
        """Lấy danh sách tất cả roles."""
        rows = self.db._fetchall(
            "SELECT * FROM role ORDER BY id"
        )
        return [
            RoleInfo(
                id=r["id"],
                role_name=r["role_name"],
                description=r.get("description", ""),
            )
            for r in rows
        ]

    def get_permission_for_role(self, role_id: int) -> Optional[PermissionInfo]:
        """Lấy permission theo role_id."""
        return self._load_permission(role_id)

    # ══════════════════════════════════════════════════════
    #  QUẢN LÝ ROLE & PERMISSION
    # ══════════════════════════════════════════════════════

    def create_role(
        self,
        role_name   : str,
        description : str = "",
    ) -> int:
        """Tạo role mới."""
        try:
            existing = self.db._fetchone(
                "SELECT id FROM role WHERE role_name = ?",
                (role_name,)
            )
            if existing:
                raise AccountError(
                    f"Role '{role_name}' đã tồn tại."
                )

            cursor = self.db._execute(
                "INSERT INTO role (role_name, description) VALUES (?, ?)",
                (role_name, description)
            )
            role_id = cursor.lastrowid

            # Tạo permission mặc định (tất cả = 0)
            self.db._execute(
                "INSERT INTO permission (role_id) VALUES (?)",
                (role_id,)
            )
            self.db.commit()

            self._log_info(
                "CreateRole",
                f"Tao role: '{role_name}' (id={role_id})"
            )
            return role_id

        except AccountError:
            raise
        except Exception as exc:
            raise AccountError(f"Lỗi tạo role: {exc}") from exc

    def update_permission(
        self,
        role_id  : int,
        perms    : dict,
    ) -> bool:
        """
        Cập nhật permission cho 1 role.

        Parameters
        ----------
        role_id : id của role
        perms   : dict chứa các field permission
                  VD: {"menu_main": 1, "can_add": 1, ...}
        """
        try:
            if not perms:
                return False

            valid_fields = {
                "menu_main", "menu_import", "menu_export",
                "menu_doi_sanh", "menu_config", "menu_user",
                "can_add", "can_edit", "can_delete", "can_print",
            }

            filtered = {
                k: v for k, v in perms.items()
                if k in valid_fields
            }

            if not filtered:
                return False

            # Kiểm tra đã có permission chưa
            existing = self.db._fetchone(
                "SELECT id FROM permission WHERE role_id = ?",
                (role_id,)
            )

            if existing:
                set_clause = ", ".join(
                    [f"{k} = ?" for k in filtered.keys()]
                )
                params = tuple(filtered.values()) + (role_id,)
                self.db._execute(
                    f"UPDATE permission SET {set_clause} WHERE role_id = ?",
                    params
                )
            else:
                filtered["role_id"] = role_id
                cols = ", ".join(filtered.keys())
                vals = ", ".join(["?" for _ in filtered])
                self.db._execute(
                    f"INSERT INTO permission ({cols}) VALUES ({vals})",
                    tuple(filtered.values())
                )

            self.db.commit()

            self._log_info(
                "UpdatePermission",
                f"Cap nhat permission role_id={role_id}: "
                f"{list(filtered.keys())}"
            )

            # Refresh permission nếu đang đăng nhập role này
            if (self._current_user
                    and self._current_user.role_id == role_id):
                self._current_permission = self._load_permission(
                    role_id
                )

            return True

        except Exception as exc:
            self._log_error("UpdatePermission", f"Loi: {exc}")
            raise AccountError(
                f"Lỗi cập nhật permission: {exc}"
            ) from exc

    # ══════════════════════════════════════════════════════
    #  PRIVATE HELPERS
    # ══════════════════════════════════════════════════════

    def _load_permission(
        self, role_id: int
    ) -> Optional[PermissionInfo]:
        """Load permission từ DB theo role_id."""
        row = self.db._fetchone(
            "SELECT * FROM permission WHERE role_id = ?",
            (role_id,)
        )

        if not row:
            return PermissionInfo(role_id=role_id)

        return PermissionInfo(
            role_id       = row.get("role_id", role_id),
            menu_main     = row.get("menu_main", 0),
            menu_import   = row.get("menu_import", 0),
            menu_export   = row.get("menu_export", 0),
            menu_doi_sanh = row.get("menu_doi_sanh", 0),
            menu_config   = row.get("menu_config", 0),
            menu_user     = row.get("menu_user", 0),
            can_add       = row.get("can_add", 0),
            can_edit      = row.get("can_edit", 0),
            can_delete    = row.get("can_delete", 0),
            can_print     = row.get("can_print", 0),
        )

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password bằng SHA-256."""
        return hashlib.sha256(
            password.encode("utf-8")
        ).hexdigest()

    def _log_info(self, action: str, detail: str) -> None:
        if self.log:
            self.log.info(
                module="Auth", action=action, detail=detail
            )

    def _log_warning(self, action: str, detail: str) -> None:
        if self.log:
            self.log.warning(
                module="Auth", action=action, detail=detail
            )

    def _log_error(self, action: str, detail: str) -> None:
        if self.log:
            self.log.error(
                module="Auth", action=action, detail=detail
            )