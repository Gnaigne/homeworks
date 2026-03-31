"""
=============================================================================
File: internal/scanner/dns_scanner.py
Layer: Infrastructure/Scanner Layer
Tác dụng: Truy vấn các bản ghi DNS (A, AAAA, MX, NS, TXT, CNAME).
=============================================================================
"""

import asyncio
import logging
import dns.resolver
from typing import List

from internal.model.asset import Asset, AssetType
from internal.model.scan import CreateDNSRecordRequest
from internal.scanner.base import BaseScanner

logger = logging.getLogger("mini-asm.scanner.dns")

class DNSScanner(BaseScanner):
    """
    Sử dụng thư viện `dnspython` để truy xuất mạng.
    """

    async def scan(self, asset: Asset) -> List[CreateDNSRecordRequest]:
        """
        Thực hiện query DNS. 
        DNSPython (phiên bản chuẩn) dùng synchronous I/O.
        Do đó, để không block luồng asyncio của FastAPI, ta phải bọc gọi hàm 
        trong run_in_executor.

        Tương tự việc gọi Goroutine trong Go để chạy background job mà không 
        chặn tiến trình chính.
        """
        # DNS Scanner chỉ hoạt động trên tên miền
        if asset.type != AssetType.DOMAIN:
            logger.info(f"Bỏ qua quét DNS cho {asset.name} vì không phải domain.")
            return []

        domain = asset.name
        records_to_query = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME']
        results = []

        # Lấy event loop hiện tại
        loop = asyncio.get_running_loop()

        for qtype in records_to_query:
            try:
                # 🎓 TEACHING NOTES: Vấn đề của Thư Viện Cũ (Synchronous Libraries)
                # - Thư viện `dns.resolver.resolve` là hàm ĐỒNG BỘ CỔ ĐIỂN, nó chạy chặn luôn cả luồng CPU
                #   trong lúc đi hỏi máy chủ DNS ngoài mạng (google.com -> ? IP)
                # 
                # - Nếu ta gọi thẳng `dns.resolver.resolve(domain, qtype)` ở đây, toàn bộ 
                #   cơ chế event loop thần thánh `asyncio` của FastAPI sẽ bị "Đóng băng" ngang xương!
                #
                # Giải pháp: run_in_executor()
                # - FastAPI sẽ âm thầm ném cái việc nặng nhọc/chờ lâu này sang một *luồng rác* khác 
                #   gọi là ThreadPoolExecutor (đóng vai trò như 1 thằng culi phụ việc).
                # - Trong lúc thằng culi chạy đi hỏi DNS, Bồi Bàn (Event Loop chính) vẫn cứ nhởn nhơ 
                #   đi phục vụ xử lý Data cho các Scanner khác (Port, Subdomain) thay vì đứng chờ vô ích.
                # - Lệnh `await` chỉ đơn giản là: "Khi nào thằng culi có kết quả mang về thì gọi tao nhé!"
                answers = await loop.run_in_executor(None, dns.resolver.resolve, domain, qtype)
                
                for rdata in answers:
                    results.append(CreateDNSRecordRequest(
                        record_type=qtype,
                        value=rdata.to_text()
                    ))

            except dns.resolver.NoAnswer:
                # Không có bản ghi loại này
                pass
            except dns.resolver.NXDOMAIN:
                # Domain không tồn tại
                logger.warning(f"Domain không tồn tại: {domain}")
                break # Không cần quét tiếp nếu domain không tồn tại
            except Exception as e:
                # Lỗi timeout hoặc lỗi khác
                logger.debug(f"Không thể truy vấn bản ghi {qtype} cho {domain}: {e}")

        logger.info(f"Đã quét thành công DNS cho {domain}: {len(results)} records")
        return results
