# Archivo: src/tests/test_security.py
import os
from datetime import timedelta

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)

import jwt
import pytest

from src.core.config import get_settings
from src.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_hash_is_not_plaintext_and_verifies() -> None:
    hashed: str = get_password_hash("Secreta123!")
    assert hashed != "Secreta123!"
    assert verify_password("Secreta123!", hashed) is True


def test_wrong_password_fails() -> None:
    hashed: str = get_password_hash("Secreta123!")
    assert verify_password("otra", hashed) is False


def test_verify_with_malformed_hash_returns_false() -> None:
    assert verify_password("x", "no-es-un-hash") is False


def test_password_over_72_bytes_is_rejected() -> None:
    with pytest.raises(ValueError):
        get_password_hash("a" * 73)


def test_token_roundtrip() -> None:
    token: str = create_access_token(subject="user-1", role="consumidor")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "consumidor"


def test_expired_token_raises() -> None:
    token: str = create_access_token("u", "consumidor", timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_token_with_wrong_signature_raises() -> None:
    forged: str = jwt.encode({"sub": "u", "exp": 9999999999}, "otra-clave" * 5, algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(forged)


def test_settings_reject_short_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "corta")
    get_settings.cache_clear()
    with pytest.raises(ValueError):
        get_settings()
    get_settings.cache_clear()