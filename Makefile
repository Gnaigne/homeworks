# =============================================================================
# Makefile — Session 3: Database Integration (Python/FastAPI)
# =============================================================================
# Tập hợp các lệnh thường dùng khi phát triển.
# Gõ "make help" để xem danh sách lệnh.
#
# Tương đương Makefile trong Go version nhưng dùng Python thay vì Go.
# =============================================================================

.PHONY: help db-start db-stop db-logs db-shell migrate-up migrate-down run run-memory clean setup venv

# Lệnh mặc định khi gõ "make" không có tham số
help:
	@echo "╔═══════════════════════════════════════════════════════════════╗"
	@echo "║           Mini ASM — Session 3 (Python/FastAPI)             ║"
	@echo "╠═══════════════════════════════════════════════════════════════╣"
	@echo "║  Database:                                                   ║"
	@echo "║    make db-start       Khởi động PostgreSQL + pgAdmin        ║"
	@echo "║    make db-stop        Tắt PostgreSQL (data vẫn còn)         ║"
	@echo "║    make db-logs        Xem log database                      ║"
	@echo "║    make db-shell       Mở terminal PostgreSQL (psql)         ║"
	@echo "║                                                              ║"
	@echo "║  Migrations & Data:                                          ║"
	@echo "║    make migrate-up     Tạo bảng assets + indexes             ║"
	@echo "║    make migrate-down   Xóa bảng assets (rollback)            ║"
	@echo "║    make seed           Thêm dữ liệu mẫu (17 assets)         ║"
	@echo "║    make seed-rollback  Xóa dữ liệu mẫu                      ║"
	@echo "║                                                              ║"
	@echo "║  Server:                                                     ║"
	@echo "║    make run            Chạy server (PostgreSQL)              ║"
	@echo "║    make run-memory     Chạy server (In-Memory, session 2)    ║"
	@echo "║                                                              ║"
	@echo "║  Setup & Cleanup:                                            ║"
	@echo "║    make venv           Tạo virtual env + install deps        ║"
	@echo "║    make clean          Xóa containers + volumes (reset DB)   ║"
	@echo "║                                                              ║"
	@echo "║  Tiện ích:                                                   ║"
	@echo "║    make db-tables      Xem danh sách bảng                    ║"
	@echo "║    make db-assets      Xem tất cả assets                     ║"
	@echo "╚═══════════════════════════════════════════════════════════════╝"

# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

# Khởi động PostgreSQL container (chạy nền)
db-start:
	@echo "🚀 Starting PostgreSQL..."
	docker compose up -d
	@echo "✅ PostgreSQL started on localhost:5432"

# Tắt PostgreSQL (dữ liệu vẫn còn)
db-stop:
	@echo "🛑 Stopping PostgreSQL..."
	docker compose stop
	@echo "✅ PostgreSQL stopped"

# Xem log của PostgreSQL (Ctrl+C để thoát)
db-logs:
	@echo "📋 Database logs (Ctrl+C to exit):"
	docker compose logs -f db

# Mở terminal PostgreSQL để chạy SQL thủ công
db-shell:
	@echo "🐘 Opening PostgreSQL shell..."
	docker compose exec db psql -U postgres -d mini_asm

# =============================================================================
# MIGRATIONS
# =============================================================================

# Chạy migration UP — tạo bảng assets + indexes
migrate-up:
	@echo "⬆️  Running migrations (up)..."
	docker compose exec db psql -U postgres -d mini_asm -f /docker-entrypoint-initdb.d/001_create_assets.up.sql
	@echo "✅ Migrations applied"

# Chạy migration DOWN — xóa bảng assets (rollback)
migrate-down:
	@echo "⬇️  Rolling back migrations (down)..."
	docker compose exec db psql -U postgres -d mini_asm -f /docker-entrypoint-initdb.d/rollback/001_create_assets.down.sql
	@echo "✅ Migrations rolled back"

# Thêm dữ liệu mẫu (seed data) vào database
seed:
	@echo "🌱 Seeding default data..."
	docker compose exec db psql -U postgres -d mini_asm -f /docker-entrypoint-initdb.d/002_seed_data.up.sql
	@echo "✅ Seed data inserted"

# Xóa dữ liệu mẫu (rollback seed)
seed-rollback:
	@echo "🗑️  Removing seed data..."
	docker compose exec db psql -U postgres -d mini_asm -f /docker-entrypoint-initdb.d/rollback/002_seed_data.down.sql
	@echo "✅ Seed data removed"

# =============================================================================
# SERVER
# =============================================================================

# Chạy server với PostgreSQL (session 3)
run:
	@echo "🚀 Starting Mini ASM Server (PostgreSQL)..."
	cd "$(CURDIR)" && .venv/bin/python -m app.server.main

# Chạy server với In-Memory storage (quay lại session 2)
run-memory:
	@echo "🚀 Starting Mini ASM Server (In-Memory)..."
	USE_MEMORY=true cd "$(CURDIR)" && .venv/bin/python -m app.server.main

# =============================================================================
# SETUP & CLEANUP
# =============================================================================

# Tạo virtual environment và cài dependencies
venv:
	@echo "🐍 Creating virtual environment..."
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	@echo "✅ Virtual environment ready"

# Xóa containers, volumes, network reset toàn bộ
clean:
	@echo "🧹 Cleaning up..."
	docker compose down -v
	@echo "✅ Containers and volumes removed"

# =============================================================================
# TIỆN ÍCH — Xem nhanh dữ liệu trong database
# =============================================================================

# Xem danh sách bảng
db-tables:
	@echo "📊 Tables in mini_asm database:"
	docker compose exec db psql -U postgres -d mini_asm -c "\dt"

# Xem tất cả assets
db-assets:
	@echo "📋 All assets in database:"
	docker compose exec db psql -U postgres -d mini_asm -c "SELECT id, name, type, status, created_at FROM assets ORDER BY created_at DESC;"
