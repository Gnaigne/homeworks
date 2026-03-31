"""
=============================================================================
File: tests/internal/scanner/test_scanners.py
Bài 2.4: Scanner Tests — Kiểm thử TẤT CẢ scanners
          (DNS, Port, IP, SSL, Tech, CertTrans)
         Dùng unittest.mock để giả lập network — không cần Internet thật
=============================================================================
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from internal.model.asset import Asset, AssetType, AssetStatus
from internal.model.scan import (
    CreateDNSRecordRequest, CreatePortScanRecordRequest,
    CreateIPRecordRequest, CreateSSLRecordRequest,
    CreateTechRecordRequest, CreateCertTransRecordRequest,
)
from internal.scanner.dns_scanner import DNSScanner
from internal.scanner.port_scanner import PortScanner
from internal.scanner.ip_scanner import IPScanner
from internal.scanner.ssl_scanner import SSLScanner
from internal.scanner.tech_scanner import TechScanner
from internal.scanner.cert_trans_scanner import CertTransScanner


# =============================================================================
# HELPERS
# =============================================================================

def make_asset(name: str, type_str: str) -> Asset:
    """Factory helper để tạo Asset object cho tests."""
    return Asset(
        id="test-asset-id",
        name=name,
        type=AssetType(type_str),
        status=AssetStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

def run_async(coro):
    """Chạy coroutine trong môi trường test đồng bộ."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# 1. DNS SCANNER TESTS
# =============================================================================

class TestDNSScanner:
    """Tests cho DNSScanner — mock dns.resolver để không cần kết nối thật."""

    def test_scan_non_domain_asset_skipped(self):
        """DNSScanner bỏ qua asset kiểu IP hoặc service."""
        scanner = DNSScanner()
        for asset_type in ("ip", "service"):
            asset = make_asset("1.1.1.1" if asset_type == "ip" else "ssh", asset_type)
            results = run_async(scanner.scan(asset))
            assert results == [], f"Phải bỏ qua {asset_type} asset"

    def test_scan_domain_returns_a_records(self):
        """DNSScanner trả về A records khi query thành công."""
        scanner = DNSScanner()
        asset = make_asset("example.com", "domain")

        mock_rdata_a1 = MagicMock()
        mock_rdata_a1.to_text.return_value = "93.184.216.34"
        mock_rdata_a2 = MagicMock()
        mock_rdata_a2.to_text.return_value = "93.184.216.35"

        def fake_resolve(domain, qtype):
            if qtype == "A":
                return [mock_rdata_a1, mock_rdata_a2]
            raise Exception("no answer")

        with patch("internal.scanner.dns_scanner.dns.resolver.resolve", side_effect=fake_resolve):
            results = run_async(scanner.scan(asset))

        a_records = [r for r in results if r.record_type == "A"]
        assert len(a_records) == 2
        assert any(r.value == "93.184.216.34" for r in a_records)

    def test_scan_domain_returns_mx_records(self):
        """DNSScanner trả về MX records khi có mail server."""
        scanner = DNSScanner()
        asset = make_asset("google.com", "domain")

        mock_mx = MagicMock()
        mock_mx.to_text.return_value = "10 smtp.google.com."

        def fake_resolve(domain, qtype):
            if qtype == "MX":
                return [mock_mx]
            raise Exception("no answer")

        with patch("internal.scanner.dns_scanner.dns.resolver.resolve", side_effect=fake_resolve):
            results = run_async(scanner.scan(asset))

        mx_records = [r for r in results if r.record_type == "MX"]
        assert len(mx_records) == 1
        assert "smtp.google.com." in mx_records[0].value

    def test_scan_domain_returns_txt_records(self):
        """DNSScanner trả về TXT records (SPF, DKIM, v.v.)."""
        scanner = DNSScanner()
        asset = make_asset("example.com", "domain")

        mock_txt = MagicMock()
        mock_txt.to_text.return_value = '"v=spf1 include:_spf.google.com ~all"'

        def fake_resolve(domain, qtype):
            if qtype == "TXT":
                return [mock_txt]
            raise Exception("no answer")

        with patch("internal.scanner.dns_scanner.dns.resolver.resolve", side_effect=fake_resolve):
            results = run_async(scanner.scan(asset))

        txt_records = [r for r in results if r.record_type == "TXT"]
        assert len(txt_records) == 1
        assert "spf1" in txt_records[0].value

    def test_scan_nxdomain_returns_empty(self):
        """Domain không tồn tại (NXDOMAIN) → trả [] và dừng sớm."""
        import dns.resolver
        scanner = DNSScanner()
        asset = make_asset("this-domain-does-not-exist-xyz123.com", "domain")

        with patch("internal.scanner.dns_scanner.dns.resolver.resolve",
                   side_effect=dns.resolver.NXDOMAIN()):
            results = run_async(scanner.scan(asset))

        assert results == []

    def test_scan_noanswer_continues_to_next_type(self):
        """NoAnswer cho 1 loại record không dừng việc query các loại khác."""
        import dns.resolver
        scanner = DNSScanner()
        asset = make_asset("example.com", "domain")

        mock_ns = MagicMock()
        mock_ns.to_text.return_value = "ns1.example.com."
        call_count = {"total": 0}

        def fake_resolve(domain, qtype):
            call_count["total"] += 1
            if qtype == "NS":
                return [mock_ns]
            raise dns.resolver.NoAnswer()

        with patch("internal.scanner.dns_scanner.dns.resolver.resolve", side_effect=fake_resolve):
            results = run_async(scanner.scan(asset))

        # Phải query đủ 6 loại record (A, AAAA, MX, NS, TXT, CNAME)
        assert call_count["total"] == 6
        ns_records = [r for r in results if r.record_type == "NS"]
        assert len(ns_records) == 1

    def test_scan_returns_create_dns_record_request_objects(self):
        """Kết quả phải là list của CreateDNSRecordRequest (đúng DTO type)."""
        import dns.resolver
        scanner = DNSScanner()
        asset = make_asset("example.com", "domain")

        mock_a = MagicMock()
        mock_a.to_text.return_value = "1.2.3.4"

        with patch("internal.scanner.dns_scanner.dns.resolver.resolve",
                   side_effect=lambda d, q: [mock_a] if q == "A"
                   else (_ for _ in ()).throw(dns.resolver.NoAnswer())):
            results = run_async(scanner.scan(asset))

        assert all(isinstance(r, CreateDNSRecordRequest) for r in results)


# =============================================================================
# 2. PORT SCANNER TESTS
# =============================================================================

class TestPortScanner:
    """Tests cho PortScanner — mock asyncio.open_connection."""

    def test_authorized_loopback_pass(self):
        """127.0.0.1 (loopback) phải được cấp phép quét."""
        scanner = PortScanner()
        assert scanner._is_authorized("127.0.0.1") is True

    def test_authorized_private_ip_pass(self):
        """Dải mạng private phải được cấp phép quét."""
        scanner = PortScanner()
        assert scanner._is_authorized("192.168.1.100") is True
        assert scanner._is_authorized("10.0.0.1") is True
        assert scanner._is_authorized("172.16.0.1") is True

    def test_authorized_public_ip_denied(self):
        """IP public PHẢI bị chặn (không được quét)."""
        scanner = PortScanner()
        with patch("internal.scanner.port_scanner.socket.gethostbyname", return_value="8.8.8.8"):
            assert scanner._is_authorized("8.8.8.8") is False
        with patch("internal.scanner.port_scanner.socket.gethostbyname", return_value="142.250.1.1"):
            assert scanner._is_authorized("google.com") is False

    def test_scan_public_ip_blocked(self):
        """Scan task cho IP public phải trả [] (bị safety check chặn)."""
        scanner = PortScanner()
        asset = make_asset("8.8.8.8", "ip")
        results = run_async(scanner.scan(asset))
        assert results == []

    def test_scan_single_port_open(self):
        """Nếu port mở, _scan_single_port trả về record với state='open'."""
        scanner = PortScanner()

        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_reader.read = AsyncMock(return_value=b"SSH-2.0-OpenSSH_8.9\r\n")
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        with patch("internal.scanner.port_scanner.asyncio.open_connection",
                   return_value=(mock_reader, mock_writer)):
            result = run_async(scanner._scan_single_port("127.0.0.1", 22))

        assert result.port == 22
        assert result.state == "open"
        assert result.service == "ssh"

    def test_scan_single_port_closed(self):
        """Nếu port đóng (ConnectionRefusedError), state='closed'."""
        scanner = PortScanner()
        with patch("internal.scanner.port_scanner.asyncio.open_connection",
                   side_effect=ConnectionRefusedError()):
            result = run_async(scanner._scan_single_port("127.0.0.1", 9999))

        assert result.port == 9999
        assert result.state == "closed"

    def test_scan_single_port_timeout_also_closed(self):
        """TimeoutError và ConnectionRefusedError đều cho state='closed' (cùng except block)."""
        scanner = PortScanner()
        with patch("internal.scanner.port_scanner.asyncio.open_connection",
                   side_effect=asyncio.TimeoutError()):
            result = run_async(scanner._scan_single_port("127.0.0.1", 444))

        assert result.port == 444
        assert result.state == "closed"

    def test_scan_localhost_returns_only_open_ports(self):
        """scan() chỉ trả về port CÓ state='open', port closed bị lọc ra."""
        scanner = PortScanner()
        asset = make_asset("127.0.0.1", "ip")

        async def fake_scan_port(target, port):
            state = "open" if port == 22 else "closed"
            return CreatePortScanRecordRequest(
                port=port, state=state,
                service="ssh" if port == 22 else "unknown",
                response_time_ms=0
            )

        with patch.object(scanner, "_scan_single_port", side_effect=fake_scan_port):
            results = run_async(scanner.scan(asset))

        # Chỉ port 22 (SSH) là open → kết quả phải có đúng 1 record
        assert len(results) == 1
        assert results[0].port == 22
        assert results[0].state == "open"

    @pytest.mark.parametrize("banner, expected_service", [
        (b"SSH-2.0-OpenSSH_8.9\r\n",                 "ssh"),
        (b"220 mail.example.com SMTP service\r\n",    "smtp"),
        (b"HTTP/1.1 200 OK\r\n",                      "http"),
        (b"\x00\x00\x00\x00",                         "unrecognized"),
    ])
    def test_service_detection_from_banner(self, banner, expected_service):
        """Banner grabbing detect đúng service từ nội dung banner trả về."""
        scanner = PortScanner()
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_reader.read = AsyncMock(return_value=banner)
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        with patch("internal.scanner.port_scanner.asyncio.open_connection",
                   return_value=(mock_reader, mock_writer)):
            result = run_async(scanner._scan_single_port("127.0.0.1", 22))

        assert result.state == "open"
        assert result.service == expected_service


# =============================================================================
# 3. IP SCANNER TESTS
# =============================================================================

class TestIPScanner:
    """Tests cho IPScanner — mock network call tới ip-api.com."""

    def test_scan_ip_asset_success(self):
        """IPScanner trả về IPRecord đúng với dữ liệu từ ip-api."""
        scanner = IPScanner()
        asset = make_asset("1.1.1.1", "ip")

        mock_api_response = {
            "status": "success",
            "country": "Australia", "countryCode": "AU",
            "regionName": "Queensland", "city": "Brisbane",
            "lat": -27.47, "lon": 153.02,
            "isp": "Cloudflare", "org": "APNIC Cloudflare",
            "as": "AS13335 Cloudflare, Inc.", "asname": "CLOUDFLARENET",
            "reverse": "one.one.one.one"
        }

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value=mock_api_response)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("internal.scanner.ip_scanner.aiohttp.ClientSession", return_value=mock_session):
            results = run_async(scanner.scan(asset))

        assert len(results) == 1
        record = results[0]
        assert isinstance(record, CreateIPRecordRequest)
        assert record.ip_address == "1.1.1.1"
        assert record.geolocation["country"] == "Australia"
        assert record.asn["number"] == 13335
        assert record.asn["name"] == "CLOUDFLARENET"
        assert record.reverse_dns == "one.one.one.one"

    def test_scan_domain_asset_resolves_ip(self):
        """IPScanner phải resolve domain sang IP trước khi query."""
        scanner = IPScanner()
        asset = make_asset("google.com", "domain")

        mock_api_response = {
            "status": "success",
            "country": "US", "countryCode": "US",
            "regionName": "Virginia", "city": "Ashburn",
            "lat": 39.03, "lon": -77.5,
            "isp": "Google LLC", "org": "Google Public DNS",
            "as": "AS15169 Google LLC", "asname": "GOOGLE",
            "reverse": "dns.google"
        }

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value=mock_api_response)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("internal.scanner.ip_scanner.socket.gethostbyname", return_value="8.8.8.8"), \
             patch("internal.scanner.ip_scanner.aiohttp.ClientSession", return_value=mock_session):
            results = run_async(scanner.scan(asset))

        assert len(results) == 1
        assert results[0].ip_address == "8.8.8.8"

    def test_scan_api_failure_returns_empty(self):
        """ip-api trả về status != success → scanner trả []."""
        scanner = IPScanner()
        asset = make_asset("0.0.0.0", "ip")

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value={"status": "fail", "message": "reserved range"})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("internal.scanner.ip_scanner.aiohttp.ClientSession", return_value=mock_session):
            results = run_async(scanner.scan(asset))

        assert results == []

    def test_scan_network_exception_returns_empty(self):
        """Kết nối mạng bị lỗi → scanner không crash và trả []."""
        scanner = IPScanner()
        asset = make_asset("1.2.3.4", "ip")

        with patch("internal.scanner.ip_scanner.aiohttp.ClientSession") as MockSession:
            MockSession.return_value.__aenter__ = AsyncMock(side_effect=Exception("connection refused"))
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            results = run_async(scanner.scan(asset))

        assert results == []

    def test_scan_asn_empty_string_defaults_to_zero(self):
        """ASN string rỗng → parser không crash, trả number=0."""
        scanner = IPScanner()
        asset = make_asset("5.5.5.5", "ip")

        mock_api_response = {
            "status": "success",
            "country": "FR", "countryCode": "FR",
            "regionName": "Île-de-France", "city": "Paris",
            "lat": 48.8566, "lon": 2.3522,
            "isp": "Free SAS", "org": "Free SAS",
            "as": "",  # String rỗng → parser phải xử lý gracefully
            "asname": "FREE-FR",
            "reverse": ""
        }

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value=mock_api_response)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("internal.scanner.ip_scanner.aiohttp.ClientSession", return_value=mock_session):
            results = run_async(scanner.scan(asset))

        assert results[0].asn["number"] == 0


# =============================================================================
# 4. SSL SCANNER TESTS
# =============================================================================

class TestSSLScanner:
    """Tests cho SSLScanner — kiểm tra safety check và TLS scan."""

    def test_scan_non_domain_asset_skipped(self):
        """SSLScanner bỏ qua asset kiểu IP (chỉ scan domain)."""
        scanner = SSLScanner()
        asset = make_asset("1.1.1.1", "ip")
        results = run_async(scanner.scan(asset))
        assert results == []

    def test_scan_public_domain_blocked_by_safety_check(self):
        """Public domain BỊ CHẶN bởi safety check (Active Scan không được scan public)."""
        scanner = SSLScanner()
        asset = make_asset("google.com", "domain")

        with patch("internal.scanner.ssl_scanner.socket.gethostbyname", return_value="142.250.1.1"):
            results = run_async(scanner.scan(asset))

        assert results == []

    def test_scan_localhost_allowed_does_not_crash(self):
        """localhost được phép scan; timeout graceful → trả [] không crash."""
        scanner = SSLScanner()
        asset = make_asset("localhost", "domain")

        with patch.object(scanner, "_is_authorized", return_value=True), \
             patch("internal.scanner.ssl_scanner.asyncio.open_connection") as mock_conn:
            mock_conn.side_effect = asyncio.TimeoutError()
            results = run_async(scanner.scan(asset))

        assert results == []

    def test_is_authorized_loopback(self):
        """_is_authorized trả True cho 127.0.0.1 (loopback)."""
        scanner = SSLScanner()
        assert scanner._is_authorized("127.0.0.1") is True

    def test_is_authorized_private_ranges(self):
        """_is_authorized trả True cho toàn bộ dải IP private."""
        scanner = SSLScanner()
        assert scanner._is_authorized("192.168.1.100") is True
        assert scanner._is_authorized("10.0.0.1") is True

    def test_is_authorized_public_ip_blocked(self):
        """_is_authorized trả False cho IP public."""
        scanner = SSLScanner()
        with patch("internal.scanner.ssl_scanner.socket.gethostbyname", return_value="8.8.8.8"):
            assert scanner._is_authorized("google.com") is False


# =============================================================================
# 5. TECH SCANNER TESTS
# =============================================================================

class TestTechScanner:
    """Tests cho TechScanner — mock HTTP response headers và body."""

    def test_scan_service_asset_skipped(self):
        """TechScanner bỏ qua asset kiểu SERVICE ('ssh', 'ftp' không phải HTTP)."""
        scanner = TechScanner()
        asset = make_asset("ssh", "service")
        results = run_async(scanner.scan(asset))
        assert results == []

    def test_scan_ip_asset_uses_http(self):
        """TechScanner quét IP bằng HTTP (không phải HTTPS — IP thường không có SSL cert)."""
        scanner = TechScanner()
        asset = make_asset("192.168.1.1", "ip")

        mock_resp = AsyncMock()
        mock_resp.headers = {"server": "nginx/1.18.0"}
        mock_resp.text = AsyncMock(return_value="<html><body></body></html>")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("internal.scanner.tech_scanner.aiohttp.ClientSession", return_value=mock_session):
            results = run_async(scanner.scan(asset))

        assert len(results) == 1
        assert results[0].domain == "192.168.1.1"
        call_url = mock_session.get.call_args[0][0]
        assert call_url.startswith("http://"), f"IP asset phải dùng HTTP, nhưng dùng: {call_url}"

    def test_scan_domain_detects_server_header(self):
        """TechScanner phát hiện web server từ header 'Server'."""
        scanner = TechScanner()
        asset = make_asset("nginx-site.com", "domain")

        mock_resp = AsyncMock()
        mock_resp.headers = {"server": "nginx/1.18.0", "x-powered-by": "Express"}
        mock_resp.text = AsyncMock(return_value="<html><head></head><body></body></html>")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("internal.scanner.tech_scanner.aiohttp.ClientSession", return_value=mock_session):
            results = run_async(scanner.scan(asset))

        assert len(results) == 1
        record = results[0]
        assert isinstance(record, CreateTechRecordRequest)
        assert record.domain == "nginx-site.com"
        assert record.headers["server"] == "nginx/1.18.0"
        tech_names = [t["name"].lower() for t in record.technologies]
        assert "nginx" in tech_names

    def test_scan_domain_detects_meta_generator(self):
        """TechScanner parse meta tag 'generator' để detect framework (vd: WordPress)."""
        scanner = TechScanner()
        asset = make_asset("wp-site.com", "domain")

        html_body = '<html><head><meta name="generator" content="WordPress 6.4"/></head></html>'

        mock_resp = AsyncMock()
        mock_resp.headers = {"server": "Apache"}
        mock_resp.text = AsyncMock(return_value=html_body)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("internal.scanner.tech_scanner.aiohttp.ClientSession", return_value=mock_session):
            results = run_async(scanner.scan(asset))

        assert len(results) == 1
        assert "generator" in results[0].meta_tags

    def test_scan_network_error_returns_empty(self):
        """Kết nối bị lỗi → TechScanner trả [] và không crash."""
        scanner = TechScanner()
        asset = make_asset("down.example.com", "domain")

        with patch("internal.scanner.tech_scanner.aiohttp.ClientSession") as MockSession:
            MockSession.return_value.__aenter__ = AsyncMock(side_effect=Exception("network error"))
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            results = run_async(scanner.scan(asset))

        assert results == []


# =============================================================================
# 6. CERT TRANSPARENCY SCANNER TESTS
# =============================================================================

class TestCertTransScanner:
    """Tests cho CertTransScanner — mock HTTP calls tới crt.sh."""

    def test_scan_non_domain_asset_skipped(self):
        """CertTransScanner bỏ qua asset kiểu IP."""
        scanner = CertTransScanner()
        asset = make_asset("8.8.8.8", "ip")
        results = run_async(scanner.scan(asset))
        assert results == []

    def test_scan_domain_returns_records(self):
        """CertTransScanner parse JSON từ crt.sh và trả về danh sách record."""
        scanner = CertTransScanner()
        asset = make_asset("example.com", "domain")

        crt_sh_response = [
            {
                "id": "1001",
                "name_value": "example.com",
                "issuer_name": "C=US, O=Let's Encrypt, CN=R3",
                "not_before": "2025-01-01T00:00:00",
                "not_after": "2025-04-01T00:00:00"
            },
            {
                "id": "1002",
                "name_value": "www.example.com",
                "issuer_name": "C=US, O=DigiCert, CN=DigiCert SHA2",
                "not_before": "2024-06-01T00:00:00",
                "not_after": "2025-06-01T00:00:00"
            }
        ]

        mock_resp = AsyncMock()
        mock_resp.status = 200  # Phải set 200 để scanner không bỏ qua response
        mock_resp.json = AsyncMock(return_value=crt_sh_response)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("internal.scanner.cert_trans_scanner.aiohttp.ClientSession", return_value=mock_session):
            results = run_async(scanner.scan(asset))

        assert len(results) == 2
        assert isinstance(results[0], CreateCertTransRecordRequest)
        assert results[0].domain == "example.com"
        assert "Let's Encrypt" in results[0].issuer_name
        assert results[1].domain == "www.example.com"

    def test_scan_empty_response_returns_empty(self):
        """crt.sh trả về [] (domain chưa có cert) → kết quả rỗng."""
        scanner = CertTransScanner()
        asset = make_asset("new-domain.io", "domain")

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=[])
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("internal.scanner.cert_trans_scanner.aiohttp.ClientSession", return_value=mock_session):
            results = run_async(scanner.scan(asset))

        assert results == []

    def test_scan_network_error_returns_empty(self):
        """Network timeout hoặc exception → trả [] an toàn."""
        scanner = CertTransScanner()
        asset = make_asset("timeout.com", "domain")

        with patch("internal.scanner.cert_trans_scanner.aiohttp.ClientSession") as MockSession:
            MockSession.return_value.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            results = run_async(scanner.scan(asset))

        assert results == []
