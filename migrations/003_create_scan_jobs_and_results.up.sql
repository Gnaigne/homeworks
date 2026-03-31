-- =============================================================================
-- Migration UP: Tạo các bảng cho EASM (Scan Jobs và Results)
-- Version: 003
-- Tác dụng: Thêm bảng scan_jobs và các bảng lưu kết quả quét dns, whois, subdomains.
-- =============================================================================

-- 1. Bảng scan_jobs
CREATE TABLE IF NOT EXISTS scan_jobs (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_type VARCHAR(50) NOT NULL CHECK (scan_type IN ('dns', 'whois', 'subdomain', 'cert_trans', 'asn', 'all', 'port', 'ssl')),
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial')),
    error TEXT,
    results INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scan_jobs_asset_id ON scan_jobs(asset_id);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_status ON scan_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_created_at ON scan_jobs(created_at DESC);

-- 2. Bảng dns_records
CREATE TABLE IF NOT EXISTS dns_records (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_job_id UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    record_type VARCHAR(20) NOT NULL, -- A, AAAA, MX, NS, TXT, CNAME
    name VARCHAR(255) NOT NULL DEFAULT '',
    value TEXT NOT NULL,
    ttl INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dns_records_asset_id ON dns_records(asset_id);
CREATE INDEX IF NOT EXISTS idx_dns_records_scan_job_id ON dns_records(scan_job_id);

-- 3. Bảng whois_records
CREATE TABLE IF NOT EXISTS whois_records (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_job_id UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    registrar VARCHAR(255),
    creation_date TIMESTAMP,
    expiration_date TIMESTAMP,
    name_servers TEXT, -- Có thể lưu dưới dạng comma-separated list
    status TEXT,
    emails TEXT,
    raw_data TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_whois_records_asset_id ON whois_records(asset_id);
CREATE INDEX IF NOT EXISTS idx_whois_records_scan_job_id ON whois_records(scan_job_id);

-- 4. Bảng subdomains
CREATE TABLE IF NOT EXISTS subdomains (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_job_id UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    subdomain VARCHAR(255) NOT NULL,
    source VARCHAR(255) NOT NULL DEFAULT 'dns_bruteforce',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ip_address VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subdomains_asset_id ON subdomains(asset_id);
CREATE INDEX IF NOT EXISTS idx_subdomains_scan_job_id ON subdomains(scan_job_id);
