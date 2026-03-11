# =============================================================================
# Package: internal.model
# =============================================================================
# Layer: Entity Layer (lõi trong cùng của Clean Architecture)
#
# Chứa các data model và custom exception.
# Đây là layer KHÔNG phụ thuộc vào bất kỳ layer nào khác.
#
# Export các thành phần chính để import ngắn gọn:
#   from internal.model import Asset, AssetType, AssetStatus
# =============================================================================

from internal.model.asset import (
    Asset,
    AssetType,
    AssetStatus,
    CreateAssetRequest,
    UpdateAssetRequest,
)
from internal.model.errors import (
    AssetNotFoundError,
    InvalidInputError,
    DuplicateAssetError,
    EmptyNameError,
    InvalidTypeError,
    InvalidStatusError,
)
