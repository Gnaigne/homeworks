"""
=============================================================================
File: internal/database/retry.py
Layer: Infrastructure — Database Utilities (Clean Architecture)
Tác dụng: Kết nối PostgreSQL với cơ chế retry tự động (tự thử lại khi thất bại).
=============================================================================

[BÀI 4] DATABASE CONNECTION RETRY

Vấn đề thực tế:
    Khi deploy ứng dụng (đặc biệt với Docker), database có thể chưa sẵn sàng
    ngay lập tức. Ví dụ:
        - Docker compose: app container khởi động TRƯỚC khi db container ready
        - Database đang restart sau khi crash
        - Network tạm thời bị gián đoạn

    Công thức: wait_time = 2 ^ (attempt - 1) giây
    Hoặc dùng bit shift: wait_time = 1 << (attempt - 1) giây
        1 << 0 = 1   (dịch bit 1 sang trái 0 lần → 0001 = 1)
        1 << 1 = 2   (dịch bit 1 sang trái 1 lần → 0010 = 2)
        1 << 2 = 4   (dịch bit 1 sang trái 2 lần → 0100 = 4)
        1 << 3 = 8   (dịch bit 1 sang trái 3 lần → 1000 = 8)
        1 << 4 = 16  (dịch bit 1 sang trái 4 lần → 10000 = 16)

    Ưu điểm: Nếu DB cần thời gian khởi động → cho nó thêm thời gian
    thay vì gõ cửa liên tục.

Python version bên dưới dùng:
    - psycopg2.connect() thay cho sql.Open() + db.Ping()
    - time.sleep() thay cho time.Sleep()
    - Exception handling thay cho error return
"""

# =============================================================================
# IMPORTS
# =============================================================================

# time: Thư viện có sẵn của Python, dùng để tạm dừng chương trình (sleep)
#   time.sleep(seconds) → dừng chương trình trong N giây
#   Tương đương Go: time.Sleep(duration)
import time

# sys: Thư viện có sẵn, dùng để thoát chương trình khi retry hết lần
#   sys.exit(1) → dừng chương trình với exit code 1 (lỗi)
#   Tương đương Go: os.Exit(1) hoặc log.Fatal()
import sys

# logging: Ghi log — đã giải thích ở postgres.py
import logging

# psycopg2: Driver PostgreSQL — dùng để kết nối database
import psycopg2

# Tạo logger riêng cho module retry
# Khi ghi log: logger.info("...") → [mini-asm.database.retry] INFO: ...
logger = logging.getLogger("mini-asm.database.retry")


# =============================================================================
# HÀM CHÍNH: connect_with_retry — Kết nối DB với retry + exponential backoff
# =============================================================================

def connect_with_retry(
    connection_string: str,
    max_retries: int = 5,
) -> "psycopg2.connection":
    """
    Kết nối PostgreSQL với cơ chế retry tự động.

    Thử kết nối tối đa max_retries lần. Nếu thất bại, chờ theo
    exponential backoff (1s → 2s → 4s → 8s → 16s) rồi thử lại.
    Nếu hết tất cả lần thử vẫn fail → thoát chương trình (sys.exit).

    Cú pháp giải thích:
        def connect_with_retry(
            connection_string: str,     ← Chuỗi kết nối DB (host, port, user, ...)
            max_retries: int = 5,       ← Số lần thử tối đa, mặc định 5
        ) -> "psycopg2.connection":     ← Trả về connection object nếu thành công
            │
            └─ -> "psycopg2.connection" = type hint cho giá trị trả về
               Đặt trong "" vì psycopg2 không export type trực tiếp

    Args:
        connection_string: Chuỗi kết nối PostgreSQL dạng DSN, ví dụ:
                           "host=localhost port=5432 user=postgres password=postgres dbname=mini_asm"
        max_retries: Số lần thử kết nối tối đa (mặc định: 5)

    Returns:
        psycopg2.connection — connection object đã kết nối thành công, sẵn sàng chạy SQL

    Side Effects:
        - Nếu hết max_retries lần vẫn fail → gọi sys.exit(1) để dừng chương trình
        - In log mỗi lần thử và kết quả (thành công / thất bại)
    """

    # last_error: Lưu lỗi cuối cùng để in ra nếu hết lần retry
    # Optional[Exception] = có thể là Exception hoặc None
    # Ban đầu = None vì chưa có lỗi nào
    last_error: Exception | None = None

    # =========================================================================
    # VÒNG LẶP RETRY
    # =========================================================================
    for attempt in range(1, max_retries + 1):
        # Log lần thử hiện tại
        logger.info(f"🔄 Database connection attempt {attempt}/{max_retries}...")

        try:
            # =================================================================
            # THỬ KẾT NỐI DATABASE
            # =================================================================
            # psycopg2.connect() mở kết nối TCP tới PostgreSQL server
            # Nếu DB chưa sẵn sàng (chưa khởi động, sai host/port, ...)
            # → raise psycopg2.OperationalError
            conn = psycopg2.connect(connection_string)

            # Nếu tới được dòng này → kết nối THÀNH CÔNG!
            # Log thành công và trả về connection
            logger.info("✅ Database connected successfully!")
            return conn

        except psycopg2.OperationalError as e:
            # =================================================================
            # KẾT NỐI THẤT BẠI — Xử lý retry
            # =================================================================
            # psycopg2.OperationalError: Lỗi khi thao tác với DB (kết nối, query, ...)
            #   - DB chưa khởi động: "connection refused"
            #   - Sai host: "could not translate host name"
            #   - Sai password: "password authentication failed"
            #   - DB chưa tạo: "database does not exist"
            #
            # "as e" gán exception object vào biến e để truy cập thông tin lỗi
            last_error = e

            # Kiểm tra còn lần retry không
            if attempt < max_retries:
                # CÒN lần retry → tính thời gian chờ và retry
                #
                # Exponential backoff: 1 << (attempt - 1)
                #   attempt=1: 1 << 0 = 1 giây
                #   attempt=2: 1 << 1 = 2 giây
                #   attempt=3: 1 << 2 = 4 giây
                #   attempt=4: 1 << 3 = 8 giây
                #   attempt=5: 1 << 4 = 16 giây (nhưng attempt=5 là lần cuối, không sleep)
                #
                # Toán tử << (left shift / dịch bit trái):
                #   Python (và hầu hết ngôn ngữ) biểu diễn số dưới dạng nhị phân (binary)
                #   1 = 0001 trong binary
                #   1 << 1 = dịch bit 1 sang trái 1 vị trí = 0010 = 2
                #   1 << 2 = dịch bit 1 sang trái 2 vị trí = 0100 = 4
                #   Tổng quát: 1 << n = 2^n (2 mũ n)
                wait_seconds = 2 << (attempt - 1)

                logger.warning(
                    f"⚠️  Connection failed: {e}. "
                    f"Retrying in {wait_seconds}s..."
                )

                # time.sleep(N): Tạm dừng chương trình N giây
                # Trong thời gian sleep, chương trình không làm gì cả — chỉ chờ
                # Tương đương Go: time.Sleep(N * time.Second)
                time.sleep(wait_seconds)
            else:
                # HẾT lần retry → log lỗi cuối cùng
                # Không sleep nữa vì không retry thêm
                logger.error(
                    f"⚠️  Connection failed: {e}. "
                    f"No more retries left."
                )

    # =========================================================================
    # HẾT TẤT CẢ LẦN RETRY — KHÔNG KẾT NỐI ĐƯỢC
    # =========================================================================
    # Nếu vòng for kết thúc mà không return → tất cả lần thử đều fail
    # → Không thể chạy app mà không có DB → phải thoát chương trình

    # Log lỗi nghiêm trọng (CRITICAL) — mức cao nhất
    logger.critical(
        f"❌ Failed to connect to database after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
    logger.critical("🛑 Server cannot start without database. Exiting...")

    # sys.exit(1): Dừng chương trình với exit code 1
    #   - Exit code 0 = thành công (bình thường)
    #   - Exit code 1 = lỗi (có vấn đề)
    #   - Tương đương Go: os.Exit(1) hoặc log.Fatal()
    #
    # Tại sao dùng sys.exit() thay vì raise Exception?
    #   - sys.exit() dừng NGAY LẬP TỨC, không ai bắt được (trừ SystemExit handler)
    #   - Phù hợp cho lỗi nghiêm trọng: không có DB → app không thể hoạt động
    #   - raise Exception → có thể bị handler bắt → app chạy tiếp dù không có DB
    sys.exit(1)
