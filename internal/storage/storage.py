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
from typing import List, Optional

from internal.model.asset import Asset


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
