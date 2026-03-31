# conftest.py — File này PHẢI tồn tại ở thư mục gốc dự án.
#
# Tại sao cần file này?
# Khi pytest tìm thấy conftest.py ở thư mục nào, nó tự động thêm
# thư mục đó vào sys.path (danh sách nơi Python tìm kiếm package).
#
# Không có file này:
#   pytest chạy → tìm `import internal` → không thấy → ModuleNotFoundError
#
# Có file này:
#   pytest chạy → thấy conftest.py ở /homeworks/ → thêm /homeworks/ vào sys.path
#   → tìm `import internal` → thấy thư mục /homeworks/internal/ → OK!
#
# File này không cần có code gì — chỉ cần TỒN TẠI là đủ.
