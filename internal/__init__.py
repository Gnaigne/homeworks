# =============================================================================
# Package: internal
# =============================================================================
# Thư mục internal/ chứa toàn bộ logic nội bộ của ứng dụng.
#
# Trong Go, "internal/" là convention đặc biệt — code bên trong không thể
# import từ bên ngoài module. Python không bắt buộc nhưng ta giữ convention
# này để tách biệt code nội bộ và giữ cấu trúc Clean Architecture rõ ràng.
#
# Các sub-package:
#   - model/    → Định nghĩa data models (Entity Layer)
#   - handler/  → Xử lý HTTP request/response (Presentation Layer)
#   - service/  → Business logic (Use Case Layer)
#   - storage/  → Data access - memory, DB (Infrastructure Layer)
