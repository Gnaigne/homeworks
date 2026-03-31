import asyncio
import ipaddress
import logging
import socket
import ssl
from datetime import datetime, timezone
from typing import List

from internal.model.asset import Asset
from internal.model.scan import CreateSSLRecordRequest
from internal.scanner.base import BaseScanner

logger = logging.getLogger("mini-asm.scanner.ssl")


class SSLScanner(BaseScanner):
    """
    Máy quét kiểm tra chứng chỉ SSL/TLS của một domain.
    """

    def _is_authorized(self, target: str) -> bool:
        """Kiểm tra xem mục tiêu có được cấp phép quét hay không (Active Scan Safety)."""
        try:
            ip_str = target
            if not target[0].isdigit():
                try:
                    ip_str = socket.gethostbyname(target)
                except socket.gaierror:
                    pass
            ip = ipaddress.ip_address(ip_str)
            return ip.is_loopback or ip.is_private
        except ValueError:
            return target in ("localhost", "127.0.0.1", "::1")

    async def scan(self, asset: Asset) -> List[CreateSSLRecordRequest]:
        results = []
        if asset.type != "domain":
            logger.info(f"Bỏ qua SSL Scan cho asset {asset.name} (không phải domain)")
            return results

        domain = asset.name
        
        # ⚠️ CRITICAL SAFETY CHECK: Ngăn ngừa quét bên thứ 3 (Do SSL là Active Scan)
        if not self._is_authorized(domain):
            logger.warning(
                f"⚠️ UNAUTHORIZED SSL SCAN BLOCKED! Target: {domain}. "
                "Chỉ cho phép quét tài sản cục bộ hoặc mạng Private (10.x.x.x, 192.168.x.x)."
            )
            return []

        port = 443

        try:
            # Context cấu hình không check hostname, vì có thể lấy cert gốc
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # Bỏ qua xác thực để lấy mộc certs

            # Connect bất đồng bộ
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(domain, port, ssl=context),
                timeout=10.0
            )

            # Extra info: peercert (dict) and cipher
            # Tuy nhiên CERT_NONE sẽ KHÔNG trả về peercert đầy đủ. 
            # Vậy ta sẽ get_peercert trong layer socket
            # Mẹo: Lấy raw socket ra để fetch cert binary
            sock = writer.get_extra_info('socket')
            raw_cert = sock.getpeercert()
            
            # Khởi tạo mặc định
            certificate_info = {}
            connection_info = {}
            
            cipher_info = sock.cipher()
            if cipher_info:
                # cipher_info = ('ECDHE-RSA-AES256-GCM-SHA384', 'TLSv1.2', 256)
                connection_info = {
                    "tls_version": cipher_info[1] if len(cipher_info) > 1 else "",
                    "cipher_suite": cipher_info[0] if len(cipher_info) > 0 else "",
                    "key_exchange": "" # Python SSL module không bóc key_exchange riêng dễ dàng
                }

            # Lấy cert dưới dạng DER binary để phân tách
            der_cert = sock.getpeercert(binary_form=True)
            
            if der_cert:
                import cryptography.x509 as x509
                from cryptography.hazmat.backends import default_backend
                
                try:
                    cert_obj = x509.load_der_x509_certificate(der_cert, default_backend())
                    
                    # Issuer
                    issuer = ", ".join([f"{a.oid._name}={a.value}" for a in cert_obj.issuer])
                    # Subject
                    subject = ", ".join([f"{a.oid._name}={a.value}" for a in cert_obj.subject])
                    
                    # Serial 
                    serial_number = f"{cert_obj.serial_number:X}"
                    
                    # Dates
                    valid_from = cert_obj.not_valid_before_utc
                    valid_until = cert_obj.not_valid_after_utc
                    
                    # Days until expiry
                    now = datetime.now(timezone.utc)
                    days_until_expiry = (valid_until - now).days
                    is_expired = days_until_expiry < 0
                    
                    # Self signed
                    is_self_signed = (issuer == subject)
                    
                    # SAN (Subject Alternative Names)
                    san_list = []
                    try:
                        ext = cert_obj.extensions.get_extension_for_oid(
                            x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                        )
                        san_list = ext.value.get_values_for_type(x509.DNSName)
                    except x509.extensions.ExtensionNotFound:
                        pass
                        
                    certificate_info = {
                        "subject": subject,
                        "issuer": issuer,
                        "serial_number": serial_number,
                        "valid_from": valid_from.isoformat() if valid_from else None,
                        "valid_until": valid_until.isoformat() if valid_until else None,
                        "days_until_expiry": days_until_expiry,
                        "is_expired": is_expired,
                        "is_self_signed": is_self_signed,
                        "san": san_list,
                    }
                    
                except Exception as cert_err:
                    logger.warning(f"Lỗi Parser DER Cert cho {domain}: {cert_err}")

            writer.close()
            await writer.wait_closed()

            grade = "A" if connection_info.get("tls_version", "").startswith("TLSv1.3") or connection_info.get("tls_version", "").startswith("TLSv1.2") else "C"
            if certificate_info.get("is_expired") or certificate_info.get("is_self_signed"):
                grade = "F"

            issues = []
            if certificate_info.get("is_expired"):
                issues.append("Certificate is expired.")
            if certificate_info.get("is_self_signed"):
                issues.append("Certificate is self-signed.")

            results.append(CreateSSLRecordRequest(
                domain=domain,
                certificate=certificate_info,
                connection=connection_info,
                grade=grade,
                issues=issues
            ))

        except asyncio.TimeoutError:
            logger.warning(f"SSL connect timeout for {domain}")
        except Exception as e:
            logger.error(f"Lỗi khi quét SSL cho asset {asset.name}: {e}")

        return results
