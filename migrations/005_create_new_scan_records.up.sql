-- =============================================================================
-- Migration UP: Update scan jobs constraint and create new tables
-- Version: 005
-- =============================================================================

-- 1. Update check constraint on scan_jobs to allow 'ip' and 'tech'
ALTER TABLE scan_jobs DROP CONSTRAINT IF EXISTS scan_jobs_scan_type_check;
ALTER TABLE scan_jobs ADD CONSTRAINT scan_jobs_scan_type_check 
CHECK (scan_type IN ('dns', 'whois', 'subdomain', 'cert_trans', 'asn', 'all', 'port', 'ssl', 'ip', 'tech'));

-- 2. IP Records
CREATE TABLE IF NOT EXISTS ip_records (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_job_id UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    ip_address VARCHAR(50) NOT NULL,
    geolocation JSONB,
    asn JSONB,
    reverse_dns TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ip_records_asset_id ON ip_records(asset_id);
CREATE INDEX IF NOT EXISTS idx_ip_records_scan_job_id ON ip_records(scan_job_id);

-- 3. SSL Records
CREATE TABLE IF NOT EXISTS ssl_records (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_job_id UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    certificate JSONB,
    connection JSONB,
    grade VARCHAR(10),
    issues JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ssl_records_asset_id ON ssl_records(asset_id);
CREATE INDEX IF NOT EXISTS idx_ssl_records_scan_job_id ON ssl_records(scan_job_id);

-- 4. Tech Records
CREATE TABLE IF NOT EXISTS tech_records (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_job_id UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    technologies JSONB,
    headers JSONB,
    meta_tags JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tech_records_asset_id ON tech_records(asset_id);
CREATE INDEX IF NOT EXISTS idx_tech_records_scan_job_id ON tech_records(scan_job_id);

-- 5. Cert Trans Records
CREATE TABLE IF NOT EXISTS cert_trans_records (
    id UUID PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_job_id UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    issuer_name TEXT,
    not_before TIMESTAMP,
    not_after TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cert_trans_records_asset_id ON cert_trans_records(asset_id);
CREATE INDEX IF NOT EXISTS idx_cert_trans_records_scan_job_id ON cert_trans_records(scan_job_id);
