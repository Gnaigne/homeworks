"""
=============================================================================
File: internal/scanner/whois_scanner.py
Layer: Infrastructure/Scanner Layer
Tác dụng: Truy vấn dữ liệu WHOIS (nhà đăng ký, thời gian, Name Server).
=============================================================================
"""

import asyncio
import logging
import whois
from typing import List

from internal.model.asset import Asset, AssetType
from internal.model.scan import CreateWhoisRecordRequest
from internal.scanner.base import BaseScanner

logger = logging.getLogger("mini-asm.scanner.whois")

class WhoisScanner(BaseScanner):
    """
    Sử dụng thư viện `python-whois` để thực thi quét tin vùng tên miền.
    """

    async def scan(self, asset: Asset) -> List[CreateWhoisRecordRequest]:
        """
        Thực hiện truy vấn WHOIS. Cũng giống như dns, đây là I/O block, 
        cần bọc trong asyncio.to_thread hoặc run_in_executor.
        """
        if asset.type != AssetType.DOMAIN:
            return []

        domain = asset.name
        loop = asyncio.get_running_loop()

        try:
            # Truy vấn Whois là thao tác blocking
            w = await loop.run_in_executor(None, whois.whois, domain)
            
            # python-whois có thể trả về domain dưới định dạng list nếu có nhiều domains liên quan
            # Ta lấy dữ liệu an toàn (lấy first element nếu trả về list)
            def safe_get(val):
                if isinstance(val, list):
                    return val[0]
                return val

            # whois.whois có thể trả về string "name_servers" chứa \n hoặc một list.
            ns = w.name_servers
            ns_str = ", ".join(ns) if isinstance(ns, list) else ns

            # Kiểm tra xem whois lib có hỗ trợ trả về status/emails hay không
            w_status = getattr(w, 'status', None)
            status_str = ", ".join(w_status) if isinstance(w_status, list) else w_status
            
            #Biến emails_str sẽ gộp các email lại bằng dấu phẩy NẾU cục w_emails là một cái Mảng (List), 
            #CÒN KHÔNG THÌ giữ nguyên giá trị gốc của w_emails.
            w_emails = getattr(w, 'emails', None)
            emails_str = ", ".join(w_emails) if isinstance(w_emails, list) else w_emails

            result = CreateWhoisRecordRequest(
                domain=domain,
                registrar=safe_get(w.registrar),
                creation_date=safe_get(getattr(w, 'creation_date', None)),
                expiration_date=safe_get(getattr(w, 'expiration_date', None)),
                name_servers=ns_str,
                status=status_str,
                emails=emails_str,
                raw_data=w.text if hasattr(w, 'text') else None
            )
            
            logger.info(f"Đã lấy thành công WHOIS cho {domain}")
            return [result]

        except Exception as e:
            logger.warning(f"Lỗi khi quét WHOIS cho {domain}: {e}")
            return []
