"""Small, password-protected identities and signed agent messages."""

from __future__ import annotations

import hmac
import base64
from dataclasses import dataclass, field, replace
from hashlib import sha256
import json
import secrets
import time
from typing import Any

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


SALT_SIZE = 16
NONCE_SIZE = 12
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
MAX_PASSWORD_LENGTH = 1024
MAX_STRING_LENGTH = 4096
PAIRING_TOKEN_VERSION = "ment1"


def _require_text(value: str, name: str, max_length: int = MAX_STRING_LENGTH) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    if len(value) > max_length:
        raise ValueError(f"{name} exceeds maximum length of {max_length}")
    return value


def _hash_parts(*parts: str) -> str:
    encoded = bytearray()
    for part in parts:
        value = _require_text(part, "hash part").encode("utf-8")
        encoded.extend(len(value).to_bytes(8, "big"))
        encoded.extend(value)
    return sha256(encoded).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _public_key_bytes(public_key: str) -> bytes:
    try:
        raw = bytes.fromhex(_require_text(public_key, "public_key"))
        Ed25519PublicKey.from_public_bytes(raw)
        return raw
    except (ValueError, TypeError):
        raise ValueError("public_key must be a valid Ed25519 public key") from None


def _derive_unlock_key(password: str, salt: bytes) -> bytes:
    _require_text(password, "password", MAX_PASSWORD_LENGTH)
    return Scrypt(
        salt=salt,
        length=32,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    ).derive(password.encode("utf-8"))


DEFAULT_H = sha256(b"agent-id-protocol-v1").hexdigest()


def derive_id(public_key: str, H: str = DEFAULT_H) -> str:
    """Derive the stable public ID from the protocol base and public key."""
    _public_key_bytes(public_key)
    return _hash_parts(H, public_key)


def verify_identity(identity_id: str, public_key: str, H: str = DEFAULT_H) -> bool:
    """Verify that an ID belongs to a specific public key."""
    _require_text(identity_id, "identity_id")
    derived = derive_id(public_key, H)
    return hmac.compare_digest(derived, identity_id)


@dataclass(frozen=True)
class AgentIdentity:
    """Public identity plus an encrypted private signing key."""

    id: str
    public_key: str
    encrypted_private_key: str = field(repr=False)
    salt: str = field(repr=False)
    nonce: str = field(repr=False)
    H: str = DEFAULT_H

    @property
    def public(self) -> dict[str, str]:
        return {"H": self.H, "id": self.id, "public_key": self.public_key}

    def bundle(self) -> dict[str, str]:
        """Return the data needed to store and restore this identity."""
        return {
            **self.public,
            "encrypted_private_key": self.encrypted_private_key,
            "salt": self.salt,
            "nonce": self.nonce,
        }

    @classmethod
    def from_bundle(cls, bundle: dict[str, str]) -> "AgentIdentity":
        identity = cls(
            id=bundle["id"],
            public_key=bundle["public_key"],
            encrypted_private_key=bundle["encrypted_private_key"],
            salt=bundle["salt"],
            nonce=bundle["nonce"],
            H=bundle["H"],
        )
        if not verify_identity(identity.id, identity.public_key, identity.H):
            raise ValueError("identity does not match its public key")
        return identity

    def _aad(self) -> bytes:
        return _canonical_bytes(self.public)

    def _private_key(self, password: str) -> Ed25519PrivateKey:
        try:
            key = _derive_unlock_key(password, bytes.fromhex(self.salt))
            raw = AESGCM(key).decrypt(
                bytes.fromhex(self.nonce),
                bytes.fromhex(self.encrypted_private_key),
                self._aad(),
            )
            private_key = Ed25519PrivateKey.from_private_bytes(raw)
            if private_key.public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            ).hex() != self.public_key:
                raise ValueError("private key does not match identity")
            return private_key
        except (InvalidTag, ValueError, TypeError):
            raise ValueError("invalid password or identity bundle") from None

    def unlock(self, password: str) -> "UnlockedIdentity":
        """Unlock the private key once for repeated agent operations."""
        return UnlockedIdentity(self.id, self.public_key, self._private_key(password))

    def sign(self, value: Any, password: str) -> str:
        """Sign data with one-off password unlocking (compatibility API)."""
        return self.unlock(password).sign(value)


@dataclass(frozen=True)
class UnlockedIdentity:
    """In-memory signing session created by AgentIdentity.unlock."""

    id: str
    public_key: str
    _private_key: Ed25519PrivateKey = field(repr=False)

    @property
    def public(self) -> dict[str, str]:
        return {"id": self.id, "public_key": self.public_key}

    def sign(self, value: Any) -> str:
        """Sign data without asking for the password again."""
        return self._private_key.sign(_canonical_bytes(value)).hex()


@dataclass(frozen=True)
class PairingToken:
    """A short-lived, single-purpose invitation for another agent.

    The token is self-contained and signed by the issuer.  It contains no
    password or private key.  The Environment consumes its nonce on first
    use, so a recipient only needs the printed token to join once.
    """

    name: str
    issuer_id: str
    issuer_public_key: str
    expires_at: int
    nonce: str
    signature: str

    @classmethod
    def create(
        cls,
        identity: UnlockedIdentity,
        name: str,
        ttl_seconds: int = 300,
    ) -> "PairingToken":
        _require_text(name, "name")
        if ttl_seconds <= 0 or ttl_seconds > 86_400:
            raise ValueError("ttl_seconds must be between 1 and 86400")
        payload = {
            "v": PAIRING_TOKEN_VERSION,
            "name": name,
            "issuer_id": identity.id,
            "issuer_public_key": identity.public_key,
            "expires_at": int(time.time()) + ttl_seconds,
            "nonce": secrets.token_urlsafe(24),
        }
        return cls(
            name=payload["name"],
            issuer_id=payload["issuer_id"],
            issuer_public_key=payload["issuer_public_key"],
            expires_at=payload["expires_at"],
            nonce=payload["nonce"],
            signature=identity.sign(payload),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "v": PAIRING_TOKEN_VERSION,
            "name": self.name,
            "issuer_id": self.issuer_id,
            "issuer_public_key": self.issuer_public_key,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
        }

    def encode(self) -> str:
        payload = base64.urlsafe_b64encode(_canonical_bytes(self._payload())).decode().rstrip("=")
        signature = base64.urlsafe_b64encode(bytes.fromhex(self.signature)).decode().rstrip("=")
        return f"{PAIRING_TOKEN_VERSION}.{payload}.{signature}"

    @classmethod
    def decode(cls, value: str) -> "PairingToken":
        _require_text(value, "token", 16_384)
        parts = value.split(".")
        if len(parts) != 3 or parts[0] != PAIRING_TOKEN_VERSION:
            raise ValueError("invalid pairing token")
        try:
            padding = "=" * (-len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + padding))
            padding = "=" * (-len(parts[2]) % 4)
            signature = base64.urlsafe_b64decode(parts[2] + padding).hex()
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("invalid pairing token") from None
        if not isinstance(payload, dict) or payload.get("v") != PAIRING_TOKEN_VERSION:
            raise ValueError("invalid pairing token payload")
        token = cls(
            name=_require_text(payload.get("name"), "token name"),
            issuer_id=_require_text(payload.get("issuer_id"), "issuer_id"),
            issuer_public_key=_require_text(payload.get("issuer_public_key"), "issuer_public_key"),
            expires_at=int(payload["expires_at"]),
            nonce=_require_text(payload.get("nonce"), "nonce"),
            signature=signature,
        )
        if token._payload() != payload:
            raise ValueError("invalid pairing token payload")
        return token

    def verify(self, now: int | None = None) -> bool:
        current = int(time.time()) if now is None else now
        return (
            self.expires_at >= current
            and verify_identity(self.issuer_id, self.issuer_public_key)
            and verify_signature(self.issuer_public_key, self._payload(), self.signature)
        )


def create_identity(password: str, H: str = DEFAULT_H) -> AgentIdentity:
    """Create a random signing key protected by a password."""
    _require_text(password, "password")
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    ).hex()
    private_raw = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)
    identity_id = derive_id(public_key, H)
    temporary = AgentIdentity(
        id=identity_id,
        public_key=public_key,
        encrypted_private_key="",
        salt=salt.hex(),
        nonce=nonce.hex(),
        H=H,
    )
    unlock_key = _derive_unlock_key(password, salt)
    encrypted = AESGCM(unlock_key).encrypt(nonce, private_raw, temporary._aad())
    return replace(temporary, encrypted_private_key=encrypted.hex())


def verify_signature(public_key: str, value: Any, signature: str) -> bool:
    """Verify an Ed25519 signature over canonical data."""
    try:
        _public_key_bytes(public_key)
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key)).verify(
            bytes.fromhex(signature), _canonical_bytes(value)
        )
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


@dataclass(frozen=True)
class Message:
    """A generic signed or unsigned message; target_id is optional."""

    source_id: str
    content: Any
    target_id: str | None = None
    t: int = field(default_factory=lambda: time.time_ns() // 1_000_000)
    signature: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        if self.target_id is not None:
            _require_text(self.target_id, "target_id")

    def _unsigned(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "content": self.content,
            "t": self.t,
        }

    def sign(
        self,
        identity: AgentIdentity | UnlockedIdentity,
        password: str | None = None,
    ) -> "Message":
        if self.source_id != identity.id:
            raise ValueError("message source does not match identity")
        if isinstance(identity, UnlockedIdentity):
            if password is not None:
                raise ValueError("password is not used by an unlocked identity")
            signer = identity
        else:
            if password is None:
                raise ValueError("password is required to unlock the identity")
            signer = identity.unlock(password)
        return replace(self, signature=signer.sign(self._unsigned()))

    def verify(self, public_key: str) -> bool:
        return self.signature is not None and verify_signature(
            public_key, self._unsigned(), self.signature
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self._unsigned(), "signature": self.signature}
