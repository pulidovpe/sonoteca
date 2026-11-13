"""Certificado TLS autofirmado del servidor de sincronización.

El móvil NO valida contra una autoridad: «fija» la huella SHA-256 del certificado, que recibe al emparejarse (en la URL
de emparejamiento). Así el cifrado funciona en la red local sin comprar ni instalar certificados."""
from __future__ import annotations

import hashlib
import os
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from ..core import paths

CERT_NAME = "server-cert.pem"
KEY_NAME = "server-key.pem"
VALID_YEARS = 10


def sync_dir() -> Path:
    return paths.data_dir() / "sync"


def fingerprint_of_pem(pem: bytes) -> str:
    cert = x509.load_pem_x509_certificate(pem)
    return hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()


def ensure_certificate(directory: Path | None = None) -> tuple[Path, Path, str]:
    """(certificado, clave, huella SHA-256 en hexadecimal). Los crea la primera vez; se conservan después."""
    directory = Path(directory) if directory else sync_dir()
    directory.mkdir(parents=True, exist_ok=True)
    cert_path, key_path = directory / CERT_NAME, directory / KEY_NAME
    if cert_path.is_file() and key_path.is_file():
        return cert_path, key_path, fingerprint_of_pem(cert_path.read_bytes())

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Sonoteca")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=365 * VALID_YEARS))
            .sign(key, hashes.SHA256()))
    key_bytes = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption())
    cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)   # la clave solo la lee el usuario
    with os.fdopen(fd, "wb") as handle:
        handle.write(key_bytes)
    cert_path.write_bytes(cert_bytes)
    return cert_path, key_path, fingerprint_of_pem(cert_bytes)


def server_context(cert_path: Path, key_path: Path) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(cert_path), str(key_path))
    return context
