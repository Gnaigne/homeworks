"""
=============================================================================
File: internal/storage/scan_storage.py
Layer: Infrastructure Layer — Interface (Clean Architecture)
Tác dụng: Định nghĩa interface cho việc lưu trữ các ScanJobs và Results (EASM).
=============================================================================
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from internal.model.scan import ScanJob, DNSRecord, WhoisRecord, SubdomainRecord, PortScanRecord, IPRecord, SSLRecord, TechRecord, CertTransRecord


class ScanStorage(ABC):
    """
    Interface cho tầng data access của EASM (ScanJobs & Results).
    
    Phân tách với Storage chính của Asset để tránh làm phình to interface `Storage`.
    Tuân thủ Interface Segregation Principle (ISP) trong SOLID.
    """

    # -------------------------------------------------------------------------
    # SCAN JOBS
    # -------------------------------------------------------------------------

    @abstractmethod
    def create_job(self, job: ScanJob) -> None:
        """Tạo mới một tiến trình quét (Scan Job)."""
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> ScanJob:
        """Lấy thông tin một Scan Job theo ID."""
        pass

    @abstractmethod
    def update_job_status(self, job_id: str, status: str, results: int = 0, error: Optional[str] = None) -> None:
        """Cập nhật trạng thái của Scan Job (kèm theo số lượng kết quả và lỗi nếu có)."""
        pass

    @abstractmethod
    def get_asset_scan_jobs(self, asset_id: str) -> List[ScanJob]:
        """Lấy lịch sử quét của một Asset."""
        pass

    # -------------------------------------------------------------------------
    # DNS RECORDS
    # -------------------------------------------------------------------------

    @abstractmethod
    def save_dns_records(self, records: List[DNSRecord]) -> None:
        """Lưu hàng loạt kết quả DNS vào DB."""
        pass

    @abstractmethod
    def get_dns_records(self, asset_id: str, job_id: Optional[str] = None) -> List[DNSRecord]:
        """Lấy kết quả DNS của 1 asset (và tùy chọn theo job)."""
        pass

    # -------------------------------------------------------------------------
    # WHOIS RECORDS
    # -------------------------------------------------------------------------

    @abstractmethod
    def save_whois_records(self, records: List[WhoisRecord]) -> None:
        """Lưu hàng loạt kết quả WHOIS vào DB."""
        pass

    @abstractmethod
    def get_whois_records(self, asset_id: str, job_id: Optional[str] = None) -> List[WhoisRecord]:
        """Lấy kết quả WHOIS của 1 asset (và tùy chọn theo job)."""
        pass

    # -------------------------------------------------------------------------
    # SUBDOMAIN RECORDS
    # -------------------------------------------------------------------------

    @abstractmethod
    def save_subdomains(self, records: List[SubdomainRecord]) -> None:
        """Lưu hàng loạt kết quả Subdomain vào DB."""
        pass

    @abstractmethod
    def get_subdomains(self, asset_id: str, job_id: Optional[str] = None) -> List[SubdomainRecord]:
        """Lấy kết quả Subdomain của 1 asset (và tùy chọn theo job)."""
        pass

    # -------------------------------------------------------------------------
    # PORT RECORDS
    # -------------------------------------------------------------------------

    @abstractmethod
    def save_port_records(self, records: List[PortScanRecord]) -> None:
        """Lưu hàng loạt kết quả Port vào DB."""
        pass

    @abstractmethod
    def get_port_records(self, asset_id: str, job_id: Optional[str] = None) -> List[PortScanRecord]:
        """Lấy kết quả Port của 1 asset (và tùy chọn theo job)."""
        pass

    # -------------------------------------------------------------------------
    # IP RECORDS (NEW)
    # -------------------------------------------------------------------------

    @abstractmethod
    def save_ip_records(self, records: List[IPRecord]) -> None:
        """Lưu hàng loạt kết quả IP (Geo & ASN) vào DB."""
        pass

    @abstractmethod
    def get_ip_records(self, asset_id: str, job_id: Optional[str] = None) -> List[IPRecord]:
        """Lấy kết quả IP của 1 asset."""
        pass

    # -------------------------------------------------------------------------
    # SSL RECORDS (NEW)
    # -------------------------------------------------------------------------

    @abstractmethod
    def save_ssl_records(self, records: List[SSLRecord]) -> None:
        pass

    @abstractmethod
    def get_ssl_records(self, asset_id: str, job_id: Optional[str] = None) -> List[SSLRecord]:
        pass

    # -------------------------------------------------------------------------
    # TECH RECORDS (NEW)
    # -------------------------------------------------------------------------

    @abstractmethod
    def save_tech_records(self, records: List[TechRecord]) -> None:
        pass

    @abstractmethod
    def get_tech_records(self, asset_id: str, job_id: Optional[str] = None) -> List[TechRecord]:
        pass

    # -------------------------------------------------------------------------
    # CERT_TRANS RECORDS (NEW)
    # -------------------------------------------------------------------------

    @abstractmethod
    def save_cert_trans_records(self, records: List[CertTransRecord]) -> None:
        pass

    @abstractmethod
    def get_cert_trans_records(self, asset_id: str, job_id: Optional[str] = None) -> List[CertTransRecord]:
        pass
