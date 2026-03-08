-- =============================================================================
-- Migration UP: Tạo bảng assets
-- Version: 001
-- Tác dụng: Tạo schema ban đầu cho hệ thống quản lý tài nguyên mạng.
-- =============================================================================
--
-- Chạy migration: make migrate-up
-- Rollback:       make migrate-down (chạy file .down.sql)
--
-- Bảng này map 1:1 với Asset model trong Python:
--   Asset.id         → id UUID PRIMARY KEY
--   Asset.name       → name VARCHAR(255)
--   Asset.type       → type VARCHAR(50)   (domain / ip / service)
--   Asset.status     → status VARCHAR(50) (active / inactive)
--   Asset.created_at → created_at TIMESTAMP
--   Asset.updated_at → updated_at TIMESTAMP
-- =============================================================================

CREATE TABLE IF NOT EXISTS assets (
    -- Primary key: UUID — mã định danh duy nhất toàn cầu
    -- Tại sao UUID thay vì auto-increment?
    --   - Không cần database để generate ID (service layer tạo)
    --   - An toàn cho distributed systems (nhiều server)
    --   - Không thể đoán được ID tiếp theo (bảo mật hơn)
    id UUID PRIMARY KEY,

    -- Tên tài nguyên (ví dụ: "example.com", "192.168.1.1")
    name VARCHAR(255) NOT NULL,

    -- Loại tài nguyên: domain, ip, hoặc service
    type VARCHAR(50) NOT NULL,

    -- Trạng thái: active hoặc inactive
    -- CHECK constraint đảm bảo chỉ nhận 2 giá trị hợp lệ
    status VARCHAR(50) NOT NULL
        CHECK (status IN ('active', 'inactive')),

    -- Timestamp tự động gán khi tạo
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Timestamp tự động cập nhật (service layer quản lý giá trị)
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES — Tăng tốc truy vấn
-- =============================================================================
-- Không có index: database phải quét TOÀN BỘ bảng (full table scan) → chậm
-- Có index: database tìm nhanh qua cấu trúc B-tree → O(log n)

-- Index cho filter theo type: GET /assets?type=domain
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);

-- Index cho filter theo status: GET /assets?status=active
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);

-- Index cho search theo name: GET /assets?search=example
-- Hỗ trợ LIKE / ILIKE queries
CREATE INDEX IF NOT EXISTS idx_assets_name ON assets(name);

-- Index cho sort theo ngày tạo (DESC): ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at DESC);
