import os
import ssl
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import ipaddress
from datetime import datetime, timedelta

from observability.otel_setup import get_tracer, log_with_context


class TLSCertificateManager:
    """Manages TLS certificates and SSL context configuration"""
    
    def __init__(self):
        self.tracer = get_tracer("tls_manager")
        self.cert_dir = Path(os.getenv("TLS_CERT_DIR", "./certs"))
        self.cert_dir.mkdir(exist_ok=True)
        
        # Certificate configuration
        self.cert_file = os.getenv("TLS_CERT_FILE", self.cert_dir / "server.crt")
        self.key_file = os.getenv("TLS_KEY_FILE", self.cert_dir / "server.key")
        self.ca_file = os.getenv("TLS_CA_FILE", self.cert_dir / "ca.crt")
        
        # SSL context configuration
        self.min_tls_version = os.getenv("TLS_MIN_VERSION", "TLSv1.2")
        self.cipher_suites = os.getenv("TLS_CIPHER_SUITES", "").split(",") if os.getenv("TLS_CIPHER_SUITES") else []
        self.verify_client = os.getenv("TLS_VERIFY_CLIENT", "false").lower() == "true"
        
        # Certificate validation settings
        self.cert_validation = os.getenv("TLS_CERT_VALIDATION", "true").lower() == "true"
        self.hostname_validation = os.getenv("TLS_HOSTNAME_VALIDATION", "true").lower() == "true"
    
    def generate_self_signed_certificate(
        self,
        hostname: str = "localhost",
        ip_addresses: list = None,
        validity_days: int = 365,
        key_size: int = 2048
    ) -> tuple[str, str]:
        """Generate a self-signed certificate for development/testing"""
        
        with self.tracer.start_as_current_span("generate_self_signed_cert") as span:
            span.set_attribute("hostname", hostname)
            span.set_attribute("validity_days", validity_days)
            span.set_attribute("key_size", key_size)
            
            log_with_context(
                "info",
                f"Generating self-signed certificate for {hostname}",
                hostname=hostname,
                validity_days=validity_days
            )
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            
            # Prepare subject
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NLP AI Service"),
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ])
            
            # Prepare SAN (Subject Alternative Names)
            san_list = [x509.DNSName(hostname)]
            
            # Add IP addresses if provided
            if ip_addresses:
                for ip in ip_addresses:
                    try:
                        ip_obj = ipaddress.ip_address(ip)
                        if isinstance(ip_obj, ipaddress.IPv4Address):
                            san_list.append(x509.IPAddress(ip_obj))
                        elif isinstance(ip_obj, ipaddress.IPv6Address):
                            san_list.append(x509.IPAddress(ip_obj))
                    except ValueError:
                        log_with_context("warning", f"Invalid IP address: {ip}")
            
            # Add common localhost IPs
            san_list.extend([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv6Address("::1"))
            ])
            
            # Create certificate
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=validity_days)
            ).add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            ).add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            ).add_extension(
                x509.KeyUsage(
                    key_cert_sign=False,
                    crl_sign=False,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                    digital_signature=True,
                ),
                critical=True,
            ).add_extension(
                x509.ExtendedKeyUsage([
                    x509.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=True,
            ).sign(private_key, hashes.SHA256(), default_backend())
            
            # Serialize certificate and key
            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            return cert_pem.decode('utf-8'), key_pem.decode('utf-8')
    
    def save_certificate_files(self, cert_pem: str, key_pem: str) -> None:
        """Save certificate and key to files"""
        
        with self.tracer.start_as_current_span("save_certificate_files") as span:
            span.set_attribute("cert_file", str(self.cert_file))
            span.set_attribute("key_file", str(self.key_file))
            
            # Save certificate
            with open(self.cert_file, 'w') as f:
                f.write(cert_pem)
            
            # Save private key
            with open(self.key_file, 'w') as f:
                f.write(key_pem)
            
            # Set secure file permissions
            os.chmod(self.cert_file, 0o644)
            os.chmod(self.key_file, 0o600)
            
            log_with_context(
                "info",
                "Certificate files saved successfully",
                cert_file=str(self.cert_file),
                key_file=str(self.key_file)
            )
    
    def create_ssl_context(
        self,
        purpose: ssl.Purpose = ssl.Purpose.SERVER_AUTH,
        verify_mode: ssl.VerifyMode = ssl.CERT_REQUIRED
    ) -> ssl.SSLContext:
        """Create SSL context with secure configuration"""
        
        with self.tracer.start_as_current_span("create_ssl_context") as span:
            span.set_attribute("purpose", purpose.name)
            span.set_attribute("verify_mode", verify_mode.name)
            
            # Create SSL context
            if self.min_tls_version == "TLSv1.3":
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            elif self.min_tls_version == "TLSv1.2":
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            else:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            
            # Set minimum TLS version
            if self.min_tls_version == "TLSv1.3":
                context.minimum_version = ssl.TLSVersion.TLSv1_3
            elif self.min_tls_version == "TLSv1.2":
                context.minimum_version = ssl.TLSVersion.TLSv1_2
            else:
                context.minimum_version = ssl.TLSVersion.TLSv1_2
            
            # Set maximum TLS version
            context.maximum_version = ssl.TLSVersion.TLSv1_3
            
            # Configure cipher suites
            if self.cipher_suites:
                context.set_ciphers(':'.join(self.cipher_suites))
            else:
                # Use secure default cipher suites
                context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            
            # Set verification mode
            if self.cert_validation:
                context.verify_mode = verify_mode
                context.check_hostname = self.hostname_validation
            else:
                context.verify_mode = ssl.CERT_NONE
                context.check_hostname = False
            
            # Load certificate and key
            if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
                context.load_cert_chain(self.cert_file, self.key_file)
                span.set_attribute("cert_loaded", True)
            
            # Load CA certificate if available
            if os.path.exists(self.ca_file):
                context.load_verify_locations(self.ca_file)
                span.set_attribute("ca_loaded", True)
            
            # Additional security options
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
            
            # Enable session tickets for performance
            context.options |= ssl.OP_NO_TICKET
            
            # Prefer server cipher suites
            context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
            
            span.set_attribute("ssl_context_created", True)
            
            log_with_context(
                "info",
                "SSL context created successfully",
                min_tls_version=self.min_tls_version,
                verify_mode=verify_mode.name,
                cert_loaded=os.path.exists(self.cert_file),
                ca_loaded=os.path.exists(self.ca_file)
            )
            
            return context
    
    def get_client_ssl_context(self) -> ssl.SSLContext:
        """Get SSL context for client connections"""
        
        with self.tracer.start_as_current_span("create_client_ssl_context") as span:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            
            # Set minimum TLS version
            if self.min_tls_version == "TLSv1.3":
                context.minimum_version = ssl.TLSVersion.TLSv1_3
            elif self.min_tls_version == "TLSv1.2":
                context.minimum_version = ssl.TLSVersion.TLSv1_2
            
            # Load CA certificate if available
            if os.path.exists(self.ca_file):
                context.load_verify_locations(self.ca_file)
                span.set_attribute("ca_loaded", True)
            
            # Configure verification
            if self.cert_validation:
                context.check_hostname = self.hostname_validation
                context.verify_mode = ssl.CERT_REQUIRED
            else:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            
            span.set_attribute("client_ssl_context_created", True)
            
            return context
    
    def validate_certificate(self, cert_file: str = None) -> Dict[str, Any]:
        """Validate certificate file"""
        
        cert_file = cert_file or self.cert_file
        
        with self.tracer.start_as_current_span("validate_certificate") as span:
            span.set_attribute("cert_file", cert_file)
            
            try:
                with open(cert_file, 'rb') as f:
                    cert_data = f.read()
                
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                
                # Get certificate info
                subject = cert.subject
                issuer = cert.issuer
                not_valid_before = cert.not_valid_before
                not_valid_after = cert.not_valid_after
                
                # Check if certificate is expired
                now = datetime.utcnow()
                is_expired = now > not_valid_after
                is_not_yet_valid = now < not_valid_before
                
                # Get SAN
                san_ext = None
                try:
                    san_ext = cert.extensions.get_extension_for_oid(x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                except x509.ExtensionNotFound:
                    pass
                
                validation_result = {
                    "valid": not is_expired and not is_not_yet_valid,
                    "expired": is_expired,
                    "not_yet_valid": is_not_yet_valid,
                    "subject": {
                        "common_name": subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value if subject.get_attributes_for_oid(NameOID.COMMON_NAME) else None,
                        "organization": subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value if subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME) else None,
                    },
                    "issuer": {
                        "common_name": issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value if issuer.get_attributes_for_oid(NameOID.COMMON_NAME) else None,
                        "organization": issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value if issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME) else None,
                    },
                    "validity": {
                        "not_before": not_valid_before.isoformat(),
                        "not_after": not_valid_after.isoformat(),
                        "days_until_expiry": (not_valid_after - now).days
                    },
                    "subject_alternative_names": []
                }
                
                if san_ext:
                    for san in san_ext.value:
                        if isinstance(san, x509.DNSName):
                            validation_result["subject_alternative_names"].append({"type": "DNS", "value": san.value})
                        elif isinstance(san, x509.IPAddress):
                            validation_result["subject_alternative_names"].append({"type": "IP", "value": str(san.value)})
                
                span.set_attribute("cert_valid", validation_result["valid"])
                span.set_attribute("cert_expired", is_expired)
                
                log_with_context(
                    "info" if validation_result["valid"] else "warning",
                    f"Certificate validation {'passed' if validation_result['valid'] else 'failed'}",
                    **validation_result
                )
                
                return validation_result
                
            except Exception as e:
                span.set_attribute("validation_error", str(e))
                
                log_with_context(
                    "error",
                    f"Certificate validation failed: {str(e)}",
                    cert_file=cert_file,
                    error=str(e)
                )
                
                return {
                    "valid": False,
                    "error": str(e)
                }
    
    def setup_tls_for_development(self, hostname: str = "localhost") -> bool:
        """Setup TLS for development environment"""
        
        with self.tracer.start_as_current_span("setup_tls_for_development") as span:
            span.set_attribute("hostname", hostname)
            
            # Check if certificates already exist
            if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
                log_with_context("info", "Certificate files already exist")
                
                # Validate existing certificate
                validation = self.validate_certificate()
                if validation.get("valid", False):
                    span.set_attribute("existing_cert_valid", True)
                    return True
                else:
                    log_with_context("warning", "Existing certificate is invalid, regenerating")
            
            try:
                # Generate new self-signed certificate
                cert_pem, key_pem = self.generate_self_signed_certificate(
                    hostname=hostname,
                    ip_addresses=["127.0.0.1", "::1"],
                    validity_days=365
                )
                
                # Save certificate files
                self.save_certificate_files(cert_pem, key_pem)
                
                span.set_attribute("tls_setup_complete", True)
                
                log_with_context(
                    "info",
                    "TLS setup completed for development",
                    hostname=hostname,
                    cert_file=str(self.cert_file),
                    key_file=str(self.key_file)
                )
                
                return True
                
            except Exception as e:
                span.set_attribute("tls_setup_error", str(e))
                
                log_with_context(
                    "error",
                    f"TLS setup failed: {str(e)}",
                    hostname=hostname,
                    error=str(e)
                )
                
                return False


# Global TLS manager instance
tls_manager = TLSCertificateManager()


def get_ssl_context() -> ssl.SSLContext:
    """Get server SSL context"""
    return tls_manager.create_ssl_context()


def get_client_ssl_context() -> ssl.SSLContext:
    """Get client SSL context"""
    return tls_manager.get_client_ssl_context()


def setup_tls() -> bool:
    """Setup TLS for the application"""
    return tls_manager.setup_tls_for_development()


def validate_tls_certificates() -> Dict[str, Any]:
    """Validate TLS certificates"""
    return tls_manager.validate_certificate()

