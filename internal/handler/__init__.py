# =============================================================================
# Package: internal.handler
# =============================================================================
# Layer: Presentation Layer (lớp ngoài cùng của Clean Architecture)
#
# Chứa HTTP handlers (FastAPI routes) — chịu trách nhiệm:
#   - Nhận và parse HTTP request
#   - Gọi service layer xử lý business logic
#   - Chuyển kết quả thành HTTP response (JSON + status code)
# =============================================================================
