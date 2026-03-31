"""
=============================================================================
File: internal/scanner/port_scanner.py
Layer: Infrastructure Layer — Scanner Implementation
Tác dụng: Quét trạm cổng TCP (Active Reconnaissance) đảm bảo tính an toàn.
=============================================================================
"""

import asyncio
import logging
import socket
import time
from typing import List

from internal.model.asset import Asset
from internal.model.scan import ScanType, CreatePortScanRecordRequest
from internal.scanner.base import BaseScanner

logger = logging.getLogger("mini-asm.scanner.port")


class PortScanner(BaseScanner):
    """
    Scanner thực hiện kiểm tra cổng mạng TCP.
    
    ⚠️ CẢNH BÁO AN TOÀN (SAFETY CHECKS):
    Đây là chức năng Active Scanning, tương đương với việc "Gõ cửa" máy chủ nhà người khác.
    Theo luật An Ninh Mạng, điều này là vi phạm nếu không được sự cho phép.
    Do đó, Scanner này bị giới hạn whitelist cứng, CHỈ CHO PHÉP quét tài sản cục bộ
    (IP: 127.0.0.1, localhost, ::1). Mọi target IP khác sẽ bị từ chối trực tiếp (Reject).
    """

    def __init__(self, timeout: int = 2):
        self.timeout = timeout
        
        # Danh sách whitelist duy nhất được phép quét
        self.authorized_ips = {
            "127.0.0.1",
            "localhost",
            "::1"
        }

        # Danh sách cổng kết nối phổ biến để dò quét (Common Ports)
        self.common_ports = [
            21,   # FTP
            22,   # SSH
            23,   # Telnet
            25,   # SMTP
            53,   # DNS
            80,   # HTTP
            110,  # POP3
            143,  # IMAP
            443,  # HTTPS
            445,  # SMB
            3306, # MySQL
            3389, # RDP
            5432, # PostgreSQL
            5900, # VNC
            8080, # HTTP Alt
            8443, # HTTPS Alt
        ]

    def get_type(self) -> ScanType:
        return ScanType.PORT

    def _is_authorized(self, target: str) -> bool:
        """Kiểm tra xem mục tiêu có được cấp phép quét hay không."""
        import ipaddress
        
        try:
            # Phân giải ra IP nếu là domain (ex: localhost)
            ip_str = target
            if not target[0].isdigit(): # Simple check if it might be a domain
                try:
                    ip_str = socket.gethostbyname(target)
                except socket.gaierror:
                    pass
                    
            ip = ipaddress.ip_address(ip_str)
            # Cho phép localhost và các dải mạng Private (10.x, 172.16.x, 192.168.x)
            return ip.is_loopback or ip.is_private
        except ValueError:
            return target in self.authorized_ips


    async def _scan_single_port(self, target: str, port: int) -> CreatePortScanRecordRequest:
        """
        Quét một port cụ thể bằng asyncio.open_connection() (non-blocking TCP Connect)
        """
        start_time = time.time()
        state = "closed"
        service = "unknown"
        banner = ""
        
        try:
            # Tạo non-blocking tcp stream tới port
            # Tương đương: conn, err := net.DialTimeout("tcp", address, timeout) trong Go
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(target, port), 
                timeout=self.timeout
            )
            
            state = "open"
            
            # -----------------------------------------------------------------
            # SERVICE DETECTION (BANNER GRABBING)
            # -----------------------------------------------------------------
            try:
                # Đọc tối đa 1024 bytes trả về đầu tiên để dò xem dịch vụ là gì
                # VD: Máy chủ SSH sẽ gửi chữ "SSH-2.0-OpenSSH..." ngay khi kết nối
                data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                if data:
                    banner = data.decode('utf-8', errors='ignore').strip()
                    
                    # Giả định sơ khởi dịch vụ dựa trên cờ
                    if banner.startswith("SSH-"):
                        service = "ssh"
                    elif "HTTP" in banner or "<html>" in banner.lower():
                        service = "http"
                    elif banner.startswith("220") and "FTP" in banner.upper():
                        service = "ftp"
                    elif banner.startswith("220") and "SMTP" in banner.upper():
                        service = "smtp"
                    else:
                        service = "unrecognized"
            except asyncio.TimeoutError:
                pass
            finally:
                writer.close()
                await writer.wait_closed()
                
        except (asyncio.TimeoutError, ConnectionRefusedError):
            state = "closed"
        except Exception as e:
            logger.debug(f"Port {port} gặp sự cố kết nối: {e}")
            state = "filtered"
            
        latency = int((time.time() - start_time) * 1000)
        
        return CreatePortScanRecordRequest(
            port=port,
            state=state,
            service=service,
            banner=banner,
            response_time_ms=latency
        )

    async def scan(self, asset: Asset) -> List[CreatePortScanRecordRequest]:
        target = asset.name
        
        logger.info(f"Khởi động tiến trình Port Scan cho {target}...")
        
        # ⚠️ CRITICAL SAFETY CHECK: Ngăn ngừa quét bên thứ 3
        if not self._is_authorized(target):
            logger.warning(
                f"⚠️ UNAUTHORIZED PORT SCAN BLOCKED! Target: {target}. "
                "Chỉ cho phép IP cục bộ (127.0.0.1) trên project học thuật này."
            )
            # Trả về rỗng do bị filter
            return []
            
        results = []
        
        # Thực thi quét đa luồng tất cả các port quy định thông qua coroutine
        # asyncio.gather giống y hệt sync.WaitGroup trong Go
        tasks = [self._scan_single_port(target, port) for port in self.common_ports]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in responses:
            if isinstance(res, Exception):
                logger.error(f"Lỗi unhandled khi test port: {res}")
                continue
            
            # Chỉ lưu lại những Port trạng thái "Open" vào DB
            if res.state == "open":
                results.append(res)
                
        logger.info(f"[Port Scan] {target}: Tìm thấy {len(results)} cổng đang mở.")
        return results
