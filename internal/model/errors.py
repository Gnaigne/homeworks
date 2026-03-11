"""
=============================================================================
File: internal/model/errors.py
Layer: Entity Layer (Clean Architecture)
Tác dụng: Định nghĩa các custom exception cho domain logic.
=============================================================================

Mỗi exception tương ứng với một lỗi business cụ thể.
Handler layer sẽ bắt (catch) các exception này và chuyển thành HTTP status code
phù hợp (ví dụ: AssetNotFoundError → 404, InvalidInputError → 400).

Trong Go dùng sentinel errors:
    var ErrNotFound = errors.New("asset not found")

Python dùng custom Exception classes — mạnh hơn vì có thể:
    - Chứa thêm thông tin (attributes)
    - Bắt theo class hierarchy (try/except)
    - Tự động phân loại lỗi qua isinstance()
"""


# =============================================================================
# BASE EXCEPTION
# =============================================================================

class AssetError(Exception):
    """
    Base exception cho tất cả lỗi liên quan đến Asset.

    Kế thừa từ Exception chuẩn của Python.
    Tất cả custom exception khác kế thừa từ class này,
    giúp handler có thể bắt chung: except AssetError
    """
    pass


# =============================================================================
# CÁC EXCEPTION CỤ THỂ
# =============================================================================

class AssetNotFoundError(AssetError):
    """
    Asset không tồn tại trong storage.
    Tương đương: ErrNotFound trong Go → HTTP 404 Not Found.
    """
    def __init__(self, message: str = "asset not found"):
        super().__init__(message)


class InvalidInputError(AssetError):
    """
    Dữ liệu đầu vào không hợp lệ (lỗi validation chung).
    Tương đương: ErrInvalidInput trong Go → HTTP 400 Bad Request.
    """
    def __init__(self, message: str = "invalid input"):
        super().__init__(message)


class DuplicateAssetError(AssetError):
    """
    Asset đã tồn tại (trùng ID).
    Tương đương: ErrDuplicate trong Go → HTTP 409 Conflict.
    """
    def __init__(self, message: str = "asset already exists"):
        super().__init__(message)


class EmptyNameError(InvalidInputError):
    """
    Tên asset bị trống — name là field bắt buộc.
    Kế thừa InvalidInputError vì bản chất cũng là lỗi input.
    Tương đương: ErrEmptyName trong Go → HTTP 400 Bad Request.
    """
    def __init__(self, message: str = "name is required"):
        super().__init__(message)


class InvalidTypeError(InvalidInputError):
    """
    Loại asset không hợp lệ — phải là domain, ip, hoặc service.
    Tương đương: ErrInvalidType trong Go → HTTP 400 Bad Request.
    """
    def __init__(self, message: str = "invalid asset type: must be domain, ip, or service"):
        super().__init__(message)


class InvalidStatusError(InvalidInputError):
    """
    Trạng thái asset không hợp lệ — phải là active hoặc inactive.
    Tương đương: ErrInvalidStatus trong Go → HTTP 400 Bad Request.
    """
    def __init__(self, message: str = "invalid status: must be active or inactive"):
        super().__init__(message)
