-- =============================================================================
-- Migration DOWN: Xóa bảng assets (Rollback)
-- Version: 001
-- Tác dụng: Hoàn tác migration UP — xóa bảng và indexes.
-- =============================================================================
--
-- File DOWN là "nút Undo" cho migration:
--   - Nếu migration UP gây lỗi → chạy DOWN để quay lại trạng thái trước
--   - Luôn viết DOWN cho mỗi UP: deploy an toàn hơn
--
-- Chạy: make migrate-down
-- =============================================================================

-- Xóa indexes trước (PostgreSQL yêu cầu)
DROP INDEX IF EXISTS idx_assets_created_at;
DROP INDEX IF EXISTS idx_assets_name;
DROP INDEX IF EXISTS idx_assets_status;
DROP INDEX IF EXISTS idx_assets_type;

-- Xóa bảng chính
DROP TABLE IF EXISTS assets;
