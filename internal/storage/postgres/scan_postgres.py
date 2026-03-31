"""
=============================================================================
File: internal/storage/postgres/scan_postgres.py
Layer: Infrastructure Layer — Implementation
Tác dụng: Implement ScanStorage bằng PostgreSQL.
=============================================================================
"""

import logging
from typing import List, Optional
import psycopg2
import psycopg2.extras

from internal.model.scan import (ScanJob, ScanType, ScanStatus, DNSRecord, WhoisRecord, SubdomainRecord, PortScanRecord,
                                IPRecord, SSLRecord, TechRecord, CertTransRecord)
from internal.model.errors import AssetNotFoundError
from internal.storage.scan_storage import ScanStorage
from internal.config.config import PostgresConfig
from internal.database.retry import connect_with_retry

logger = logging.getLogger("mini-asm.storage.postgres.scan")


class PostgresScanStorage(ScanStorage):
    """
    Triển khai ScanStorage cho PostgreSQL.
    """

    def __init__(self, connection: "psycopg2.connection", connection_string: str = ""):
        self._conn = connection
        self._conn_string = connection_string

    @classmethod
    def from_config(cls, config: PostgresConfig) -> "PostgresScanStorage":
        conn = connect_with_retry(
            connection_string=config.connection_string,
            max_retries=5,
        )
        conn.autocommit = True
        return cls(conn, connection_string=config.connection_string)

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()

    def _reconnect(self) -> None:
        if not self._conn_string:
            raise RuntimeError("Không có connection string để reconnect")
        
        if self._conn and not self._conn.closed:
            self._conn.close()
        
        self._conn = psycopg2.connect(self._conn_string)
        self._conn.autocommit = True

    def _ensure_connection(self) -> None:
        if self._conn.closed:
            self._reconnect()
            return

        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception:
            self._reconnect()

    # =========================================================================
    # ROW MAPPERS (Helpers)
    #
    # 🎓 TEACHING NOTES:
    # Tại sao cần Row Mappers?
    # - Khi dùng thư viện psycopg2 thuần túy (không dùng ORM như SQLAlchemy), 
    #   kết quả trả về từ lệnh SELECT trong Database sẽ là một dạng Tuple: 
    #   ví dụ: (uuid, asset_id, scan_job_id, 'A', '1.1.1.1', '2026-...')
    # 
    # - Không thể gửi trực tiếp cái Tuple thô này về cho Frontend (API Client) được
    #   vì họ chẳng hiểu phần tử số 3, số 4 đại diện cho trường dữ liệu chữ gì.
    #
    # - Các hàm tĩnh (@staticmethod) dưới đây làm nhiệm vụ "Xưởng Lắp Ráp": 
    #   Chúng hút lần lượt từng phần tử của Tuple và nhét vào đúng biến tên cột
    #   của Pydantic Model (Data Transfer Object). Từ đó chuyển hoá Tuple vô hồn
    #   thành một Object có cấu trúc đàng hoàng để FastAPI tự động biến thành JSON!
    # =========================================================================

    @staticmethod
    def _row_to_scan_job(row: tuple) -> ScanJob:
        return ScanJob(
            id=str(row[0]),
            asset_id=str(row[1]),
            scan_type=ScanType(row[2]),
            status=ScanStatus(row[3]),
            error=row[4],
            results=row[5],
            created_at=row[6],
            updated_at=row[7],
        )

    @staticmethod
    def _row_to_dns(row: tuple) -> DNSRecord:
        return DNSRecord(
            id=str(row[0]),
            asset_id=str(row[1]),
            scan_job_id=str(row[2]),
            record_type=row[3],
            name=row[4],
            value=row[5],
            ttl=row[6],
            created_at=row[7]
        )

    @staticmethod
    def _row_to_whois(row: tuple) -> WhoisRecord:
        return WhoisRecord(
            id=str(row[0]),
            asset_id=str(row[1]),
            scan_job_id=str(row[2]),
            domain=row[3],
            registrar=row[4],
            creation_date=row[5],
            expiration_date=row[6],
            name_servers=row[7],
            status=row[8],
            emails=row[9],
            raw_data=row[10],
            created_at=row[11]
        )

    @staticmethod
    def _row_to_subdomain(row: tuple) -> SubdomainRecord:
        return SubdomainRecord(
            id=str(row[0]),
            asset_id=str(row[1]),
            scan_job_id=str(row[2]),
            subdomain=row[3],
            source=row[4],
            is_active=row[5],
            ip_address=row[6],
            created_at=row[7]
        )

    @staticmethod
    def _row_to_port(row: tuple) -> PortScanRecord:
        return PortScanRecord(
            id=str(row[0]),
            asset_id=str(row[1]),
            scan_job_id=str(row[2]),
            port=row[3],
            state=row[4],
            service=row[5],
            version=row[6],
            banner=row[7],
            response_time_ms=row[8],
            created_at=row[9]
        )

    @staticmethod
    def _row_to_ip(row: tuple) -> IPRecord:
        return IPRecord(
            id=str(row[0]),
            asset_id=str(row[1]),
            scan_job_id=str(row[2]),
            ip_address=row[3],
            geolocation=row[4],
            asn=row[5],
            reverse_dns=row[6],
            created_at=row[7]
        )

    @staticmethod
    def _row_to_ssl(row: tuple) -> SSLRecord:
        return SSLRecord(
            id=str(row[0]),
            asset_id=str(row[1]),
            scan_job_id=str(row[2]),
            domain=row[3],
            certificate=row[4],
            connection=row[5],
            grade=row[6],
            issues=row[7] if row[7] else [],
            created_at=row[8]
        )

    @staticmethod
    def _row_to_tech(row: tuple) -> TechRecord:
        return TechRecord(
            id=str(row[0]),
            asset_id=str(row[1]),
            scan_job_id=str(row[2]),
            domain=row[3],
            technologies=row[4] if row[4] else [],
            headers=row[5],
            meta_tags=row[6],
            created_at=row[7]
        )

    @staticmethod
    def _row_to_cert_trans(row: tuple) -> CertTransRecord:
        return CertTransRecord(
            id=str(row[0]),
            asset_id=str(row[1]),
            scan_job_id=str(row[2]),
            domain=row[3],
            issuer_name=row[4],
            not_before=row[5],
            not_after=row[6],
            created_at=row[7]
        )

    # =========================================================================
    # JOBS
    # =========================================================================

    def create_job(self, job: ScanJob) -> None:
        self._ensure_connection()
        query = """
            INSERT INTO scan_jobs (id, asset_id, scan_type, status, error, results, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with self._conn.cursor() as cur:
                cur.execute(query, (
                    job.id,
                    job.asset_id,
                    job.scan_type.value,
                    job.status.value,
                    job.error,
                    job.results,
                    job.created_at,
                    job.updated_at
                ))
        except psycopg2.errors.ForeignKeyViolation:
            raise AssetNotFoundError()
        except Exception as e:
            logger.error(f"Failed to create scan job: {e}")
            raise

    def get_job(self, job_id: str) -> ScanJob:
        self._ensure_connection()
        query = """
            SELECT id, asset_id, scan_type, status, error, results, created_at, updated_at
            FROM scan_jobs
            WHERE id = %s
        """
        with self._conn.cursor() as cur:
            cur.execute(query, (job_id,))
            row = cur.fetchone()
            if row is None:
                # Có thể định nghĩa thêm ScanJobNotFoundError nếu cần
                raise AssetNotFoundError()
            return self._row_to_scan_job(row)

    def update_job_status(self, job_id: str, status: str, results: int = 0, error: Optional[str] = None) -> None:
        self._ensure_connection()
        query = """
            UPDATE scan_jobs
            SET status = %s, results = %s, error = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        with self._conn.cursor() as cur:
            cur.execute(query, (status, results, error, job_id))
            if cur.rowcount == 0:
                raise AssetNotFoundError()

    def get_asset_scan_jobs(self, asset_id: str) -> List[ScanJob]:
        self._ensure_connection()
        query = """
            SELECT id, asset_id, scan_type, status, error, results, created_at, updated_at
            FROM scan_jobs
            WHERE asset_id = %s
            ORDER BY created_at DESC
        """
        with self._conn.cursor() as cur:
            cur.execute(query, (asset_id,))
            rows = cur.fetchall()
            return [self._row_to_scan_job(row) for row in rows]

    # =========================================================================
    # DNS RECORDS
    # =========================================================================

    def save_dns_records(self, records: List[DNSRecord]) -> None:
        """
        Lưu Hàng Loạt (Bulk Insert) Bản ghi DNS.
        
        🎓 TEACHING NOTES - Bulk Insert Performance:
        Thay vì chạy 100 câu lệnh INSERT riêng lẻ mất rất nhiều thời gian, thư viện 
        `psycopg2.extras.execute_values` sẽ gộp 100 bộ values đó lại thành một 
        câu truy vấn khổng lồ kiểu: INSERT INTO tbl VALUES (...), (...), (...)
        Việc này giúp tốc độ chèn Database nhanh gấp hàng chục lần!
        """
        if not records:
            return
        self._ensure_connection()
        query = """
            INSERT INTO dns_records (id, asset_id, scan_job_id, record_type, value, created_at)
            VALUES %s
        """
        # Chuyển đổi List[DNSRecord] thành list các tuples
        values = [(
            r.id, r.asset_id, r.scan_job_id, r.record_type, r.value, r.created_at
        ) for r in records]
        
        with self._conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, values)

    def get_dns_records(self, asset_id: str, job_id: Optional[str] = None) -> List[DNSRecord]:
        """
        Khi không truyền job_id, tự động tìm scan_job_id mới nhất trong bảng dns_records
        (thay vì lấy toàn bộ lịch sử), đảm bảo chỉ hiển thị lần quét gần nhất.
        Khi có job_id cụ thể, lọc theo job đó.
        """
        self._ensure_connection()
        if job_id:
            query = """
                SELECT id, asset_id, scan_job_id, record_type, name, value, ttl, created_at
                FROM dns_records
                WHERE asset_id = %s AND scan_job_id = %s
            """
            params = (asset_id, job_id)
        else:
            query = """
                SELECT id, asset_id, scan_job_id, record_type, name, value, ttl, created_at
                FROM dns_records
                WHERE asset_id = %s
                AND scan_job_id = (
                    SELECT scan_job_id FROM dns_records
                    WHERE asset_id = %s
                    ORDER BY created_at DESC LIMIT 1
                )
            """
            params = (asset_id, asset_id)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_dns(row) for row in rows]

    # =========================================================================
    # WHOIS RECORDS
    # =========================================================================

    def save_whois_records(self, records: List[WhoisRecord]) -> None:
        if not records:
            return
        self._ensure_connection()
        query = """
            INSERT INTO whois_records (
                id, asset_id, scan_job_id, domain, registrar, 
                creation_date, expiration_date, name_servers, status, emails, raw_data, created_at
            ) VALUES %s
        """
        values = [(
            r.id, r.asset_id, r.scan_job_id, r.domain, r.registrar,
            r.creation_date, r.expiration_date, r.name_servers, r.status, r.emails, r.raw_data, r.created_at
        ) for r in records]

        with self._conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, values)

    def get_whois_records(self, asset_id: str, job_id: Optional[str] = None) -> List[WhoisRecord]:
        self._ensure_connection()
        if job_id:
            query = """
                SELECT id, asset_id, scan_job_id, domain, registrar,
                       creation_date, expiration_date, name_servers, status, emails, raw_data, created_at
                FROM whois_records
                WHERE asset_id = %s AND scan_job_id = %s
            """
            params = (asset_id, job_id)
        else:
            query = """
                SELECT id, asset_id, scan_job_id, domain, registrar,
                       creation_date, expiration_date, name_servers, status, emails, raw_data, created_at
                FROM whois_records
                WHERE asset_id = %s
                AND scan_job_id = (
                    SELECT scan_job_id FROM whois_records
                    WHERE asset_id = %s
                    ORDER BY created_at DESC LIMIT 1
                )
            """
            params = (asset_id, asset_id)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_whois(row) for row in rows]

    # =========================================================================
    # SUBDOMAIN RECORDS
    # =========================================================================

    def save_subdomains(self, records: List[SubdomainRecord]) -> None:
        if not records:
            return
        self._ensure_connection()
        query = """
            INSERT INTO subdomains (id, asset_id, scan_job_id, subdomain, source, is_active, ip_address, created_at)
            VALUES %s
        """
        values = [(
            r.id, r.asset_id, r.scan_job_id, r.subdomain, r.source, r.is_active, r.ip_address, r.created_at
        ) for r in records]

        with self._conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, values)

    def get_subdomains(self, asset_id: str, job_id: Optional[str] = None) -> List[SubdomainRecord]:
        self._ensure_connection()
        if job_id:
            query = """
                SELECT id, asset_id, scan_job_id, subdomain, source, is_active, ip_address, created_at
                FROM subdomains
                WHERE asset_id = %s AND scan_job_id = %s
            """
            params = (asset_id, job_id)
        else:
            query = """
                SELECT id, asset_id, scan_job_id, subdomain, source, is_active, ip_address, created_at
                FROM subdomains
                WHERE asset_id = %s
                AND scan_job_id = (
                    SELECT scan_job_id FROM subdomains
                    WHERE asset_id = %s
                    ORDER BY created_at DESC LIMIT 1
                )
            """
            params = (asset_id, asset_id)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_subdomain(row) for row in rows]

    # =========================================================================
    # PORT RECORDS
    # =========================================================================

    def save_port_records(self, records: List[PortScanRecord]) -> None:
        if not records:
            return
        self._ensure_connection()
        query = """
            INSERT INTO port_records (
                id, asset_id, scan_job_id, port, state, 
                service, version, banner, response_time_ms, created_at
            ) VALUES %s
        """
        values = [(
            r.id, r.asset_id, r.scan_job_id, r.port, r.state,
            r.service, r.version, r.banner, r.response_time_ms, r.created_at
        ) for r in records]

        with self._conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, values)

    def get_port_records(self, asset_id: str, job_id: Optional[str] = None) -> List[PortScanRecord]:
        self._ensure_connection()
        if job_id:
            query = """
                SELECT id, asset_id, scan_job_id, port, state,
                       service, version, banner, response_time_ms, created_at
                FROM port_records
                WHERE asset_id = %s AND scan_job_id = %s
            """
            params = (asset_id, job_id)
        else:
            query = """
                SELECT id, asset_id, scan_job_id, port, state,
                       service, version, banner, response_time_ms, created_at
                FROM port_records
                WHERE asset_id = %s
                AND scan_job_id = (
                    SELECT scan_job_id FROM port_records
                    WHERE asset_id = %s
                    ORDER BY created_at DESC LIMIT 1
                )
            """
            params = (asset_id, asset_id)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_port(row) for row in rows]

    # =========================================================================
    # IP RECORDS (NEW)
    # =========================================================================

    def save_ip_records(self, records: List[IPRecord]) -> None:
        if not records:
            return
        self._ensure_connection()
        query = """
            INSERT INTO ip_records (
                id, asset_id, scan_job_id, ip_address, geolocation, 
                asn, reverse_dns, created_at
            ) VALUES %s
        """
        values = [(
            r.id, r.asset_id, r.scan_job_id, r.ip_address,
            
            # `geolocation` và `asn` là kiểu Dict (Dictionary/JSON) trong Model và trong Database thiết kế là cột JSONB.
            # Ta KHÔNG THỂ truyền Object Dict của Python thẳng vào query SQL.
            # Bắt buộc phải dùng psycopg2.extras.Json() ép Python chuyển Dictionary thành string JSON 
            # để PosgreSQL hiểu và cho vào Data Type JSONB. Nếu None thì chèn thẳng giá trị None (NULL trong SQL).
            psycopg2.extras.Json(r.geolocation) if r.geolocation is not None else None,
            psycopg2.extras.Json(r.asn) if r.asn is not None else None,
            
            # `reverse_dns` chỉ là một chuỗi văn bản thuần túy (Text Type) ví dụ: "one.one.one.one"
            # Nên truyền thẳng giá trị của nó vào là được, không cần ép Json.
            r.reverse_dns, 
            r.created_at
        ) for r in records]

        with self._conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, values)

    def get_ip_records(self, asset_id: str, job_id: Optional[str] = None) -> List[IPRecord]:
        self._ensure_connection()
        if job_id:
            query = """
                SELECT id, asset_id, scan_job_id, ip_address, geolocation,
                       asn, reverse_dns, created_at
                FROM ip_records
                WHERE asset_id = %s AND scan_job_id = %s
            """
            params = (asset_id, job_id)
        else:
            query = """
                SELECT id, asset_id, scan_job_id, ip_address, geolocation,
                       asn, reverse_dns, created_at
                FROM ip_records
                WHERE asset_id = %s
                AND scan_job_id = (
                    SELECT scan_job_id FROM ip_records
                    WHERE asset_id = %s
                    ORDER BY created_at DESC LIMIT 1
                )
            """
            params = (asset_id, asset_id)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_ip(row) for row in rows]

    # =========================================================================
    # SSL RECORDS (NEW)
    # =========================================================================

    def save_ssl_records(self, records: List[SSLRecord]) -> None:
        if not records:
            return
        self._ensure_connection()
        query = """
            INSERT INTO ssl_records (
                id, asset_id, scan_job_id, domain, certificate, 
                connection, grade, issues, created_at
            ) VALUES %s
        """
        values = [(
            r.id, r.asset_id, r.scan_job_id, r.domain,
            psycopg2.extras.Json(r.certificate) if r.certificate is not None else None,
            psycopg2.extras.Json(r.connection) if r.connection is not None else None,
            r.grade,
            psycopg2.extras.Json(r.issues) if r.issues is not None else '[]',
            r.created_at
        ) for r in records]

        with self._conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, values)

    def get_ssl_records(self, asset_id: str, job_id: Optional[str] = None) -> List[SSLRecord]:
        self._ensure_connection()
        if job_id:
            query = """
                SELECT id, asset_id, scan_job_id, domain, certificate,
                       connection, grade, issues, created_at
                FROM ssl_records
                WHERE asset_id = %s AND scan_job_id = %s
            """
            params = (asset_id, job_id)
        else:
            query = """
                SELECT id, asset_id, scan_job_id, domain, certificate,
                       connection, grade, issues, created_at
                FROM ssl_records
                WHERE asset_id = %s
                AND scan_job_id = (
                    SELECT scan_job_id FROM ssl_records
                    WHERE asset_id = %s
                    ORDER BY created_at DESC LIMIT 1
                )
            """
            params = (asset_id, asset_id)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_ssl(row) for row in rows]

    # =========================================================================
    # TECH RECORDS (NEW)
    # =========================================================================

    def save_tech_records(self, records: List[TechRecord]) -> None:
        if not records:
            return
        self._ensure_connection()
        query = """
            INSERT INTO tech_records (
                id, asset_id, scan_job_id, domain, technologies, 
                headers, meta_tags, created_at
            ) VALUES %s
        """
        values = [(
            r.id, r.asset_id, r.scan_job_id, r.domain,
            psycopg2.extras.Json(r.technologies) if r.technologies is not None else '[]',
            psycopg2.extras.Json(r.headers) if r.headers is not None else None,
            psycopg2.extras.Json(r.meta_tags) if r.meta_tags is not None else None,
            r.created_at
        ) for r in records]

        with self._conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, values)

    def get_tech_records(self, asset_id: str, job_id: Optional[str] = None) -> List[TechRecord]:
        self._ensure_connection()
        if job_id:
            query = """
                SELECT id, asset_id, scan_job_id, domain, technologies,
                       headers, meta_tags, created_at
                FROM tech_records
                WHERE asset_id = %s AND scan_job_id = %s
            """
            params = (asset_id, job_id)
        else:
            query = """
                SELECT id, asset_id, scan_job_id, domain, technologies,
                       headers, meta_tags, created_at
                FROM tech_records
                WHERE asset_id = %s
                AND scan_job_id = (
                    SELECT scan_job_id FROM tech_records
                    WHERE asset_id = %s
                    ORDER BY created_at DESC LIMIT 1
                )
            """
            params = (asset_id, asset_id)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_tech(row) for row in rows]

    # =========================================================================
    # CERT TRANS RECORDS (NEW)
    # =========================================================================

    def save_cert_trans_records(self, records: List[CertTransRecord]) -> None:
        if not records:
            return
        self._ensure_connection()
        query = """
            INSERT INTO cert_trans_records (
                id, asset_id, scan_job_id, domain, issuer_name, 
                not_before, not_after, created_at
            ) VALUES %s
        """
        values = [(
            r.id, r.asset_id, r.scan_job_id, r.domain, r.issuer_name,
            r.not_before, r.not_after, r.created_at
        ) for r in records]

        with self._conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, query, values)

    def get_cert_trans_records(self, asset_id: str, job_id: Optional[str] = None) -> List[CertTransRecord]:
        self._ensure_connection()
        if job_id:
            query = """
                SELECT id, asset_id, scan_job_id, domain, issuer_name,
                       not_before, not_after, created_at
                FROM cert_trans_records
                WHERE asset_id = %s AND scan_job_id = %s
            """
            params = (asset_id, job_id)
        else:
            query = """
                SELECT id, asset_id, scan_job_id, domain, issuer_name,
                       not_before, not_after, created_at
                FROM cert_trans_records
                WHERE asset_id = %s
                AND scan_job_id = (
                    SELECT scan_job_id FROM cert_trans_records
                    WHERE asset_id = %s
                    ORDER BY created_at DESC LIMIT 1
                )
            """
            params = (asset_id, asset_id)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_cert_trans(row) for row in rows]

