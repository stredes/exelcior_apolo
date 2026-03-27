from __future__ import annotations

import base64
import hashlib
import hmac
import os


PBKDF2_ROUNDS = 200_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    secret = (password or "").encode("utf-8")
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", secret, salt, PBKDF2_ROUNDS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ROUNDS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    value = (stored_hash or "").strip()
    if not value.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(password or "", stored_hash or "")

    try:
        _algo, rounds_raw, salt_raw, digest_raw = value.split("$", 3)
        rounds = int(rounds_raw)
        salt = base64.b64decode(salt_raw.encode("ascii"))
        expected = base64.b64decode(digest_raw.encode("ascii"))
    except Exception:
        return False

    current = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt, rounds)
    return hmac.compare_digest(current, expected)


def looks_hashed(value: str) -> bool:
    return (value or "").startswith("pbkdf2_sha256$")
