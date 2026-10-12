from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Tuple


PASSWORD_SCHEME = "scrypt"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return "$".join(
        [
            PASSWORD_SCHEME,
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )


def _verify_legacy_pbkdf2(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$")
        if scheme != "pbkdf2_sha256" or not 1 <= int(iterations) <= 2_000_000:
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def verify_password(password: str, encoded: str) -> Tuple[bool, bool]:
    """Return (valid, needs_rehash). Supports migration from the V6 PBKDF2 format."""
    if len(password) > 256 or len(encoded) > 1024:
        return False, False
    if encoded.startswith("pbkdf2_sha256$"):
        valid = _verify_legacy_pbkdf2(password, encoded)
        return valid, valid
    try:
        scheme, n, r, p, salt_b64, digest_b64 = encoded.split("$")
        if scheme != PASSWORD_SCHEME:
            return False, False
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        if not (1 <= int(n) <= 2**16 and 1 <= int(r) <= 8 and 1 <= int(p) <= 2 and 16 <= len(expected) <= 64 and 8 <= len(salt) <= 64):
            return False, False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        valid = hmac.compare_digest(actual, expected)
        needs = valid and (int(n), int(r), int(p), len(expected)) != (SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DKLEN)
        return valid, needs
    except Exception:
        return False, False


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 12:
        return False, "Password must contain at least 12 characters."
    if len(password) > 256:
        return False, "Password is too long."
    categories = 0
    categories += any(c.islower() for c in password)
    categories += any(c.isupper() for c in password)
    categories += any(c.isdigit() for c in password)
    categories += any(not c.isalnum() for c in password)
    if categories < 3:
        return False, "Use at least three character types: lowercase, uppercase, numbers, or symbols."
    return True, "Password accepted."


def new_session_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    hashed = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, hashed


def hash_session_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_identifier_hash(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def secure_filename_stem(name: str, max_len: int = 80) -> str:
    import re
    from pathlib import Path

    stem = Path(name).stem
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", stem).strip("_")[:max_len]
    return cleaned or "file"


class LoginThrottle:
    """Small in-memory throttle; suitable for local single-host deployments."""

    def __init__(self, max_attempts: int, lock_seconds: int):
        self.max_attempts = max_attempts
        self.lock_seconds = lock_seconds
        self._entries: dict[str, tuple[int, float]] = {}

    def blocked(self, identifier: str) -> tuple[bool, int]:
        key = stable_identifier_hash(identifier)
        attempts, until = self._entries.get(key, (0, 0.0))
        now = time.time()
        if until > now:
            return True, int(until - now) + 1
        if until:
            self._entries.pop(key, None)
        return False, 0

    def failure(self, identifier: str) -> None:
        key = stable_identifier_hash(identifier)
        attempts, _ = self._entries.get(key, (0, 0.0))
        attempts += 1
        if attempts >= self.max_attempts:
            self._entries[key] = (0, time.time() + self.lock_seconds)
        else:
            self._entries[key] = (attempts, 0.0)

    def success(self, identifier: str) -> None:
        self._entries.pop(stable_identifier_hash(identifier), None)
