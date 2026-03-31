import logging
import socket
from typing import List
import aiohttp

from internal.model.asset import Asset
from internal.model.scan import CreateIPRecordRequest
from internal.scanner.base import BaseScanner

logger = logging.getLogger("mini-asm.scanner.ip")

class IPScanner(BaseScanner):
    """
    Máy quét lấy thông tin Geolocation và ASN cho một IP.
    Tuân thủ mô hình Non-blocking I/O (aiohttp).
    """

    async def scan(self, asset: Asset) -> List[CreateIPRecordRequest]:
        target = asset.name
        results = []

        try:
            # 1. Chuyển đổi target thành IP nếu asset là domain
            ip_address = target
            if asset.type == "domain":
                try:
                    ip_address = socket.gethostbyname(target)
                    logger.info(f"Đã phân giải domain {target} thành IP {ip_address}")
                except Exception as ex:
                    logger.warning(f"Không thể phân giải {target} thành IP: {ex}")
                    return results

            # 2. Gọi API ip-api (miễn phí, không cần auth, <45 req/min)
            # Truyền đúng fields cần thiết cho Geolocation & ASN & Reverse
            api_url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country,countryCode,regionName,city,lat,lon,isp,org,as,asname,reverse"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=10) as response:
                    data = await response.json()
                    
                    if data.get("status") != "success":
                        logger.warning(f"IP API query failed cho {ip_address}: {data.get('message')}")
                        return results

                    # 3. Phân tách Geolocation Dictionary
                    geolocation = {
                        "country": data.get("country", ""),
                        "country_code": data.get("countryCode", ""),
                        "city": data.get("city", ""),
                        "region": data.get("regionName", ""),
                        "latitude": float(data.get("lat", 0.0)),
                        "longitude": float(data.get("lon", 0.0)),
                        "isp": data.get("isp", ""),
                        "org": data.get("org", "")
                    }

                    # 4. Phân tách ASN Dictionary
                    as_raw = data.get("as", "")
                    asn_number = 0
                    if as_raw and as_raw.startswith("AS"):
                        try:
                            # Lấy số từ block string ví dụ: "AS13335 Cloudflare, Inc."
                            parts = as_raw.split(" ", 1)
                            asn_number = int(parts[0].replace("AS", ""))
                        except ValueError:
                            pass
                            
                    asn = {
                        "number": asn_number,
                        "name": data.get("asname", ""),
                        "description": as_raw
                    }

                    reverse_dns = data.get("reverse", "")
                    
                    record = CreateIPRecordRequest(
                        ip_address=ip_address,
                        geolocation=geolocation,
                        asn=asn,
                        reverse_dns=reverse_dns
                    )
                    results.append(record)

        except Exception as e:
            logger.error(f"Lỗi khi quét IP cho asset {asset.name}: {e}")

        return results
