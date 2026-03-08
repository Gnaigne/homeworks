"""
=============================================================================
File: internal/storage/memory/memory.py
Layer: Infrastructure Layer — Implementation (Clean Architecture)
Tác dụng: Implement Storage interface bằng in-memory dict (dictionary).
=============================================================================

ĐỌC FILE NÀY SAU storage.py (interface) — đây là implementation cụ thể.

Dữ liệu được lưu trong Python dict — tương đương map[string]*Asset trong Go.
Dữ liệu sẽ MẤT khi tắt server (restart = mất hết dữ liệu).
Phù hợp cho development và testing. Session 3 sẽ thay bằng PostgreSQL.

Thread Safety:
    Go dùng sync.RWMutex để bảo vệ concurrent access.
    Python (CPython) có GIL (Global Interpreter Lock) nên dict operations
    là thread-safe ở mức cơ bản. Tuy nhiên, ta dùng threading.Lock()
    để đảm bảo an toàn cho các thao tác phức hợp (read-then-write).
"""

import threading
from typing import List, Optional

from internal.model.asset import Asset
from internal.model.errors import AssetNotFoundError, DuplicateAssetError
from internal.storage.storage import Storage


class MemoryStorage(Storage):
    """
    In-memory implementation của Storage interface.

    Lưu trữ Asset trong dict với key là asset ID.
    Tương đương MemoryStorage struct trong Go:
        type MemoryStorage struct {
            data map[string]*model.Asset
            mu   sync.RWMutex
        }

    Attributes:
        _data: Dictionary lưu trữ (key=id, value=Asset)
        _lock: Lock bảo vệ concurrent access
    """

    def __init__(self):
        """Khởi tạo storage rỗng với lock bảo vệ."""
        # dict tương đương map[string]*model.Asset trong Go
        self._data: dict[str, Asset] = {}
        # threading.Lock tương đương sync.RWMutex trong Go
        # Dùng để bảo vệ khi nhiều request truy cập cùng lúc
        self._lock = threading.Lock()

    def create(self, asset: Asset) -> None:
        """
        Thêm asset mới vào dict.

        Kiểm tra trùng ID trước khi thêm — nếu trùng sẽ raise DuplicateAssetError.

        Args:
            asset: Asset đã có đầy đủ thông tin (id, name, type, status, timestamps)

        Raises:
            DuplicateAssetError: Nếu ID đã tồn tại trong storage
        """
        with self._lock:  # Tự động khóa và mở khóa sau khi block kết thúc
            if asset.id in self._data:
                raise DuplicateAssetError()
            # Lưu copy của asset bằng model_copy() để tránh reference sharing
            self._data[asset.id] = asset.model_copy()

    def get_all(self) -> List[Asset]:
        """
        Lấy tất cả asset, sắp xếp mới nhất trước (created_at giảm dần).

        Returns:
            List[Asset] đã sắp xếp. Trả về list rỗng nếu storage trống.
        """
        with self._lock:
            # Chuyển dict values thành list và sort theo created_at giảm dần
            # Tương đương Go: sort.Slice + assets[i].CreatedAt.After(...)
            assets = list(self._data.values())
            assets.sort(key=lambda a: a.created_at, reverse=True)
            return assets

    def get_by_id(self, id: str) -> Asset:
        """
        Tìm asset theo ID.

        Args:
            id: UUID cần tìm

        Returns:
            Asset tìm được

        Raises:
            AssetNotFoundError: Nếu không có asset nào khớp ID
        """
        with self._lock:
            asset = self._data.get(id)
            if asset is None:
                raise AssetNotFoundError()
            return asset

    def update(self, id: str, asset: Asset) -> None:
        """
        Ghi đè asset tại vị trí ID (toàn bộ object được thay thế).

        Args:
            id: UUID của asset cần cập nhật
            asset: Asset mới (đã chỉnh sửa bởi service layer)

        Raises:
            AssetNotFoundError: Nếu ID không tồn tại
        """
        with self._lock:
            if id not in self._data:
                raise AssetNotFoundError()
            self._data[id] = asset.model_copy()

    def delete(self, id: str) -> None:
        """
        Xóa asset khỏi storage.

        Tương đương Go: delete(m.data, id)

        Args:
            id: UUID của asset cần xóa

        Raises:
            AssetNotFoundError: Nếu ID không tồn tại
        """
        with self._lock:
            if id not in self._data:
                raise AssetNotFoundError()
            del self._data[id]

    def filter(self, asset_type: Optional[str] = None, status: Optional[str] = None) -> List[Asset]:
        """
        Lọc asset theo type và/hoặc status.

        Cả hai tham số đều tùy chọn — nếu None thì bỏ qua điều kiện đó.
        Ví dụ: filter("domain", None) → lấy tất cả asset loại domain.

        Args:
            asset_type: Lọc theo loại (None = không lọc theo type)
            status: Lọc theo trạng thái (None = không lọc theo status)

        Returns:
            List[Asset] phù hợp, sắp xếp mới nhất trước
        """
        with self._lock:
            results = []
            for asset in self._data.values():
                # Bỏ qua nếu không khớp type (khi có filter type)
                if asset_type and asset.type != asset_type:
                    continue
                # Bỏ qua nếu không khớp status (khi có filter status)
                if status and asset.status != status:
                    continue
                results.append(asset)

            # Sắp xếp mới nhất trước
            results.sort(key=lambda a: a.created_at, reverse=True)
            return results

    def search(self, query: str) -> List[Asset]:
        """
        Tìm kiếm asset theo tên — tìm name chứa chuỗi query (case-insensitive).

        Ví dụ: search("example") sẽ tìm thấy "example.com", "test.example.org"

        Args:
            query: Chuỗi tìm kiếm

        Returns:
            List[Asset] có name chứa query, sắp xếp mới nhất trước
        """
        with self._lock:
            query_lower = query.lower()
            results = [
                asset
                for asset in self._data.values()
                # So sánh không phân biệt hoa/thường
                # Tương đương Go: strings.Contains(strings.ToLower(name), query)
                if query_lower in asset.name.lower()
            ]
            results.sort(key=lambda a: a.created_at, reverse=True)
            return results

    # =========================================================================
    # [BÀI 1] STATISTICS — Thống kê asset
    # =========================================================================

    def get_stats(self) -> dict:
        """
        Thống kê tổng quan assets trong memory.

        Duyệt qua toàn bộ dict _data, đếm theo type và status.

        Returns:
            dict chứa total, by_type, by_status
        """
        with self._lock:
            # Khởi tạo bộ đếm với giá trị 0 cho mỗi loại/trạng thái
            by_type = {"domain": 0, "ip": 0, "service": 0}
            by_status = {"active": 0, "inactive": 0}

            # Duyệt qua tất cả asset, tăng bộ đếm tương ứng
            for asset in self._data.values():
                # asset.type.value lấy giá trị string từ Enum
                # Ví dụ: AssetType.DOMAIN.value → "domain"
                by_type[asset.type.value] = by_type.get(asset.type.value, 0) + 1
                by_status[asset.status.value] = by_status.get(asset.status.value, 0) + 1

            return {
                "total": len(self._data),  # len() đếm số phần tử trong dict
                "by_type": by_type,
                "by_status": by_status,
            }

    def count(self, asset_type: Optional[str] = None, status: Optional[str] = None) -> int:
        """
        Đếm số asset thỏa điều kiện lọc.

        Nếu không truyền filter nào → đếm tất cả.
        Nếu truyền type và/hoặc status → chỉ đếm asset khớp.

        Args:
            asset_type: Lọc theo loại (None = bỏ qua)
            status: Lọc theo trạng thái (None = bỏ qua)

        Returns:
            int — số lượng asset thỏa điều kiện
        """
        with self._lock:
            count = 0
            for asset in self._data.values():
                # Bỏ qua nếu không khớp type
                if asset_type and asset.type.value != asset_type:
                    continue
                # Bỏ qua nếu không khớp status
                if status and asset.status.value != status:
                    continue
                count += 1
            return count
    
    # =========================================================================
    # [BÀI 2] BATCH CREATE — Tạo nhiều asset cùng lúc
    # =========================================================================

    def batch_create(self, assets: List[Asset]) -> None:
        """
        Thêm nhiều asset cùng lúc — mô phỏng transaction trong memory.

        Cách mô phỏng "all or nothing" trong memory:
            1. Kiểm tra TẤT CẢ ID trước (chưa thêm gì vào dict)
            2. Nếu có ID trùng → raise lỗi ngay, dict không bị thay đổi
            3. Nếu tất cả ID mới → thêm hết vào dict

        Khác với PostgresStorage:
            - PostgresStorage dùng transaction thật (BEGIN → COMMIT/ROLLBACK)
            - MemoryStorage chỉ kiểm tra trước rồi thêm sau (đơn giản hơn)

        Args:
            assets: Danh sách Asset đã tạo đầy đủ bởi service layer

        Raises:
            DuplicateAssetError: Nếu bất kỳ ID nào đã tồn tại
        """
        # ⚠️ Lưu ý: self._lock (có dấu _ ở đầu), không phải self.lock
        with self._lock:
            # Bước 1: Kiểm tra TẤT CẢ ID trước — nếu trùng thì dừng ngay
            # Chưa thêm gì vào dict → nếu lỗi thì dict không bị ảnh hưởng
            for asset in assets:
                if asset.id in self._data:
                    raise DuplicateAssetError(
                        f"Asset with ID {asset.id} already exists"
                    )

            # Bước 2: Tất cả OK → thêm hết vào dict
            for asset in assets:
                self._data[asset.id] = asset.model_copy()

    # =========================================================================
    # [BÀI 3] BATCH DELETE — Xóa nhiều asset cùng lúc
    # =========================================================================

    def batch_delete(self, ids: List[str]) -> dict:
        """
        Xóa nhiều asset theo danh sách ID — bỏ qua ID không tồn tại.

        Khác với delete() đơn lẻ (raise lỗi nếu không tìm thấy),
        batch_delete chỉ đếm và báo cáo kết quả.

        Args:
            ids: Danh sách UUID cần xóa

        Returns:
            dict {"deleted": int, "not_found": int}
        """
        with self._lock:
            deleted = 0
            not_found = 0

            for asset_id in ids:
                # pop(key, default) — xóa key khỏi dict và trả về value
                # Nếu key không tồn tại → trả về default (None) thay vì raise KeyError
                removed = self._data.pop(asset_id, None)

                if removed is not None:
                    deleted += 1      # Xóa thành công
                else:
                    not_found += 1    # ID không tồn tại, bỏ qua

            return {"deleted": deleted, "not_found": not_found}

    # =========================================================================
    # [BÀI 6] PAGINATION & FILTERING — Phân trang + lọc (in-memory)
    # =========================================================================

    def list_paginated(
        self,
        page: int = 1,
        limit: int = 20,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """
        Lấy danh sách asset có phân trang và lọc (in-memory version).

        So với PostgresStorage dùng SQL LIMIT/OFFSET,
        ở đây ta dùng Python list slicing để phân trang:
            data[offset : offset + limit]

        Args:
            page: Trang hiện tại (bắt đầu từ 1)
            limit: Số item mỗi trang
            asset_type: Lọc theo type — None = bỏ qua
            status: Lọc theo status — None = bỏ qua

        Returns:
            dict {"data": List[Asset], "total": int}
        """
        with self._lock:
            # Lấy tất cả asset, sắp xếp mới nhất trước
            assets = list(self._data.values())
            assets.sort(key=lambda a: a.created_at, reverse=True)

            # Lọc theo type và status nếu có
            if asset_type:
                assets = [a for a in assets if a.type.value == asset_type]
            if status:
                assets = [a for a in assets if a.status.value == status]

            total = len(assets)

            # Cắt trang bằng Python slice
            # Ví dụ: page=2, limit=10 → offset=10 → assets[10:20]
            offset = (page - 1) * limit
            page_data = assets[offset : offset + limit]

            return {"data": page_data, "total": total}
