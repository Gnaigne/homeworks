"""
=============================================================================
File: internal/scanner/subdomain_scanner.py
Layer: Infrastructure/Scanner Layer
Tác dụng: Quét Subdomain bằng kỹ thuật DNS Bruteforce (concurrency).
=============================================================================
"""

import asyncio
import logging
import aiohttp
from typing import List

from internal.model.asset import Asset, AssetType
from internal.model.scan import CreateSubdomainRecordRequest
from internal.scanner.base import BaseScanner

logger = logging.getLogger("mini-asm.scanner.subdomain")

# Lấy danh sách subdomains từ file text chung
WORDLIST_PATH = "internal/scanner/wordlists/subdomains.txt"

def load_wordlist() -> List[str]:
    words = []
    try:
        with open(WORDLIST_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    words.append(line)
        return words
    except Exception as e:
        logger.warning(f"Không thể đọc wordlist tại {WORDLIST_PATH}: {e}. Sẽ dùng list mặc định.")
        return ["www", "mail", "api", "dev", "test"]

class SubdomainScanner(BaseScanner):
    """
    Subdomain Scanner mô phỏng DNS Bruteforce.
    Sử dụng thư viện `aiohttp` để gửi yêu cầu tới DNS-over-HTTPS (DoH) API của Cloudflare,
    chứng minh khả năng xử lý concurrency cao của asyncio bằng Worker Pool.
    
    Giống như mô hình Worker Pool Goroutines + Channels trong Go:
        Chặn N goroutines chờ đọc từ 1 channel. Ở Python, ta dùng N Tasks đọc từ dòng
        chờ chung asyncio.Queue().
    """

    async def scan(self, asset: Asset) -> List[CreateSubdomainRecordRequest]:
        if asset.type != AssetType.DOMAIN:
            return []

        domain = asset.name
        results = []
        
        # Load danh sách Subdomains từ file
        wordlist = load_wordlist()
        
        # Tạo Queue chứa tất cả task (subdomains cần check)
        # Giống với Buffered Channel trong Go
        queue: asyncio.Queue[str] = asyncio.Queue()
        for word in wordlist:
            queue.put_nowait(f"{word}.{domain}")

        # Tương thích Session 5 Go: Rate Limiter 100 requests / second
        # Mô phỏng `time.NewTicker(time.Second / 100)` trong Go
        # Giới hạn số Token được cấp phát mỗi giây để kiểm soát Worker
        rate_limit = 100
        token_bucket = asyncio.Queue()
        
        # Background task chuyên đổ Token vào Xô với tốc độ cố định
        async def token_feeder():
            try:
                # Mỗi 1/100 giây cấp 1 token (tức 10ms)
                delay = 1.0 / rate_limit
                while True:
                    await asyncio.sleep(delay)
                    try:
                        token_bucket.put_nowait(1)
                    except asyncio.QueueFull:
                        pass
            except asyncio.CancelledError:
                pass
                
        # Khởi chạy Feeder Job ở cửa sổ ngầm
        feeder_task = asyncio.create_task(token_feeder())

        # Định nghĩa hàm cho mỗi Worker (Goroutine)
        async def worker(session: aiohttp.ClientSession):
            while True:
                try:
                    # Lấy domain ra khỏi hàng đợi
                    subdomain = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                
                # --- APPLY RATE LIMITING GIỐNG BẢN GO ---
                # Worker phải chờ bốc được 1 Token từ Feeder thì mới được làm việc
                # Tương đương mã Go: <-limiter.C
                await token_bucket.get()

                # Gửi request lên API Cloudflare DoH (DNS over HTTPS)
                url = "https://cloudflare-dns.com/dns-query"
                headers = {"accept": "application/dns-json"}
                params = {"name": subdomain, "type": "A"}

                try:
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Status 0 là NOERROR (tìm thấy bản ghi)
                            if data.get("Status") == 0 and "Answer" in data:
                                # Chỉ lấy IP của bản ghi A trả về đầu tiên
                                ip = data["Answer"][0]["data"]
                                results.append(CreateSubdomainRecordRequest(
                                    subdomain=subdomain,
                                    ip_address=ip
                                ))
                        # elif response.status == 429: # Rate limiting handled by token bucket
                        #     logger.warning(f"⚠️ Bị giới hạn Rate Limit (429) ở {subdomain}. Tạm nghỉ 1s...")
                        #     await asyncio.sleep(1)
                except Exception as e:
                    logger.debug(f"Lỗi truy xuất cho {subdomain}: {e}")
                finally:
                    # Báo hiệu queue là task đã xử lý xong
                    queue.task_done()
                    # TRÁNH BỊ BLOCK: Bắt buộc mỗi worker phải nghỉ 0.2 giây trước khi nhận task mới
                    # await asyncio.sleep(0.2) # Replaced by token bucket

        # Số lượng worker đồng thời (Mức concurrency)
        NUM_WORKERS = 50 # Tăng số worker lên 50 giống Go, vì đã có Rate Limiter ghìm lại
        
        # aiohttp ClientSession sử dụng connection pooling nội bộ (rất nhanh)
        async with aiohttp.ClientSession() as session:
            # Khởi tạo N tasks (workers) nạp vào event loop
            workers = [
                asyncio.create_task(worker(session))
                for _ in range(NUM_WORKERS)
            ]
            
            # Chờ cho đến khi tất cả các task trong Queue được xử lý xong
            # Tương tự như WaitGroup.Wait()
            await queue.join()
            
            # Hủy Background Feeder và các Workers còn đang ngủ
            feeder_task.cancel()
            for w in workers:
                w.cancel()
            
            # Đợi các task bị hủy hoàn tất (để tránh RuntimeWarning)
            await asyncio.gather(feeder_task, *workers, return_exceptions=True)

        logger.info(f"Đã quét xong Subdomain cho {domain}: {len(results)} kết quả")
        return results
