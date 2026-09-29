# Archivo: src/core/security.py
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.database import get_db

logger = logging.getLogger(__name__)
_bearer_scheme = HTTPBearer(auto_error=False)
_MAX_BCRYPT_BYTES: int = 72


def get_password_hash(password: str) -> str:
    raw: bytes = password.encode("utf-8")
    if len(raw) > _MAX_BCRYPT_BYTES:
        raise ValueError("La contraseña excede 72 bytes.")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Hash malformado o contraseña >72 bytes: nunca válido.
        return False


def create_access_token(
    subject: Optional[str] = None,
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    *,
    data: Optional[dict[str, Any]] = None,
) -> str:
    settings = get_settings()
    payload: dict[str, Any] = dict(data or {})
    token_subject = subject or payload.get("sub")
    if not isinstance(token_subject, str) or not token_subject:
        raise ValueError("El token requiere un subject válido.")

    delta: timedelta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    now: datetime = datetime.now(timezone.utc)
    payload.update({"sub": token_subject, "iat": now, "exp": now + delta})
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],  # lista fija: evita algorithm confusion / alg=none
        options={"require": ["exp", "sub"]},
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
):
    # Import local para evitar ciclos identity.service -> security -> identity.model
    from src.modules.identity.model import User

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise unauthorized

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise unauthorized
    return user