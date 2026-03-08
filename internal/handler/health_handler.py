"""
=============================================================================
File: internal/handler/health_handler.py
Layer: Presentation Layer — HTTP Handler (Clean Architecture)
Tác dụng: Health check endpoint — kiểm tra server + database có đang hoạt động.
=============================================================================

[BÀI 5] Nâng cấp:
    - Trước: GET /health chỉ trả "ok" + uptime (không kiểm tra DB)
    - Sau: GET /health kiểm tra DB connection bằng SELECT 1
           → 200 OK nếu DB connected
           → 503 Service Unavailable nếu DB down

Tại sao cần health check DB?
    - Monitoring tools (Kubernetes, Docker, Prometheus) gọi /health định kỳ
    - Nếu DB down → /health trả 503 → alert team DevOps xử lý
    - Load balancer thấy 503 → ngừng chuyển traffic đến server này
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("mini-asm.handler.health")


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class DatabaseHealth(BaseModel):
    """Thông tin sức khỏe database."""
    status: str                 # "connected" hoặc "disconnected"
    latency_ms: Optional[float] = None  # Thời gian ping DB (ms), None nếu fail
    # Các field dưới đây mô phỏng Go's db.Stats()
    # psycopg2 dùng single connection (không phải pool), nên giá trị đơn giản
    open_connections: int       # Số connection đang mở (0 hoặc 1)
    in_use: int                 # Số connection đang dùng
    idle: int                   # Số connection rảnh
    max_open: int               # Giới hạn connection tối đa


class HealthResponse(BaseModel):
    """
    Response cho GET /health.

    Attributes:
        status: "ok" (DB connected) hoặc "degraded" (DB down)
        message: Mô tả ngắn
        uptime_seconds: Thời gian server đã chạy (giây)
        database: Thông tin chi tiết về DB connection
        timestamp: Thời điểm kiểm tra
    """
    status: str
    message: str
    uptime_seconds: float
    database: Optional[DatabaseHealth] = None  # None nếu dùng MemoryStorage
    timestamp: datetime


# =============================================================================
# HEALTH ROUTER
# =============================================================================

def create_health_router(
    start_time: datetime,
    storage=None,
) -> APIRouter:
    """
    Tạo router cho health check endpoint.

    [BÀI 5] Thêm tham số storage để kiểm tra sức khỏe database.
    Truyền cả storage object (không chỉ connection) để có thể reconnect
    khi DB restart — vì cần gọi store.check_health() ở tầng storage.

    Args:
        start_time: Thời điểm server khởi động (tính uptime)
        storage: Storage object (PostgresStorage hoặc MemoryStorage)
                 Có .check_health() nếu là PostgresStorage

    Returns:
        APIRouter chứa endpoint GET /health
    """

    router = APIRouter(tags=["Health"])

    def _check_database() -> DatabaseHealth:
        """
        Kiểm tra DB thông qua storage.check_health().

        Flow:
            1. Kiểm tra storage có method check_health() không (dùng hasattr)
               - MemoryStorage không có → trả "no_database"
               - PostgresStorage có → gọi method đó
            2. check_health() bên trong sẽ:
               - Thử SELECT 1 → nếu OK → trả connected
               - Nếu fail → tạo connection MỚI → thử lại
               - Nếu vẫn fail → trả disconnected

        Returns:
            DatabaseHealth với status "connected" / "disconnected" / "no_database"
        """
        # hasattr(obj, 'method'): kiểm tra object có method/thuộc tính đó không
        # MemoryStorage không có check_health() → False
        # PostgresStorage có check_health() → True
        if storage is None or not hasattr(storage, 'check_health'):
            return DatabaseHealth(
                status="no_database",
                open_connections=0, in_use=0, idle=0, max_open=0,
            )

        # Gọi storage.check_health() — logic reconnect nằm BÊN TRONG storage layer
        # → Giữ đúng Clean Architecture: handler không biết chi tiết DB/reconnect
        result = storage.check_health()

        if result["connected"]:
            return DatabaseHealth(
                status="connected",
                latency_ms=result["latency_ms"],
                open_connections=1,
                in_use=0,
                idle=1,
                max_open=1,
            )
        else:
            return DatabaseHealth(
                status="disconnected",
                open_connections=0, in_use=0, idle=0, max_open=1,
            )

    @router.get(
        "/health",
        summary="Kiểm tra sức khỏe server + database",
        description=(
            "[Bài 5] Trả về trạng thái server và database.\n"
            "- 200 OK: Server + DB hoạt động bình thường\n"
            "- 503 Service Unavailable: DB bị down"
        ),
    )
    def health_check():
        """
        GET /health — Kiểm tra sức khỏe server và database.

        [BÀI 5] Nâng cấp:
            - Kiểm tra DB bằng SELECT 1
            - Trả 200 nếu OK, 503 nếu DB down
            - Response chứa database status, latency, connection info

        Returns:
            JSONResponse: Trả trực tiếp (không dùng response_model)
            vì cần kiểm soát status_code (200 hoặc 503).
        """
        now = datetime.now(timezone.utc)
        uptime = round((now - start_time).total_seconds(), 2)

        # Kiểm tra database health
        db_health = _check_database()

        # Quyết định status dựa trên DB
        # "connected" hoặc "no_database" (MemoryStorage) → OK
        # "disconnected" → degraded + HTTP 503
        if db_health.status == "disconnected":
            status = "degraded"
            message = "Server is running but database is unavailable"
            http_status = 503
        else:
            status = "ok"
            message = "Mini ASM service is running"
            http_status = 200

        # Tạo response data
        response_data = HealthResponse(
            status=status,
            message=message,
            uptime_seconds=uptime,
            database=db_health if storage is not None else None,
            timestamp=now,
        )

        # JSONResponse cho phép set status_code linh hoạt (200 hoặc 503)
        # Nếu dùng return trực tiếp → FastAPI luôn trả 200
        return JSONResponse(
            status_code=http_status,
            content=response_data.model_dump(mode="json"),
            # model_dump(mode="json"): chuyển Pydantic model → dict
            # mode="json" đảm bảo datetime → ISO string (thay vì datetime object)
        )

    return router
