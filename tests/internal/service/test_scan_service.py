"""
=============================================================================
File: tests/internal/service/test_scan_service.py
Bài 2.3 (Bonus): Service Tests — Kiểm thử ScanService với Mock Storage
=============================================================================
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from internal.model.asset import Asset, AssetType, AssetStatus
from internal.model.scan import ScanJob, ScanType, ScanStatus, AssetScanResultsResponse
from internal.service.scan_service import ScanService


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_asset_storage():
    """Mock lớp Asset Storage — giả lập đọc/ghi asset từ DB."""
    storage = MagicMock()
    storage.get_by_id.return_value = Asset(
        id="asset-test-01",
        name="example.com",
        type=AssetType.DOMAIN,
        status=AssetStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    return storage


@pytest.fixture
def mock_scan_storage():
    """Mock lớp Scan Storage — giả lập đọc/ghi scan jobs và results."""
    storage = MagicMock()
    
    now = datetime.now(timezone.utc)
    storage.create_job.return_value = ScanJob(
        id="job-test-01",
        asset_id="asset-test-01",
        scan_type=ScanType.IP,
        status=ScanStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    storage.get_job.return_value = ScanJob(
        id="job-test-01",
        asset_id="asset-test-01",
        scan_type=ScanType.IP,
        status=ScanStatus.COMPLETED,
        results=1,
        created_at=now,
        updated_at=now,
    )
    # Các method get records trả về list rỗng mặc định
    storage.get_dns_records.return_value = []
    storage.get_whois_records.return_value = []
    storage.get_subdomains.return_value = []
    storage.get_port_records.return_value = []
    storage.get_ip_records.return_value = []
    storage.get_ssl_records.return_value = []
    storage.get_tech_records.return_value = []
    storage.get_cert_trans_records.return_value = []
    return storage


@pytest.fixture
def scan_service(mock_asset_storage, mock_scan_storage):
    """Khởi tạo ScanService với Mock storages."""
    return ScanService(
        asset_storage=mock_asset_storage,
        scan_storage=mock_scan_storage
    )


# =============================================================================
# 1. TEST start_scan
# =============================================================================

class TestStartScan:
    def test_start_scan_creates_pending_job(self, scan_service, mock_scan_storage):
        """start_scan phải tạo một Job mới có status PENDING."""
        bg_tasks = MagicMock()
        bg_tasks.add_task = MagicMock()

        job = scan_service.start_scan("asset-test-01", ScanType.IP, bg_tasks)

        assert job is not None
        assert job.status == ScanStatus.PENDING
        assert job.scan_type == ScanType.IP
        mock_scan_storage.create_job.assert_called_once()

    def test_start_scan_calls_background_task(self, scan_service):
        """start_scan phải queue background task thay vì block luồng chính."""
        bg_tasks = MagicMock()

        scan_service.start_scan("asset-test-01", ScanType.IP, bg_tasks)

        # BackgroundTasks.add_task phải được gọi để chạy pipeline ngầm
        bg_tasks.add_task.assert_called_once()

    def test_start_scan_invalid_asset_raises(self, scan_service, mock_asset_storage):
        """Nếu asset không tồn tại, start_scan phải raise exception."""
        from internal.model.errors import AssetNotFoundError
        mock_asset_storage.get_by_id.side_effect = AssetNotFoundError("not found")
        bg_tasks = MagicMock()

        with pytest.raises(AssetNotFoundError):
            scan_service.start_scan("invalid-id", ScanType.IP, bg_tasks)


# =============================================================================
# 2. TEST get_job / get_job_results
# =============================================================================

class TestGetJobResults:
    def test_get_job_returns_scan_job(self, scan_service, mock_scan_storage):
        """get_job lấy đúng thông tin của ScanJob từ storage."""
        job = scan_service.get_job("job-test-01")

        assert job.id == "job-test-01"
        assert job.status == ScanStatus.COMPLETED
        mock_scan_storage.get_job.assert_called_once_with("job-test-01")

    def test_get_job_results_returns_response_model(self, scan_service, mock_scan_storage):
        """get_job_results trả về AssetScanResultsResponse tổng hợp đúng fields."""
        response = scan_service.get_job_results("job-test-01")

        assert isinstance(response, AssetScanResultsResponse)
        assert response.asset_id == "asset-test-01"
        assert response.ip_records == []
        assert response.ssl_records == []
        assert response.tech_records == []
        assert response.cert_trans_records == []

    def test_get_job_results_calls_all_record_getters(self, scan_service, mock_scan_storage):
        """get_job_results phải gọi getter cho TẤT CẢ loại scan (inclusive IP, SSL, Tech, Cert)."""
        scan_service.get_job_results("job-test-01")

        mock_scan_storage.get_ip_records.assert_called_once()
        mock_scan_storage.get_ssl_records.assert_called_once()
        mock_scan_storage.get_tech_records.assert_called_once()
        mock_scan_storage.get_cert_trans_records.assert_called_once()


# =============================================================================
# 3. TEST get_asset_results
# =============================================================================

class TestGetAssetResults:
    def test_get_asset_results_validates_asset_exists(self, scan_service, mock_asset_storage):
        """get_asset_results phải kiểm tra asset tồn tại trước khi query records."""
        scan_service.get_asset_results("asset-test-01")
        mock_asset_storage.get_by_id.assert_called()

    def test_get_asset_results_returns_combined_response(self, scan_service):
        """get_asset_results trả về response tổng hợp từ tất cả record types."""
        response = scan_service.get_asset_results("asset-test-01")

        assert isinstance(response, AssetScanResultsResponse)
        assert hasattr(response, "dns_records")
        assert hasattr(response, "ip_records")
        assert hasattr(response, "ssl_records")
        assert hasattr(response, "tech_records")
        assert hasattr(response, "cert_trans_records")


# =============================================================================
# 4. TEST get_ip_records / get_ssl_records (Bonus getters)
# =============================================================================

class TestSpecificRecordGetters:
    def test_get_ip_records_delegates_to_storage(self, scan_service, mock_scan_storage):
        """get_ip_records phải truyền thẳng về scan_storage.get_ip_records()."""
        result = scan_service.get_ip_records("asset-test-01")
        mock_scan_storage.get_ip_records.assert_called_once_with("asset-test-01")
        assert result == []

    def test_get_tech_records_delegates_to_storage(self, scan_service, mock_scan_storage):
        result = scan_service.get_tech_records("asset-test-01")
        mock_scan_storage.get_tech_records.assert_called_once_with("asset-test-01")
        assert result == []

    def test_get_cert_trans_records_delegates_to_storage(self, scan_service, mock_scan_storage):
        result = scan_service.get_cert_trans_records("asset-test-01")
        mock_scan_storage.get_cert_trans_records.assert_called_once_with("asset-test-01")
        assert result == []
