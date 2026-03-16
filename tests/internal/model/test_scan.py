"""
=============================================================================
File: tests/internal/model/test_scan.py
Bài 2.1: Model Tests — Kiểm thử toàn bộ Enum và Model của Scan Layer
=============================================================================
"""
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from internal.model.scan import (
    ScanType, ScanCategory, ScanStatus, CreateScanJobRequest,
    IPRecord, SSLRecord, TechRecord, CertTransRecord,
    CreateIPRecordRequest, CreateSSLRecordRequest,
    CreateTechRecordRequest, CreateCertTransRecordRequest,
)


# =============================================================================
# 1. SCANTYPE ENUM — Phân loại Active / Passive (bao gồm tất cả types cũ và mới)
# =============================================================================

@pytest.mark.parametrize("scan_type, expected_category", [
    # 🎓 TEACHING NOTES: Edge Case Testing — liệt kê ĐỦ MỌI TRƯỜNG HỢP để đạt coverage 100%
    # Passive Scans (chỉ đọc, không gõ cửa server)
    (ScanType.DNS,        ScanCategory.PASSIVE),
    (ScanType.WHOIS,      ScanCategory.PASSIVE),
    (ScanType.SUBDOMAIN,  ScanCategory.PASSIVE),
    (ScanType.CERT_TRANS, ScanCategory.PASSIVE),
    (ScanType.ASN,        ScanCategory.PASSIVE),
    (ScanType.IP,         ScanCategory.PASSIVE),   # ← Scan mới Session 7
    (ScanType.TECH,       ScanCategory.PASSIVE),   # ← Scan mới Session 7
    (ScanType.ALL,        ScanCategory.PASSIVE),   # ALL dùng pipeline passive

    # Active Scans (chủ động kết nối tới server đích)
    (ScanType.PORT,       ScanCategory.ACTIVE),
    (ScanType.SSL,        ScanCategory.ACTIVE),    # ← Scan mới Session 7 (xếp Active)
])
def test_scan_type_category(scan_type, expected_category):
    """Kiểm tra phân loại Active/Passive chính xác cho TẤT CẢ scan types."""
    assert scan_type.category() == expected_category


@pytest.mark.parametrize("scan_type, requires_perm", [
    (ScanType.DNS,        False),
    (ScanType.WHOIS,      False),
    (ScanType.SUBDOMAIN,  False),
    (ScanType.CERT_TRANS, False),
    (ScanType.ASN,        False),
    (ScanType.IP,         False),   # Passive → không cần permission
    (ScanType.TECH,       False),   # Passive → không cần permission
    (ScanType.PORT,       True),    # Active → yêu cầu permission (gõ cửa port thật)
    (ScanType.SSL,        True),    # Active → yêu cầu permission (kết nối TLS thật)
])
def test_scan_type_requires_permission(scan_type, requires_perm):
    """IP và TECH là passive nên không cần permission. PORT và SSL là active."""
    assert scan_type.requires_permission() == requires_perm


@pytest.mark.parametrize("valid_type_str", [
    "dns", "whois", "subdomain", "cert_trans",
    "asn", "ip", "tech", "port", "ssl", "all"
])
def test_scan_type_from_string(valid_type_str):
    """ScanType có thể khởi tạo từ chuỗi lowercase (dùng khi parse JSON request)."""
    st = ScanType(valid_type_str)
    assert st.value == valid_type_str


# =============================================================================
# 2. VALIDATION — Pydantic reject scan type không hợp lệ
# =============================================================================

@pytest.mark.parametrize("invalid_scan_type", [
    "nmap",    # Tool quét ngoài luồng
    "nikto",   # Tool quét ngoài luồng
    "sqlmap",  # Tool injection
    "",        # Rỗng
    "DNS",     # Phân biệt hoa/thường
])
def test_invalid_scan_type_raises(invalid_scan_type):
    """CreateScanJobRequest phải reject enum không hợp lệ bằng ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        CreateScanJobRequest(scan_type=invalid_scan_type)
    assert "scan_type" in str(exc_info.value)


# =============================================================================
# 3. SCANSTATUS ENUM
# =============================================================================

@pytest.mark.parametrize("status_val", [
    "pending", "running", "completed", "failed", "partial"
])
def test_scan_status_valid(status_val):
    """ScanStatus khớp với chuỗi trạng thái lưu trong Database."""
    assert ScanStatus(status_val).value == status_val


# =============================================================================
# 4. CREATE REQUEST MODELS (DTO từ Scanner gửi lên Service)
# =============================================================================

def test_create_ip_record_request_valid():
    """IPRecord Request chấp nhận đủ trường geo và asn."""
    req = CreateIPRecordRequest(
        ip_address="1.1.1.1",
        geolocation={"country": "US", "city": "Ashburn", "latitude": 38.0, "longitude": -77.0,
                     "isp": "Cloudflare", "org": "CF", "country_code": "US", "region": "VA"},
        asn={"number": 13335, "name": "CLOUDFLARENET", "description": "AS13335"},
        reverse_dns="one.one.one.one"
    )
    assert req.ip_address == "1.1.1.1"
    assert req.asn["number"] == 13335
    assert req.geolocation["country"] == "US"


def test_create_ip_record_request_minimal():
    """CreateIPRecordRequest chỉ cần ip_address (các trường còn lại có default)."""
    req = CreateIPRecordRequest(ip_address="8.8.8.8")
    assert req.ip_address == "8.8.8.8"
    assert req.geolocation is None
    assert req.asn is None
    assert req.reverse_dns == ""


def test_create_ssl_record_request_valid():
    """SSL Record chứa domain, cert info và connection info."""
    req = CreateSSLRecordRequest(
        domain="example.com",
        certificate={"subject": "CN=example.com", "issuer": "Let's Encrypt", "is_expired": False, "san": ["example.com"]},
        connection={"tls_version": "TLSv1.3", "cipher_suite": "TLS_AES_256_GCM_SHA384"},
        grade="A",
        issues=[]
    )
    assert req.domain == "example.com"
    assert req.grade == "A"
    assert req.certificate["is_expired"] is False


def test_create_ssl_record_request_with_issues():
    """SSL Record ghi nhận lỗi khi cert hết hạn."""
    req = CreateSSLRecordRequest(
        domain="expired.com",
        grade="F",
        issues=["Certificate is expired.", "Certificate is self-signed."]
    )
    assert len(req.issues) == 2
    assert "expired" in req.issues[0]


def test_create_tech_record_request_valid():
    """Tech Record lưu technologies, headers và meta_tags chính xác."""
    req = CreateTechRecordRequest(
        domain="google.com",
        technologies=[{"name": "nginx", "category": "Web Server", "version": "1.18.0", "confidence": 100}],
        headers={"server": "gws", "content-type": "text/html"},
        meta_tags={"generator": "WordPress"}
    )
    assert req.domain == "google.com"
    assert req.technologies[0]["name"] == "nginx"
    assert req.headers["server"] == "gws"


def test_create_cert_trans_record_request_valid():
    """CertTrans Record lưu domain và thông tin issuer từ CT logs."""
    req = CreateCertTransRecordRequest(
        domain="example.com",
        issuer_name="C=US, O=Let's Encrypt, CN=R3",
        not_before="2026-01-01T00:00:00",
        not_after="2026-04-01T00:00:00"
    )
    assert req.domain == "example.com"
    assert "Let's Encrypt" in req.issuer_name


# =============================================================================
# 5. DOMAIN MODELS (DB Entity — chứa thêm id, asset_id, scan_job_id, created_at)
# =============================================================================

def test_ip_record_model_from_dict():
    """IPRecord model chuyển đổi đúng từ dict (dùng khi map từ DB row)."""
    now = datetime.now(timezone.utc)
    record = IPRecord(
        id="uuid-001", asset_id="asset-001", scan_job_id="job-001",
        ip_address="1.1.1.1",
        geolocation={"country": "US"},
        asn={"number": 13335, "name": "CLOUDFLARENET"},
        reverse_dns="one.one.one.one",
        created_at=now
    )
    assert record.ip_address == "1.1.1.1"
    assert record.asn["name"] == "CLOUDFLARENET"


def test_ssl_record_model_expired_cert():
    """SSLRecord với cert hết hạn có grade F và issues không rỗng."""
    now = datetime.now(timezone.utc)
    record = SSLRecord(
        id="uuid-002", asset_id="asset-002", scan_job_id="job-002",
        domain="old.example.com",
        certificate={"is_expired": True, "days_until_expiry": -10},
        connection={},
        grade="F",
        issues=["Certificate is expired."],
        created_at=now
    )
    assert record.grade == "F"
    assert record.certificate["is_expired"] is True
    assert len(record.issues) == 1


def test_tech_record_model_empty_meta():
    """TechRecord cho phép meta_tags rỗng (không phải mọi trang đều có meta tags)."""
    now = datetime.now(timezone.utc)
    record = TechRecord(
        id="uuid-003", asset_id="asset-003", scan_job_id="job-003",
        domain="minimal.com",
        technologies=[],
        headers={"server": "Apache"},
        meta_tags={},
        created_at=now
    )
    assert record.meta_tags == {}
    assert record.technologies == []


def test_cert_trans_record_model():
    """CertTransRecord lưu đúng trường từ crt.sh."""
    now = datetime.now(timezone.utc)
    record = CertTransRecord(
        id="uuid-004", asset_id="asset-004", scan_job_id="job-004",
        domain="sub1.example.com\nsub2.example.com",
        issuer_name="C=US, O=DigiCert",
        not_before="2025-01-01T00:00:00",
        not_after="2026-01-01T00:00:00",
        created_at=now
    )
    assert "sub1" in record.domain
    assert "DigiCert" in record.issuer_name
