"""
=============================================================================
File: internal/scanner/base.py
Layer: Infrastructure/Scanner Layer
Tác dụng: Định nghĩa giao diện cơ sở cho mọi module quét EASM.
=============================================================================
"""

from abc import ABC, abstractmethod
from typing import Any

from internal.model.asset import Asset


class BaseScanner(ABC):
    """
    Interface chung cho tất cả các Scanner (DNS, WHOIS, Subdomain).
    Bất kỳ scanner nào mới thêm vào đều phải kế thừa class này.
    
    Giống với khái niệm Interface trong Go:
        type Scanner interface {
            Scan(asset *model.Asset) (ResultType, error)
        }
    """

    @abstractmethod
    async def scan(self, asset: Asset) -> Any:
        """
        Khởi chạy tiến trình quét dựa trên nội dung Asset.
        Vì hoạt động mạng I/O (call tới DNS server, HTTP API) tốn thời gian,
        hàm `scan` bắt buộc phải là hàm Async (`async def`) để không chặn
        Main Thread của FastAPI.
        
        Args:
            asset: Asset — Thực thể chứa `name` (VD: "example.com") 
                   và `type` (domain, ip).

        Returns:
            Any — Cấu trúc dữ liệu chứa kết quả (vd: List[CreateDNSRecordRequest]).
            Kết quả sẽ được ScanService thu nhận và lưu vào DB.
        """
        pass
