# =============================================================================
# Package: internal.service
# =============================================================================
# Layer: Use Case Layer (Business Logic)
#
# Chứa business logic — chịu trách nhiệm:
#   - Validate dữ liệu theo business rules
#   - Tạo giá trị mặc định (UUID, timestamp, status)
#   - Điều phối (orchestrate) giữa các layer khác
#   - KHÔNG biết gì về HTTP hay database cụ thể
# =============================================================================
