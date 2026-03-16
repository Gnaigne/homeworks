"""
=============================================================================
File: tests/internal/service/test_asset_service.py
Bài 2.3 (Bonus): Service Tests — Kiểm thử AssetService với Mock Storage
=============================================================================
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from internal.model.asset import Asset, AssetType, AssetStatus
from internal.model.errors import (
    EmptyNameError, InvalidTypeError, InvalidInputError, AssetNotFoundError
)
from internal.service.asset_service import AssetService
from internal.storage.storage import QueryParams


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_storage():
    """
    Pytest Fixture: Tạo một Storage GIẢ (mock) dùng MagicMock.

    Vấn đề: Storage thật cần kết nối database (PostgreSQL).
    Nếu test gọi storage thật → cần DB đang chạy → test chậm, phụ thuộc môi trường.

    Giải pháp: MagicMock() tạo ra một object "ma" có thể giả làm BẤT KỲ class nào.
    Ta cấu hình sẵn return_value cho từng method, ví dụ:
        storage.get_by_id.return_value = make_asset()
    → Khi service gọi storage.get_by_id(...), thay vì chạy query DB thật,
      nó sẽ trả về make_asset() ngay lập tức — không chạm DB.

    Kỹ thuật này gọi là "mocking" — isolate unit cần test (service)
    khỏi các dependency bên ngoài (storage, DB).
    """
    storage = MagicMock()

    now = datetime.now(timezone.utc)
    storage.get_by_id.return_value = Asset(
        id="asset-001",
        name="example.com",
        type=AssetType.DOMAIN,
        status=AssetStatus.ACTIVE,
        created_at=now,
        updated_at=now
    )
    storage.get_all.return_value = []
    storage.list_assets.return_value = {"data": [], "total": 0, "page": 1, "page_size": 10, "total_pages": 1}
    storage.filter.return_value = []
    storage.search.return_value = []
    storage.get_stats.return_value = {"total": 0, "by_type": {}, "by_status": {}}
    storage.count.return_value = 0
    storage.batch_delete.return_value = {"deleted": 0, "not_found": 0}
    return storage

# Tạo AssetService mock để test 
@pytest.fixture
def asset_service(mock_storage):
    return AssetService(mock_storage)


# =============================================================================
# 1. TEST create_asset
# =============================================================================

class TestCreateAsset:
    def test_create_valid_domain_asset(self, asset_service, mock_storage):
        """create_asset với domain hợp lệ phải gọi storage.create() và trả về Asset."""
        asset = asset_service.create_asset("example.com", "domain")

        assert asset is not None
        assert asset.name == "example.com"
        assert asset.type == AssetType.DOMAIN
        assert asset.status == AssetStatus.ACTIVE
        mock_storage.create.assert_called_once()

    def test_create_valid_ip_asset(self, asset_service, mock_storage):
        """create_asset với IP hợp lệ phải thành công."""
        asset = asset_service.create_asset("192.168.1.1", "ip")

        assert asset.type == AssetType.IP
        assert asset.name == "192.168.1.1"
        mock_storage.create.assert_called_once()

    def test_create_generates_unique_uuid(self, asset_service):
        """Mỗi lần tạo phải có UUID khác nhau."""
        asset1 = asset_service.create_asset("a.com", "domain")
        asset2 = asset_service.create_asset("b.com", "domain")
        assert asset1.id != asset2.id

    def test_create_sets_default_active_status(self, asset_service):
        """Asset mới tạo phải có status = ACTIVE."""
        asset = asset_service.create_asset("test.com", "domain")
        assert asset.status == AssetStatus.ACTIVE

    def test_create_sets_created_at_timestamp(self, asset_service):
        """Asset phải có created_at và updated_at timestamp."""
        asset = asset_service.create_asset("time.com", "domain")
        assert asset.created_at is not None
        assert asset.updated_at is not None

    @pytest.mark.parametrize("invalid_type", ["website", "server", "DATABASE", "DOMAIN"])
    def test_create_invalid_type_raises(self, asset_service, invalid_type):
        """Type không hợp lệ phải raise InvalidInputError."""
        with pytest.raises((InvalidInputError, InvalidTypeError)):
            asset_service.create_asset("test.com", invalid_type)

    def test_create_empty_name_raises(self, asset_service):
        """Name trống phải raise EmptyNameError hoặc InvalidInputError."""
        with pytest.raises((EmptyNameError, InvalidInputError)):
            asset_service.create_asset("", "domain")

    def test_create_none_name_raises(self, asset_service):
        """Name None phải raise error."""
        with pytest.raises(Exception):
            asset_service.create_asset(None, "domain")

    def test_create_whitespace_name_raises(self, asset_service):
        """Name chỉ chứa dấu cách phải raise error."""
        with pytest.raises((EmptyNameError, InvalidInputError)):
            asset_service.create_asset("   ", "domain")


# =============================================================================
# 2. TEST get_asset_by_id
# =============================================================================

class TestGetAssetById:
    def test_get_existing_asset(self, asset_service, mock_storage):
        """get_asset_by_id trả về asset từ storage."""
        asset = asset_service.get_asset_by_id("asset-001")

        assert asset.id == "asset-001"
        mock_storage.get_by_id.assert_called_once_with("asset-001")

    def test_get_empty_id_raises(self, asset_service):
        """ID rỗng phải raise InvalidInputError (kiểm tra sớm, không cần query DB)."""
        with pytest.raises(InvalidInputError):
            asset_service.get_asset_by_id("")

    def test_get_not_found_raises(self, asset_service, mock_storage):
        """storage trả về AssetNotFoundError phải được bubble up."""
        mock_storage.get_by_id.side_effect = AssetNotFoundError("not found")

        with pytest.raises(AssetNotFoundError):
            asset_service.get_asset_by_id("non-existent-id")


# =============================================================================
# 3. TEST update_asset
# =============================================================================

class TestUpdateAsset:
    def test_update_name_only(self, asset_service, mock_storage):
        """update_asset chỉ với name → chỉ cập nhật name, giữ nguyên type và status."""
        updated = asset_service.update_asset("asset-001", name="new-name.com")

        assert updated.name == "new-name.com"
        assert updated.type == AssetType.DOMAIN  # Giữ nguyên
        mock_storage.update.assert_called_once()

    def test_update_status_only(self, asset_service, mock_storage):
        """update_asset chỉ với status → chỉ cập nhật status."""
        updated = asset_service.update_asset("asset-001", status="inactive")

        assert updated.status == AssetStatus.INACTIVE
        assert updated.name == "example.com"  # Giữ nguyên

    def test_update_invalid_status_raises(self, asset_service):
        """Status không hợp lệ phải raise error."""
        with pytest.raises(Exception):
            asset_service.update_asset("asset-001", status="deleted")

    def test_update_not_found_raises(self, asset_service, mock_storage):
        """Asset không tồn tại → raise AssetNotFoundError."""
        mock_storage.get_by_id.side_effect = AssetNotFoundError("not found")

        with pytest.raises(AssetNotFoundError):
            asset_service.update_asset("bad-id", name="test.com")

    def test_update_updated_at_changes(self, asset_service):
        """updated_at phải thay đổi sau khi update."""
        old_time = datetime.now(timezone.utc)
        updated = asset_service.update_asset("asset-001", name="updated.com")
        assert updated.updated_at >= old_time


# =============================================================================
# 4. TEST delete_asset
# =============================================================================

class TestDeleteAsset:
    def test_delete_calls_storage(self, asset_service, mock_storage):
        """delete_asset gọi đúng storage.delete() với đúng ID."""
        asset_service.delete_asset("asset-001")
        mock_storage.delete.assert_called_once_with("asset-001")

    def test_delete_empty_id_raises(self, asset_service):
        """ID rỗng phải raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            asset_service.delete_asset("")


# =============================================================================
# 5. TEST batch_create_assets
# =============================================================================

class TestBatchCreate:
    def test_batch_create_valid_assets(self, asset_service, mock_storage):
        """batch_create với list hợp lệ phải tạo đúng số asset."""
        assets_data = [
            {"name": "one.com", "type": "domain"},
            {"name": "two.com", "type": "domain"},
            {"name": "1.2.3.4", "type": "ip"},
        ]
        results = asset_service.batch_create_assets(assets_data)

        assert len(results) == 3
        mock_storage.batch_create.assert_called_once()

    def test_batch_create_empty_list_raises(self, asset_service):
        """List rỗng phải raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            asset_service.batch_create_assets([])

    def test_batch_create_too_many_raises(self, asset_service):
        """Quá 100 assets phải raise InvalidInputError."""
        data = [{"name": f"host{i}.com", "type": "domain"} for i in range(101)]
        with pytest.raises(InvalidInputError):
            asset_service.batch_create_assets(data)

    def test_batch_create_one_invalid_rollback_all(self, asset_service, mock_storage):
        """Nếu 1 asset trong batch không hợp lệ → không tạo bất kỳ cái nào."""
        assets_data = [
            {"name": "valid.com", "type": "domain"},
            {"name": "", "type": "domain"},  # ← Lỗi: name trống
        ]
        with pytest.raises(Exception):
            asset_service.batch_create_assets(assets_data)

        # storage.batch_create KHÔNG được gọi vì fail trước khi tới đó
        mock_storage.batch_create.assert_not_called()


# =============================================================================
# 6. TEST batch_delete_assets
# =============================================================================

class TestBatchDelete:
    def test_batch_delete_calls_storage(self, asset_service, mock_storage):
        """batch_delete gọi đúng storage.batch_delete() với danh sách IDs."""
        mock_storage.batch_delete.return_value = {"deleted": 2, "not_found": 0}
        result = asset_service.batch_delete_assets(["id1", "id2"])

        mock_storage.batch_delete.assert_called_once_with(["id1", "id2"])
        assert result["deleted"] == 2

    def test_batch_delete_empty_list_raises(self, asset_service):
        """List rỗng phải raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            asset_service.batch_delete_assets([])

    def test_batch_delete_strips_whitespace_ids(self, asset_service, mock_storage):
        """IDs có dấu cách thừa phải được strip trước khi gọi storage."""
        mock_storage.batch_delete.return_value = {"deleted": 1, "not_found": 0}
        asset_service.batch_delete_assets(["  id1  ", "id2"])

        called_ids = mock_storage.batch_delete.call_args[0][0]
        assert "id1" in called_ids
        assert "id2" in called_ids
        assert "  id1  " not in called_ids


# =============================================================================
# 7. TEST filter/search/stats
# =============================================================================

class TestFilterSearchStats:
    def test_filter_by_type(self, asset_service, mock_storage):
        """filter_assets với type hợp lệ phải gọi storage.filter()."""
        asset_service.filter_assets(asset_type="domain")
        mock_storage.filter.assert_called_once_with("domain", None)

    def test_filter_invalid_type_raises(self, asset_service):
        """Type không hợp lệ phải raise InvalidTypeError."""
        with pytest.raises(InvalidTypeError):
            asset_service.filter_assets(asset_type="invalid")

    def test_search_empty_query_raises(self, asset_service):
        """Search với query rỗng phải raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            asset_service.search_assets("")

    def test_get_stats_delegates_to_storage(self, asset_service, mock_storage):
        """get_stats phải gọi storage.get_stats()."""
        asset_service.get_stats()
        mock_storage.get_stats.assert_called_once()

    def test_count_delegates_to_storage(self, asset_service, mock_storage):
        """count_assets phải gọi storage.count() với đúng params."""
        asset_service.count_assets(asset_type="domain")
        mock_storage.count.assert_called_once_with("domain", None)
