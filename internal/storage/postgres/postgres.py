"""
=============================================================================
File: internal/storage/postgres/postgres.py
Layer: Infrastructure Layer — Implementation (Clean Architecture)
Tác dụng: Implement Storage interface bằng PostgreSQL (dữ liệu persistent).
=============================================================================

SESSION 3 MỚI THÊM — đây là thay đổi chính so với session 2.

So sánh 2 cách lưu dữ liệu:
    Session 2 — MemoryStorage:
        - Lưu trong dict Python (bộ nhớ RAM)
        - Tắt server → MẤT HẾT dữ liệu
        - Đơn giản, dùng để học

    Session 3 — PostgresStorage (file này):
        - Lưu trong PostgreSQL (database thực, ghi xuống ổ cứng)
        - Tắt server → dữ liệu VẪN CÒN (persistent)
        - Dùng trong thực tế

Cả hai đều implement CÙNG interface Storage (trong storage.py).
→ service và handler KHÔNG CẦN THAY ĐỔI — chỉ đổi 1 dòng trong main.py.
  Đây chính là sức mạnh của Clean Architecture + Interface pattern.

Thư viện psycopg2 — Driver PostgreSQL cho Python:
    - psycopg2 là thư viện phổ biến nhất để Python nói chuyện với PostgreSQL
    - Nó cung cấp: connection (kết nối), cursor (con trỏ chạy SQL), parameterized queries
    - Cài qua pip: pip install psycopg2-binary

⚠️  SQL INJECTION — LỖ HỔNG BẢO MẬT NGUY HIỂM:
    Khi viết câu SQL, KHÔNG BAO GIỜ nối string trực tiếp:

    ❌ SAI (Hacker có thể inject SQL):
        query = f"SELECT * FROM assets WHERE id = '{user_input}'"
        # Nếu user_input = "'; DROP TABLE assets; --"
        # → Câu SQL trở thành: SELECT * FROM assets WHERE id = ''; DROP TABLE assets; --'
        # → XÓA TOÀN BỘ BẢNG!

    ✅ ĐÚNG (Dùng parameterized query — psycopg2 tự escape):
        cursor.execute("SELECT * FROM assets WHERE id = %s", (user_input,))
        # psycopg2 tự xử lý escape, hacker không thể inject được
        # %s là placeholder, giá trị thật truyền qua tuple (user_input,)
"""

# =============================================================================
# IMPORTS — Các thư viện cần dùng
# =============================================================================

# logging: Thư viện có sẵn của Python, dùng để ghi log (nhật ký)
#   Thay vì dùng print() rồi phải xóa sau, logging cho phép:
#   - Phân cấp: DEBUG < INFO < WARNING < ERROR < CRITICAL
#   - Ghi ra file, console, hoặc cả hai
#   - Tắt/bật từng cấp độ mà không cần sửa code
import logging

# typing: Module có sẵn, cung cấp các kiểu dữ liệu "gợi ý" (type hints)
#   List[Asset]     = danh sách chứa các Asset object
#   Optional[str]   = có thể là str HOẶC None
#
#   Type hints KHÔNG bắt buộc — Python vẫn chạy nếu không có.
#   Nhưng nó giúp:
#     - IDE gợi ý thông minh hơn (autocomplete)
#     - Đọc code biết ngay hàm nhận gì, trả gì
#     - Phát hiện lỗi sớm hơn (qua tool mypy/pyright)
from typing import List, Optional

# psycopg2: Thư viện kết nối PostgreSQL
#   Cần cài: pip install psycopg2-binary
#   Cung cấp: connect(), cursor, execute(), fetchall(), fetchone()
import psycopg2

# psycopg2.extras: Tiện ích bổ sung (ở đây import để dùng một số feature nâng cao)
import psycopg2.extras

# Import từ các module trong project:
from internal.config.config import PostgresConfig       # Cấu hình DB (host, port, user, ...)
from internal.database.retry import connect_with_retry   # [BÀI 4] Retry kết nối DB (exponential backoff)
from internal.model.asset import Asset, AssetType, AssetStatus  # Model + Enum
from internal.model.errors import AssetNotFoundError, DuplicateAssetError  # Custom errors
from internal.storage.storage import Storage             # Interface (ABC) mà class này implement

# Tạo logger riêng cho module này
# "mini-asm.storage.postgres" là tên logger — giúp phân biệt log từ đâu
# Khi ghi log: logger.info("...") → [mini-asm.storage.postgres] INFO: ...
logger = logging.getLogger("mini-asm.storage.postgres")


# =============================================================================
# CLASS: PostgresStorage — Lưu trữ dữ liệu bằng PostgreSQL
# =============================================================================

class PostgresStorage(Storage):
    """
    PostgreSQL implementation của Storage interface.

    Cú pháp:  class PostgresStorage(Storage):
                                     ↑
        (Storage) nghĩa là class này KẾ THỪA từ Storage (trong storage.py).
        Storage là ABC (Abstract Base Class) — định nghĩa "phải có method gì".
        PostgresStorage phải implement TẤT CẢ method abstract:
            create(), get_all(), get_by_id(), update(), delete(), filter(), search()
        Nếu thiếu 1 method → Python báo lỗi ngay khi tạo object.

    Khác với MemoryStorage:
        ┌─────────────────┬──────────────────────┬──────────────────────────┐
        │                 │ MemoryStorage         │ PostgresStorage          │
        ├─────────────────┼──────────────────────┼──────────────────────────┤
        │ Lưu ở đâu?      │ dict trong RAM        │ PostgreSQL trên disk     │
        │ Tắt server?     │ Mất hết               │ Dữ liệu vẫn còn         │
        │ Dữ liệu lớn?   │ Chậm (RAM có hạn)     │ Nhanh (có index)         │
        │ Nhiều user?     │ Cần Lock thủ công      │ DB tự xử lý             │
        │ Sort/Filter?    │ Python code            │ SQL (DB tự tối ưu)       │
        └─────────────────┴──────────────────────┴──────────────────────────┘
    """

    # -------------------------------------------------------------------------
    # __init__: Hàm khởi tạo — được gọi khi tạo object
    # -------------------------------------------------------------------------

    def __init__(self, connection: "psycopg2.connection", connection_string: str = ""):
        """
        Lưu connection database vào thuộc tính của object.

        Cú pháp giải thích:
            def __init__(self, connection: "psycopg2.connection", connection_string: str = ""):
                │              │            │                      │
                │              │            │                      └─ DSN dùng cho reconnect (Bài 5)
                │              │            └─ psycopg2 connection object
                │              └─ Tham số truyền vào
                └─ self = chính object đang được tạo (tương tự "this" trong Java/C#)

        self._conn: Connection hiện tại (quy ước "private" với dấu _)
        self._conn_string: [BÀI 5] Lưu DSN để reconnect khi DB restart
        """
        self._conn = connection
        self._conn_string = connection_string

    # -------------------------------------------------------------------------
    # from_config: Factory method — cách tạo object "thông minh" hơn __init__
    # -------------------------------------------------------------------------

    @classmethod  # ← Decorator: biến method thành CLASS method (gọi trên class, không phải object)
    def from_config(cls, config: PostgresConfig) -> "PostgresStorage":
        """
        Tạo PostgresStorage bằng cách đọc config và kết nối tới database.

        [BÀI 4] Cải tiến: Dùng connect_with_retry() thay vì psycopg2.connect() trực tiếp.
        Nếu DB chưa sẵn sàng → tự động retry tối đa 5 lần với exponential backoff.
        Xem chi tiết retry logic tại: internal/database/retry.py

        @classmethod là gì?
            - Method thường: gọi trên OBJECT  → storage.create(asset)
            - Class method:  gọi trên CLASS   → PostgresStorage.from_config(config)
            - "cls" = class hiện tại (PostgresStorage), giống "self" nhưng cho class
            - cls(conn) = PostgresStorage(conn) = gọi __init__ để tạo object mới

        Tại sao dùng @classmethod thay vì __init__ trực tiếp?
            - __init__ đơn giản: chỉ nhận connection đã có sẵn, lưu vào self._conn
            - from_config phức tạp hơn: đọc config → retry kết nối DB → bật autocommit → tạo object
            - Tách ra giúp code linh hoạt: muốn tạo bằng config → from_config()
                                           muốn tạo bằng connection có sẵn → __init__()
            - Pattern này gọi là "Factory Method"

        autocommit là gì?
            - Trong database, mỗi thao tác (INSERT, UPDATE, DELETE) nằm trong 1 "transaction"
            - Mặc định psycopg2: phải gọi conn.commit() thủ công sau mỗi INSERT/UPDATE/DELETE
              Nếu quên commit → dữ liệu KHÔNG được lưu!
            - autocommit = True: tự động commit sau mỗi câu SQL → đơn giản hơn, không sợ quên
            - Phù hợp cho app đơn giản. App phức tạp cần control transaction thì tắt autocommit***.

        Args:
            config: PostgresConfig — chứa host, port, user, password, database name

        Returns:
            PostgresStorage — object đã kết nối thành công, sẵn sàng chạy SQL

        Side Effects:
            - Nếu DB không sẵn sàng: retry tối đa 5 lần (1s → 2s → 4s → 8s → 16s)
            - Nếu hết 5 lần vẫn fail → sys.exit(1) (dừng chương trình)
        """
        # Log thông tin kết nối (KHÔNG log password vì lý do bảo mật)
        logger.info(
            f"📊 Connecting to database: {config.db_user}@{config.db_host}:{config.db_port}/{config.db_name}"
        )

        # =====================================================================
        # [BÀI 4] Bước 1: Kết nối PostgreSQL VỚI RETRY
        # =====================================================================
        # TRƯỚC (Session 3):
        #   conn = psycopg2.connect(config.connection_string)
        #   → Thử 1 lần, fail là crash ngay
        #
        # SAU (Bài 4):
        #   conn = connect_with_retry(config.connection_string, max_retries=5)
        #   → Thử tối đa 5 lần, chờ 1s → 2s → 4s → 8s → 16s giữa các lần
        #   → Log rõ ràng mỗi attempt: "🔄 attempt 1/5...", "⚠️ failed...", "✅ connected!"
        #   → Nếu hết 5 lần → sys.exit(1) (không return về đây)
        conn = connect_with_retry(
            connection_string=config.connection_string,
            max_retries=5,
        )

        # Bước 2: Bật autocommit
        # Chỉ tới được đây nếu connect_with_retry() thành công
        # (nếu fail → sys.exit(1) bên trong hàm retry, không return về)
        conn.autocommit = True

        # Bước 3: Tạo PostgresStorage object
        # cls = PostgresStorage (vì đây là classmethod)
        # cls(conn, ...) = gọi __init__(self, connection=conn, connection_string=...)
        # [BÀI 5] Truyền connection_string để check_health() có thể reconnect
        return cls(conn, connection_string=config.connection_string)

    # -------------------------------------------------------------------------
    # close: Đóng kết nối database
    # -------------------------------------------------------------------------

    def close(self):
        """
        Đóng connection tới database.

        Khi nào gọi?
            → Khi server shutdown (tắt). Được gọi trong main.py ở event "shutdown".

        Tại sao cần đóng?
            - Mỗi connection chiếm 1 slot trên PostgreSQL server
            - PostgreSQL có giới hạn connection (mặc định 100)
            - Không đóng → "connection leak" → hết slot → app mới không kết nối được

        self._conn.closed:
            - Thuộc tính có sẵn của psycopg2 connection
            - True = đã đóng rồi, False = đang mở
            - Kiểm tra trước khi đóng để tránh lỗi đóng 2 lần
        """
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("🔌 Database connection closed")

    # =========================================================================
    # [BÀI 5] RECONNECT — Tạo lại connection khi DB restart
    # =========================================================================

    def _reconnect(self) -> None:
        """
        Tạo connection MỚI hoàn toàn tới database.

        Khi nào cần?
            - Connection bị stale (DB restart, mất mạng, idle timeout)
            - psycopg2 đánh dấu self._conn.closed = True
            - Hoặc query fail với OperationalError

        Flow:
            1. Đóng connection cũ (nếu còn mở) → giải phóng tài nguyên
            2. Tạo connection mới bằng psycopg2.connect(self._conn_string)
            3. Bật autocommit
            4. Gán vào self._conn → tất cả method khác tự dùng connection mới

        Raises:
            Exception: Nếu không có connection_string hoặc connect() fail
        """
        if not self._conn_string:
            raise RuntimeError("Không có connection string để reconnect")

        logger.info("🔄 Attempting to reconnect database...")

        # Đóng connection cũ (nếu chưa đóng)
        if self._conn and not self._conn.closed:
            self._conn.close()

        # Tạo connection MỚI hoàn toàn
        new_conn = psycopg2.connect(self._conn_string)
        new_conn.autocommit = True

        # Gán vào self._conn → tất cả method (create, get_all, ...) dùng connection mới
        self._conn = new_conn
        logger.info("✅ Database reconnected successfully")

    def _ensure_connection(self) -> None:
        """
        Kiểm tra connection còn sống không, reconnect nếu đã chết.

        Được gọi ở đầu MỖI method CRUD (create, get_all, update, delete, ...)
        → Tự heal khi DB restart mà không cần client gọi /health trước.

        Cách check (2 bước):
            1. self._conn.closed == True → client BIẾT CHẮC connection đã chết → reconnect
            2. Thử SELECT 1 → nếu fail → "zombie connection" (server chết, client chưa biết)
               → reconnect

        Zombie connection là gì?
            - Khi DB restart, TCP connection vẫn "open" từ phía client
            - self._conn.closed trả về False (client nghĩ vẫn OK)
            - Nhưng khi thử query → "server closed the connection unexpectedly"
            - → Phải thử query thật (SELECT 1) để phát hiện

        Chi phí: thêm 1 SELECT 1 (~0.3ms) trước mỗi CRUD call
        → Chấp nhận được cho app đơn giản. Production dùng connection pool sẽ tự handle.
        """
        # Bước 1: Client-side check
        if self._conn.closed:
            logger.warning("Connection closed (client-side), auto-reconnecting...")
            self._reconnect()
            return

        # Bước 2: Server-side check — thử ping thật
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception as e:
            logger.warning(f"Connection stale (zombie): {e}")
            self._reconnect()

    # =========================================================================
    # [BÀI 5] HEALTH CHECK — Kiểm tra + tự reconnect khi DB restart
    # =========================================================================

    def check_health(self) -> dict:
        """
        Kiểm tra sức khỏe database bằng SELECT 1.

        Nếu connection bị stale (DB đã restart) → tạo connection MỚI hoàn toàn
        bằng connection_string đã lưu, rồi thử lại.

        Tại sao không dùng conn.reset()?
            - reset() fail nếu connection đã closed hoàn toàn
            - Khi DB restart, psycopg2 đánh dấu connection là "closed"
            - → Phải tạo connection MỚI bằng psycopg2.connect()

        Returns:
            dict có các key:
                - "connected": bool — DB có phản hồi không
                - "latency_ms": float | None — thời gian ping (ms)
        """
        import time

        def _try_ping() -> float:
            """Thử SELECT 1, trả về latency (ms). Raise nếu fail."""
            start = time.perf_counter()
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return (time.perf_counter() - start) * 1000

        # --- Lần 1: Thử ping bình thường ---
        try:
            latency = _try_ping()
            return {"connected": True, "latency_ms": round(latency, 2)}
        except Exception as first_error:
            logger.warning(f"Database ping failed: {first_error}")

        # --- Lần 2: Reconnect rồi thử lại ---
        # Connection bị stale → dùng _reconnect() để tạo connection MỚI
        try:
            self._reconnect()

            # Thử ping lại sau khi reconnect
            latency = _try_ping()
            return {"connected": True, "latency_ms": round(latency, 2)}

        except Exception as reconnect_error:
            # Reconnect cũng fail → DB thực sự down
            logger.warning(f"Database reconnect failed: {reconnect_error}")
            return {"connected": False, "latency_ms": None}

    # =========================================================================
    # HELPER: Chuyển database row (tuple) → Asset object
    # =========================================================================

    @staticmethod  # ← Decorator: method KHÔNG dùng self hay cls — giống hàm thường nhưng đặt trong class
    def _row_to_asset(row: tuple) -> Asset:
        """
        Chuyển 1 dòng kết quả SQL thành Asset object.

        @staticmethod là gì?
            - Method thường cần "self" (truy cập thuộc tính object)
            - @classmethod cần "cls" (truy cập class)
            - @staticmethod KHÔNG cần self hay cls — nó là hàm thuần túy (pure function)
            - Đặt trong class vì nó liên quan đến PostgresStorage, nhưng không dùng self._conn

        Tại sao cần hàm này?
            PostgreSQL trả kết quả SQL dạng TUPLE (giống list nhưng không sửa được):
                ("abc-123", "example.com", "domain", "active", datetime(...), datetime(...))
                  row[0]      row[1]        row[2]    row[3]    row[4]         row[5]

            Nhưng service layer cần OBJECT Asset để truy cập bằng tên:
                asset.id, asset.name, asset.type, ...

            → Hàm này chuyển từ tuple → Asset object.

        row[0], row[1], ... là gì?
            - tuple truy cập phần tử bằng index (vị trí), bắt đầu từ 0
            - Thứ tự PHẢI khớp với thứ tự cột trong câu SELECT:
              SELECT id,    name,   type,   status, created_at, updated_at
                     row[0] row[1]  row[2]  row[3]  row[4]      row[5]

        AssetType(row[2]) là gì?
            - row[2] = string từ DB, ví dụ "domain"
            - AssetType("domain") = chuyển string → Enum object (AssetType.DOMAIN)
            - Tương tự AssetStatus(row[3]): "active" → AssetStatus.ACTIVE

        str(row[0]) là gì?
            - PostgreSQL trả UUID có thể là kiểu uuid, không phải str
            - str() đảm bảo luôn là string

        Args:
            row: tuple — 1 dòng kết quả từ cursor.fetchone() hoặc cursor.fetchall()
                 Thứ tự: (id, name, type, status, created_at, updated_at)

        Returns:
            Asset: Object với đầy đủ thuộc tính, sẵn sàng trả về cho service layer
        """
        return Asset(
            id=str(row[0]),             # UUID → str
            name=row[1],                # str  — giữ nguyên
            type=AssetType(row[2]),     # str  → Enum (AssetType.DOMAIN, .IP, .SERVICE)
            status=AssetStatus(row[3]), # str  → Enum (AssetStatus.ACTIVE, .INACTIVE)
            created_at=row[4],          # datetime — giữ nguyên
            updated_at=row[5],          # datetime — giữ nguyên
        )

    # =========================================================================
    # CRUD OPERATIONS — Create, Read, Update, Delete
    # =========================================================================

    # -------------------------------------------------------------------------
    # CREATE — Thêm asset mới vào database
    # -------------------------------------------------------------------------

    def create(self, asset: Asset) -> None:
        """
        Chạy câu SQL INSERT để thêm 1 dòng mới vào bảng assets.

        Args:
            asset: Asset — object đã có đầy đủ thông tin (id, name, type, status, timestamps)
                   (Service layer đã gán id, created_at, updated_at trước khi gọi hàm này)

        Returns:
            None — không trả gì (dữ liệu đã được lưu vào DB)

        Raises:
            DuplicateAssetError: Nếu ID đã tồn tại trong DB
                (vi phạm PRIMARY KEY constraint → PostgreSQL ném UniqueViolation)
        """
        self._ensure_connection()

        # Câu SQL INSERT — thêm 1 dòng mới vào bảng assets
        # %s là placeholder — psycopg2 sẽ thay thế bằng giá trị thật (an toàn, chống SQL injection)
        # Có 6 cột → cần 6 placeholder %s
        query = """
            INSERT INTO assets (id, name, type, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        # try/except: Bắt lỗi — nếu INSERT thất bại thì xử lý thay vì crash
        try:
            # --- "with" statement và cursor ---
            # cursor (con trỏ): object dùng để CHẠY câu SQL và LẤY kết quả
            #
            # with self._conn.cursor() as cur:
            #   - Tạo cursor → gán vào biến "cur"
            #   - Khi block "with" kết thúc → tự động đóng cursor (giải phóng bộ nhớ)
            #   - Giống try-finally nhưng gọn hơn:
            #       cur = self._conn.cursor()
            #       try:
            #           ... dùng cur ...
            #       finally:
            #           cur.close()  ← "with" tự làm dòng này
            with self._conn.cursor() as cur:

                # cur.execute(query, params):
                #   - Chạy câu SQL "query" với các giá trị trong "params"
                #   - Mỗi %s trong query được thay bằng 1 phần tử trong tuple params
                #   - psycopg2 tự ESCAPE giá trị → chống SQL injection
                #
                # Tuple params: (asset.id, asset.name, ...)
                #   - Tuple = giống list nhưng không thay đổi được, dùng dấu ()
                #   - Phần tử thứ 1 → thay vào %s thứ 1 (id)
                #   - Phần tử thứ 2 → thay vào %s thứ 2 (name)
                #   - ...
                #
                # asset.type.value:
                #   - asset.type = Enum object, ví dụ AssetType.DOMAIN
                #   - .value = lấy giá trị string gốc, ví dụ "domain"
                #   - PostgreSQL cần string "domain", không hiểu Enum Python
                cur.execute(query, (
                    asset.id,
                    asset.name,
                    asset.type.value,     # AssetType.DOMAIN → "domain"
                    asset.status.value,   # AssetStatus.ACTIVE → "active"
                    asset.created_at,
                    asset.updated_at,
                ))

        except psycopg2.errors.UniqueViolation:
            # PostgreSQL ném lỗi UniqueViolation khi INSERT 1 ID đã tồn tại
            # (vì cột id là PRIMARY KEY → không cho phép trùng)
            # Ta chuyển thành DuplicateAssetError — lỗi do app mình định nghĩa
            # → Handler sẽ bắt lỗi này và trả HTTP 409 Conflict cho client
            raise DuplicateAssetError()

        except psycopg2.Error as e:
            # Bắt MỌI lỗi psycopg2 khác (mất kết nối, syntax SQL sai, ...)
            # "as e" gán lỗi vào biến e để log chi tiết
            logger.error(f"Failed to create asset: {e}")
            raise  # raise không có tham số = ném lại lỗi gốc (không nuốt lỗi)

    # -------------------------------------------------------------------------
    # READ ALL — Lấy tất cả assets
    # -------------------------------------------------------------------------

    def get_all(self) -> List[Asset]:
        """
        Chạy câu SQL SELECT để lấy TẤT CẢ assets, sắp xếp mới nhất trước.

        Returns:
            List[Asset] — danh sách Asset objects, sắp xếp theo created_at giảm dần
                          Nếu bảng trống → trả về list rỗng []
        """
        self._ensure_connection()

        # ORDER BY created_at DESC: sắp xếp theo ngày tạo, MỚI NHẤT lên đầu
        # DESC = descending (giảm dần). Ngược lại là ASC = ascending (tăng dần)
        query = """
            SELECT id, name, type, status, created_at, updated_at
            FROM assets
            ORDER BY created_at DESC
        """
        with self._conn.cursor() as cur:
            cur.execute(query)

            # fetchall(): Lấy TẤT CẢ dòng kết quả
            # Trả về list of tuples:
            #   [("id1", "name1", ...), ("id2", "name2", ...), ...]
            # Nếu không có dòng nào → trả về list rỗng []
            rows = cur.fetchall()

            # List comprehension — cách viết ngắn gọn để tạo list mới:
            #   [self._row_to_asset(row) for row in rows]
            #
            # Tương đương viết dài:
            #   result = []
            #   for row in rows:
            #       asset = self._row_to_asset(row)
            #       result.append(asset)
            #   return result
            #
            # Đọc: "Với MỖI row trong rows, chạy _row_to_asset(row), gom kết quả thành list"
            return [self._row_to_asset(row) for row in rows]

    # -------------------------------------------------------------------------
    # READ ONE — Lấy 1 asset theo ID
    # -------------------------------------------------------------------------

    def get_by_id(self, id: str) -> Asset:
        """
        Chạy câu SQL SELECT WHERE id = %s để tìm 1 asset cụ thể.

        Args:
            id: str — UUID của asset cần tìm, ví dụ "a1b2c3d4-..."

        Returns:
            Asset — object tìm được

        Raises:
            AssetNotFoundError: Nếu không tìm thấy (ID không tồn tại trong DB)
        """
        self._ensure_connection()

        query = """
            SELECT id, name, type, status, created_at, updated_at
            FROM assets
            WHERE id = %s
        """
        # WHERE id = %s: Lọc chỉ lấy dòng có id khớp
        # %s sẽ được thay bằng giá trị "id" truyền vào

        with self._conn.cursor() as cur:
            # Chú ý: (id,) có dấu phẩy!
            # Vì psycopg2 yêu cầu params phải là TUPLE hoặc LIST
            # (id)  = chỉ là string trong ngoặc, KHÔNG phải tuple
            # (id,) = tuple có 1 phần tử (dấu phẩy tạo tuple)
            #
            # Ví dụ:
            #   ("hello")   → string "hello"
            #   ("hello",)  → tuple ("hello",) — đây mới đúng!
            cur.execute(query, (id,))

            # fetchone(): Lấy 1 dòng kết quả (vì ta tìm theo PRIMARY KEY → chỉ có 0 hoặc 1 dòng)
            # Trả về tuple ("id", "name", ...) nếu tìm thấy
            # Trả về None nếu không tìm thấy
            row = cur.fetchone()

            if row is None:
                # Không tìm thấy → ném lỗi để handler trả HTTP 404
                raise AssetNotFoundError()

            return self._row_to_asset(row)

    # -------------------------------------------------------------------------
    # UPDATE — Cập nhật thông tin asset
    # -------------------------------------------------------------------------

    def update(self, id: str, asset: Asset) -> None:
        """
        Chạy câu SQL UPDATE SET ... WHERE id = %s để cập nhật 1 asset.

        Cách kiểm tra asset có tồn tại:
            Thay vì SELECT trước rồi UPDATE (2 câu SQL, chậm),
            ta UPDATE luôn rồi kiểm tra cur.rowcount:
            - rowcount = 1 → UPDATE thành công (có 1 dòng bị ảnh hưởng)
            - rowcount = 0 → không có dòng nào bị ảnh hưởng → ID không tồn tại

        Args:
            id: str — UUID của asset cần cập nhật
            asset: Asset — object chứa dữ liệu MỚI (name, type, status, updated_at)

        Returns:
            None — không trả gì

        Raises:
            AssetNotFoundError: Nếu ID không tồn tại trong DB
        """
        self._ensure_connection()

        # SET name = %s, type = %s, ...: Gán giá trị mới cho các cột
        # WHERE id = %s: Chỉ cập nhật dòng có id khớp
        # Lưu ý: id nằm ở %s CUỐI CÙNG trong tuple params
        query = """
            UPDATE assets
            SET name = %s, type = %s, status = %s, updated_at = %s
            WHERE id = %s
        """
        with self._conn.cursor() as cur:
            # Thứ tự params PHẢI khớp với thứ tự %s trong query:
            # %s thứ 1 → name, %s thứ 2 → type, ..., %s thứ 5 → id (trong WHERE)
            cur.execute(query, (
                asset.name,
                asset.type.value,
                asset.status.value,
                asset.updated_at,
                id,  # ← id cho WHERE clause, nằm cuối
            ))

            # cur.rowcount: Số dòng bị ảnh hưởng bởi câu SQL vừa chạy
            #   - UPDATE thành công 1 dòng → rowcount = 1
            #   - Không có dòng nào khớp WHERE → rowcount = 0 → asset không tồn tại
            if cur.rowcount == 0:
                raise AssetNotFoundError()

    # -------------------------------------------------------------------------
    # DELETE — Xóa asset khỏi database
    # -------------------------------------------------------------------------

    def delete(self, id: str) -> None:
        """
        Chạy câu SQL DELETE WHERE id = %s để xóa 1 asset.

        Tương tự update(), dùng cur.rowcount để kiểm tra:
            - rowcount = 1 → xóa thành công
            - rowcount = 0 → ID không tồn tại → raise lỗi

        Args:
            id: str — UUID của asset cần xóa

        Raises:
            AssetNotFoundError: Nếu ID không tồn tại
        """
        self._ensure_connection()

        query = "DELETE FROM assets WHERE id = %s"
        with self._conn.cursor() as cur:
            cur.execute(query, (id,))  # (id,) ← tuple 1 phần tử, nhớ dấu phẩy!
            if cur.rowcount == 0:
                raise AssetNotFoundError()

    # -------------------------------------------------------------------------
    # FILTER — Lọc asset theo type và/hoặc status (query ĐỘNG)
    # -------------------------------------------------------------------------

    def filter(self, asset_type: Optional[str] = None, status: Optional[str] = None) -> List[Asset]:
        """
        Lọc assets theo type và/hoặc status. Cả 2 đều tùy chọn (optional).

        Cú pháp tham số:
            asset_type: Optional[str] = None
            │           │               │
            │           │               └─ Giá trị mặc định: None (không truyền thì = None)
            │           └─ Type hint: Optional[str] = có thể là str HOẶC None
            │              Optional[str] = Union[str, None] = str | None (Python 3.10+)
            └─ Tên tham số

        Kỹ thuật "WHERE 1=1" — xây dựng câu SQL ĐỘNG:
            Bài toán: Tùy theo tham số, câu SQL có thể là:
                - Không có filter:  SELECT ... FROM assets (không có WHERE)
                - Chỉ type:        SELECT ... WHERE type = 'domain'
                - Chỉ status:      SELECT ... WHERE status = 'active'
                - Cả hai:          SELECT ... WHERE type = 'domain' AND status = 'active'

            Nếu không dùng "WHERE 1=1", phải kiểm tra phức tạp:
                query = "SELECT ... FROM assets"
                if asset_type:
                    query += " WHERE type = %s"       # Điều kiện ĐẦU TIÊN dùng WHERE
                if status:
                    if asset_type:
                        query += " AND status = %s"   # Nếu có rồi → dùng AND
                    else:
                        query += " WHERE status = %s" # Nếu chưa có → dùng WHERE
                # → Rườm rà, dễ sai!

            Dùng "WHERE 1=1" — đơn giản hơn nhiều:
                query = "SELECT ... FROM assets WHERE 1=1"
                # 1=1 LUÔN đúng → không ảnh hưởng kết quả
                # Giờ mọi điều kiện chỉ cần nối " AND ..." — không phân biệt đầu/sau
                if asset_type:
                    query += " AND type = %s"
                if status:
                    query += " AND status = %s"
                # → Gọn gàng, dễ đọc!

        Args:
            asset_type: Optional[str] — lọc theo type ("domain", "ip", "service"), None = bỏ qua
            status: Optional[str] — lọc theo status ("active", "inactive"), None = bỏ qua

        Returns:
            List[Asset] — danh sách asset phù hợp, sắp xếp mới nhất trước
        """
        self._ensure_connection()

        query = """
            SELECT id, name, type, status, created_at, updated_at
            FROM assets
            WHERE 1=1
        """
        # params: List chứa giá trị cho các %s placeholder
        # Ban đầu rỗng, sẽ append thêm tùy theo điều kiện
        # Cú pháp:  params: list = []
        #           │        │      │
        #           │        │      └─ Giá trị mặc định: list rỗng
        #           │        └─ Type hint: kiểu list
        #           └─ Tên biến
        params: list = []

        if asset_type:
            # Nếu asset_type có giá trị (không phải None, không phải "")
            # → Thêm điều kiện lọc theo type
            query += " AND type = %s"
            params.append(asset_type)  # append() = thêm phần tử vào cuối list

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY created_at DESC"

        with self._conn.cursor() as cur:
            # params có thể là:
            #   [] → không có %s nào → SELECT ... WHERE 1=1 ORDER BY ...
            #   ["domain"] → 1 phần tử → WHERE 1=1 AND type = 'domain'
            #   ["domain", "active"] → 2 phần tử → WHERE 1=1 AND type = 'domain' AND status = 'active'
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_asset(row) for row in rows]

    # -------------------------------------------------------------------------
    # SEARCH — Tìm kiếm asset theo tên (không phân biệt hoa/thường)
    # -------------------------------------------------------------------------

    def search(self, query: str) -> List[Asset]:
        """
        Tìm kiếm asset có TÊN chứa từ khóa (case-insensitive, partial match).

        Ví dụ: search("exam") → tìm thấy "example.com", "EXAM-server", "my-example"

        ILIKE là gì? (PostgreSQL-specific)
            - LIKE: So sánh chuỗi, PHÂN BIỆT hoa/thường
              "Example" LIKE "%example%" → FALSE (E ≠ e)
            - ILIKE: Giống LIKE nhưng KHÔNG phân biệt hoa/thường (I = Insensitive)
              "Example" ILIKE "%example%" → TRUE ✓

            Ký tự đặc biệt:
              % = wildcard, đại diện cho BẤT KỲ chuỗi nào (0 hoặc nhiều ký tự)
              _ = wildcard, đại diện cho ĐÚNG 1 ký tự

            Ví dụ:
              "%exam%"   → chứa "exam" ở BẤT KỲ vị trí nào
              "exam%"    → BẮT ĐẦU bằng "exam"
              "%exam"    → KẾT THÚC bằng "exam"
              "e_am"     → "exam", "eaam", "e1am", ... (ký tự thứ 2 bất kỳ)

        f-string nhắc lại:
            search_pattern = f"%{query}%"
            Nếu query = "exam" → search_pattern = "%exam%"
            f"..." cho phép chèn biến {query} vào giữa chuỗi

        Args:
            query: str — từ khóa tìm kiếm, ví dụ "example"

        Returns:
            List[Asset] — các asset có tên chứa từ khóa, sắp xếp mới nhất trước
        """
        self._ensure_connection()

        # Lưu ý: tên biến là "sql_query" (không phải "query")
        # vì tham số hàm đã dùng tên "query" rồi → tránh trùng tên (shadowing)
        sql_query = """
            SELECT id, name, type, status, created_at, updated_at
            FROM assets
            WHERE name ILIKE %s
            ORDER BY created_at DESC
        """
        # Tạo pattern tìm kiếm: thêm % hai đầu → tìm "chứa" keyword
        # Ví dụ: query = "exam" → search_pattern = "%exam%"
        # → Tìm mọi asset có name chứa "exam" (không phân biệt hoa/thường)
        search_pattern = f"%{query}%"

        with self._conn.cursor() as cur:
            #psycopg2 yêu cầu tham số thứ 2 của cur.execute() phải là 
            #tuple hoặc list, không được là string
            cur.execute(sql_query, (search_pattern,))  # (search_pattern,) ← tuple 1 phần tử
            rows = cur.fetchall()
            return [self._row_to_asset(row) for row in rows]

    # =========================================================================
    # [BÀI 1] STATISTICS — Thống kê asset
    # =========================================================================

    def get_stats(self) -> dict:
        """
        Thống kê tổng quan assets bằng SQL aggregate functions.

        Dùng 3 câu SQL riêng biệt:
            1. COUNT(*) → tổng số asset
            2. GROUP BY type → đếm theo từng loại
            3. GROUP BY status → đếm theo từng trạng thái

        COUNT(*) là gì?
            - Hàm SQL đếm số dòng trong bảng
            - COUNT(*) đếm TẤT CẢ dòng (kể cả dòng có giá trị NULL)
            - Ví dụ: SELECT COUNT(*) FROM assets → 150

        GROUP BY là gì?
            - Gom các dòng có CÙNG giá trị vào 1 nhóm
            - Kết hợp với COUNT(*) để đếm từng nhóm
            - Ví dụ: SELECT type, COUNT(*) FROM assets GROUP BY type
              → ("domain", 100), ("ip", 40), ("service", 10)

        Returns:
            dict chứa total, by_type, by_status
        """
        self._ensure_connection()

        with self._conn.cursor() as cur:
            # --- Bước 1: Đếm tổng ---
            cur.execute("SELECT COUNT(*) FROM assets")
            # fetchone() trả về tuple, ví dụ: (150,)
            # [0] lấy phần tử đầu tiên → 150
            total = cur.fetchone()[0]

            # --- Bước 2: Đếm theo type ---
            # Khởi tạo dict với tất cả type = 0 (đảm bảo luôn có key dù DB trống)
            by_type = {"domain": 0, "ip": 0, "service": 0}
            cur.execute("SELECT type, COUNT(*) FROM assets GROUP BY type")
            # fetchall() trả về list of tuples: [("domain", 100), ("ip", 40), ...]
            for row in cur.fetchall():
                # row[0] = tên type (string), row[1] = số lượng (int)
                by_type[row[0]] = row[1]

            # --- Bước 3: Đếm theo status ---
            by_status = {"active": 0, "inactive": 0}
            cur.execute("SELECT status, COUNT(*) FROM assets GROUP BY status")
            for row in cur.fetchall():
                by_status[row[0]] = row[1]

            return {
                "total": total,
                "by_type": by_type,
                "by_status": by_status,
            }

    def count(self, asset_type: Optional[str] = None, status: Optional[str] = None) -> int:
        """
        Đếm số asset bằng SQL COUNT(*) với điều kiện lọc tùy chọn.

        Dùng kỹ thuật WHERE 1=1 giống method filter() — xây dựng câu SQL động.

        Args:
            asset_type: Lọc theo loại (None = bỏ qua)
            status: Lọc theo trạng thái (None = bỏ qua)

        Returns:
            int — số lượng asset thỏa điều kiện
        """
        self._ensure_connection()

        # Xây dựng câu SQL động với WHERE 1=1
        query = "SELECT COUNT(*) FROM assets WHERE 1=1"
        params: list = []

        if asset_type:
            query += " AND type = %s"
            params.append(asset_type)

        if status:
            query += " AND status = %s"
            params.append(status)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            # fetchone() trả về (count_value,) → lấy [0]
            return cur.fetchone()[0]
    
    # =========================================================================
    # [BÀI 2] BATCH CREATE — Tạo nhiều asset cùng lúc (transaction)
    # =========================================================================

    def batch_create(self, assets: List[Asset]) -> None:
        """
        Thêm nhiều asset cùng lúc bằng database TRANSACTION.

        Transaction là gì?
            - Nhóm nhiều câu SQL thành 1 "gói"
            - NẾU tất cả thành công → COMMIT (lưu hết vào DB)
            - NẾU 1 câu fail → ROLLBACK (hủy hết, DB không đổi)
            - Gọi là "all or nothing" — được hết hoặc mất hết

        Cách dùng transaction với psycopg2:
            1. Tắt autocommit (conn.autocommit = False)
               → psycopg2 tự mở transaction ngầm khi chạy SQL
            2. Chạy các câu INSERT
            3. Nếu OK → conn.commit() (lưu)
            4. Nếu lỗi → conn.rollback() (hủy)
            5. Bật lại autocommit (conn.autocommit = True) cho các method khác

        Tại sao cần try/except/finally?
            - try: chạy code chính (INSERT)
            - except: bắt lỗi → rollback
            - finally: LUÔN chạy dù có lỗi hay không → bật lại autocommit
              Nếu thiếu finally → autocommit bị tắt vĩnh viễn → các method khác hỏng

        Args:
            assets: List[Asset] — danh sách asset đã validate + có UUID

        Raises:
            DuplicateAssetError: Nếu có ID trùng trong DB
        """
        self._ensure_connection()

        if not assets:
            return  # List rỗng → không làm gì

        # Câu SQL INSERT cho 1 asset — sẽ chạy N lần trong vòng lặp
        query = """
            INSERT INTO assets (id, name, type, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        try:
            # Bước 1: Tắt autocommit → bắt đầu transaction
            # Bình thường autocommit = True (mỗi SQL tự commit ngay)
            # Giờ tắt đi để gom nhiều INSERT vào 1 transaction
            self._conn.autocommit = False

            with self._conn.cursor() as cur:
                # Bước 2: INSERT từng asset
                # Vòng lặp for: chạy INSERT cho mỗi asset
                # Nếu 1 cái fail → except bắt → rollback tất cả
                for asset in assets:
                    cur.execute(query, (
                        asset.id,
                        asset.name,
                        asset.type.value,       # Enum → string
                        asset.status.value,     # Enum → string
                        asset.created_at,
                        asset.updated_at,
                    ))

            # Bước 3: Tất cả INSERT OK → COMMIT (lưu vào DB)
            self._conn.commit()
            logger.info(f"Batch created {len(assets)} assets (committed)")

        except psycopg2.errors.UniqueViolation:
            # Trùng ID → ROLLBACK (hủy tất cả INSERT đã chạy)
            self._conn.rollback()
            logger.warning("Batch create failed: duplicate ID, rolled back")
            raise DuplicateAssetError()

        except psycopg2.Error as e:
            # Lỗi DB khác (mất kết nối, syntax sai, ...) → ROLLBACK
            self._conn.rollback()
            logger.error(f"Batch create failed: {e}, rolled back")
            raise

        finally:
            # Bước 4: LUÔN bật lại autocommit cho các method khác
            # finally block LUÔN chạy — dù có lỗi hay không
            # Nếu thiếu dòng này → create(), update(), delete() sẽ bị hỏng
            # vì chúng dựa vào autocommit = True
            self._conn.autocommit = True

    # =========================================================================
    # [BÀI 3] BATCH DELETE — Xóa nhiều asset cùng lúc
    # =========================================================================

    def batch_delete(self, ids: List[str]) -> dict:
        """
        Xóa nhiều asset theo danh sách ID bằng SQL DELETE.

        Dùng 1 câu SQL duy nhất:
            DELETE FROM assets WHERE id = ANY(%s)

        ANY(%s) là gì?
            - PostgreSQL syntax để so sánh 1 cột với NHIỀU giá trị
            - Tương đương: WHERE id IN ('uuid1', 'uuid2', 'uuid3')
            - Nhưng ANY(%s) tương thích tốt hơn với parameterized query của psycopg2
            - %s nhận vào list Python → psycopg2 tự chuyển thành PostgreSQL array

        Cách tính not_found:
            - Truyền vào N id → SQL xóa được M dòng (rowcount)
            - not_found = N - M (số ID không khớp dòng nào trong DB)

        Args:
            ids: Danh sách UUID cần xóa

        Returns:
            dict {"deleted": int, "not_found": int}
        """
        self._ensure_connection()

        if not ids:
            return {"deleted": 0, "not_found": 0}

        # Câu SQL xóa nhiều dòng 1 lúc
        # ANY(%s::text[]) : ép kiểu array thành text[] trước khi so sánh
        # Vì cột id trong DB là kiểu uuid, còn Python truyền string
        # ::text[] ép mảng thành text, rồi PostgreSQL tự cast uuid ↔ text khi compare
        # Nếu không cast → lỗi "operator does not exist: uuid = text"
        query = "DELETE FROM assets WHERE id::text = ANY(%s)"

        with self._conn.cursor() as cur:
            # Truyền list ids cho ANY — psycopg2 tự convert list → PG array
            cur.execute(query, (ids,))

            # rowcount = số dòng thực sự bị xóa
            deleted = cur.rowcount

            # Số ID không tìm thấy = tổng truyền vào - số xóa được
            not_found = len(ids) - deleted

            return {"deleted": deleted, "not_found": not_found}

    # =========================================================================
    # [BÀI 6] PAGINATION & FILTERING — Phân trang + lọc
    # =========================================================================

    def list_paginated(
        self,
        page: int = 1,
        limit: int = 20,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """
        Lấy danh sách asset có phân trang và lọc theo type/status.

        Dùng 2 câu SQL:
            1. COUNT(*) với conditions → tổng số dòng thỏa điều kiện
            2. SELECT ... LIMIT ... OFFSET ... → lấy đúng trang cần

        OFFSET là gì?
            - OFFSET N: bỏ qua N dòng đầu tiên
            - Ví dụ: page=2, limit=10 → OFFSET 10 (bỏ 10 dòng trang 1)
            - Công thức: offset = (page - 1) * limit

        Args:
            page: Trang hiện tại (bắt đầu từ 1, không phải 0)
            limit: Số item mỗi trang
            asset_type: Lọc theo type — None = bỏ qua
            status: Lọc theo status — None = bỏ qua

        Returns:
            dict {"data": List[Asset], "total": int}
        """
        self._ensure_connection()

        # Xây dựng điều kiện WHERE động (kỹ thuật WHERE 1=1)
        conditions = "WHERE 1=1"
        params: list = []

        if asset_type:
            conditions += " AND type = %s"
            params.append(asset_type)

        if status:
            conditions += " AND status = %s"
            params.append(status)

        # --- Bước 1: Đếm tổng số dòng thỏa điều kiện ---
        count_query = f"SELECT COUNT(*) FROM assets {conditions}"
        with self._conn.cursor() as cur:
            cur.execute(count_query, params)
            total = cur.fetchone()[0]

        # --- Bước 2: Lấy dữ liệu trang hiện tại ---
        # OFFSET = số dòng cần bỏ qua (trang 1 → bỏ 0, trang 2 → bỏ limit, ...)
        offset = (page - 1) * limit

        # Thêm limit và offset vào cuối params
        data_params = params + [limit, offset]

        data_query = f"""
            SELECT id, name, type, status, created_at, updated_at
            FROM assets
            {conditions}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """


        with self._conn.cursor() as cur:
            cur.execute(data_query, data_params)
            rows = cur.fetchall()
            data = [self._row_to_asset(row) for row in rows]

        return {"data": data, "total": total}
