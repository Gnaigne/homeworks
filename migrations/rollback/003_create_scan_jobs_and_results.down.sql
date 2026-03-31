-- =============================================================================
-- Migration DOWN: Xóa các bảng EASM
-- Version: 003
-- Tác dụng: Rollback tạo bảng scan_jobs và kết quả.
-- =============================================================================

DROP TABLE IF EXISTS subdomains;
DROP TABLE IF EXISTS whois_records;
DROP TABLE IF EXISTS dns_records;
DROP TABLE IF EXISTS scan_jobs;
