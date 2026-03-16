Xin chào! Tôi đang có một dự án Python (FastAPI + PostgreSQL) tên là Mini ASM (quản lý Attack Surface) vừa hoàn thành các tính năng của Session 4 (CRUD cơ bản, Pagination, Sorting, Validation layer, In-memory/Postgres gộp chung qua struct QueryParams). 

Hiện tại, tôi muốn bạn giúp tôi **tích hợp các tính năng của Session 5 (EASM - External Attack Surface Management)** từ bộ code mẫu viết bằng Go sang dự án Python của tôi một cách mượt mà nhất, tuân thủ chặt chẽ Clean Architecture.

### Mục tiêu tích hợp Session 5:
1. **Thiết kế Database Schema (Migrations):**
   - Giữ nguyên bảng `assets` hiện có.
   - Thêm bảng `scan_jobs` để lưu lịch sử quét (asset_id, scan_type, status: pending/running/completed/failed).
   - Thêm 3 bảng lưu kết quả quét: `dns_records`, `whois_records`, `subdomains` (Tất cả đều link khóa ngoại với `scan_jobs` và `assets`). Cần thiết kế Data Models (Pydantic & SQLAlchemy/Raw SQL tuỳ bạn) tương ứng.

2. **Cơ chế Async Job Pattern (Background Tasks):**
   - Xây dựng luồng quét bất đồng bộ (Background processing). Khi gọi API `POST /assets/{id}/scan`, API phải trả về `202 Accepted` kèm theo Job ID ngay lập tức.
   - Process quét sẽ chạy ngầm bằng tính năng `BackgroundTasks` của FastAPI (tương tự như Goroutine bên Go).
   - Có cơ chế đánh dấu trạng thái Job (`running` -> `completed` / `failed`).

3. **Scanner Framework (Tầng Scanner mới):**
   - Viết các file Scanner riêng biệt nằm trong package `internal/scanner/`.
   - **`dns_scanner.py`**: Dùng thư viện `dnspython` để query các record A, AAAA, MX, NS, TXT, CNAME.
   - **`whois_scanner.py`**: Dùng thư viện `whois` (hoặc python-whois) để lấy Registrar, Expiration Date, Name Servers.
   - **`subdomain_scanner.py`**: Mô phỏng DNS Bruteforce (Dùng thư viện `aiohttp` / `asyncio` để chạy concurrency cao, tạo worker pool quét mượt mà danh sách từ điển nhỏ).

4. **Service & Handler (Cập nhật APIs):**
   - Tạo `ScanService` (`internal/service/scan_service.py`) quản lý việc orchestrate (điều phối) các scanner.
   - Thêm các endpoint vào `scan_handler.py`: 
     - `POST /assets/{id}/scan` (Bắt đầu quét)
     - `GET /scan-jobs/{id}` (Xem luồng trạng thái)
     - `GET /scan-jobs/{id}/results` (Kết quả một job nọ)
     - `GET /assets/{id}/results` (Lấy TOÀN BỘ kết quả gộp lại của 1 Asset - DNS + WHOIS + Subdomain)

### Yêu cầu khi sinh code:
1. **Tương thích hoàn toàn:** Code sinh ra phải ráp khít vào Project Python hiện tại (Không làm hỏng [asset_validator.py](file:///home/giangne/Documents/CMC/homeworks/internal/validator/asset_validator.py), [storage.py](file:///home/giangne/Documents/CMC/homeworks/internal/storage/storage.py) QueryParams đã tốn công làm ở Session 4).
2. **Comment tiếng Việt siêu chi tiết:** Tương tự như session trước, hãy comment giải thích cực kì cặn kẽ (so sánh với logic Go tương ứng nếu có) ở mọi class, mọi hàm, mọi đoạn thuật toán concurrency để giúp tôi học.
3. **Thứ tự thực hiện:** Bạn hãy làm theo trừng bước: 
   - Kế hoạch (Implementation Plan) -> 
   - Viết / Sửa Code -> 
   - Kiểm thử & Update README.

Bạn đã hiểu yêu cầu chưa, hãy lên cho tôi một cái **Implementation Plan** để tôi chốt trước nhé!
