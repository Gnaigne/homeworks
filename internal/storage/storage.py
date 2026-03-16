"""
=============================================================================
File: internal/storage/storage.py
Layer: Infrastructure Layer — Interface (Clean Architecture)
Tác dụng: Định nghĩa interface (contract) cho tầng data access.
=============================================================================

ĐỌC FILE NÀY SAU model/ — đây là "hợp đồng" mà mọi storage implementation
phải tuân thủ (memory, PostgreSQL, MongoDB, v.v.).

Dùng Abstract Base Class (ABC) của Python — tương đương interface trong Go:
    type Storage interface {
        Create(asset *model.Asset) error
        GetAll() ([]*model.Asset, error)
        ...
    }

Lợi ích:
    - Cho phép nhiều implementation khác nhau (memory, database, mock)
    - Dễ test — inject mock storage vào service
    - Tuân thủ Dependency Inversion Principle (DIP):
      Service layer phụ thuộc vào interface, KHÔNG phụ thuộc implementation cụ thể
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from internal.model.asset import Asset


# =============================================================================
# [SESSION 4] QueryParams — Gộp tất cả query parameters vào 1 struct
# =============================================================================

@dataclass
class QueryParams:
    """
    Chứa tất cả query parameters cho việc list assets.

    Tương đương Go struct:
        type QueryParams struct {
            Page     int
            PageSize int
            Type     string
            Status   string
            Search   string
            SortBy   string
            SortOrder string
        }

    Session 4 Enhancement — Thay vì truyền từng parameter riêng lẻ:
        Trước: filter(type, status), search(query), list_paginated(page, limit, type, status)
        Sau:   list_assets(QueryParams) — 1 method xử lý tất cả!

    Lợi ích:
        - Gộp filter + search + pagination + sorting vào 1 chỗ
        - Thêm filter mới = thêm field, KHÔNG đổi method signature
        - Dễ truyền qua các layer (handler → service → storage)
    """

    # Pagination — phân trang
    page: int = 1                    # Trang hiện tại (bắt đầu từ 1)
    page_size: int = 20              # Số item mỗi trang (mặc định 20, tối đa 100)

    # Filtering — lọc
    asset_type: Optional[str] = None  # Lọc theo type (domain/ip/service), None = không lọc
    status: Optional[str] = None      # Lọc theo status (active/inactive), None = không lọc
    search: Optional[str] = None      # Tìm kiếm theo name (partial match), None = không tìm

    # Sorting — sắp xếp (Session 4 NEW)
    sort_by: str = "created_at"       # Cột để sắp xếp (mặc định created_at)
    sort_order: str = "desc"          # Thứ tự: "asc" hoặc "desc" (mặc định desc)


class Storage(ABC):
    """
    Interface cho tầng data access.

    Tất cả phương thức đều là abstract — class con BẮT BUỘC phải implement.
    Nếu thiếu method nào, Python sẽ raise TypeError khi tạo instance.

    Hiện có:
        - MemoryStorage (session 2): lưu trong dict, mất khi tắt server
        - PostgresStorage (session 3): lưu vào database, bền vững
    """

    @abstractmethod
    def create(self, asset: Asset) -> None:
        """
        Thêm asset mới vào storage.

        Args:
            asset: Asset đã được tạo đầy đủ (có id, timestamps, v.v.)

        Raises:
            DuplicateAssetError: Nếu asset với id đó đã tồn tại
        """
        pass

    @abstractmethod
    def get_all(self) -> List[Asset]:
        """
        Lấy tất cả asset, sắp xếp theo thời gian tạo (mới nhất trước).

        Returns:
            Danh sách tất cả Asset. Trả về list rỗng nếu không có asset nào.
        """
        pass

    @abstractmethod
    def get_by_id(self, id: str) -> Asset:
        """
        Lấy một asset theo ID.

        Args:
            id: UUID của asset cần tìm

        Returns:
            Asset tìm được

        Raises:
            AssetNotFoundError: Nếu không tìm thấy asset
        """
        pass

    @abstractmethod
    def update(self, id: str, asset: Asset) -> None:
        """
        Cập nhật asset đã tồn tại.

        Args:
            id: UUID của asset cần cập nhật
            asset: Asset với dữ liệu đã được cập nhật

        Raises:
            AssetNotFoundError: Nếu không tìm thấy asset
        """
        pass

    @abstractmethod
    def delete(self, id: str) -> None:
        """
        Xóa asset khỏi storage.

        Args:
            id: UUID của asset cần xóa

        Raises:
            AssetNotFoundError: Nếu không tìm thấy asset
        """
        pass

    @abstractmethod
    def filter(self, asset_type: Optional[str] = None, status: Optional[str] = None) -> List[Asset]:
        """
        Lọc asset theo type và/hoặc status.

        Args:
            asset_type: Lọc theo loại asset (None = không lọc)
            status: Lọc theo trạng thái (None = không lọc)

        Returns:
            Danh sách Asset phù hợp điều kiện lọc
        """
        pass

    @abstractmethod
    def search(self, query: str) -> List[Asset]:
        """
        Tìm kiếm asset theo tên (không phân biệt hoa/thường).

        Args:
            query: Chuỗi tìm kiếm — tìm asset có name chứa chuỗi này

        Returns:
            Danh sách Asset có name khớp với query
        """
        pass

    # =========================================================================
    # [BÀI 1] STATISTICS — Thống kê asset
    # =========================================================================

    @abstractmethod
    def get_stats(self) -> dict:
        """
        Lấy thống kê tổng quan về assets trong storage.

        Returns:
            dict có cấu trúc:
            {
                "total": int,          # Tổng số asset
                "by_type": {           # Đếm theo từng loại
                    "domain": int,
                    "ip": int,
                    "service": int,
                },
                "by_status": {         # Đếm theo từng trạng thái
                    "active": int,
                    "inactive": int,
                },
            }
        """
        pass

    @abstractmethod
    def count(self, asset_type: Optional[str] = None, status: Optional[str] = None) -> int:
        """
        Đếm số lượng asset, có thể lọc theo type và/hoặc status.

        Args:
            asset_type: Lọc theo loại asset (None = không lọc)
            status: Lọc theo trạng thái (None = không lọc)

        Returns:
            int — số lượng asset thỏa điều kiện
        """
        pass
    
    # =========================================================================
    # [BÀI 2] BATCH CREATE — Tạo nhiều asset cùng lúc
    # =========================================================================

    # =========================================================================
    # [BÀI 3] BATCH DELETE — Xóa nhiều asset cùng lúc
    # =========================================================================

    @abstractmethod
    def batch_delete(self, ids: List[str]) -> dict:
        """
        Xóa nhiều asset cùng lúc theo danh sách ID.

        Khác với delete() đơn lẻ:
            - delete(id) → nếu không tìm thấy → raise AssetNotFoundError
            - batch_delete(ids) → bỏ qua ID không tồn tại, KHÔNG raise lỗi

        Args:
            ids: Danh sách UUID cần xóa

        Returns:
            dict có 2 key:
                - "deleted": int — số asset đã xóa thành công
                - "not_found": int — số ID không tìm thấy (bị bỏ qua)
        """
        pass

    # =========================================================================
    # [BÀI 2] BATCH CREATE — Tạo nhiều asset cùng lúc
    # =========================================================================

    @abstractmethod
    def batch_create(self, assets: List[Asset]) -> None:
        """
        Thêm nhiều asset cùng lúc trong 1 transaction.

        Transaction = "all or nothing":
            - Nếu tất cả INSERT thành công → commit (lưu hết)
            - Nếu 1 cái fail (vd: trùng ID) → rollback (hủy hết, DB không đổi)

        Args:
            assets: Danh sách Asset đã được tạo đầy đủ (có id, timestamps, v.v.)
                    Service layer đã validate + tạo UUID trước khi gọi hàm này.

        Raises:
            DuplicateAssetError: Nếu có asset nào trong danh sách bị trùng ID
        """
        pass

    # =========================================================================
    # [BÀI 6] PAGINATION & FILTERING — Phân trang + lọc
    # =========================================================================

    @abstractmethod
    def list_paginated(
        self,
        page: int = 1,
        limit: int = 20,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """
        Lấy danh sách asset có phân trang và lọc tùy chọn.

        Args:
            page: Trang hiện tại (bắt đầu từ 1)
            limit: Số item mỗi trang (mặc định 20, tối đa 100)
            asset_type: Lọc theo loại asset (None = bỏ qua)
            status: Lọc theo trạng thái (None = bỏ qua)

        Returns:
            dict có cấu trúc:
            {
                "data": List[Asset],   # Danh sách asset trang hiện tại
                "total": int,          # Tổng số asset thỏa điều kiện
            }
        """
        pass

    # =========================================================================
    # [SESSION 4] UNIFIED LIST — Gộp filter + search + sort + pagination
    # =========================================================================

    @abstractmethod
    def list_assets(self, params: "QueryParams") -> dict:
        """
        [Session 4] Lấy danh sách asset với đầy đủ tính năng.

        Tương đương Go:
            GetAll(params QueryParams) (*PaginatedResult, error)

        Thay thế cho get_all(), filter(), search(), list_paginated().
        Gộp tất cả vào 1 method duy nhất — unified query approach.

        Args:
            params: QueryParams chứa filter, search, sort, pagination

        Returns:
            dict có cấu trúc:
            {
                "data": List[Asset],
                "total": int,
                "page": int,
                "page_size": int,
                "total_pages": int,
            }
        """
        pass
