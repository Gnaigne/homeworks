"""
=============================================================================
File: internal/handler/asset_handler.py
Layer: Presentation Layer — HTTP Handler (Clean Architecture)
Tác dụng: Xử lý tất cả HTTP request liên quan đến Asset (CRUD + filter/search).
=============================================================================

ĐỌC FILE NÀY SAU service/ — handler gọi service, không gọi storage trực tiếp.

Handler layer chịu trách nhiệm 100% về HTTP concerns:
    ✅ Parse request body (JSON), query params, path params
    ✅ Gọi service method tương ứng
    ✅ Chuyển exception thành HTTP status code phù hợp
    ✅ Trả JSON response cho client
    ❌ KHÔNG chứa business logic (validation, UUID, timestamps)
    ❌ KHÔNG truy cập storage trực tiếp

Mapping Exception → HTTP Status Code:
    AssetNotFoundError  → 404 Not Found
    InvalidInputError   → 400 Bad Request  (bao gồm EmptyName, InvalidType, InvalidStatus)
    DuplicateAssetError → 409 Conflict
    Exception khác      → 500 Internal Server Error
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from internal.model.asset import Asset, CreateAssetRequest, UpdateAssetRequest, BatchCreateAssetRequest
from internal.storage.storage import QueryParams
from internal.model.errors import (
    AssetNotFoundError,
    InvalidInputError,
    DuplicateAssetError,
)
from internal.service.asset_service import AssetService

# Logger cho handler — ghi log các request để debug
logger = logging.getLogger("mini-asm.handler.asset")


# =============================================================================
# HELPER: Chuyển exception thành HTTPException
# =============================================================================

def _map_error_to_http(error: Exception) -> HTTPException:
    """
    Chuyển domain exception thành FastAPI HTTPException với status code phù hợp.

    Tương đương Go function:
        func mapErrorToStatus(err error) int { switch {...} }

    Nhưng trong Python, FastAPI dùng HTTPException thay vì viết thẳng status code
    vào response writer. HTTPException tự động tạo JSON error response:
        {"detail": "error message"}

    Args:
        error: Domain exception từ service/storage layer

    Returns:
        HTTPException với status_code và detail message tương ứng
    """
    if isinstance(error, AssetNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    elif isinstance(error, InvalidInputError):
        # Bao gồm cả EmptyNameError, InvalidTypeError, InvalidStatusError
        # vì chúng kế thừa InvalidInputError
        return HTTPException(status_code=400, detail=str(error))
    elif isinstance(error, DuplicateAssetError):
        return HTTPException(status_code=409, detail=str(error))
    else:
        # Lỗi không xác định → 500 Internal Server Error
        logger.error(f"Unexpected error: {error}", exc_info=True)
        return HTTPException(status_code=500, detail="internal server error")


# =============================================================================
# ASSET ROUTER
# =============================================================================

def create_asset_router(service: AssetService) -> APIRouter:
    """
    Tạo router chứa tất cả asset endpoints (CRUD + filter + search).

    Tương đương Go:
        type AssetHandler struct { service *service.AssetService }
        func NewAssetHandler(service) *AssetHandler

    Python dùng closure: service được "bắt" vào scope,
    tất cả endpoint function bên trong đều truy cập được service.

    Args:
        service: AssetService instance (đã inject storage dependency)

    Returns:
        APIRouter chứa các routes:
            POST   /assets         → Tạo asset mới
            GET    /assets         → Liệt kê/lọc/tìm kiếm asset
            GET    /assets/{id}    → Lấy asset theo ID
            PUT    /assets/{id}    → Cập nhật asset
            DELETE /assets/{id}    → Xóa asset
    """

    # prefix="/assets" tự động thêm /assets vào đầu mọi route
    # Ví dụ: @router.post("/stats") → POST /assets/stats
    router = APIRouter(prefix="/assets", tags=["Assets"])

    # -----------------------------------------------------------------
    # [BÀI 1] GET /assets/stats — Thống kê tổng quan
    # -----------------------------------------------------------------
    # ⚠️ LưU Ý: Đặt TRƯỚC route "/{id}" để FastAPI không nhầm "stats" là {id}
    # Ví dụ: GET /assets/stats → nếu đặt sau /{id}, FastAPI sẽ hiểu id="stats"
    @router.get(
        "/stats",
        summary="Thống kê tổng quan assets",
        description="Trả về tổng số asset, đếm theo type và theo status.",
    )
    def get_stats() -> dict:
        """
        Xử lý GET /assets/stats.

        Trả về thống kê:
            - total: tổng số asset
            - by_type: đếm theo domain/ip/service
            - by_status: đếm theo active/inactive
        """
        try:
            stats = service.get_stats()
            return stats
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # [BÀI 1] GET /assets/count — Đếm asset theo filter
    # -----------------------------------------------------------------
    @router.get(
        "/count",
        summary="Đếm số lượng asset",
        description="Đếm asset, hỗ trợ lọc theo ?type= và ?status= (tùy chọn).",
    )
    def count_assets(
        type: Optional[str] = Query(None, description="Lọc theo loại: domain, ip, service"),
        status: Optional[str] = Query(None, description="Lọc theo trạng thái: active, inactive"),
    ) -> dict:
        """
        Xử lý GET /assets/count.

        Query params:
            - type: lọc theo loại asset (tùy chọn)
            - status: lọc theo trạng thái (tùy chọn)

        Returns:
            dict với count và filters đã áp dụng
        """
        try:
            count = service.count_assets(type, status)

            # Tạo dict filters chỉ chứa các filter được truyền vào
            # Ví dụ: ?type=domain → {"type": "domain"}
            #         ?type=domain&status=active → {"type": "domain", "status": "active"}
            filters = {}
            if type:
                filters["type"] = type
            if status:
                filters["status"] = status

            return {
                "count": count,
                "filters": filters,
            }
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # [BÀI 2] POST /assets/batch — Tạo nhiều asset cùng lúc
    # -----------------------------------------------------------------
    # ⚠️ Đặt TRƯỚC route "/" và "/{id}" để FastAPI không nhầm "batch" là {id}
    @router.post(
        "/batch",
        status_code=201,
        summary="Tạo nhiều asset cùng lúc (batch)",
        description=(
            "Tạo nhiều asset trong 1 transaction.\n"
            "- Tối đa 100 asset/request\n"
            "- Nếu 1 asset fail validation → rollback tất cả\n"
            "- Trả về số lượng đã tạo và danh sách ID"
        ),
    )
    def batch_create(request: BatchCreateAssetRequest) -> dict:
        """
        Xử lý POST /assets/batch — tạo nhiều asset cùng lúc.

        Cú pháp giải thích:
            def batch_create(request: BatchCreateAssetRequest) -> dict:
                │              │         │                        │
                │              │         │                        └─ Trả về dict (JSON response)
                │              │         └─ Type hint: kiểu dữ liệu của request
                │              └─ Tham số duy nhất — FastAPI TỰ ĐỘNG truyền vào
                └─ Tên hàm

        request: BatchCreateAssetRequest — TRƯỚC khi hàm này chạy, FastAPI đã:
            1. Đọc raw JSON từ HTTP body, ví dụ:
               {"assets": [{"name":"a.com","type":"domain"}, {"name":"b.com","type":"ip"}]}

            2. Gọi Pydantic parse: BatchCreateAssetRequest(**json_data)
               → Kiểm tra: assets có phải list không? Mỗi item đúng format không?
               → Nếu SAI → FastAPI tự trả HTTP 422, hàm này KHÔNG CHẠY

            3. Nếu ĐÚNG → truyền object request vào hàm này
               → request.assets = [CreateAssetRequest(name="a.com", type=DOMAIN), ...]
               → Mỗi phần tử đã là Pydantic model, có .name và .type sẵn

        Tóm lại: khi code vào tới dòng đầu tiên trong hàm,
        request đã được validate hoàn toàn — ta chỉ việc dùng.

        -> dict:
            Hàm trả về dict Python → FastAPI tự chuyển thành JSON response.
            Ví dụ: return {"created": 2, "ids": [...]}
            → Client nhận: {"created": 2, "ids": [...]} với status 201

        Response format:
            {"created": 3, "ids": ["uuid-1", "uuid-2", "uuid-3"]}
        """
        try:
            # =============================================================
            # BƯỚC 1: Chuyển Pydantic objects → list of dict
            # =============================================================
            # request.assets là List[CreateAssetRequest] — list các Pydantic model
            # Nhưng service layer nhận list[dict] (không phụ thuộc vào Pydantic)
            # → Cần chuyển đổi: Pydantic model → dict Python
            #
            # Tại sao service không nhận Pydantic model trực tiếp?
            #   - Service layer KHÔNG nên biết HTTP/Pydantic tồn tại
            #   - dict là kiểu dữ liệu cơ bản của Python, ai cũng dùng được
            #   - Giúp service có thể được gọi từ CLI, test, ... không chỉ HTTP
            assets_data = []
            for item in request.assets:
                # item = 1 CreateAssetRequest object
                # item.name = string, ví dụ "a.com"
                # item.type = Enum AssetType.DOMAIN
                # item.type.value = string "domain" (lấy giá trị gốc từ Enum)
                assets_data.append({
                    "name": item.name,
                    "type": item.type.value,  # Enum → string, ví dụ: AssetType.DOMAIN → "domain"
                })
            # Kết quả: assets_data = [{"name": "a.com", "type": "domain"}, {"name": "b.com", "type": "ip"}]

            # =============================================================
            # BƯỚC 2: Gọi service xử lý business logic
            # =============================================================
            # Service sẽ:
            #   - Validate lại (name trống? quá 100 items?)
            #   - Tạo UUID + timestamps cho từng asset
            #   - Gọi storage.batch_create() trong transaction
            #   - Trả về list Asset đã tạo thành công
            created_assets = service.batch_create_assets(assets_data)

            # =============================================================
            # BƯỚC 3: Tạo response JSON
            # =============================================================
            # List comprehension: lấy id của từng asset đã tạo
            # [asset.id for asset in created_assets]
            # = duyệt qua từng asset, lấy thuộc tính .id, gom thành list
            # Ví dụ: [Asset(id="abc"), Asset(id="def")] → ["abc", "def"]
            ids = [asset.id for asset in created_assets]

            logger.info(f"Batch created {len(ids)} assets")

            # Trả về dict → FastAPI tự chuyển thành JSON + status 201
            return {
                "created": len(ids),  # Số asset đã tạo, ví dụ: 2
                "ids": ids,           # Danh sách UUID, ví dụ: ["abc-123", "def-456"]
            }

        except Exception as e:
            # Nếu có lỗi (EmptyNameError, InvalidTypeError, ...)
            # → chuyển thành HTTPException với status code phù hợp (400, 409, 500)
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # [BÀI 3] DELETE /assets/batch — Xóa nhiều asset cùng lúc
    # -----------------------------------------------------------------
    # ⚠️ Đặt TRƯỚC route "/{id}" để FastAPI không nhầm "batch" là {id}
    @router.delete(
        "/batch",
        summary="Xóa nhiều asset cùng lúc (batch delete)",
        description=(
            "Xóa nhiều asset theo danh sách ID truyền qua query param.\n"
            "- IDs hợp lệ → xóa\n"
            "- IDs không tồn tại → bỏ qua (không trả lỗi)\n"
            "- Trả về số đã xóa và số không tìm thấy"
        ),
    )
    def batch_delete(
        ids: str = Query(
            ...,  # ... = bắt buộc (không có giá trị mặc định)
            description="Danh sách UUID cách nhau bởi dấu phẩy, ví dụ: ?ids=uuid1,uuid2,uuid3",
        ),
    ) -> dict:
        """
        Xử lý DELETE /assets/batch?ids=uuid1,uuid2,uuid3

        Cú pháp giải thích:
            ids: str = Query(...)
                 │       │     │
                 │       │     └─ ... (Ellipsis) = tham số BẮT BUỘC, không có default
                 │       └─ Query() = FastAPI lấy giá trị từ query param (?ids=...)
                 └─ Nhận vào dạng string, ví dụ: "uuid1,uuid2,uuid3"

        Tại sao nhận string thay vì list?
            - URL query param: ?ids=abc,def,ghi → ids = "abc,def,ghi" (1 string)
            - Ta phải tự split(",") để tách thành list
            - Đây là cách đơn giản nhất để truyền nhiều ID qua URL

        Returns:
            {"deleted": 2, "not_found": 1}
        """
        try:
            # Split chuỗi thành list theo dấu phẩy
            # "uuid1,uuid2,uuid3".split(",") → ["uuid1", "uuid2", "uuid3"]
            id_list = ids.split(",")

            # Gọi service — service sẽ lọc ID rỗng + gọi storage xóa
            result = service.batch_delete_assets(id_list)

            logger.info(
                f"Batch deleted: {result['deleted']} deleted, "
                f"{result['not_found']} not found"
            )
            return result

        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # POST /assets — Tạo asset mới
    # -----------------------------------------------------------------
    @router.post(
        "",
        response_model=Asset,
        status_code=201,
        summary="Tạo asset mới",
        description="Tạo asset với name và type được cung cấp. ID, status, timestamps tự động tạo.",
    )
    def create_asset(request: CreateAssetRequest) -> Asset:
        """
        Xử lý POST /assets.

        Tương đương Go: func (h *AssetHandler) CreateAsset(w, r)

        FastAPI tự động:
            1. Parse JSON body thành CreateAssetRequest (Pydantic validate luôn)
            2. Nếu body không hợp lệ → tự trả 422 Unprocessable Entity
            3. Nếu hợp lệ → gọi hàm này với request đã parse
        """
        try:
            # request.type là enum AssetType → lấy .value để truyền string cho service
            asset = service.create_asset(request.name, request.type.value)
            logger.info(f"Created asset: id={asset.id}, name={asset.name}, type={asset.type}")
            return asset
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # [BÀI 7] GET /assets/search — Tìm kiếm asset theo tên
    # -----------------------------------------------------------------
    # ⚠️ Đặt TRƯỚC route "/{id}" để FastAPI không nhầm "search" là {id}
    @router.get(
        "/search",
        response_model=List[Asset],
        summary="[DEPRECATED] Tìm kiếm asset theo tên",
        description=(
            "LƯU Ý: Khuyên dùng GET /assets?search=... (Session 4)\n\n"
            "Tìm asset có tên chứa từ khóa (case-insensitive, partial match).\n"
            "- `?q=example` → tìm tất cả asset có name chứa 'example'\n"
            "- Trả về tối đa 100 kết quả"
        ),
        deprecated=True,
    )
    def search_assets(
        q: str = Query(
            ...,  # Bắt buộc — không có default
            description="Từ khóa tìm kiếm (tìm name chứa chuỗi này, không phân biệt hoa/thường)",
        ),
    ) -> List[Asset]:
        """
        Xử lý GET /assets/search?q=<keyword>.

        Ví dụ:
            GET /assets/search?q=example
            → Tìm tất cả asset có name chứa "example" (không phân biệt hoa/thường)
            → Trả về List[Asset] trực tiếp (không bọc trong pagination)
        """
        try:
            assets = service.search_assets(q)
            return assets
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # [SESSION 4] GET /assets — Liệt kê asset (Filter + Search + Sort + Paginate)
    # -----------------------------------------------------------------
    @router.get(
        "",
        summary="Liệt kê asset với phân trang, lọc, tìm kiếm và sắp xếp",
        description=(
            "[Session 4] Phương thức duy nhất để query danh sách asset.\n"
            "- Phân trang: `?page=1&page_size=20`\n"
            "- Lọc: `?type=domain&status=active`\n"
            "- Tìm kiếm: `?search=example`\n"
            "- Sắp xếp: `?sort_by=created_at&sort_order=desc`\n"
        ),
    )
    def list_assets(
        page: int = Query(1, ge=1, description="Số trang (bắt đầu từ 1)"),
        page_size: int = Query(20, ge=1, le=100, description="Số item mỗi trang (tối đa 100)"),
        type: Optional[str] = Query(None, description="Lọc theo loại: domain, ip, service"),
        status: Optional[str] = Query(None, description="Lọc theo trạng thái: active, inactive"),
        search: Optional[str] = Query(None, description="Tìm kiếm theo tên (partial match)"),
        sort_by: str = Query("created_at", description="Trường để sắp xếp (name, type, status, created_at, updated_at)"),
        sort_order: str = Query("desc", description="Thứ tự sắp xếp (asc, desc)"),
    ) -> dict:
        """
        Xử lý GET /assets với filter + search + sort + pagination.

        Gộp tất cả các tham số query vào 1 struct QueryParams như Go session 4.
        """
        try:
            params = QueryParams(
                page=page,
                page_size=page_size,
                asset_type=type,
                status=status,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            result = service.list_assets(params)
            return result
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /assets/{id} — Lấy một asset theo ID
    # -----------------------------------------------------------------
    @router.get(
        "/{id}",
        response_model=Asset,
        summary="Lấy asset theo ID",
        description="Trả về asset với UUID tương ứng. 404 nếu không tìm thấy.",
    )
    def get_asset(id: str) -> Asset:
        """
        Xử lý GET /assets/{id}.

        Tương đương Go: func (h *AssetHandler) GetAsset(w, r)
        Trong Go: id := r.PathValue("id")
        Trong FastAPI: id tự động lấy từ path parameter.
        """
        try:
            asset = service.get_asset_by_id(id)
            return asset
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # PUT /assets/{id} — Cập nhật asset (partial update)
    # -----------------------------------------------------------------
    @router.put(
        "/{id}",
        response_model=Asset,
        summary="Cập nhật asset",
        description="Cập nhật thông tin asset. Chỉ field được gửi mới thay đổi (partial update).",
    )
    def update_asset(id: str, request: UpdateAssetRequest) -> Asset:
        """
        Xử lý PUT /assets/{id}.

        Tương đương Go: func (h *AssetHandler) UpdateAsset(w, r)

        Partial update: chỉ cập nhật field có giá trị trong request body.
        Field None (không gửi) sẽ giữ nguyên giá trị cũ.
        """
        try:
            asset = service.update_asset(
                id=id,
                name=request.name,
                # Chuyển enum → string value nếu có, None nếu không
                asset_type=request.type.value if request.type else None,
                status=request.status.value if request.status else None,
            )
            logger.info(f"Updated asset: id={asset.id}")
            return asset
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # DELETE /assets/{id} — Xóa asset
    # -----------------------------------------------------------------
    @router.delete(
        "/{id}",
        status_code=204,
        summary="Xóa asset",
        description="Xóa asset theo ID. Trả về 204 No Content nếu thành công.",
    )
    def delete_asset(id: str) -> None:
        """
        Xử lý DELETE /assets/{id}.

        Tương đương Go: func (h *AssetHandler) DeleteAsset(w, r)

        Trả về 204 No Content (không có response body) khi xóa thành công.
        Tương đương Go: w.WriteHeader(http.StatusNoContent)
        """
        try:
            service.delete_asset(id)
            logger.info(f"Deleted asset: id={id}")
            # FastAPI tự trả 204 vì status_code=204 ở decorator
            return None
        except Exception as e:
            raise _map_error_to_http(e)

    return router
