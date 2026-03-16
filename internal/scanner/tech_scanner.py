import logging
from typing import List
import aiohttp
import asyncio
import re

from internal.model.asset import Asset
from internal.model.scan import CreateTechRecordRequest
from internal.scanner.base import BaseScanner

logger = logging.getLogger("mini-asm.scanner.tech")

class TechScanner(BaseScanner):
    """
    Máy quét kiểm tra công nghệ sử dụng của một Website.
    Dựa trên việc đọc HTTP Headers và thẻ Meta Tags.
    """

    async def scan(self, asset: Asset) -> List[CreateTechRecordRequest]:
        results = []
        # TechScanner quét được cả domain lẫn IP:
        # - domain: dùng HTTPS (https://example.com)
        # - ip: dùng HTTP vì IP thường không có SSL cert (http://192.168.1.1)
        # Chỉ loại trừ kiểu 'service' (vd: 'ssh', 'ftp') vì đó không phải HTTP endpoint.
        if asset.type not in ("domain", "ip"):
            logger.info(f"Bỏ qua Tech Scan cho asset {asset.name} kiểu {asset.type}")
            return results

        # Domain dùng HTTPS, IP dùng HTTP (IP thường không có SSL)
        url = f"https://{asset.name}" if asset.type == "domain" else f"http://{asset.name}"

        try:
            async with aiohttp.ClientSession() as session:
                # Disable SSL verification in case website uses self-signed
                async with session.get(url, timeout=10, ssl=False, allow_redirects=True) as response:
                    html_content = await response.text()
                    
                    headers = dict(response.headers)
                    headers_lower = {k.lower(): v for k, v in headers.items()}
                    
                    technologies = []
                    meta_tags = {}
                    
                    # 1. Trích xuất Server từ Header
                    server = headers_lower.get("server", "")
                    if server:
                        version = ""
                        name = server
                        if "/" in server:
                            name, version = server.split("/", 1)
                        technologies.append({
                            "name": name,
                            "category": "Web Server",
                            "version": version,
                            "confidence": 100
                        })
                        
                    # 2. X-Powered-By Header
                    x_powered_by = headers_lower.get("x-powered-by", "")
                    if x_powered_by:
                        technologies.append({
                            "name": x_powered_by,
                            "category": "Framework",
                            "version": "",
                            "confidence": 100
                        })

                    # 3. Phân tích Meta Tags (Generator, Viewport)
                    # Cách parse cơ bản qua Regex vì Beautifulsoup có thể khóa luồng (tốn CPU blocking) trừ khi dùng async parse
                    meta_generator = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\'](.*?)["\']', html_content, re.IGNORECASE)
                    if meta_generator:
                        gen_value = meta_generator.group(1)
                        meta_tags["generator"] = gen_value
                        technologies.append({
                            "name": gen_value,
                            "category": "CMS/Generator",
                            "version": "",
                            "confidence": 90
                        })
                        
                    meta_viewport = re.search(r'<meta[^>]+name=["\']viewport["\'][^>]+content=["\'](.*?)["\']', html_content, re.IGNORECASE)
                    if meta_viewport:
                        meta_tags["viewport"] = meta_viewport.group(1)

                    # 4. Phân tích Cloudflare (qua Headers Server = cloudflare)
                    if server.lower() == "cloudflare":
                        technologies.append({
                            "name": "Cloudflare",
                            "category": "CDN",
                            "version": None,
                            "confidence": 100
                        })

                    # 5. Phân tích React/Vue trong Script/HTML
                    if 'id="root"' in html_content or 'data-reactroot' in html_content:
                        technologies.append({
                            "name": "React",
                            "category": "JavaScript Framework",
                            "version": "",
                            "confidence": 80
                        })
                        
                    if 'data-v-' in html_content or '__VUE_HOT_MAP__' in html_content:
                         technologies.append({
                            "name": "Vue.js",
                            "category": "JavaScript Framework",
                            "version": "",
                            "confidence": 80
                        })

                    results.append(CreateTechRecordRequest(
                        domain=asset.name,
                        technologies=technologies,
                        headers=headers_lower,
                        meta_tags=meta_tags
                    ))
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout khi quét Tech cho {asset.name}")
        except Exception as e:
            logger.error(f"Lỗi khi quét Technology cho asset {asset.name}: {e}")

        return results
