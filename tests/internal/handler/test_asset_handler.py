"""
=============================================================================
File: tests/internal/handler/test_asset_handler.py
Bài 2.2 (Bonus): Handler Tests — Kiểm thử Asset API Endpoints
               dùng FastAPI TestClient + Mock AssetService
=============================================================================
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from internal.model.asset import Asset, AssetType, AssetStatus
from internal.model.errors import (
    AssetNotFoundError, InvalidInputError, DuplicateAssetError
)
from internal.handler.asset_handler import create_asset_router


# =============================================================================
# FIXTURES
# =============================================================================

#Hàm tiện ích để tạo Asset mock
def make_asset(name="example.com", asset_type=AssetType.DOMAIN, id="asset-001"):
    now = datetime.now(timezone.utc)
    return Asset(
        id=id, name=name, type=asset_type,
        status=AssetStatus.ACTIVE,
        created_at=now, updated_at=now
    )


@pytest.fixture
def mock_service():
    """
    Pytest Fixture: Tạo một AssetService GIẢ (mock) dùng MagicMock.

    Vấn đề: AssetService thật cần kết nối database (PostgreSQL).
    Nếu test gọi service thật → cần DB đang chạy → test chậm, phụ thuộc môi trường.

    Giải pháp: MagicMock() tạo ra một object "ma" có thể giả làm BẤT KỲ class nào.
    Ta cấu hình sẵn return_value cho từng method, ví dụ:
        service.create_asset.return_value = make_asset()
    → Khi handler gọi service.create_asset(...), thay vì chạy business logic thật,
      nó sẽ trả về make_asset() ngay lập tức — không chạm DB.

    Kỹ thuật này gọi là "mocking" — isolate unit cần test (handler)
    khỏi các dependency bên ngoài (service, storage, DB).
    """
    service = MagicMock()
    # Cấu hình giá trị trả về giả cho từng method của service
    service.create_asset.return_value = make_asset()
    service.get_asset_by_id.return_value = make_asset()
    service.get_all_assets.return_value = [make_asset()]
    service.update_asset.return_value = make_asset(name="updated.com")
    service.delete_asset.return_value = None
    service.get_stats.return_value = {"total": 1, "by_type": {"domain": 1}, "by_status": {"active": 1}}
    service.count_assets.return_value = 1
    service.filter_assets.return_value = [make_asset()]
    service.search_assets.return_value = [make_asset()]
    service.list_assets.return_value = {
        "data": [make_asset().model_dump()],
        "total": 1, "page": 1, "page_size": 20, "total_pages": 1
    }
    service.batch_create_assets.return_value = [make_asset("a.com", id="id-1"), make_asset("b.com", id="id-2")]
    service.batch_delete_assets.return_value = {"deleted": 2, "not_found": 0}
    return service

@pytest.fixture
def client(mock_service):
    """
    Pytest Fixture: Tạo FastAPI TestClient để giả lập gửi HTTP request trong test.

    Cách hoạt động:
        1. Tạo app FastAPI mới (app trắng, không phải app production)
        2. Gọi create_asset_router(mock_service) — inject mock service vào router
           (Đây là Dependency Injection: thay vì service thật, ta truyền mock vào)
        3. Đăng ký router vào app
        4. Bọc app vào TestClient — client này mô phỏng browser/curl:
               tc.get("/assets") ≡ curl GET http://localhost/assets
               tc.post("/assets", json={...}) ≡ curl POST với body JSON

    Return tuple (tc, mock_service) để test có thể:
        - tc: gửi HTTP request
        - mock_service: kiểm tra xem handler có gọi đúng service method không
          (assert_called_once_with, call_args, v.v.)

    Tại sao fixture nhận mock_service làm tham số?
        Pytest tự động inject — khi test khai báo `def test_...(self, client)`,
        pytest chạy fixture `mock_service` trước, rồi truyền kết quả vào fixture `client`.
    """
    app = FastAPI()
    router = create_asset_router(mock_service)  # Inject mock service — không dùng service thật
    app.include_router(router)                  # Gắn router vào app
    return TestClient(app), mock_service        # Trả cả TestClient lẫn mock để test dùng


# =============================================================================
# 1. POST /assets — Tạo asset mới
# =============================================================================

class TestCreateAsset:
    def test_create_valid_domain_returns_201(self, client):
        tc, svc = client #tc: TestClient, svc: mock_service
        resp = tc.post("/assets", json={"name": "example.com", "type": "domain"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "example.com"
        assert data["type"] == "domain"
        svc.create_asset.assert_called_once_with("example.com", "domain")

    def test_create_valid_ip_returns_201(self, client):
        tc, svc = client
        svc.create_asset.return_value = make_asset("1.2.3.4", AssetType.IP)
        resp = tc.post("/assets", json={"name": "1.2.3.4", "type": "ip"})
        assert resp.status_code == 201
        assert resp.json()["type"] == "ip"

    def test_create_invalid_type_returns_422(self, client):
        """Pydantic reject type không hợp lệ → 422 trước khi chạm handler."""
        tc, _ = client
        resp = tc.post("/assets", json={"name": "test.com", "type": "invalid"})
        assert resp.status_code == 422

    def test_create_missing_name_returns_422(self, client):
        tc, _ = client
        resp = tc.post("/assets", json={"type": "domain"})
        assert resp.status_code == 422

    def test_create_service_raises_400(self, client):
        """Service raise InvalidInputError → handler trả 400."""
        tc, svc = client
        svc.create_asset.side_effect = InvalidInputError("invalid domain format")
        resp = tc.post("/assets", json={"name": "not_a_domain", "type": "domain"})
        assert resp.status_code == 400

    def test_create_service_raises_409_duplicate(self, client):
        """Service raise DuplicateAssetError → handler trả 409."""
        tc, svc = client
        svc.create_asset.side_effect = DuplicateAssetError("already exists")
        resp = tc.post("/assets", json={"name": "example.com", "type": "domain"})
        assert resp.status_code == 409


# =============================================================================
# 2. GET /assets/{id} — Lấy asset theo ID
# =============================================================================

class TestGetAsset:
    def test_get_existing_returns_200(self, client):
        tc, _ = client
        resp = tc.get("/assets/asset-001")
        assert resp.status_code == 200
        assert resp.json()["id"] == "asset-001"

    def test_get_not_found_returns_404(self, client):
        tc, svc = client
        # Mock service raise AssetNotFoundError
        svc.get_asset_by_id.side_effect = AssetNotFoundError("not found")
        resp = tc.get("/assets/non-existent")
        assert resp.status_code == 404

    def test_get_empty_id_invalid(self, client):
        """ID rỗng → service raise → handler trả lỗi."""
        tc, svc = client
        svc.get_asset_by_id.side_effect = InvalidInputError("ID required")
        resp = tc.get("/assets/ ")
        assert resp.status_code in (400, 404, 422)


# =============================================================================
# 3. GET /assets — Liệt kê tất cả
# =============================================================================

class TestListAssets:
    def test_list_returns_200(self, client):
        tc, svc = client
        resp = tc.get("/assets")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body or isinstance(body, list)

    def test_list_with_type_filter(self, client):
        tc, svc = client
        resp = tc.get("/assets?type=domain")
        assert resp.status_code == 200

        # call_args lưu lại tham số của LẦN GỌI MỚN NHẤT vào mock.
        # Cấu trúc: call_args[0] = positional args (tuple), call_args[1] = keyword args (dict)
        # Ví dụ: handler gọi service.list_assets(params) → call_args[0][0] = params
        #
        # Tại sao cần kiểm tra này?
        # Không đủ khi chỉ thấy response 200 — cần đảm bảo handler đã đọc đúng ?type=domain
        # và truyền đúng vào service (không bỏ sót query param).
        called_params = svc.list_assets.call_args[0][0]
        assert called_params.asset_type == "domain"  # Phải là "domain", không phải None hay string khác

    def test_list_with_pagination(self, client):
        tc, svc = client
        resp = tc.get("/assets?page=2&page_size=10")
        assert resp.status_code == 200

        # Tương tự: kiểm tra handler đã parse đúng ?page=2 và ?page_size=10
        # rồi gọi service với QueryParams có giá trị đúng.
        # Nếu handler hard-code page=1 hay bỏ quên page_size → test này sẽ FAIL ← phát hiện bug!
        called_params = svc.list_assets.call_args[0][0]
        assert called_params.page == 2
        assert called_params.page_size == 10

    def test_list_with_search(self, client):
        tc, svc = client
        resp = tc.get("/assets?search=example")
        assert resp.status_code == 200

        # Kiểm tra ?search=example được truyền đúng vào service (không bị bỏ quên hay thay đổi)
        called_params = svc.list_assets.call_args[0][0]
        assert called_params.search == "example"


# =============================================================================
# 4. PUT /assets/{id} — Cập nhật asset
# =============================================================================

class TestUpdateAsset:
    def test_update_name_returns_200(self, client):
        tc, svc = client
        resp = tc.put("/assets/asset-001", json={"name": "updated.com"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated.com"

    def test_update_not_found_returns_404(self, client):
        tc, svc = client
        svc.update_asset.side_effect = AssetNotFoundError("not found")
        resp = tc.put("/assets/bad-id", json={"name": "new.com"})
        assert resp.status_code == 404

    def test_update_invalid_status_returns_400(self, client):
        tc, svc = client
        svc.update_asset.side_effect = InvalidInputError("invalid status")
        resp = tc.put("/assets/asset-001", json={"status": "deleted"})
        assert resp.status_code in (400, 422)


# =============================================================================
# 5. DELETE /assets/{id} — Xóa asset
# =============================================================================

class TestDeleteAsset:
    def test_delete_existing_returns_204(self, client):
        tc, svc = client
        resp = tc.delete("/assets/asset-001")
        assert resp.status_code == 204
        svc.delete_asset.assert_called_once_with("asset-001")

    def test_delete_not_found_returns_404(self, client):
        tc, svc = client
        svc.delete_asset.side_effect = AssetNotFoundError("not found")
        resp = tc.delete("/assets/bad-id")
        assert resp.status_code == 404


# =============================================================================
# 6. GET /assets/stats — Thống kê
# =============================================================================

class TestStatsEndpoint:
    def test_stats_returns_200(self, client):
        tc, svc = client
        resp = tc.get("/assets/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_type" in data

    def test_count_returns_correct_value(self, client):
        tc, svc = client
        svc.count_assets.return_value = 42
        resp = tc.get("/assets/count")
        assert resp.status_code == 200
        assert resp.json()["count"] == 42


# =============================================================================
# 7. POST /assets/batch — Tạo hàng loạt
# =============================================================================

class TestBatchCreate:
    def test_batch_create_returns_201(self, client):
        tc, svc = client
        body = {"assets": [
            {"name": "a.com", "type": "domain"},
            {"name": "b.com", "type": "domain"},
        ]}
        resp = tc.post("/assets/batch", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["created"] == 2
        assert len(data["ids"]) == 2

    def test_batch_create_empty_list_returns_400(self, client):
        tc, svc = client
        svc.batch_create_assets.side_effect = InvalidInputError("empty list")
        # Pydantic yêu cầu ít nhất 1 phần tử → 422 hoặc 400 tùy validator
        resp = tc.post("/assets/batch", json={"assets": []})
        assert resp.status_code in (400, 422)

    def test_batch_create_invalid_item_returns_422(self, client):
        tc, _ = client
        body = {"assets": [{"name": "a.com", "type": "INVALID_TYPE"}]}
        resp = tc.post("/assets/batch", json=body)
        assert resp.status_code == 422


# =============================================================================
# 8. DELETE /assets/batch — Xóa hàng loạt
# =============================================================================

class TestBatchDelete:
    def test_batch_delete_returns_200(self, client):
        tc, svc = client
        resp = tc.delete("/assets/batch?ids=id1,id2")
        assert resp.status_code == 200
        data = resp.json()
        assert "deleted" in data
        assert "not_found" in data
