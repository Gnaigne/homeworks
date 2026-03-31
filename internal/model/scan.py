"""
=============================================================================
File: internal/model/scan.py
Layer: Entity Layer (Clean Architecture)
Tác dụng: Định nghĩa cấu trúc dữ liệu cho EASM (ScanJobs, DNS, Whois, Subdomain).
=============================================================================
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


# =============================================================================
# ENUMS
# =============================================================================
class ScanCategory(str, Enum):
    """Trạng thái quét Thụ Động hay Chủ Động."""
    PASSIVE = "passive"
    ACTIVE = "active"

class ScanType(str, Enum):
    """Loại quét được hỗ trợ trong hệ thống."""
    # Passive Scans
    DNS = "dns"
    WHOIS = "whois"
    SUBDOMAIN = "subdomain"
    CERT_TRANS = "cert_trans"
    ASN = "asn"
    IP = "ip"
    TECH = "tech"
    
    # Active Scans
    PORT = "port" 
    SSL = "ssl"
    
    # Special
    ALL = "all"
    
    def category(self) -> ScanCategory:
        if self in {ScanType.PORT, ScanType.SSL}:
            return ScanCategory.ACTIVE
        return ScanCategory.PASSIVE
        
    def requires_permission(self) -> bool:
        return self.category() == ScanCategory.ACTIVE

class ScanStatus(str, Enum):
    """Trạng thái của một tiến trình quét."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# =============================================================================
# SCAN JOB MODELS
# =============================================================================

class ScanJob(BaseModel):
    """
    Model ghi lại lịch sử và trạng thái của một lần quét.
    """
    id: str
    asset_id: str
    scan_type: ScanType
    status: ScanStatus
    error: Optional[str] = None
    results: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "111e8400-e29b-41d4-a716-446655440000",
                "asset_id": "550e8400-e29b-41d4-a716-446655440000",
                "scan_type": "all",
                "status": "completed",
                "created_at": "2026-03-10T10:00:00Z",
                "updated_at": "2026-03-10T10:05:00Z",
            }
        },
    }

class CreateScanJobRequest(BaseModel):
    """
    Request body cho POST /assets/{id}/scan.
    Chỉ cần cung cấp loại scan muốn thực hiện.
    """
    scan_type: ScanType

    model_config = {
        "json_schema_extra": {
            "example": {
                "scan_type": "all",
            }
        },
    }


# =============================================================================
# SCAN RESULT MODELS
# =============================================================================

class DNSRecord(BaseModel):
    """Kết quả quét DNS."""
    id: str
    asset_id: str
    scan_job_id: str
    record_type: str
    name: str = "" # Thêm trường Name 
    value: str
    ttl: int = 0   # Thêm trường TTL
    created_at: datetime

    model_config = {"from_attributes": True}

class CreateDNSRecordRequest(BaseModel):
    """Payload từ scanner để lưu DNS."""
    record_type: str
    name: str = ""
    value: str
    ttl: int = 0


class WhoisRecord(BaseModel):
    """Kết quả quét WHOIS."""
    id: str
    asset_id: str
    scan_job_id: str
    domain: str
    registrar: Optional[str] = None
    creation_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    name_servers: Optional[str] = None # JSON Array
    status: Optional[str] = None       # Thêm Status
    emails: Optional[str] = None       # Thêm Emails (JSON Array)
    raw_data: Optional[str] = None     # Thêm vỏ bọc Raw_Data
    created_at: datetime

    model_config = {"from_attributes": True}

class CreateWhoisRecordRequest(BaseModel):
    """Payload từ scanner để lưu WHOIS."""
    domain: str
    registrar: Optional[str] = None
    creation_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    name_servers: Optional[str] = None
    status: Optional[str] = None
    emails: Optional[str] = None
    raw_data: Optional[str] = None


class SubdomainRecord(BaseModel):
    """Kết quả quét Subdomain."""
    id: str
    asset_id: str
    scan_job_id: str
    subdomain: str
    source: str = "dns_bruteforce"     # Thêm Source 
    is_active: bool = True             # Thêm trạng thái Active
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class CreateSubdomainRecordRequest(BaseModel):
    """Payload từ scanner để lưu Subdomain."""
    subdomain: str
    source: str = "dns_bruteforce"
    is_active: bool = True
    ip_address: Optional[str] = None


class PortScanRecord(BaseModel):
    """Kết quả quét một cổng mạng (Port)."""
    id: str
    asset_id: str
    scan_job_id: str
    port: int
    state: str       # "open", "closed", "filtered"
    service: str     # "ssh", "http", "unknown"
    version: str     # "OpenSSH 8.2", "nginx" ...
    banner: str      # Raw text trả về ban đầu
    response_time_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}

class CreatePortScanRecordRequest(BaseModel):
    """Payload từ scanner gửi về để insert Port Record."""
    port: int
    state: str
    service: str
    version: str = ""
    banner: str = ""
    response_time_ms: int = 0


class IPRecord(BaseModel):
    """Kết quả quét IP (Geolocation & ASN)."""
    id: str
    asset_id: str
    scan_job_id: str
    ip_address: str
    geolocation: Optional[dict] = None
    asn: Optional[dict] = None
    reverse_dns: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}

class CreateIPRecordRequest(BaseModel):
    """Payload từ scanner gửi về để insert IP Record."""
    ip_address: str
    geolocation: Optional[dict] = None
    asn: Optional[dict] = None
    reverse_dns: str = ""


class SSLRecord(BaseModel):
    """Kết quả quét SSL/TLS."""
    id: str
    asset_id: str
    scan_job_id: str
    domain: str
    certificate: Optional[dict] = None
    connection: Optional[dict] = None
    grade: str = ""
    issues: List[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}

class CreateSSLRecordRequest(BaseModel):
    """Payload từ scanner gửi về để insert SSL Record."""
    domain: str
    certificate: Optional[dict] = None
    connection: Optional[dict] = None
    grade: str = ""
    issues: List[str] = []


class TechRecord(BaseModel):
    """Kết quả quét Technology."""
    id: str
    asset_id: str
    scan_job_id: str
    domain: str
    technologies: List[dict] = []
    headers: Optional[dict] = None
    meta_tags: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class CreateTechRecordRequest(BaseModel):
    """Payload từ scanner gửi về để insert Tech Record."""
    domain: str
    technologies: List[dict] = []
    headers: Optional[dict] = None
    meta_tags: Optional[dict] = None


class CertTransRecord(BaseModel):
    """Kết quả quét Certificate Transparency."""
    id: str
    asset_id: str
    scan_job_id: str
    domain: str
    issuer_name: str
    not_before: Optional[datetime] = None
    not_after: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class CreateCertTransRecordRequest(BaseModel):
    """Payload từ scanner gửi về để insert Cert Trans Record."""
    domain: str
    issuer_name: str
    not_before: Optional[datetime] = None
    not_after: Optional[datetime] = None


# =============================================================================
# AGGREGATED RESPONSE (Cho API GET /assets/{id}/results)
# =============================================================================

class AssetScanResultsResponse(BaseModel):
    """Tổng hợp toàn bộ kết quả quét của một asset."""
    asset_id: str
    dns_records: List[DNSRecord] = []
    whois_records: List[WhoisRecord] = []
    subdomains: List[SubdomainRecord] = []
    port_records: List[PortScanRecord] = []
    ip_records: List[IPRecord] = []
    ssl_records: List[SSLRecord] = []
    tech_records: List[TechRecord] = []
    cert_trans_records: List[CertTransRecord] = []

    model_config = {"from_attributes": True}
