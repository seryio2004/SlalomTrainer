"""Password and session primitives; HTTP authorization lives in main.py."""

import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt$16384${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        method, cost, salt, expected = stored.split("$")
        if method != "scrypt" or cost != "16384":
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def secret_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
