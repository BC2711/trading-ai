import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return f"pbkdf2_sha256${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        algorithm, salt_value, digest_value = hashed_password.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False

    salt = base64.urlsafe_b64decode(salt_value.encode())
    expected = base64.urlsafe_b64decode(digest_value.encode())
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return hmac.compare_digest(actual, expected)


def create_access_token(subject: str, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": int(expires_at.timestamp())}
    return encode_jwt(payload)


def encode_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = b64json(header)
    payload_b64 = b64json(payload)
    signature = sign(f"{header_b64}.{payload_b64}")
    return f"{header_b64}.{payload_b64}.{signature}"


def decode_jwt(token: str) -> dict[str, Any] | None:
    try:
        header_b64, payload_b64, signature = token.split(".", 2)
        expected = sign(f"{header_b64}.{payload_b64}")
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(pad_b64(payload_b64)).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None

    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        return None
    return payload


def encrypt_secret(secret: str) -> str:
    nonce = os.urandom(16)
    data = secret.encode("utf-8")
    key_stream = stream_key(nonce, len(data))
    encrypted = bytes(byte ^ key_stream[index] for index, byte in enumerate(data))
    return base64.urlsafe_b64encode(nonce + encrypted).decode("utf-8")


def decrypt_secret(encrypted_secret: str) -> str:
    payload = base64.urlsafe_b64decode(encrypted_secret.encode("utf-8"))
    nonce = payload[:16]
    data = payload[16:]
    key_stream = stream_key(nonce, len(data))
    decrypted = bytes(byte ^ key_stream[index] for index, byte in enumerate(data))
    return decrypted.decode("utf-8")


def stream_key(nonce: bytes, length: int) -> bytes:
    seed = settings.credential_encryption_secret.encode("utf-8")
    blocks: list[bytes] = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        blocks.append(hmac.new(seed, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def b64json(value: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode("utf-8")).decode("utf-8").rstrip("=")


def sign(value: str) -> str:
    digest = hmac.new(settings.jwt_secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def pad_b64(value: str) -> bytes:
    return (value + "=" * (-len(value) % 4)).encode("utf-8")
