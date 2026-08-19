"""Password hashing via stdlib hashlib/secrets (pbkdf2-hmac) — avoids a
compiled-wheel dependency (bcrypt/passlib) on Windows for this project's scale."""
import hashlib
import secrets

_ITERATIONS = 200_000


def hash_password(password: str) -> tuple[str, str]:
    """Returns (password_hash, password_salt), both hex-encoded."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, password_salt: str) -> bool:
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), password_salt.encode("utf-8"), _ITERATIONS
    ).hex()
    return secrets.compare_digest(candidate, password_hash)
