# =============================================================================
# PowerShell Script — Session 3: Database Integration (Python/FastAPI)
# =============================================================================
# Tập hợp các lệnh thường dùng khi phát triển.
# Gõ ".\make.ps1 help" để xem danh sách lệnh.
#
# Tương đương Makefile nhưng dành riêng cho Windows user.
# =============================================================================

param (
    [string]$Command = "help"
)

# Để có thể xử lý các unicode characters như emoji trên Console
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Show-Help {
    Write-Host "╔═══════════════════════════════════════════════════════════════╗"
    Write-Host "║           Mini ASM — Session 3 (Python/FastAPI)             ║"
    Write-Host "╠═══════════════════════════════════════════════════════════════╣"
    Write-Host "║  Database:                                                   ║"
    Write-Host "║    .\make.ps1 db-start       Khởi động PostgreSQL + pgAdmin        ║"
    Write-Host "║    .\make.ps1 db-stop        Tắt PostgreSQL (data vẫn còn)         ║"
    Write-Host "║    .\make.ps1 db-logs        Xem log database                      ║"
    Write-Host "║    .\make.ps1 db-shell       Mở terminal PostgreSQL (psql)         ║"
    Write-Host "║                                                              ║"
    Write-Host "║  Migrations & Data:                                          ║"
    Write-Host "║    .\make.ps1 migrate-up     Tạo bảng assets + indexes             ║"
    Write-Host "║    .\make.ps1 migrate-down   Xóa bảng assets (rollback)            ║"
    Write-Host "║    .\make.ps1 seed           Thêm dữ liệu mẫu (17 assets)         ║"
    Write-Host "║    .\make.ps1 seed-rollback  Xóa dữ liệu mẫu                      ║"
    Write-Host "║                                                              ║"
    Write-Host "║  Server:                                                     ║"
    Write-Host "║    .\make.ps1 run            Chạy server (PostgreSQL)              ║"
    Write-Host "║    .\make.ps1 run-memory     Chạy server (In-Memory, session 2)    ║"
    Write-Host "║                                                              ║"
    Write-Host "║  Setup & Cleanup:                                            ║"
    Write-Host "║    .\make.ps1 venv           Tạo virtual env + install deps        ║"
    Write-Host "║    .\make.ps1 clean          Xóa containers + volumes (reset DB)   ║"
    Write-Host "║                                                              ║"
    Write-Host "║  Tiện ích:                                                   ║"
    Write-Host "║    .\make.ps1 db-tables      Xem danh sách bảng                    ║"
    Write-Host "║    .\make.ps1 db-assets      Xem tất cả assets                     ║"
    Write-Host "╚═══════════════════════════════════════════════════════════════╝"
}

switch ($Command) {
    "help" {
        Show-Help
    }
    "db-start" {
        Write-Host "🚀 Starting PostgreSQL..."
        docker compose up -d
        Write-Host "✅ PostgreSQL started on localhost:5432"
    }
    "db-stop" {
        Write-Host "🛑 Stopping PostgreSQL..."
        docker compose stop
        Write-Host "✅ PostgreSQL stopped"
    }
    "db-logs" {
        Write-Host "📋 Database logs (Ctrl+C to exit):"
        docker compose logs -f db
    }
    "db-shell" {
        Write-Host "🐘 Opening PostgreSQL shell..."
        docker compose exec db psql -U postgres -d mini_asm
    }
    "migrate-up" {
        Write-Host "⬆️  Running migrations (up)..."
        docker compose exec db psql -U postgres -d mini_asm -f /docker-entrypoint-initdb.d/001_create_assets.up.sql
        Write-Host "✅ Migrations applied"
    }
    "migrate-down" {
        Write-Host "⬇️  Rolling back migrations (down)..."
        docker compose exec db psql -U postgres -d mini_asm -f /docker-entrypoint-initdb.d/rollback/001_create_assets.down.sql
        Write-Host "✅ Migrations rolled back"
    }
    "seed" {
        Write-Host "🌱 Seeding default data..."
        docker compose exec db psql -U postgres -d mini_asm -f /docker-entrypoint-initdb.d/002_seed_data.up.sql
        Write-Host "✅ Seed data inserted"
    }
    "seed-rollback" {
        Write-Host "🗑️  Removing seed data..."
        docker compose exec db psql -U postgres -d mini_asm -f /docker-entrypoint-initdb.d/rollback/002_seed_data.down.sql
        Write-Host "✅ Seed data removed"
    }
    "run" {
        Write-Host "🚀 Starting Mini ASM Server (PostgreSQL)..."
        Set-Location -Path $PSScriptRoot
        & .\.venv\Scripts\python.exe -m app.server.main
    }
    "run-memory" {
        Write-Host "🚀 Starting Mini ASM Server (In-Memory)..."
        $env:USE_MEMORY = "true"
        Set-Location -Path $PSScriptRoot
        try {
            & .\.venv\Scripts\python.exe -m app.server.main
        } finally {
            Remove-Item Env:\USE_MEMORY -ErrorAction SilentlyContinue
        }
    }
    "venv" {
        Write-Host "🐍 Creating virtual environment..."
        python -m venv .venv
        & .\.venv\Scripts\pip.exe install -r requirements.txt
        Write-Host "✅ Virtual environment ready"
    }
    "clean" {
        Write-Host "🧹 Cleaning up..."
        docker compose down -v
        Write-Host "✅ Containers and volumes removed"
    }
    "db-tables" {
        Write-Host "📊 Tables in mini_asm database:"
        docker compose exec db psql -U postgres -d mini_asm -c "\dt"
    }
    "db-assets" {
        Write-Host "📋 All assets in database:"
        docker compose exec db psql -U postgres -d mini_asm -c "SELECT id, name, type, status, created_at FROM assets ORDER BY created_at DESC;"
    }
    default {
        Write-Host "Lệnh không hợp lệ. Gõ '.\make.ps1 help' để xem danh sách lệnh." -ForegroundColor Red
        Show-Help
    }
}
