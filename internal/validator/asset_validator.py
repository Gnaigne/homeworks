"""
=============================================================================
File: internal/validator/asset_validator.py
Layer: Validation Layer (Clean Architecture)
Tác dụng: Validate input cho tất cả asset operations (create, update, query).
=============================================================================

Session 4 Enhancement — Tách validation logic ra module riêng.

Trước đây (Session 3): Validate trực tiếp trong service layer.
Bây giờ (Session 4): Validator package riêng → tái sử dụng, dễ test, single responsibility.

Tương đương Go: internal/validator/asset_validator.go
    type AssetValidator struct{}
    func (v *AssetValidator) ValidateCreate(name, assetType string) error

Chức năng validation:
    1. Name validation: trống, quá dài, null byte
    2. Type-specific format validation:
       - Domain: RFC 1035 regex (ví dụ: example.com ✓, invalid..com ✗)
       - IP: IPv4/IPv6 parsing (ví dụ: 192.168.1.1 ✓, 999.999.999.999 ✗)
       - Service: URL/protocol format (ví dụ: http://example.com ✓, ssh ✓)
    3. Sort params: whitelist fields (chống SQL injection)
    4. Search query: length + SQL injection pattern detection
    5. Pagination: range check (page >= 1, page_size <= 100)

Security:
    - Null byte injection prevention
    - SQL injection pattern detection trong search
    - Whitelist approach cho sort fields
    - Length limits trên tất cả inputs
"""

import re
import ipaddress
from typing import List

from internal.model.asset import AssetType, AssetStatus
from internal.model.errors import InvalidInputError


class AssetValidator:
    """
    Validator cho tất cả asset operations.

    Tương đương Go struct:
        type AssetValidator struct{}

    Tách riêng ra module để:
        - Single Responsibility: chỉ làm validation
        - Reusable: service, handler, test đều dùng được
        - Dễ test: test validator riêng, không cần mock storage
    """

    # =========================================================================
    # WHITELIST — Danh sách trường được phép sort
    # =========================================================================

    # Tương đương Go: validSortFields := map[string]bool{...}
    # QUAN TRỌNG: Whitelist chống SQL injection — chỉ cho phép sort theo các cột này
    VALID_SORT_FIELDS = {"name", "type", "status", "created_at", "updated_at"}

    # Regex cho domain name theo RFC 1035
    # Tương đương Go: domainRegex := regexp.MustCompile(`^([a-zA-Z0-9]...)$`)
    # Giải thích từng phần:
    #   ^                     — bắt đầu chuỗi
    #   [a-zA-Z0-9]          — ký tự đầu tiên phải là chữ/số (không cho phép - hoặc .)
    #   ([a-zA-Z0-9\-]{0,61} — tiếp theo tối đa 61 ký tự chữ/số/dấu gạch ngang
    #   [a-zA-Z0-9])?        — ký tự cuối của label phải là chữ/số
    #   (\....)*              — có thể có nhiều labels phân tách bằng dấu chấm
    #   $                     — kết thúc chuỗi
    _DOMAIN_REGEX = re.compile(
        r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*"
        r"[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$"
    )

    # Regex cho service name — cho phép URL hoặc tên service đơn giản
    # Tương đương Go: serviceRegex := regexp.MustCompile(`^([a-zA-Z0-9\-]+)(://...)`)
    # Cho phép: http://example.com, https://example.com:443, ssh, ftp, https-443
    # Dấu +: 1 ký tự trở lên
    # Dấu ?: 0 hoặc 1 lần
    _SERVICE_REGEX = re.compile(
        r"^([a-zA-Z0-9\-]+)(://[a-zA-Z0-9\-\.]+)?(:[0-9]+)?(/.*)?$"
    )

    # Patterns nguy hiểm trong search query — defense in depth
    # Tương đương Go: dangerousPatterns := []string{"'", "\"", ";", "--", ...}
    # Dù đã dùng parameterized query, vẫn check thêm cho chắc chắn
    _DANGEROUS_PATTERNS = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]

    # =========================================================================
    # CREATE / UPDATE VALIDATION
    # =========================================================================

    def validate_create(self, name: str, asset_type: str) -> None:
        """
        Validate toàn bộ request tạo asset mới.

        Tương đương Go:
            func (v *AssetValidator) ValidateCreate(name, assetType string) error

        Flow:
            1. Validate name (trống, dài, null byte)
            2. Validate type (phải là domain/ip/service)
            3. Validate format theo type (domain regex, IP parsing, service regex)

        Args:
            name: Tên asset
            asset_type: Loại asset ("domain", "ip", "service")

        Raises:
            InvalidInputError: Nếu input không hợp lệ (kèm message cụ thể)
        """
        # Validate name cơ bản
        self.validate_name(name)

        # Validate type là enum hợp lệ
        self.validate_type(asset_type)

        # Validate format cụ thể theo type
        # Tương đương Go: switch assetType { case model.TypeDomain: ... }
        if asset_type == AssetType.DOMAIN.value:
            self.validate_domain(name)
        elif asset_type == AssetType.IP.value:
            self.validate_ip(name)
        elif asset_type == AssetType.SERVICE.value:
            self.validate_service(name)

    def validate_update(self, name: str, asset_type: str, status: str) -> None:
        """
        Validate request cập nhật asset (partial update).

        Tương đương Go:
            func (v *AssetValidator) ValidateUpdate(name, assetType, status string) error

        Khác validate_create: chỉ validate field nào được cung cấp (không trống).

        Args:
            name: Tên mới (có thể trống = không đổi)
            asset_type: Type mới (có thể trống = không đổi)
            status: Status mới (có thể trống = không đổi)
        """
        # Validate name nếu được cung cấp
        if name:
            self.validate_name(name)

            # Validate format theo type nếu biết type
            if asset_type:
                if asset_type == AssetType.DOMAIN.value:
                    self.validate_domain(name)
                elif asset_type == AssetType.IP.value:
                    self.validate_ip(name)
                elif asset_type == AssetType.SERVICE.value:
                    self.validate_service(name)

        # Validate type nếu được cung cấp
        if asset_type:
            self.validate_type(asset_type)

        # Validate status nếu được cung cấp
        if status:
            self.validate_status(status)

    # =========================================================================
    # FIELD VALIDATION — Từng trường riêng lẻ
    # =========================================================================

    def validate_name(self, name: str) -> None:
        """
        Validate tên asset: không trống, không quá dài, không chứa null byte.

        Tương đương Go:
            func (v *AssetValidator) ValidateName(name string) error

        Security: Kiểm tra null byte \\x00 — kỹ thuật injection phổ biến trong C/C++.
            Dù Python ít bị ảnh hưởng, vẫn check cho defense in depth.

        Raises:
            InvalidInputError: Nếu name trống, quá dài, hoặc chứa null byte
        """
        if not name or not name.strip():
            raise InvalidInputError("name is required")

        if len(name) > 255:
            raise InvalidInputError("name too long (max 255 characters)")

        # Check null byte — tương đương Go: strings.Contains(name, "\\x00")
        if "\x00" in name:
            raise InvalidInputError("name contains invalid characters")

    def validate_type(self, asset_type: str) -> None:
        """
        Validate type phải là giá trị enum hợp lệ (domain/ip/service).

        Tương đương Go:
            func (v *AssetValidator) ValidateType(assetType string) error
            → dùng model.IsValidType(assetType)

        Python dùng enum: thử AssetType(value), nếu ValueError → invalid.

        Raises:
            InvalidInputError: Nếu type không phải domain/ip/service
        """
        try:
            AssetType(asset_type)
        except ValueError:
            valid_types = ", ".join(t.value for t in AssetType)
            raise InvalidInputError(
                f"invalid asset type: must be {valid_types}"
            )

    def validate_status(self, status: str) -> None:
        """
        Validate status phải là active hoặc inactive.

        Tương đương Go:
            func (v *AssetValidator) ValidateStatus(status string) error

        Raises:
            InvalidInputError: Nếu status không hợp lệ
        """
        try:
            AssetStatus(status)
        except ValueError:
            valid_statuses = ", ".join(s.value for s in AssetStatus)
            raise InvalidInputError(
                f"invalid status: must be {valid_statuses}"
            )

    # =========================================================================
    # TYPE-SPECIFIC FORMAT VALIDATION — Validate format theo loại asset
    # =========================================================================

    def validate_domain(self, domain: str) -> None:
        """
        Validate domain name theo RFC 1035.

        Tương đương Go:
            func (v *AssetValidator) ValidateDomain(domain string) error
            → dùng regexp.MustCompile cho domain regex

        Python dùng re.compile — tương tự nhưng khác syntax:
            Go:     regexp.MustCompile(`^([a-zA-Z0-9]...)$`)
            Python: re.compile(r"^([a-zA-Z0-9]...)$")

        Ví dụ:
            ✅ "example.com", "sub.example.com", "my-domain-123.net"
            ❌ "invalid..com", "-example.com", "example-.com"

        Raises:
            InvalidInputError: Nếu domain format không hợp lệ
        """
        # Length check — domain max 253 ký tự theo RFC
        if len(domain) < 1 or len(domain) > 253:
            raise InvalidInputError(
                "invalid domain: domain length must be between 1 and 253 characters"
            )

        # Regex match — kiểm tra format
        if not self._DOMAIN_REGEX.match(domain):
            raise InvalidInputError(
                "invalid domain: invalid domain format (e.g., example.com)"
            )

        # Không cho phép bắt đầu/kết thúc bằng dấu chấm
        if domain.startswith(".") or domain.endswith("."):
            raise InvalidInputError(
                "invalid domain: domain cannot start or end with a dot"
            )

        # Không cho phép bắt đầu/kết thúc bằng dấu gạch ngang
        if domain.startswith("-") or domain.endswith("-"):
            raise InvalidInputError(
                "invalid domain: domain cannot start or end with a hyphen"
            )

    def validate_ip(self, ip: str) -> None:
        """
        Validate IP address — hỗ trợ cả IPv4 và IPv6.

        Tương đương Go:
            func (v *AssetValidator) ValidateIP(ip string) error
            → dùng net.ParseIP(ip)

        Python dùng module ipaddress (standard library):
            ipaddress.ip_address("192.168.1.1")  → IPv4Address OK
            ipaddress.ip_address("2001:db8::1")  → IPv6Address OK
            ipaddress.ip_address("invalid")      → ValueError

        Ví dụ:
            ✅ "192.168.1.1", "10.0.0.1", "2001:db8::1", "fe80::1"
            ❌ "999.999.999.999", "not-an-ip", "192.168"

        Raises:
            InvalidInputError: Nếu không phải IP address hợp lệ
        """
        try:
            # ipaddress.ip_address() tự nhận biết IPv4 hoặc IPv6
            # Tương đương Go: net.ParseIP(ip)
            ipaddress.ip_address(ip)
        except ValueError:
            raise InvalidInputError(
                "invalid IP address: invalid IP address format "
                "(e.g., 192.168.1.1 or 2001:db8::1)"
            )

    def validate_service(self, service: str) -> None:
        """
        Validate service name — hỗ trợ URL hoặc tên service đơn giản.

        Tương đương Go:
            func (v *AssetValidator) ValidateService(service string) error

        Cho phép các dạng:
            - URL: http://example.com, https://example.com:443
            - Tên service: ssh, ftp, https-443
            - URL có path: http://example.com/api/v1

        Ví dụ:
            ✅ "http://example.com", "ssh", "ftp", "https-443"
            ❌ "invalid service!!!", "service with spaces"

        Raises:
            InvalidInputError: Nếu format không hợp lệ
        """
        if len(service) < 1:
            raise InvalidInputError("invalid service: service name is required")

        if not self._SERVICE_REGEX.match(service):
            raise InvalidInputError(
                "invalid service: invalid service format "
                "(e.g., http://example.com or ssh)"
            )

    # =========================================================================
    # QUERY VALIDATION — Validate query parameters
    # =========================================================================

    def validate_pagination_params(self, page: int, page_size: int) -> None:
        """
        Validate pagination parameters: page >= 1, page_size trong phạm vi hợp lệ.

        Tương đương Go:
            func (v *AssetValidator) ValidatePaginationParams(page, pageSize int) error

        Raises:
            InvalidInputError: Nếu page < 1 hoặc page_size ngoài phạm vi
        """
        if page < 1:
            raise InvalidInputError("page must be >= 1")

        if page_size < 1:
            raise InvalidInputError("page_size must be >= 1")

        if page_size > 100:
            raise InvalidInputError("page_size too large (max 100)")

    def validate_sort_params(self, sort_by: str, sort_order: str) -> None:
        """
        Validate sort parameters — QUAN TRỌNG cho bảo mật.

        Tương đương Go:
            func (v *AssetValidator) ValidateSortParams(sortBy, sortOrder string) error

        SECURITY: Whitelist approach — chỉ cho phép sort theo các cột đã định sẵn.
        Nếu user truyền sort_by="; DROP TABLE assets" → sẽ bị reject ngay.
        Tương đương Go: validSortFields := map[string]bool{...}

        Go dùng map[string]bool → Python dùng set — cùng tác dụng O(1) lookup.

        Raises:
            InvalidInputError: Nếu sort field không hợp lệ hoặc order sai
        """
        if sort_by and sort_by not in self.VALID_SORT_FIELDS:
            valid_fields = ", ".join(sorted(self.VALID_SORT_FIELDS))
            raise InvalidInputError(
                f"invalid sort field: {sort_by} "
                f"(allowed: {valid_fields})"
            )

        if sort_order and sort_order not in ("asc", "desc"):
            raise InvalidInputError("sort order must be 'asc' or 'desc'")

    def validate_search_query(self, query: str) -> None:
        """
        Validate search query — kiểm tra length + SQL injection patterns.

        Tương đương Go:
            func (v *AssetValidator) ValidateSearchQuery(query string) error

        Defense in depth — dù đã dùng parameterized query (psycopg2 %s),
        vẫn check thêm patterns nguy hiểm trong search input.

        Ví dụ bị reject:
            "test'; DROP TABLE assets;--"  → chứa "'" và ";"
            "test /* comment */"           → chứa "/*" và "*/"

        Raises:
            InvalidInputError: Nếu query quá dài hoặc chứa pattern nguy hiểm
        """
        if len(query) > 255:
            raise InvalidInputError("search query too long (max 255 characters)")

        # Check SQL injection patterns — tương đương Go: dangerousPatterns
        lower_query = query.lower()
        for pattern in self._DANGEROUS_PATTERNS:
            if pattern in lower_query:
                raise InvalidInputError(
                    f"search query contains invalid characters: {pattern}"
                )
