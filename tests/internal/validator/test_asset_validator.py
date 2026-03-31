import pytest
from internal.validator.asset_validator import AssetValidator
from internal.model.errors import InvalidInputError

# Khởi tạo instance Validator dùng chung cho các test case
@pytest.fixture
def validator():
    return AssetValidator()

# =============================================================================
# 1. TEST NAME VALIDATION (Trống, độ dài, Null bytes)
# =============================================================================
@pytest.mark.parametrize("valid_name", [
    "example.com",
    "192.168.1.1",
    "a" * 255, # Tối đa cho phép
])
def test_validate_name_valid(validator, valid_name):
    """Kiểm tra Name hợp lệ không quăng lỗi."""
    validator.validate_name(valid_name) # Không báo Exception là Pass

@pytest.mark.parametrize("invalid_name, expected_err", [
    ("", "name is required"),
    ("   ", "name is required"),
    (None, "name is required"),
    ("a" * 256, "name too long"),
    ("hacked\x00.com", "name contains invalid characters"), # Lỗ hổng Null Byte
])
def test_validate_name_invalid(validator, invalid_name, expected_err):
    """Kiểm tra Name sai chuẩn sẽ văng lỗi InvalidInputError."""
    with pytest.raises(InvalidInputError) as exc:
        validator.validate_name(invalid_name)
    assert expected_err in str(exc.value)

# =============================================================================
# 2. TEST DOMAIN VALIDATION (Format Regex RFC 1035)
# =============================================================================
@pytest.mark.parametrize("valid_domain", [
    "example.com",
    "sub.example.com",
    "my-domain-123.net",
    "a.com",
])
def test_validate_domain_valid(validator, valid_domain):
    validator.validate_domain(valid_domain)

@pytest.mark.parametrize("invalid_domain, expected_err", [
    ("", "domain length must be between 1 and 253"),
    ("a" * 254, "domain length must be between 1 and 253"),
    ("invalid..com", "invalid domain format"), # Sai regex
    ("ex ample.com", "invalid domain format"),
    (".example.com", "invalid domain format"), # Regex chặn trước khi tới hàm kiểm tra dấu chấm
    ("example.com.", "invalid domain format"),
    ("-example.com", "invalid domain format"),
    ("example.com-", "invalid domain format"),
])
def test_validate_domain_invalid(validator, invalid_domain, expected_err):
    with pytest.raises(InvalidInputError) as exc:
        validator.validate_domain(invalid_domain)
    assert expected_err in str(exc.value)

# =============================================================================
# 2.5 TEST TYPE & STATUS VALIDATION
# =============================================================================
def test_validate_type(validator):
    validator.validate_type("domain")
    with pytest.raises(InvalidInputError, match="invalid asset type"):
        validator.validate_type("invalid_type")

def test_validate_status(validator):
    validator.validate_status("active")
    with pytest.raises(InvalidInputError, match="invalid status"):
        validator.validate_status("invalid_status")

# =============================================================================
# 3. TEST IP VALIDATION (IPv4 & IPv6 format)
# =============================================================================
@pytest.mark.parametrize("valid_ip", [
    "192.168.1.1",
    "10.0.0.1",
    "2001:db8::1",
    "fe80::1",
    "0.0.0.0",
])
def test_validate_ip_valid(validator, valid_ip):
    validator.validate_ip(valid_ip)

@pytest.mark.parametrize("invalid_ip", [
    "999.999.999.999",
    "not-an-ip",
    "192.168",
    "2001:db8:::1",
    "",
])
def test_validate_ip_invalid(validator, invalid_ip):
    with pytest.raises(InvalidInputError) as exc:
        validator.validate_ip(invalid_ip)
    assert "invalid IP address format" in str(exc.value)

# =============================================================================
# 4. TEST SERVICE VALIDATION (URL hoặc giao thức)
# =============================================================================
@pytest.mark.parametrize("valid_service", [
    "http://example.com",
    "https://example.com:443",
    "ssh",
    "ftp",
    "https-443",
    "http://example.com/api/v1",
])
def test_validate_service_valid(validator, valid_service):
    validator.validate_service(valid_service)

@pytest.mark.parametrize("invalid_service", [
    "invalid service!!!", 
    "service with spaces",
    "",
])
def test_validate_service_invalid(validator, invalid_service):
    with pytest.raises(InvalidInputError):
        validator.validate_service(invalid_service)

# =============================================================================
# 5. TEST SQL INJECTION PREVENTION (Pagination / Sort / Search)
# =============================================================================
@pytest.mark.parametrize("sort_by, sort_order", [
    ("name", "asc"),
    ("status", "desc"),
    ("created_at", "asc"),
    ("", "desc"),
])
def test_validate_sort_params_valid(validator, sort_by, sort_order):
    validator.validate_sort_params(sort_by, sort_order)

@pytest.mark.parametrize("sort_by, sort_order", [
    ("injected_column", "asc"), # Không nằm trong Whitelist
    ("; DROP TABLE assets", "asc"), # Hacker inject
    ("name", "ascending"), # Sai chữ asc/desc
])
def test_validate_sort_params_invalid(validator, sort_by, sort_order):
    with pytest.raises(InvalidInputError):
        validator.validate_sort_params(sort_by, sort_order)

@pytest.mark.parametrize("hacked_query", [
    "test'; DROP TABLE assets;--",
    "admin /*",
    'name="admin"',
    "xp_cmdshell",
])
def test_validate_search_query_sqli(validator, hacked_query):
    """Đảm bảo các mẫu chữ nguy hiểm (Dangerous Patterns) bị chặn đứng."""
    with pytest.raises(InvalidInputError) as exc:
        validator.validate_search_query(hacked_query)
    assert "search query contains invalid characters" in str(exc.value)

def test_validate_pagination_invalid(validator):
    with pytest.raises(InvalidInputError, match="page must be >= 1"):
        validator.validate_pagination_params(0, 10)
    with pytest.raises(InvalidInputError, match="page_size must be >= 1"):
        validator.validate_pagination_params(1, 0)
    with pytest.raises(InvalidInputError, match="page_size too large"):
        validator.validate_pagination_params(1, 101)

# =============================================================================
# 6. TEST COMPOUND VALIDATORS (CREATE & UPDATE)
# =============================================================================
def test_validate_create(validator):
    validator.validate_create("example.com", "domain")
    validator.validate_create("1.1.1.1", "ip")
    validator.validate_create("ssh", "service")

def test_validate_update(validator):
    validator.validate_update("example.com", "domain", "active")
    validator.validate_update("1.1.1.1", "ip", "inactive")
    validator.validate_update("ssh", "service", None)
    validator.validate_update(None, None, None)
