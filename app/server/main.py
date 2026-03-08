"""
=============================================================================
File: app/server/main.py
Layer: Entry Point — Composition Root (Clean Architecture)
Tác dụng: Khởi tạo ứng dụng, nối các layer lại (Dependency Injection), chạy server.
=============================================================================

ĐỌC FILE NÀY CUỐI CÙNG — sau khi đã hiểu model, storage, service, handler.

Đây là file "nối dây" (wiring) duy nhất biết về TẤT CẢ các layer.
Trách nhiệm:
    1. Khởi tạo Storage (infrastructure)
    2. Khởi tạo Service (inject storage)
    3. Khởi tạo Handler/Router (inject service)
    4. Đăng ký routes vào FastAPI app
    5. Chạy server

Đây cũng là nơi DUY NHẤT thay đổi khi swap implementation:
    Ví dụ: đổi từ MemoryStorage sang PostgresStorage chỉ cần sửa 1 dòng ở đây.

=============================================================================
THỨ TỰ ĐỌC CODE ĐỂ HIỂU PROJECT (Session 3 — Database):
=============================================================================
    1. internal/model/asset.py             → Data structures (không đổi)
    2. internal/model/errors.py            → Error types (không đổi)
    3. internal/storage/storage.py         → Storage interface (không đổi)
    4. internal/storage/memory/memory.py   → Memory implementation (giữ lại)
    5. internal/config/config.py           → [MỚI] Cấu hình database
    6. internal/storage/postgres/postgres.py → [MỚI] PostgreSQL implementation
    7. internal/service/asset_service.py   → Business logic (không đổi!)
    8. internal/handler/asset_handler.py   → HTTP handling (không đổi!)
    9. app/server/main.py (FILE NÀY)      → Đổi 1 chỗ: Memory → Postgres

=============================================================================
THAY ĐỔI SO VỚI SESSION 2:
=============================================================================
    File thay đổi:
        - app/server/main.py       → Đổi storage từ Memory sang Postgres
        - requirements.txt         → Thêm psycopg2-binary, python-dotenv

    File mới thêm:
        - internal/config/config.py              → Đọc cấu hình DB từ env
        - internal/storage/postgres/postgres.py  → PostgreSQL storage
        - docker-compose.yml       → Chạy PostgreSQL bằng Docker
        - migrations/              → SQL tạo/xóa bảng
        - Makefile                 → Lệnh tắt (make db-start, make run, ...)
        - .env                     → Biến môi trường (DB_HOST, DB_PORT, ...)

    File KHÔNG thay đổi (sức mạnh Clean Architecture!):
        - internal/model/*         → Entity layer giữ nguyên
        - internal/service/*       → Business logic giữ nguyên
        - internal/handler/*       → HTTP handler giữ nguyên
        - internal/storage/storage.py → Interface giữ nguyên

=============================================================================
FLOW HOẠT ĐỘNG (Request → Response):
=============================================================================
    Ví dụ: POST /assets {"name": "example.com", "type": "domain"}

    1. Client gửi HTTP POST request đến /assets
    2. FastAPI nhận request → parse JSON body → tạo CreateAssetRequest (Pydantic)
       - Nếu JSON không hợp lệ → trả 422 tự động
    3. Router chuyển đến hàm create_asset() trong asset_handler.py
    4. Handler gọi service.create_asset("example.com", "domain")
    5. Service validate (name không trống, type hợp lệ)
       - Nếu lỗi → raise EmptyNameError hoặc InvalidTypeError
    6. Service tạo Asset entity (UUID, default status, timestamps)
    7. Service gọi storage.create(asset) để lưu
    8. [SESSION 3] PostgresStorage chạy INSERT INTO SQL → lưu vào database
       (Session 2 là MemoryStorage lưu vào dict — chỉ khác bước này!)
    9. Service trả về Asset cho handler
    10. Handler trả JSON response với status 201 Created

    Khi có lỗi (ví dụ: name trống):
    5. Service raise EmptyNameError("name is required")
    6. Handler catch → chuyển thành HTTPException(400, "name is required")
    7. FastAPI trả JSON: {"detail": "name is required"} với status 400
=============================================================================
"""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Thêm đường dẫn gốc project vào sys.path ---
# Để Python tìm được các module trong internal/ khi import
# Ví dụ: "from internal.model import Asset" cần sys.path chứa thư mục session2_py/
# Tương đương GOPATH hoặc go.mod trong Go
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --- Load biến môi trường từ file .env ---
# python-dotenv đọc file .env và đưa vào os.environ
# Phải gọi TRƯỚC khi import config (config đọc os.environ)
from dotenv import load_dotenv
load_dotenv(Path(PROJECT_ROOT) / ".env")

import uvicorn
from fastapi import FastAPI

from internal.handler.asset_handler import create_asset_router
from internal.handler.health_handler import create_health_router
from internal.service.asset_service import AssetService

# --- [SESSION 3] Import thêm config và PostgresStorage ---
from internal.config.config import load_postgres_config
from internal.storage.postgres.postgres import PostgresStorage
# Giữ lại MemoryStorage để dễ chuyển đổi khi cần
from internal.storage.memory.memory import MemoryStorage


# =============================================================================
# LOGGING SETUP
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mini-asm")


# =============================================================================
# DEPENDENCY INJECTION — Nối các layer lại với nhau
# =============================================================================
# Session 2:
#   store = MemoryStorage()
# Session 3 (THAY ĐỔI CHÍNH):
#   config = load_postgres_config()
#   store = PostgresStorage.from_config(config)
#
# Service và Handler KHÔNG THAY ĐỔI — đây là sức mạnh của Clean Architecture!

def create_app() -> FastAPI:
    """
    Factory function tạo và cấu hình FastAPI application.

    Thực hiện Dependency Injection:
        Config → Storage → Service → Handler → App

    [SESSION 3] Thay đổi duy nhất:
        - Đọc config từ .env
        - Tạo PostgresStorage thay vì MemoryStorage
        - Đóng connection khi server shutdown

    Returns:
        FastAPI app đã cấu hình đầy đủ, sẵn sàng chạy
    """

    logger.info("🚀 Starting Mini ASM Server (Session 3 - Database)...")

    # =========================================================================
    # [SESSION 3] THAY ĐỔI: MemoryStorage → PostgresStorage
    # =========================================================================
    #
    # Session 2 (cũ — chỉ 1 dòng):
    #   store = MemoryStorage()
    #
    # Session 3 (mới — đọc config rồi kết nối DB):
    #   config = load_postgres_config()
    #   store = PostgresStorage.from_config(config)
    #
    # Chỉ thay đổi ở ĐÂY — không sửa service, handler, hay model!
    # Đặt biến USE_MEMORY=true trong .env nếu muốn quay lại dùng memory.

    use_memory = os.getenv("USE_MEMORY", "false").lower() == "true"

    if use_memory:
        # Dùng in-memory storage (như session 2)
        store = MemoryStorage()
        logger.info("✅ Storage initialized: In-Memory (USE_MEMORY=true)")
    else:
        # [SESSION 3] Dùng PostgreSQL storage
        # [BÀI 4] Cải tiến: from_config() giờ dùng connect_with_retry()
        #   → Tự retry tối đa 5 lần với exponential backoff (1s → 2s → 4s → 8s → 16s)
        #   → Nếu DB chưa sẵn sàng (vd: Docker khởi động chậm) → server chờ thay vì crash
        #   → Nếu hết 5 lần vẫn fail → sys.exit(1)
        config = load_postgres_config()
        store = PostgresStorage.from_config(config)
        logger.info("✅ Storage initialized: PostgreSQL (with connection retry)")

    # --- 2. Khởi tạo Service Layer (Business Logic) ---
    # ✨ KHÔNG THAY ĐỔI! Service không biết storage là Memory hay Postgres
    asset_service = AssetService(store)
    logger.info("✅ Service initialized: AssetService")

    # --- 3. Khởi tạo Handler Layer (HTTP) ---
    # [BÀI 5] Truyền store cho health handler để kiểm tra sức khỏe DB
    # Health handler gọi store.check_health() → tự xử lý ping + reconnect
    start_time = datetime.now(timezone.utc)
    health_router = create_health_router(start_time, storage=store)
    asset_router = create_asset_router(asset_service)
    logger.info("✅ Handlers initialized")

    # --- 4. Tạo FastAPI App và đăng ký routes ---
    app = FastAPI(
        title="Mini ASM API",
        description=(
            "Attack Surface Management API — Quản lý tài nguyên mạng "
            "(domain, IP, service) với CRUD operations đầy đủ.\n\n"
            "Session 3: Dữ liệu lưu trong PostgreSQL (persistent)."
        ),
        version="3.0.0",   # Nâng version từ 2.0.0 → 3.0.0
        redirect_slashes=False,  # Tắt 307 redirect: /assets → /assets/ để curl không bị mất data
    )

    # include_router gắn router vào app — tương đương mux.HandleFunc() trong Go
    app.include_router(health_router)
    app.include_router(asset_router)

    # --- [SESSION 3] Đóng database connection khi server shutdown ---
    # Tương đương Go: defer db.Close()
    # FastAPI có event "shutdown" — chạy khi server dừng (Ctrl+C)
    @app.on_event("shutdown")
    def shutdown_event():
        """Đóng database connection khi server shutdown."""
        if hasattr(store, 'close'):
            store.close()
            logger.info("🔌 Database connection closed on shutdown")

    logger.info("✅ Routes registered:")
    logger.info("   GET    /health")
    logger.info("   POST   /assets")
    logger.info("   POST   /assets/batch")
    logger.info("   GET    /assets                  (pagination + filter)")
    logger.info("   GET    /assets/stats")
    logger.info("   GET    /assets/count")
    logger.info("   GET    /assets/search?q=...     [BÀI 7]")
    logger.info("   GET    /assets/{id}")
    logger.info("   PUT    /assets/{id}")
    logger.info("   DELETE /assets/batch")
    logger.info("   DELETE /assets/{id}")

    return app


# =============================================================================
# CHẠY SERVER
# =============================================================================
if __name__ == "__main__":
    logger.info("🌐 Server listening on http://localhost:8080")
    logger.info("📖 API Documentation: http://localhost:8080/docs (Swagger UI)")
    logger.info("🗄️  Database: PostgreSQL (persistent storage)")
    logger.info("Press Ctrl+C to stop")

    # Tương đương Go: http.ListenAndServe(":8080", mux)
    # Uvicorn là ASGI server — chạy FastAPI app
    #
    # factory=True → uvicorn gọi create_app() CHỈ ở worker process
    #
    # Tại sao cần factory=True?
    #   Khi reload=True, uvicorn tạo 2 process:
    #     - Reloader process: theo dõi file thay đổi → KHÔNG cần app thật
    #     - Worker process: thực sự serve request → CẦN app thật
    #
    #   Không có factory=True:
    #     uvicorn.run("app.server.main:app") → import module ở CẢ HAI process
    #     → create_app() chạy 2 lần → kết nối DB 2 lần → log in ra 2 lần
    #
    #   Có factory=True:
    #     uvicorn.run("app.server.main:create_app", factory=True)
    #     → Reloader process chỉ import module, KHÔNG gọi create_app()
    #     → Worker process mới gọi create_app() → kết nối DB DUY NHẤT 1 lần
    uvicorn.run(
        "app.server.main:create_app",  # Trỏ đến FUNCTION (không phải biến app)
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
        factory=True,   # ← Chìa khóa: uvicorn sẽ GỌI create_app() thay vì import app
    )
