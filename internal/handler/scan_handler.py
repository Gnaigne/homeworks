"""
=============================================================================
File: internal/handler/scan_handler.py
Layer: Presentation Layer — HTTP Handler
Tác dụng: Xử lý các HTTP request mới cho quy trình quét (EASM).
=============================================================================
"""

import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional
from pydantic import BaseModel

from internal.model.scan import (
    ScanJob, CreateScanJobRequest, AssetScanResultsResponse, 
    DNSRecord, WhoisRecord, SubdomainRecord, PortScanRecord
)
from internal.model.errors import AssetNotFoundError
from internal.service.scan_service import ScanService

logger = logging.getLogger("mini-asm.handler.scan")

def _map_error_to_http(error: Exception) -> HTTPException:
    if isinstance(error, AssetNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    else:
        logger.error(f"Unexpected error: {error}", exc_info=True)
        return HTTPException(status_code=500, detail="internal server error")

def create_scan_router(service: ScanService) -> APIRouter:
    # Router này dành cho scan, nhưng ta có thể gắn vào 2 prefix khác nhau (/assets và /scan-jobs)
    # Vì thế ta chỉ gán router tổng và gán tên cụ thể ở sub-routes
    router = APIRouter(tags=["EASM Scans"])

    # -----------------------------------------------------------------
    # POST /assets/{id}/scan — Bắt đầu quét EASM
    # -----------------------------------------------------------------
    @router.post(
        "/assets/{id}/scan",
        response_model=ScanJob,
        status_code=202,
        summary="Cấp lệnh quét Asset",
        description="Bắt đầu chạy pipeline quét (DNS, WHOIS, Subdomain). \nTrả về Job ID và chạy ngầm tiến trình (Background Processing)."
    )
    def start_scan(id: str, request: CreateScanJobRequest, background_tasks: BackgroundTasks) -> ScanJob:
        """
        Hàm dùng BackgroundTasks của FastAPI để gửi công việc chạy dưới nền.
        """
        try:
            job = service.start_scan(id, request.scan_type, background_tasks)
            logger.info(f"Accepted scan job {job.id} for asset {id}")
            return job
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /scan-jobs/{id} — Theo dõi trạng thái một job
    # -----------------------------------------------------------------
    @router.get(
        "/scan-jobs/{id}",
        response_model=ScanJob,
        summary="Theo dõi Scan Job",
        description="Trả ra metadata và thông tin trạng thái của Scan Job"
    )
    def get_scan_job(id: str) -> ScanJob:
        try:
            return service.get_job(id)
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /scan-jobs/{id}/results — Xem kết quả của riêng một job nọ
    # -----------------------------------------------------------------
    @router.get(
        "/scan-jobs/{id}/results",
        response_model=AssetScanResultsResponse,
        summary="Kết quả một Scan Job",
        description="Xem thành quả scan (của job cụ thể này)."
    )
    def get_job_results(id: str) -> AssetScanResultsResponse:
        try:
            return service.get_job_results(id)
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /assets/{id}/results —  TOÀN BỘ kết quả của một asset
    # -----------------------------------------------------------------
    @router.get(
        "/assets/{id}/results",
        response_model=AssetScanResultsResponse,
        summary="Tổng hợp kết quả Asset",
        description="Lấy toàn bộ kết quả tổng hợp của tất cả các job cũ tới nay."
    )
    def get_asset_results(id: str) -> AssetScanResultsResponse:
        try:
            return service.get_asset_results(id)
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /assets/{id}/scans — Danh sách các lần quét của 1 asset
    # -----------------------------------------------------------------
    @router.get(
        "/assets/{id}/scans",
        summary="Lịch sử quét của 1 Asset",
        description="Trả về danh sách các tác vụ quét từng thực hiện trên Asset này."
    )
    def get_asset_scans(id: str, page: int = Query(1), page_size: int = Query(10)) -> dict:
        try:
            records = service.get_asset_scan_jobs(id)
            start = (page - 1) * page_size
            items = records[start:start + page_size]
            return {
                "data": items,
                "total": len(records),
                "page": page,
                "page_size": page_size,
                "total_pages": max(1, (len(records) + page_size - 1) // page_size)
            }
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /assets/{id}/dns — Chi tiết kết quả DNS
    # -----------------------------------------------------------------
    @router.get("/assets/{id}/dns")
    def get_asset_dns(
        id: str, 
        page: int = Query(1), 
        page_size: int = Query(10), 
        search: Optional[str] = Query(None),
        type: Optional[str] = Query(None)
    ) -> dict:
        try:
            records = service.get_dns_records(id)
            
            if search:
                search_lower = search.lower()
                records = [r for r in records if (r.name and search_lower in r.name.lower()) or (r.value and search_lower in (str(r.value)).lower())]
            if type:
                records = [r for r in records if r.record_type and r.record_type.lower() == type.lower()]
                
            start = (page - 1) * page_size
            items = records[start:start + page_size]
            return {
                "data": items,
                "total": len(records),
                "page": page,
                "page_size": page_size,
                "total_pages": max(1, (len(records) + page_size - 1) // page_size)
            }
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /assets/{id}/whois — Chi tiết kết quả WHOIS
    # -----------------------------------------------------------------
    @router.get("/assets/{id}/whois")
    def get_asset_whois(id: str) -> dict:
        try:
            records = service.get_whois_records(id)
            whois_data = records[0] if records else None
            return {"data": whois_data}
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /assets/{id}/subdomains — Chi tiết kết quả Subdomains
    # -----------------------------------------------------------------
    @router.get("/assets/{id}/subdomains")
    def get_asset_subdomains(
        id: str,
        page: int = Query(1), 
        page_size: int = Query(10), 
        search: Optional[str] = Query(None),
        active: Optional[str] = Query(None)
    ) -> dict:
        try:
            records = service.get_subdomains(id)
            
            if search:
                search_lower = search.lower()
                records = [r for r in records if r.subdomain and search_lower in r.subdomain.lower()]
            if active == "true":
                records = [r for r in records if r.is_active]
            elif active == "false":
                records = [r for r in records if not r.is_active]
                
            start = (page - 1) * page_size
            items = records[start:start + page_size]
            return {
                "data": items,
                "total": len(records),
                "page": page,
                "page_size": page_size,
                "total_pages": max(1, (len(records) + page_size - 1) // page_size)
            }
        except Exception as e:
            raise _map_error_to_http(e)
    # -----------------------------------------------------------------
    # GET /assets/{id}/port — Chi tiết kết quả Port Scan
    # -----------------------------------------------------------------
    @router.get("/assets/{id}/port")
    def get_asset_port(id: str) -> dict:
        try:
            records = service.get_port_records(id)
            return {"data": records}
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /assets/{id}/ip — Chi tiết kết quả IP Scan
    # -----------------------------------------------------------------
    @router.get("/assets/{id}/ip")
    def get_asset_ip(id: str) -> dict:
        try:
            records = service.get_ip_records(id)
            return {"data": records}
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /assets/{id}/ssl — Chi tiết kết quả SSL Scan
    # -----------------------------------------------------------------
    @router.get("/assets/{id}/ssl")
    def get_asset_ssl(id: str) -> dict:
        try:
            records = service.get_ssl_records(id)
            return {"data": records}
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /assets/{id}/tech — Chi tiết kết quả Technology
    # -----------------------------------------------------------------
    @router.get("/assets/{id}/tech")
    def get_asset_tech(id: str) -> dict:
        try:
            records = service.get_tech_records(id)
            return {"data": records}
        except Exception as e:
            raise _map_error_to_http(e)

    # -----------------------------------------------------------------
    # GET /assets/{id}/cert_trans — Chi tiết kết quả Cert Transparency
    # -----------------------------------------------------------------
    @router.get("/assets/{id}/cert_trans")
    def get_asset_cert_trans(id: str) -> dict:
        try:
            records = service.get_cert_trans_records(id)
            return {"data": records}
        except Exception as e:
            raise _map_error_to_http(e)

    return router
