"""
=============================================================================
File: internal/service/asset_service.py
Layer: Use Case Layer — Business Logic (Clean Architecture)
Tác dụng: Xử lý toàn bộ business logic cho Asset (validate, tạo ID, timestamps).
=============================================================================

ĐỌC FILE NÀY SAU model/ và storage/ — service là lớp "điều phối" ở giữa.

Service layer nằm giữa handler (HTTP) và storage (data access):
    Handler → Service → Storage

Trách nhiệm:
    ✅ Validate dữ liệu theo business rules
    ✅ Tạo giá trị mặc định (UUID, timestamp, default status)
    ✅ Điều phối flow: validate → tạo entity → lưu vào storage
    ❌ KHÔNG biết gì về HTTP (status code, JSON, headers)
    ❌ KHÔNG biết gì về database cụ thể (SQL, table name)

Dependency Injection:
    Service nhận Storage interface qua constructor → dễ test
    (inject mock storage cho unit test, inject real DB cho production)
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from internal.model.asset import Asset, AssetType, AssetStatus
from internal.model.errors import (
    EmptyNameError,
    InvalidTypeError,
    InvalidStatusError,
    InvalidInputError,
)
from internal.storage.storage import Storage, QueryParams
from internal.validator.asset_validator import AssetValidator


class AssetService:
    """
    Business logic cho quản lý Asset.

    Tương đương Go struct:
        type AssetService struct {
            storage storage.Storage
        }

    Service KHÔNG giữ state nào ngoài reference đến storage.
    Mọi business rule được enforce ở đây (không phải handler hay storage).

    Attributes:
        _storage: Storage interface — inject qua constructor
    """

    def __init__(self, storage: Storage):
        """
        Khởi tạo service với storage dependency.

        Tương đương: func NewAssetService(storage storage.Storage) *AssetService

        Args:
            storage: Implementation của Storage interface (memory, postgres, v.v.)
        """
        self._storage = storage
        # Inject validator (Session 4)
        self.validator = AssetValidator()

    def create_asset(self, name: str, asset_type: str) -> Asset:
        """
        Tạo asset mới với validation và giá trị mặc định.

        Flow:
            1. Validate name (không được trống)
            2. Validate type (phải là domain/ip/service)
            3. Tạo Asset entity với UUID, default status, timestamps
            4. Lưu vào storage
            5. Trả về asset đã tạo

        Args:
            name: Tên asset (bắt buộc, không được trống)
            asset_type: Loại asset ("domain", "ip", "service")

        Returns:
            Asset đã được tạo và lưu thành công

        Raises:
            EmptyNameError: Nếu name trống
            InvalidTypeError: Nếu type không hợp lệ
            InvalidInputError: Nếu format không hợp lệ (domain/ip/service)
        """
        # --- Validation (Session 4) ---
        # Gọi validator (sẽ raise InvalidInputError nếu sai format)
        self.validator.validate_create(name, asset_type)

        # Lấy Enum hợp lệ (validator đã check type nên ở đây an toàn)
        valid_type = AssetType(asset_type)

        # --- Tạo entity ---
        now = datetime.now(timezone.utc)
        asset = Asset(
            id=str(uuid.uuid4()),       # Tự động tạo UUID, tương đương uuid.New().String()
            name=name,
            type=valid_type,
            status=AssetStatus.ACTIVE,  # Default status = active
            created_at=now,
            updated_at=now,
        )

        # --- Lưu vào storage ---
        self._storage.create(asset)

        return asset

    def get_all_assets(self) -> List[Asset]:
        """
        Lấy tất cả asset từ storage.

        Returns:
            Danh sách tất cả Asset, sắp xếp mới nhất trước.
            Trả về list rỗng nếu không có asset nào.
        """
        return self._storage.get_all()

    def get_asset_by_id(self, id: str) -> Asset:
        """
        Lấy một asset theo ID.

        Args:
            id: UUID của asset

        Returns:
            Asset tìm được

        Raises:
            InvalidInputError: Nếu id trống
            AssetNotFoundError: Nếu không tìm thấy (raise bởi storage)
        """
        if not id:
            raise InvalidInputError("asset ID is required")

        return self._storage.get_by_id(id)

    def update_asset(
        self,
        id: str,
        name: Optional[str] = None,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Asset:
        """
        Cập nhật asset — chỉ thay đổi field được cung cấp (partial update).

        Flow:
            1. Validate id
            2. Lấy asset hiện tại từ storage
            3. Áp dụng thay đổi (chỉ field != None)
            4. Cập nhật updated_at timestamp
            5. Lưu lại và trả về asset đã cập nhật

        Args:
            id: UUID của asset cần cập nhật
            name: Tên mới (None = giữ nguyên)
            asset_type: Loại mới (None = giữ nguyên)
            status: Trạng thái mới (None = giữ nguyên)

        Returns:
            Asset đã cập nhật

        Raises:
            InvalidInputError: Nếu id trống
            InvalidTypeError: Nếu type không hợp lệ
            InvalidStatusError: Nếu status không hợp lệ
            AssetNotFoundError: Nếu không tìm thấy asset
        """
        if not id:
            raise InvalidInputError("asset ID is required")

        # Lấy asset hiện tại — raise AssetNotFoundError nếu không có
        existing = self._storage.get_by_id(id)

        # --- Validation (Session 4) ---
        # Chỉ validate các field có giá trị truyền vào
        self.validator.validate_update(name or "", asset_type or "", status or "")

        # Áp dụng thay đổi (chỉ field được gửi — partial update)
        updated_name = name if name and name.strip() else existing.name
        updated_type = AssetType(asset_type) if asset_type else existing.type
        updated_status = AssetStatus(status) if status else existing.status

        # Nếu type thay đổi, phải validate lại name với type mới
        # Ví dụ: đổi từ 'domain' sang 'ip' → name 'example.com' không hợp lệ nữa
        if asset_type and asset_type != existing.type.value:
            self.validator.validate_create(updated_name, updated_type.value)

        # Tạo asset mới với dữ liệu đã cập nhật (Pydantic model là immutable by default)
        updated_asset = Asset(
            id=existing.id,
            name=updated_name,
            type=updated_type,
            status=updated_status,
            created_at=existing.created_at,
            updated_at=datetime.now(timezone.utc),  # Cập nhật timestamp
        )

        self._storage.update(id, updated_asset)
        return updated_asset

    # =========================================================================
    # [SESSION 4] UNIFIED LIST — Gộp filter + search + sort + pagination
    # =========================================================================

    def list_assets(self, params: QueryParams) -> dict:
        """
        [Session 4] Lấy danh sách asset với đầy đủ filter, search, sort, pagination.

        Tương đương Go:
            func (s *AssetService) ListAssets(params storage.QueryParams) (*storage.PaginatedResult, error)

        Flow:
            1. Validate pagination params & sort params
            2. Validate filter & search params (nếu có)
            3. Gọi storage.list_assets()

        Args:
            params: QueryParams chứa thông tin query

        Returns:
            dict chứa data và metadata phân trang
        """
        # --- Validation ---
        self.validator.validate_pagination_params(params.page, params.page_size)
        self.validator.validate_sort_params(params.sort_by, params.sort_order)

        if params.asset_type:
            self.validator.validate_type(params.asset_type)
            
        if params.status:
            self.validator.validate_status(params.status)

        if params.search:
            self.validator.validate_search_query(params.search)

        # --- Gọi storage ---
        return self._storage.list_assets(params)

    def delete_asset(self, id: str) -> None:
        """
        Xóa asset khỏi storage.

        Args:
            id: UUID của asset cần xóa

        Raises:
            InvalidInputError: Nếu id trống
            AssetNotFoundError: Nếu không tìm thấy asset
        """
        if not id:
            raise InvalidInputError("asset ID is required")

        self._storage.delete(id)

    def filter_assets(
        self,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Asset]:
        """
        Lọc asset theo type và/hoặc status.

        Validate giá trị filter trước khi gửi xuống storage.

        Args:
            asset_type: Lọc theo loại asset (None = bỏ qua)
            status: Lọc theo trạng thái (None = bỏ qua)

        Returns:
            Danh sách Asset phù hợp

        Raises:
            InvalidTypeError: Nếu asset_type không hợp lệ
            InvalidStatusError: Nếu status không hợp lệ
        """
        # Validate filter values nếu được cung cấp
        if asset_type:
            try:
                AssetType(asset_type)
            except ValueError:
                raise InvalidTypeError()

        if status:
            try:
                AssetStatus(status)
            except ValueError:
                raise InvalidStatusError()

        return self._storage.filter(asset_type, status)

    def search_assets(self, query: str) -> List[Asset]:
        """
        Tìm kiếm asset theo tên (tìm name chứa chuỗi query).

        Args:
            query: Chuỗi tìm kiếm

        Returns:
            Danh sách Asset có name khớp

        Raises:
            InvalidInputError: Nếu query trống
        """
        if not query or not query.strip():
            raise InvalidInputError("search query is required")

        return self._storage.search(query)

    # =========================================================================
    # [BÀI 1] STATISTICS — Thống kê asset
    # =========================================================================

    def get_stats(self) -> dict:
        """
        Lấy thống kê tổng quan về assets.

        Gọi thẳng xuống storage vì không có business logic đặc biệt.

        Returns:
            dict chứa total, by_type, by_status
        """
        return self._storage.get_stats()

    def count_assets(
        self,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """
        Đếm số lượng asset, có thể lọc theo type và/hoặc status.

        Validate giá trị filter trước khi gọi xuống storage.

        Args:
            asset_type: Lọc theo loại asset (None = bỏ qua)
            status: Lọc theo trạng thái (None = bỏ qua)

        Returns:
            int — số lượng asset thỏa điều kiện

        Raises:
            InvalidTypeError: Nếu asset_type không hợp lệ
            InvalidStatusError: Nếu status không hợp lệ
        """
        # Validate filter values nếu được cung cấp
        if asset_type:
            try:
                AssetType(asset_type)
            except ValueError:
                raise InvalidTypeError()

        if status:
            try:
                AssetStatus(status)
            except ValueError:
                raise InvalidStatusError()

        return self._storage.count(asset_type, status)

    # =========================================================================
    # [BÀI 2] BATCH CREATE — Tạo nhiều asset cùng lúc
    # =========================================================================

    def batch_create_assets(
        self,
        assets_data: list[dict],
    ) -> List[Asset]:
        """
        Tạo nhiều asset cùng lúc với validation đầy đủ.

        Flow:
            1. Kiểm tra list không rỗng và không quá 100 items
            2. Validate TỪNG asset (name không trống, type hợp lệ)
               → Nếu 1 cái fail → raise lỗi ngay, KHÔNG tạo asset nào
            3. Tạo UUID + timestamps cho từng asset
            4. Gọi storage.batch_create() trong transaction
            5. Trả về list Asset đã tạo

        Tại sao validate hết TRƯỚC rồi mới insert?
            - Tránh trường hợp: insert 5 cái OK, cái thứ 6 fail → phải rollback
            - Validate trước = "fail fast" = phát hiện lỗi sớm nhất có thể
            - Tiết kiệm thời gian (không cần mở transaction rồi mới phát hiện lỗi)

        Args:
            assets_data: List các dict, mỗi dict có {"name": "...", "type": "..."}
                         (Đã được Pydantic parse từ BatchCreateAssetRequest)

        Returns:
            List[Asset] — danh sách asset đã tạo thành công

        Raises:
            InvalidInputError: Nếu list rỗng hoặc quá 100 items
            EmptyNameError: Nếu có asset nào name trống
            InvalidTypeError: Nếu có asset nào type không hợp lệ
        """
        # --- Bước 1: Kiểm tra số lượng ---
        if not assets_data:
            raise InvalidInputError("assets list is required and cannot be empty")

        if len(assets_data) > 100:
            raise InvalidInputError(
                f"too many assets: {len(assets_data)}, maximum is 100"
            )

        # --- Bước 2: Validate TỪNG asset + tạo entity ---
        # Dùng list để chứa tất cả Asset đã validate + tạo xong
        assets_to_create: List[Asset] = []
        now = datetime.now(timezone.utc)

        # enumerate(list) trả về (index, item) cho mỗi phần tử
        # Ví dụ: enumerate(["a", "b"]) → (0, "a"), (1, "b")
        # index dùng để báo lỗi cụ thể: "asset thứ 2 name trống"
        for index, data in enumerate(assets_data):
            name = data.get("name", "")
            asset_type = data.get("type", "")

            # --- Validation (Session 4) ---
            try:
                self.validator.validate_create(name, asset_type)
            except InvalidInputError as e:
                # Bọc lỗi bằng index để client biết cái nào sai
                raise InvalidInputError(f"asset at index {index}: {str(e)}")

            valid_type = AssetType(asset_type)

            # --- Tạo entity ---
            asset = Asset(
                id=str(uuid.uuid4()),
                name=name,
                type=valid_type,
                status=AssetStatus.ACTIVE,  # Default status
                created_at=now,
                updated_at=now,
            )
            assets_to_create.append(asset)

        # --- Bước 3: Gọi storage batch_create (trong transaction) ---
        # Chỉ tới được đây nếu TẤT CẢ asset đều valid
        self._storage.batch_create(assets_to_create)

        return assets_to_create

    # =========================================================================
    # [BÀI 3] BATCH DELETE — Xóa nhiều asset cùng lúc
    # =========================================================================

    def batch_delete_assets(self, ids: list[str]) -> dict:
        """
        Xóa nhiều asset cùng lúc theo danh sách ID.

        Flow:
            1. Kiểm tra list ids không rỗng
            2. Loại bỏ ID rỗng hoặc chỉ có khoảng trắng
            3. Gọi storage.batch_delete() — storage tự phân biệt ID nào tồn tại
            4. Trả về kết quả {"deleted": N, "not_found": M}

        Khác với batch_create:
            - batch_create: validate kỹ → nếu 1 fail thì rollback hết
            - batch_delete: "best effort" — xóa được bao nhiêu hay bấy nhiêu

        Args:
            ids: Danh sách UUID cần xóa (từ query param, đã split bởi handler)

        Returns:
            dict {"deleted": int, "not_found": int}

        Raises:
            InvalidInputError: Nếu list ids rỗng
        """
        # --- Bước 1: Kiểm tra list không rỗng ---
        if not ids:
            raise InvalidInputError("ids list is required and cannot be empty")

        # --- Bước 2: Lọc bỏ ID rỗng ---
        # Trường hợp query param có dấu phẩy thừa: ?ids=abc,,def
        # → split ra: ["abc", "", "def"] → lọc bỏ chuỗi rỗng
        # strip() xóa khoảng trắng 2 đầu, ví dụ: " abc " → "abc"
        clean_ids = [id.strip() for id in ids if id.strip()]

        if not clean_ids:
            raise InvalidInputError("no valid IDs provided")

        # --- Bước 3: Gọi storage xóa ---
        return self._storage.batch_delete(clean_ids)

    # =========================================================================
    # [BÀI 6] PAGINATION & FILTERING — Phân trang + lọc
    # =========================================================================

    def list_assets_paginated(
        self,
        page: int = 1,
        limit: int = 20,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """
        Lấy danh sách asset có phân trang và lọc.

        Validate giá trị page/limit trước khi xuống storage:
            - page phải >= 1
            - limit phải trong [1, 100]
            - type và status nếu có phải là giá trị hợp lệ

        Args:
            page: Trang hiện tại (bắt đầu từ 1)
            limit: Số item mỗi trang (mặc định 20, tối đa 100)
            asset_type: Lọc theo loại asset (None = bỏ qua)
            status: Lọc theo trạng thái (None = bỏ qua)

        Returns:
            dict {
                "data": List[Asset],
                "pagination": {
                    "page": int,
                    "limit": int,
                    "total": int,
                    "total_pages": int,
                }
            }

        Raises:
            InvalidInputError: Nếu page/limit không hợp lệ
            InvalidTypeError: Nếu asset_type không hợp lệ
            InvalidStatusError: Nếu status không hợp lệ
        """
        # --- Validate page ---
        if page < 1:
            raise InvalidInputError("page phải >= 1")

        # --- Validate limit ---
        if limit < 1 or limit > 100:
            raise InvalidInputError("limit phải trong khoảng [1, 100]")

        # --- Validate filter values nếu được cung cấp ---
        if asset_type:
            try:
                AssetType(asset_type)
            except ValueError:
                raise InvalidTypeError()

        if status:
            try:
                AssetStatus(status)
            except ValueError:
                raise InvalidStatusError()

        # --- Gọi storage ---
        result = self._storage.list_paginated(
            page=page,
            limit=limit,
            asset_type=asset_type,
            status=status,
        )

        total = result["total"]

        # Tính tổng số trang: math.ceil(total / limit)
        # Dùng integer division: (total + limit - 1) // limit → không cần import math
        # Ví dụ: total=150, limit=20 → (150 + 19) // 20 = 169 // 20 = 8 trang
        total_pages = max(1, (total + limit - 1) // limit)

        return {
            "data": result["data"],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
            },
        }
