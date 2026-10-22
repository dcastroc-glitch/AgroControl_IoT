"""Autenticación local basada en PBKDF2, sin contraseñas en texto plano."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 120_000)
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def usuarios_por_defecto() -> dict[str, Any]:
    return {
        "operador": {"rol": "operador", "password": hash_password("agrocontrol")},
        "admin": {
            "rol": "admin",
            "password": hash_password(os.getenv("AGRO_ADMIN_PASSWORD", "agrocontrol-admin")),
        },
    }
