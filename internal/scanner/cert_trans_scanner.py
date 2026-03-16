import logging
from typing import List
import aiohttp
from datetime import datetime

from internal.model.asset import Asset
from internal.model.scan import CreateCertTransRecordRequest
from internal.scanner.base import BaseScanner

logger = logging.getLogger("mini-asm.scanner.cert-trans")

class CertTransScanner(BaseScanner):
    """
    Máy quét kiểm tra Certificate Transparency logs thông qua crt.sh API.
    Lấy danh sách các chứng chỉ TLS đã từng được phát hành cho domain.
    """

    async def scan(self, asset: Asset) -> List[CreateCertTransRecordRequest]:
        results = []
        if asset.type != "domain":
            return results

        domain = asset.name
        # Sử dụng API của crt.sh trả về Output=json (có giới hạn limit nếu cần, thường có thể quá tải DB crt.sh)
        url = f"https://crt.sh/?q={domain}&output=json"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    # crt.sh thường trả về 200, nhưng có lúc database lỗi
                    if response.status != 200:
                         logger.warning(f"crt.sh không phản hồi 200 cho {domain}")
                         return results

                    data = await response.json()
                    
                    # deduplicate by ID since CRT log can return multiple same entries
                    seen = set()
                    
                    for entry in data:
                        cert_id = str(entry.get("id"))
                        if cert_id in seen:
                            continue
                        seen.add(cert_id)
                        
                        issuer = entry.get("issuer_name", "")
                        not_before_str = entry.get("not_before", "")
                        not_after_str = entry.get("not_after", "")
                        
                        not_before = None
                        if not_before_str:
                            try:
                                not_before = datetime.strptime(not_before_str, "%Y-%m-%dT%H:%M:%S")
                            except:
                                pass
                                
                        not_after = None
                        if not_after_str:
                            try:
                                not_after = datetime.strptime(not_after_str, "%Y-%m-%dT%H:%M:%S")
                            except:
                                pass

                        record = CreateCertTransRecordRequest(
                            domain=entry.get("name_value", domain),  # Name on cert (Subject or SAN)
                            issuer_name=issuer,
                            not_before=not_before,
                            not_after=not_after
                        )
                        results.append(record)
                        
        except Exception as e:
            logger.error(f"Lỗi khi quét Cert Transparency cho asset {asset.name}: {e}")

        return results
