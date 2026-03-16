"""
=============================================================================
File: tests/internal/handler/test_scan_handler.py
Bài 2.2 (Bonus): Handler Tests — Kiểm thử HTTP API endpoints của Scan
                  Sử dụng FastAPI TestClient để test end-to-end tầng Handler
=============================================================================
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone

from internal.model.scan import (
    ScanJob, ScanType, ScanStatus, AssetScanResultsResponse,
    IPRecord, TechRecord
)
from internal.model.errors import AssetNotFoundError
from internal.handler.scan_handler import create_scan_router


# =============================================================================
# FIXTURES: Tạo mock service và test client
# =============================================================================

@pytest.fixture
def mock_scan_service():
    """Mock ScanService để test handler mà không cần database thật."""
    service = MagicMock()
    
    now = datetime.now(timezone.utc)
    
    # Mặc định: start_scan trả về pending job
    service.start_scan.return_value = ScanJob(
        id="job-handler-01",
        asset_id="asset-handler-01",
        scan_type=ScanType.IP,
        status=ScanStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    
    # get_job trả về completed job
    service.get_job.return_value = ScanJob(
        id="job-handler-01",
        asset_id="asset-handler-01",
        scan_type=ScanType.IP,
        status=ScanStatus.COMPLETED,
        results=1,
        created_at=now,
        updated_at=now,
    )
    
    # get_job_results trả về empty response
    service.get_job_results.return_value = AssetScanResultsResponse(
        asset_id="asset-handler-01",
        dns_records=[], whois_records=[], subdomains=[], port_records=[],
        ip_records=[], ssl_records=[], tech_records=[], cert_trans_records=[]
    )
    
    # get_asset_results
    service.get_asset_results.return_value = AssetScanResultsResponse(
        asset_id="asset-handler-01",
        dns_records=[], whois_records=[], subdomains=[], port_records=[],
        ip_records=[], ssl_records=[], tech_records=[], cert_trans_records=[]
    )
    
    service.get_asset_scan_jobs.return_value = []
    service.get_ip_records.return_value = []
    service.get_ssl_records.return_value = []
    service.get_tech_records.return_value = []
    service.get_cert_trans_records.return_value = []
    
    return service


@pytest.fixture
def test_client(mock_scan_service):
    """Tạo FastAPI test app với scan router, inject mock service."""
    app = FastAPI()
    router = create_scan_router(mock_scan_service)
    app.include_router(router)
    return TestClient(app)


# =============================================================================
# 1. TEST POST /assets/{id}/scan — Khởi chạy scan
# =============================================================================

class TestStartScanEndpoint:
    def test_start_ip_scan_returns_202(self, test_client):
        """POST /assets/{id}/scan với scan_type=ip phải trả 202 Accepted."""
        response = test_client.post(
            "/assets/asset-handler-01/scan",
            json={"scan_type": "ip"}
        )
        assert response.status_code == 202

    def test_start_scan_response_contains_job_id(self, test_client):
        """Response body phải có trường id (Job ID)."""
        response = test_client.post(
            "/assets/asset-handler-01/scan",
            json={"scan_type": "ip"}
        )
        data = response.json()
        assert "id" in data
        assert data["id"] == "job-handler-01"

    def test_start_scan_response_status_is_pending(self, test_client):
        """Job mới tạo phải có status = pending."""
        response = test_client.post(
            "/assets/asset-handler-01/scan",
            json={"scan_type": "ip"}
        )
        data = response.json()
        assert data["status"] == "pending"

    def test_start_scan_invalid_type_returns_422(self, test_client):
        """Scan type không hợp lệ phải trả 422 Unprocessable Entity."""
        response = test_client.post(
            "/assets/asset-handler-01/scan",
            json={"scan_type": "nmap"}  # không tồn tại trong enum
        )
        assert response.status_code == 422

    def test_start_scan_asset_not_found_returns_404(self, test_client, mock_scan_service):
        """Nếu asset không tồn tại, phải trả 404."""
        mock_scan_service.start_scan.side_effect = AssetNotFoundError("asset not found")
        response = test_client.post(
            "/assets/non-existent-id/scan",
            json={"scan_type": "dns"}
        )
        assert response.status_code == 404

    @pytest.mark.parametrize("scan_type", ["dns", "whois", "subdomain", "ip", "tech", "cert_trans"])
    def test_start_scan_all_valid_passive_types(self, test_client, scan_type):
        """Tất cả scan types hợp lệ đều phải được chấp nhận."""
        response = test_client.post(
            "/assets/asset-handler-01/scan",
            json={"scan_type": scan_type}
        )
        assert response.status_code == 202


# =============================================================================
# 2. TEST GET /scan-jobs/{id} — Lấy trạng thái job
# =============================================================================

class TestGetScanJobEndpoint:
    def test_get_job_returns_200(self, test_client):
        """GET /scan-jobs/{id} phải trả 200 OK."""
        response = test_client.get("/scan-jobs/job-handler-01")
        assert response.status_code == 200

    def test_get_job_response_contains_status(self, test_client):
        """Response phải có trường status là 'completed'."""
        response = test_client.get("/scan-jobs/job-handler-01")
        data = response.json()
        assert data["status"] == "completed"

    def test_get_job_response_contains_scan_type(self, test_client):
        """Response phải có trường scan_type."""
        response = test_client.get("/scan-jobs/job-handler-01")
        data = response.json()
        assert "scan_type" in data
        assert data["scan_type"] == "ip"


# =============================================================================
# 3. TEST GET /scan-jobs/{id}/results — Lấy kết quả job
# =============================================================================

class TestGetJobResultsEndpoint:
    def test_get_job_results_returns_200(self, test_client):
        """GET /scan-jobs/{id}/results phải trả 200 OK."""
        response = test_client.get("/scan-jobs/job-handler-01/results")
        assert response.status_code == 200

    def test_get_job_results_has_all_record_arrays(self, test_client):
        """Response phải có mảng cho TẤT CẢ loại record (kể cả mới: ip, ssl, tech, cert_trans)."""
        response = test_client.get("/scan-jobs/job-handler-01/results")
        data = response.json()
        assert "dns_records" in data
        assert "ip_records" in data
        assert "ssl_records" in data
        assert "tech_records" in data
        assert "cert_trans_records" in data

    def test_get_job_results_record_arrays_are_lists(self, test_client):
        """Tất cả trường record phải là kiểu mảng (list)."""
        response = test_client.get("/scan-jobs/job-handler-01/results")
        data = response.json()
        assert isinstance(data["ip_records"], list)
        assert isinstance(data["ssl_records"], list)
        assert isinstance(data["tech_records"], list)
        assert isinstance(data["cert_trans_records"], list)


# =============================================================================
# 4. TEST GET /assets/{id}/results — Lấy tổng hợp kết quả của asset
# =============================================================================

class TestGetAssetResultsEndpoint:
    def test_get_asset_results_returns_200(self, test_client):
        """GET /assets/{id}/results phải trả 200 OK."""
        response = test_client.get("/assets/asset-handler-01/results")
        assert response.status_code == 200

    def test_get_asset_results_has_asset_id(self, test_client):
        """Response body phải có trường asset_id."""
        response = test_client.get("/assets/asset-handler-01/results")
        data = response.json()
        assert "asset_id" in data
        assert data["asset_id"] == "asset-handler-01"


# =============================================================================
# 5. TEST GET /assets/{id}/ip — Endpoint riêng lẻ cho IP records
# =============================================================================

class TestGetAssetIPEndpoint:
    def test_get_asset_ip_returns_200(self, test_client):
        """GET /assets/{id}/ip phải trả 200 OK."""
        response = test_client.get("/assets/asset-handler-01/ip")
        assert response.status_code == 200

    def test_get_asset_ip_returns_data_key(self, test_client):
        """Response phải có key 'data' là dạng array."""
        response = test_client.get("/assets/asset-handler-01/ip")
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_get_asset_ip_asset_not_found_returns_404(self, test_client, mock_scan_service):
        """Asset không tồn tại → 404."""
        mock_scan_service.get_ip_records.side_effect = AssetNotFoundError("not found")
        response = test_client.get("/assets/non-existent/ip")
        assert response.status_code == 404


# =============================================================================
# 6. TEST GET /assets/{id}/tech và cert_trans
# =============================================================================

class TestOtherScanResultEndpoints:
    def test_get_asset_tech_returns_200(self, test_client):
        response = test_client.get("/assets/asset-handler-01/tech")
        assert response.status_code == 200
        assert "data" in response.json()

    def test_get_asset_cert_trans_returns_200(self, test_client):
        response = test_client.get("/assets/asset-handler-01/cert_trans")
        assert response.status_code == 200
        assert "data" in response.json()

    def test_get_asset_ssl_returns_200(self, test_client):
        response = test_client.get("/assets/asset-handler-01/ssl")
        assert response.status_code == 200
        assert "data" in response.json()
