# Archivo: src/modules/identity/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any

from src.core.database import get_db
from src.core.security import create_access_token
from .service import UserService
from .schema import UserCreate, UserResponse, LoginRequest, LoginResponse

# Definición del Router unificado para el módulo Identity & Access (RBAC & JWT)
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Identity & Access"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registro de nuevos usuarios",
    description="Crea una cuenta asignando el rol correspondiente (Consumidor/Dropshipper/Admin)."
)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Endpoint para el registro de nuevos usuarios en la plataforma ValoraBot.
    Garantiza la creación de la cuenta y retorna la representación pública del usuario.
    """
    service = UserService(db)
    try:
        # Delegación de lógica de negocio y persistencia
        new_user = service.create_user(user_in)
        return new_user

    except ValueError as ve:
        # Captura errores de negocio (ej. correo electrónico previamente registrado)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except RuntimeError as re:
        # Captura fallos de infraestructura o excepciones de BD no controladas
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al procesar el registro."
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Autenticación de usuario y generación de JWT",
    description="Valida credenciales contra la base de datos y emite un token de acceso JWT Bearer."
)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
) -> LoginResponse:
    """
    Endpoint para autenticación. Verifica la existencia del usuario, valida el hash 
    de la contraseña y devuelve un token de acceso firmado en formato JWT.
    """
    service = UserService(db)
    try:
        user = service.authenticate_user(credentials.email, credentials.password)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor durante la autenticación."
        ) from exc

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role: str = user.plan_type.value
    return LoginResponse(
        access_token=create_access_token(subject=str(user.id), role=role),
        token_type="bearer",
        role=role,
    )