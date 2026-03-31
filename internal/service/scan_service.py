"""
=============================================================================
File: internal/service/scan_service.py
Layer: Application Layer — Business Logic (Clean Architecture)
Tác dụng: Quản lý luồng quét bề mặt tấn công (EASM), chứa business logic và pipeline quét mạng.
=============================================================================
"""

import logging
import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import BackgroundTasks

from internal.model.scan import (
    ScanJob, ScanType, ScanStatus, DNSRecord, WhoisRecord, SubdomainRecord, PortScanRecord,
    IPRecord, SSLRecord, TechRecord, CertTransRecord,
    AssetScanResultsResponse
)
from internal.storage.storage import Storage
from internal.storage.scan_storage import ScanStorage

from internal.scanner import (DNSScanner, WhoisScanner, SubdomainScanner, PortScanner,
                              IPScanner, SSLScanner, TechScanner, CertTransScanner)

logger = logging.getLogger("mini-asm.service.scan")

class ScanService:
    """
    Điều phối các quá trình quét EASM cho hệ thống.
    Khởi chạy Scanner, xử lý kết quả, cập nhật storage một cách bất đồng bộ.
    """

    def __init__(self, asset_storage: Storage, scan_storage: ScanStorage):
        self.asset_storage = asset_storage
        self.scan_storage = scan_storage
        
        # Khởi tạo các module máy quét
        self.dns_scanner = DNSScanner()
        self.whois_scanner = WhoisScanner()
        self.subdomain_scanner = SubdomainScanner()
        self.port_scanner = PortScanner()
        self.ip_scanner = IPScanner()
        self.ssl_scanner = SSLScanner()
        self.tech_scanner = TechScanner()
        self.cert_trans_scanner = CertTransScanner()

    def start_scan(self, asset_id: str, scan_type: ScanType, background_tasks: BackgroundTasks) -> ScanJob:
        """
        Tạo ScanJob mới và thêm tác vụ quét vào Background Tasks của FastAPI.
        Client gọi hàm này sẽ nhận về HTTP 202 Accepted ngay lập tức.
        
        Tương đương việc gọi Goroutine + return response ngay ở bên Go.
        """
        # 1. Kiểm tra xem Asset có tồn tại không
        asset = self.asset_storage.get_by_id(asset_id)

        # 2. Sinh Job ID
        job_id = str(uuid.uuid4())

        # 3. Tạo record ScanJob (Trạng thái Pending)
        job = ScanJob(
            id=job_id,
            asset_id=asset.id,
            scan_type=scan_type,
            status=ScanStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.scan_storage.create_job(job)

        # 4. Giao việc cho Background Tasks (Chạy hàm _run_scan_task)
        background_tasks.add_task(self._run_scan_task, job.id, asset.id, scan_type)

        return job

    async def _run_scan_task(self, job_id: str, asset_id: str, scan_type: ScanType) -> None:
        """
        Hàm xử lý ngầm (Worker).
        Gọi song song các Scanner (Concurrency).
        """
        logger.info(f"🚀 [Job {job_id}] Bắt đầu quy trình quét EASM cho asset {asset_id}")
        
        try:
            # Chuyển trạng thái lưu DB -> RUNNING
            self.scan_storage.update_job_status(job_id, ScanStatus.RUNNING.value)
            
            # Lấy object Asset thật
            asset = self.asset_storage.get_by_id(asset_id)
            
            # Lưu trữ các task pending
            tasks = []
            
            # --- Các hàm wrapper bọc logic insert SQL sau khi scan xong ---
            async def run_and_save_dns() -> int:
                res = await self.dns_scanner.scan(asset)
                records = [DNSRecord(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    scan_job_id=job_id,
                    record_type=r.record_type,
                    name=r.name,
                    value=r.value,
                    ttl=r.ttl,
                    created_at=datetime.now(timezone.utc)
                ) for r in res]
                self.scan_storage.save_dns_records(records)
                return len(records)
                
            async def run_and_save_whois() -> int:
                res = await self.whois_scanner.scan(asset)
                records = [WhoisRecord(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    scan_job_id=job_id,
                    domain=r.domain,
                    registrar=r.registrar,
                    creation_date=r.creation_date.replace(tzinfo=timezone.utc) if getattr(r.creation_date, 'tzinfo', None) is None else r.creation_date if r.creation_date else None,
                    expiration_date=r.expiration_date.replace(tzinfo=timezone.utc) if getattr(r.expiration_date, 'tzinfo', None) is None else r.expiration_date if r.expiration_date else None,
                    name_servers=r.name_servers,
                    status=r.status,
                    emails=r.emails,
                    raw_data=r.raw_data,
                    created_at=datetime.now(timezone.utc)
                ) for r in res]
                self.scan_storage.save_whois_records(records)
                return len(records)
                
            async def run_and_save_subdomain() -> int:
                res = await self.subdomain_scanner.scan(asset)
                records = [SubdomainRecord(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    scan_job_id=job_id,
                    subdomain=r.subdomain,
                    source=r.source,
                    is_active=r.is_active,
                    ip_address=r.ip_address,
                    created_at=datetime.now(timezone.utc)
                ) for r in res]
                self.scan_storage.save_subdomains(records)
                return len(records)
            
            async def run_and_save_port() -> int:
                res = await self.port_scanner.scan(asset)
                records = [PortScanRecord(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    scan_job_id=job_id,
                    port=r.port,
                    state=r.state,
                    service=r.service,
                    version=r.version,
                    banner=r.banner,
                    response_time_ms=r.response_time_ms,
                    created_at=datetime.now(timezone.utc)
                ) for r in res]
                self.scan_storage.save_port_records(records)
                return len(records)
            
            async def run_and_save_ip() -> int:
                res = await self.ip_scanner.scan(asset)
                records = [IPRecord(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    scan_job_id=job_id,
                    ip_address=r.ip_address,
                    geolocation=r.geolocation,
                    asn=r.asn,
                    reverse_dns=r.reverse_dns,
                    created_at=datetime.now(timezone.utc)
                ) for r in res]
                self.scan_storage.save_ip_records(records)
                return len(records)
            
            async def run_and_save_ssl() -> int:
                res = await self.ssl_scanner.scan(asset)
                records = [SSLRecord(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    scan_job_id=job_id,
                    domain=r.domain,
                    certificate=r.certificate,
                    connection=r.connection,
                    grade=r.grade,
                    issues=r.issues,
                    created_at=datetime.now(timezone.utc)
                ) for r in res]
                self.scan_storage.save_ssl_records(records)
                return len(records)
                
            async def run_and_save_tech() -> int:
                res = await self.tech_scanner.scan(asset)
                records = [TechRecord(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    scan_job_id=job_id,
                    domain=r.domain,
                    technologies=r.technologies,
                    headers=r.headers,
                    meta_tags=r.meta_tags,
                    created_at=datetime.now(timezone.utc)
                ) for r in res]
                self.scan_storage.save_tech_records(records)
                return len(records)

            async def run_and_save_cert_trans() -> int:
                res = await self.cert_trans_scanner.scan(asset)
                records = [CertTransRecord(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    scan_job_id=job_id,
                    domain=r.domain,
                    issuer_name=r.issuer_name,
                    not_before=r.not_before.replace(tzinfo=timezone.utc) if getattr(r.not_before, 'tzinfo', None) is None else r.not_before if r.not_before else None,
                    not_after=r.not_after.replace(tzinfo=timezone.utc) if getattr(r.not_after, 'tzinfo', None) is None else r.not_after if r.not_after else None,
                    created_at=datetime.now(timezone.utc)
                ) for r in res]
                self.scan_storage.save_cert_trans_records(records)
                return len(records)
            
            # -------------------------------------------------------------------------
            # BƯỚC 3: XẾP LỊCH CHẠY (Task Queuing)
            # -------------------------------------------------------------------------
            if scan_type in (ScanType.ALL, ScanType.DNS):
                tasks.append(run_and_save_dns())
            if scan_type in (ScanType.ALL, ScanType.WHOIS):
                tasks.append(run_and_save_whois())
            if scan_type in (ScanType.ALL, ScanType.SUBDOMAIN):
                tasks.append(run_and_save_subdomain())
            if scan_type in (ScanType.ALL, ScanType.PORT):
                tasks.append(run_and_save_port())
            if scan_type in (ScanType.ALL, ScanType.IP, ScanType.ASN):  # ASN query falls into IP logic theoretically (or handles differently, we map to IP)
                tasks.append(run_and_save_ip())
            if scan_type in (ScanType.ALL, ScanType.SSL):
                tasks.append(run_and_save_ssl())
            if scan_type in (ScanType.ALL, ScanType.TECH):
                tasks.append(run_and_save_tech())
            if scan_type in (ScanType.ALL, ScanType.CERT_TRANS):
                tasks.append(run_and_save_cert_trans())

            # -------------------------------------------------------------------------
            # BƯỚC 4: THÔNG QUAN CHẠY ĐỒNG THỜI (Concurrency)
            # 
            # 🎓 TEACHING NOTES:
            # - Hàm `asyncio.gather(*tasks)` là trái tim của Service này.
            # - Nó tương đương chính xác với việc tạo `sync.WaitGroup` ở trong Go.
            # - Thay vì gõ lệnh chạy Tuần Tự (chờ DNS -> 10s -> chờ Port -> 20s -> ...), 
            #   fastAPI sẽ tung hết 4 cái module này ra chạy song song Tật Lực cùng 1 lúc!
            # - Khi VÀ CHỈ KHI toàn bộ 4 thằng Culi đều đã chạy xong và gộp kết quả về mảng `results_counts`,
            #   thì hàm `gather` mới bắt đầu rẽ khóa, đi tiếp xuống dòng tính tổng Total bên dưới.
            # -------------------------------------------------------------------------
            results_counts = await asyncio.gather(*tasks)
            total_results = sum(results_counts)

            # Cập nhật thành công 
            self.scan_storage.update_job_status(job_id, ScanStatus.COMPLETED.value, results=total_results)
            logger.info(f"✅ [Job {job_id}] Đã hoàn tất thành công. Tìm thấy {total_results} results.")
            
        except Exception as e:
            logger.error(f"❌ [Job {job_id}] Thất bại hệ thống: {e}")
            self.scan_storage.update_job_status(job_id, ScanStatus.FAILED.value, error=str(e))

    def get_job(self, job_id: str) -> ScanJob:
        return self.scan_storage.get_job(job_id)

    def get_job_results(self, job_id: str) -> AssetScanResultsResponse:
        job = self.scan_storage.get_job(job_id)
        asset_id = job.asset_id

        dns_records = self.scan_storage.get_dns_records(asset_id, job_id)
        whois_records = self.scan_storage.get_whois_records(asset_id, job_id)
        subdomains = self.scan_storage.get_subdomains(asset_id, job_id)
        port_records = self.scan_storage.get_port_records(asset_id, job_id)
        ip_records = self.scan_storage.get_ip_records(asset_id, job_id)
        ssl_records = self.scan_storage.get_ssl_records(asset_id, job_id)
        tech_records = self.scan_storage.get_tech_records(asset_id, job_id)
        cert_trans_records = self.scan_storage.get_cert_trans_records(asset_id, job_id)

        return AssetScanResultsResponse(
            asset_id=asset_id,
            dns_records=dns_records,
            whois_records=whois_records,
            subdomains=subdomains,
            port_records=port_records,
            ip_records=ip_records,
            ssl_records=ssl_records,
            tech_records=tech_records,
            cert_trans_records=cert_trans_records
        )

    def get_asset_results(self, asset_id: str) -> AssetScanResultsResponse:
        self.asset_storage.get_by_id(asset_id) # validate xem asset có không
        
        dns_records = self.scan_storage.get_dns_records(asset_id)
        whois_records = self.scan_storage.get_whois_records(asset_id)
        subdomains = self.scan_storage.get_subdomains(asset_id)
        port_records = self.scan_storage.get_port_records(asset_id)
        ip_records = self.scan_storage.get_ip_records(asset_id)
        ssl_records = self.scan_storage.get_ssl_records(asset_id)
        tech_records = self.scan_storage.get_tech_records(asset_id)
        cert_trans_records = self.scan_storage.get_cert_trans_records(asset_id)

        return AssetScanResultsResponse(
            asset_id=asset_id,
            dns_records=dns_records,
            whois_records=whois_records,
            subdomains=subdomains,
            port_records=port_records,
            ip_records=ip_records,
            ssl_records=ssl_records,
            tech_records=tech_records,
            cert_trans_records=cert_trans_records
        )

    def get_asset_scan_jobs(self, asset_id: str) -> List[ScanJob]:
        self.asset_storage.get_by_id(asset_id) # validate xem asset có không
        return self.scan_storage.get_asset_scan_jobs(asset_id)

    def get_dns_records(self, asset_id: str) -> List[DNSRecord]:
        self.asset_storage.get_by_id(asset_id)
        return self.scan_storage.get_dns_records(asset_id)

    def get_whois_records(self, asset_id: str) -> List[WhoisRecord]:
        self.asset_storage.get_by_id(asset_id)
        return self.scan_storage.get_whois_records(asset_id)

    def get_subdomains(self, asset_id: str) -> List[SubdomainRecord]:
        self.asset_storage.get_by_id(asset_id)
        return self.scan_storage.get_subdomains(asset_id)

    def get_port_records(self, asset_id: str) -> List[PortScanRecord]:
        self.asset_storage.get_by_id(asset_id)
        return self.scan_storage.get_port_records(asset_id)

    def get_ip_records(self, asset_id: str) -> List[IPRecord]:
        self.asset_storage.get_by_id(asset_id)
        return self.scan_storage.get_ip_records(asset_id)

    def get_ssl_records(self, asset_id: str) -> List[SSLRecord]:
        self.asset_storage.get_by_id(asset_id)
        return self.scan_storage.get_ssl_records(asset_id)

    def get_tech_records(self, asset_id: str) -> List[TechRecord]:
        self.asset_storage.get_by_id(asset_id)
        return self.scan_storage.get_tech_records(asset_id)

    def get_cert_trans_records(self, asset_id: str) -> List[CertTransRecord]:
        self.asset_storage.get_by_id(asset_id)
        return self.scan_storage.get_cert_trans_records(asset_id)

