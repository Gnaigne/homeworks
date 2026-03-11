"""
=============================================================================
File: internal/config/config.py
Layer: Infrastructure (Clean Architecture)
Tác dụng: Đọc cấu hình database từ file .env hoặc environment variables.
=============================================================================

SESSION 3 MỚI THÊM — Session 2 không cần config vì dùng in-memory storage.
Khi chuyển sang dùng PostgreSQL (database thật), ta cần biết:
    - Database nằm ở đâu? (host, port)
    - Đăng nhập bằng gì? (user, password)
    - Tên database là gì? (db_name)

Những thông tin này KHÔNG NÊN viết cứng (hardcode) trong code, vì:
    1. Bảo mật: Nếu push code lên GitHub, mọi người đều thấy password
    2. Linh hoạt: Khi deploy lên server thật, host/port/password sẽ KHÁC
       - Máy mình: host=localhost, password=postgres
       - Server công ty: host=db.company.com, password=Str0ngP@ss!
    3. 12-Factor App: Đây là best practice trong ngành — config để ở environment

Cách hoạt động:
    1. File .env chứa các biến: DB_HOST=localhost, DB_PORT=5432, ...
    2. main.py dùng python-dotenv load file .env vào os.environ
    3. File này đọc os.environ → tạo object PostgresConfig
    4. PostgresConfig được truyền cho PostgresStorage để kết nối DB

Tương đương Go:
    type PostgresConfig struct { ... }
    func LoadPostgresConfig(file_name string) (*PostgresConfig, error)
    Go dùng thư viện viper để đọc config, Python dùng os.getenv() + dataclass.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------
# os: Thư viện có sẵn của Python, dùng để đọc biến môi trường (environment variables)
#     os.getenv("TEN_BIEN") → trả về giá trị của biến đó
#     Ví dụ: os.getenv("DB_HOST") → "localhost"
import os

# dataclass: Decorator có sẵn của Python (từ 3.7+), giúp tạo class chứa data nhanh gọn
#     Thay vì phải viết __init__, __repr__, __eq__ thủ công,
#     @dataclass tự generate hết cho mình.
#
#     Ví dụ KHÔNG dùng dataclass (viết thủ công):
#         class PostgresConfig:
#             def __init__(self, db_host, db_port, db_user, ...):
#                 self.db_host = db_host
#                 self.db_port = db_port
#                 self.db_user = db_user
#                 ...
#
#     Ví dụ CÓ dùng dataclass (ngắn gọn hơn nhiều):
#         @dataclass
#         class PostgresConfig:
#             db_host: str = "localhost"
#             db_port: str = "5432"
#             → Python tự tạo __init__(self, db_host="localhost", db_port="5432", ...)
from dataclasses import dataclass


# =============================================================================
# CLASS: PostgresConfig — Chứa thông tin kết nối database
# =============================================================================

@dataclass  # ← Decorator này bảo Python tự tạo __init__() từ các field bên dưới
class PostgresConfig:
    """
    Cấu hình kết nối PostgreSQL — gom tất cả thông tin DB vào 1 object.

    Tương đương Go struct:
        type PostgresConfig struct {
            DBHost     string `mapstructure:"DB_HOST"`
            DBPort     string `mapstructure:"DB_PORT"`
            ...
        }

    Tại sao dùng class thay vì dict thường?
        - dict: config["db_host"] → nếu gõ sai key sẽ lỗi runtime, IDE không gợi ý được
        - class: config.db_host → IDE gợi ý tên field, lỗi gõ sai bắt ngay lúc viết code

    Ví dụ sử dụng:
        config = PostgresConfig(db_host="localhost", db_port="5432", ...)
        print(config.db_host)              # → "localhost"
        print(config.connection_string)    # → "host=localhost port=5432 ..."
    """

    # -------------------------------------------------------------------------
    # Các field (thuộc tính) — mỗi dòng khai báo 1 thông tin kết nối
    # -------------------------------------------------------------------------
    # Cú pháp:  tên_field: kiểu_dữ_liệu = giá_trị_mặc_định
    #
    # "str" nghĩa là kiểu chuỗi (string).
    # "= ..." là giá trị mặc định — nếu không truyền vào thì dùng giá trị này.
    # Nhờ @dataclass, Python tự tạo:
    #   def __init__(self, db_host="localhost", db_port="5432", ...):
    #       self.db_host = db_host
    #       self.db_port = db_port
    #       ...

    db_host: str = "localhost"
    # ↑ Địa chỉ server PostgreSQL
    #   - "localhost" = database chạy trên chính máy mình (qua Docker)
    #   - Khi deploy: có thể là "10.0.0.5" hoặc "db.company.com"

    db_port: str = "5432"
    # ↑ Port mà PostgreSQL lắng nghe
    #   - 5432 là port mặc định của PostgreSQL (giống 3306 là của MySQL)
    #   - Kiểu str chứ không phải int vì connection string cần dạng text

    db_user: str = "postgres"
    # ↑ Username đăng nhập PostgreSQL
    #   - "postgres" là user mặc định khi cài PostgreSQL

    db_password: str = "postgres"
    # ↑ Password đăng nhập PostgreSQL
    #   - Development dùng password đơn giản cho tiện
    #   - Production PHẢI dùng password mạnh + KHÔNG được commit vào Git

    db_name: str = "mini_asm"
    # ↑ Tên database trong PostgreSQL
    #   - 1 server PostgreSQL có thể chứa NHIỀU database
    #   - App mình chỉ dùng 1 database tên "mini_asm"

    db_sslmode: str = "disable"
    # ↑ Chế độ mã hóa kết nối (SSL/TLS)
    #   - "disable": Không mã hóa — OK cho development vì DB chạy local
    #   - "require": Bắt buộc mã hóa — dùng cho production (bảo mật dữ liệu)

    # -------------------------------------------------------------------------
    # Property: connection_string — Tạo chuỗi kết nối cho psycopg2
    # -------------------------------------------------------------------------

    @property  # ← @property biến method thành thuộc tính, gọi bằng config.connection_string (KHÔNG cần ())
    def connection_string(self) -> str:
        """
        Ghép tất cả thông tin thành 1 chuỗi kết nối (DSN — Data Source Name).

        psycopg2 (thư viện kết nối PostgreSQL) cần chuỗi dạng:
            "host=localhost port=5432 user=postgres password=postgres dbname=mini_asm"

        @property là gì?
            - Bình thường method phải gọi: config.connection_string()  ← có ()
            - Với @property, gọi như thuộc tính: config.connection_string  ← không ()
            - Giống cách gọi config.db_host — trông tự nhiên hơn

        f-string là gì?
            - f"..." cho phép chèn biến Python vào giữa chuỗi
            - f"host={self.db_host}" → nếu db_host = "localhost" → "host=localhost"
            - Tương đương Go: fmt.Sprintf("host=%s", config.DBHost)

        Tương đương Go:
            connStr := fmt.Sprintf(
                "host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
                c.DBHost, c.DBPort, c.DBUser, c.DBPassword, c.DBName, c.DBSSLMode)

        Returns:
            str: Chuỗi kết nối hoàn chỉnh, ví dụ:
                 "host=localhost port=5432 user=postgres password=postgres dbname=mini_asm sslmode=disable"
        """
        # Dùng f-string ghép các field lại thành 1 chuỗi
        # Mỗi dòng f"..." là 1 phần, Python tự nối chúng lại (implicit string concatenation)
        # Cuối mỗi phần có dấu cách " " để ngăn cách các tham số
        return (
            f"host={self.db_host} "       # ← self.db_host = giá trị của thuộc tính db_host
            f"port={self.db_port} "       #    self = chính object PostgresConfig hiện tại
            f"user={self.db_user} "       #    Tương tự Go: c.DBUser (c là receiver)
            f"password={self.db_password} "
            f"dbname={self.db_name} "
            f"sslmode={self.db_sslmode}"  # ← dòng cuối KHÔNG có dấu cách thừa
        )


# =============================================================================
# FUNCTION: load_postgres_config — Đọc config từ environment variables
# =============================================================================

def load_postgres_config() -> PostgresConfig:
    """
    Đọc thông tin cấu hình PostgreSQL từ environment variables (biến môi trường).

    Luồng hoạt động:
        1. main.py gọi: dotenv.load_dotenv()
           → Đọc file .env, đưa các biến (DB_HOST=localhost, ...) vào os.environ
        2. main.py gọi: config = load_postgres_config()
           → Hàm này đọc os.environ → tạo PostgresConfig object
        3. main.py gọi: storage = PostgresStorage.from_config(config)
           → Truyền config cho PostgresStorage để kết nối database

    os.getenv("TEN_BIEN", "gia_tri_mac_dinh") là gì?
        - Đọc biến môi trường tên "TEN_BIEN"
        - Nếu biến đó TỒN TẠI → trả về giá trị của nó
        - Nếu biến đó KHÔNG tồn tại → trả về "gia_tri_mac_dinh"
        - Ví dụ: os.getenv("DB_HOST", "localhost")
            + Nếu file .env có DB_HOST=10.0.0.5 → trả về "10.0.0.5"
            + Nếu file .env KHÔNG có DB_HOST    → trả về "localhost"

    Tại sao dùng os.getenv() thay vì đọc file .env trực tiếp?
        - os.getenv() đọc từ environment — hoạt động ở MỌI nơi (Docker, K8s, CI/CD)
        - File .env chỉ là 1 CÁCH để set environment variables (dùng cho development)
        - Khi deploy production, DevOps set biến bằng cách khác (Docker secrets, vault, ...)

    Tương đương Go:
        func LoadPostgresConfig(file_name string) (*PostgresConfig, error) {
            viper.SetConfigFile(file_name)
            viper.ReadInConfig()
            viper.Unmarshal(&config)
            return &config, nil
        }
    Nhưng Python đơn giản hơn — chỉ cần os.getenv(), không cần thư viện ngoài.

    Returns:
        PostgresConfig: Object chứa đầy đủ thông tin kết nối database.
                        Nếu không có file .env → dùng các giá trị mặc định (phù hợp cho dev).
    """
    # Tạo PostgresConfig bằng cách đọc từng biến môi trường
    # Mỗi os.getenv() đọc 1 biến, có fallback mặc định nếu biến không tồn tại
    return PostgresConfig(
        db_host=os.getenv("DB_HOST", "localhost"),         # Đọc DB_HOST, mặc định "localhost"
        db_port=os.getenv("DB_PORT", "5432"),              # Đọc DB_PORT, mặc định "5432"
        db_user=os.getenv("DB_USER", "postgres"),          # Đọc DB_USER, mặc định "postgres"
        db_password=os.getenv("DB_PASSWORD", "postgres"),  # Đọc DB_PASSWORD, mặc định "postgres"
        db_name=os.getenv("DB_NAME", "mini_asm"),          # Đọc DB_NAME, mặc định "mini_asm"
        db_sslmode=os.getenv("DB_SSLMODE", "disable"),     # Đọc DB_SSLMODE, mặc định "disable"
    )
