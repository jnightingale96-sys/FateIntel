"""Detached RSA-PSS signatures for exact manifest bytes."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import stat
from typing import Any


class SigningError(ValueError):
    """Raised when explicitly requested signing cannot be completed."""


def signing_available() -> bool:
    try:
        import cryptography  # noqa: F401
    except ImportError:
        return False
    return True


def read_private_key_file(path: str | Path) -> bytes:
    key_path = Path(path).expanduser()
    if not key_path.is_absolute():
        raise SigningError("REACH manifest private key path must be absolute")
    if not key_path.is_file():
        raise SigningError("Configured REACH manifest private key file does not exist")
    size = key_path.stat().st_size
    if size <= 0 or size > 1024 * 1024:
        raise SigningError("REACH manifest private key file has an invalid size")
    if os.name != "nt":
        permissions = stat.S_IMODE(key_path.stat().st_mode)
        if permissions & 0o077:
            raise SigningError("REACH manifest private key must not be group- or world-readable")
    return key_path.read_bytes()


@dataclass(frozen=True)
class RSAPSSSigner:
    private_key: Any
    public_key_fingerprint_sha256: str
    key_size_bits: int

    @classmethod
    def from_private_pem(cls, private_pem: bytes) -> "RSAPSSSigner":
        if not signing_available():
            raise SigningError("RSA signing requires the optional cryptography dependency")
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        try:
            key = serialization.load_pem_private_key(private_pem, password=None)
        except (TypeError, ValueError) as exc:
            raise SigningError("Private key must be a valid, unencrypted PEM key") from exc
        if not isinstance(key, rsa.RSAPrivateKey):
            raise SigningError("REACH manifest signing requires an RSA private key")
        if key.key_size < 2048:
            raise SigningError("REACH manifest RSA keys must be at least 2048 bits")
        public_der = key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return cls(
            private_key=key,
            public_key_fingerprint_sha256=sha256(public_der).hexdigest(),
            key_size_bits=key.key_size,
        )

    def metadata(self) -> dict[str, object]:
        return {
            "mode": "rsa",
            "algorithm": "rsa-pss-sha256",
            "signature_file": "manifest.sig",
            "key_fingerprint_sha256": self.public_key_fingerprint_sha256,
            "key_size_bits": self.key_size_bits,
            "trust_note": "Verify the key fingerprint against an independently trusted record.",
        }

    def sign(self, data: bytes) -> bytes:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        return self.private_key.sign(
            data,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=hashes.SHA256().digest_size),
            hashes.SHA256(),
        )


def public_key_fingerprint(public_pem: bytes) -> str:
    if not signing_available():
        raise SigningError("RSA verification requires the optional cryptography dependency")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    try:
        key = serialization.load_pem_public_key(public_pem)
    except (TypeError, ValueError) as exc:
        raise SigningError("Public key must be a valid PEM key") from exc
    if not isinstance(key, rsa.RSAPublicKey):
        raise SigningError("REACH manifest verification requires an RSA public key")
    public_der = key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return sha256(public_der).hexdigest()


def verify_rsa_pss(data: bytes, signature: bytes, public_pem: bytes) -> bool:
    if not signing_available():
        raise SigningError("RSA verification requires the optional cryptography dependency")
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    try:
        key = serialization.load_pem_public_key(public_pem)
    except (TypeError, ValueError) as exc:
        raise SigningError("Public key must be a valid PEM key") from exc
    if not isinstance(key, rsa.RSAPublicKey):
        raise SigningError("REACH manifest verification requires an RSA public key")
    try:
        key.verify(
            signature,
            data,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=hashes.SHA256().digest_size),
            hashes.SHA256(),
        )
    except InvalidSignature:
        return False
    return True
