"""Password hashing (bcrypt) and username validation."""

from __future__ import annotations

import bcrypt

from profile import USERNAME_RE


def validate_username(username: str) -> bool:
    return bool(USERNAME_RE.match(username))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            password_hash.encode("ascii"),
        )
    except ValueError:
        return False
