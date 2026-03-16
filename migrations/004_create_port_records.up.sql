-- =============================================================================
-- Migration UP: Thêm Cấu trúc cho Port Scanner
-- Version: 004
-- Tác dụng: Thêm bảng port_records lưu trữ kết quả phân tích Service của Cổng trạm,
--           Cập nhật Enum type scan_jobs cho lệnh 'port'.
-- =============================================================================

-- Sửa ENUM của scan_jobs (VARCHAR CHECK)
-- Vì PostgreSQL CHECK constraint không cho ALTER thêm thẳng, ta phải drop constraint cũ
-- (Tên constraint có thể khác nhau, giả định tên do PG tự sinh hoặc tạo mới hẳn)
ALTER TABLE scan_jobs DROP CONSTRAINT IF EXISTS scan_jobs_scan_type_check;
ALTER TABLE scan_jobs ADD CONSTRAINT scan_jobs_scan_type_check 
    CHECK (scan_type IN ('dns', 'whois', 'subdomain', 'cert_trans', 'asn', 'all', 'port', 'ssl'));

ALTER TABLE scan_jobs DROP CONSTRAINT IF EXISTS scan_jobs_status_check;
ALTER TABLE scan_jobs ADD CONSTRAINT scan_jobs_status_check 
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial'));

-- Tạo bảng port_records
CREATE TABLE IF NOT EXISTS port_records (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_job_id UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    port INTEGER NOT NULL,
    state VARCHAR(20) NOT NULL, -- open, closed, filtered
    service VARCHAR(50) NOT NULL,
    version VARCHAR(255),
    banner TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_port_records_asset_id ON port_records(asset_id);
CREATE INDEX IF NOT EXISTS idx_port_records_scan_job_id ON port_records(scan_job_id);
