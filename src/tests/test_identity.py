# Archivo: tests/test_identity.py
import pytest
from fastapi import status


def test_register_user_success(client):
    """Verifica el registro exitoso de un nuevo usuario."""
    payload = {
        "email": "nuevo.usuario@valorabot.io",
        "password": "PasswordSeguro123!"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == payload["email"]
    assert "id" in data


def test_register_duplicate_email_fails(client):
    """Verifica que no se permitan registros con correos electrónicos duplicados."""
    payload = {
        "email": "duplicado@valorabot.io",
        "password": "PasswordSeguro123!"
    }
    # Primer registro
    client.post("/api/v1/auth/register", json=payload)
    
    # Intento duplicado
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_success(client):
    """Verifica la generación correcta del token JWT al ingresar credenciales válidas."""
    email = "login.test@valorabot.io"
    password = "MiPassword123!"
    
    # Crear usuario
    client.post("/api/v1/auth/register", json={"email": email, "password": password})

    # Iniciar sesión
    login_data = {"email": email, "password": password}
    response = client.post("/api/v1/auth/login", json=login_data)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client):
    """Verifica que el sistema rechace contraseñas incorrectas con HTTP 401."""
    email = "login.fail@valorabot.io"
    client.post("/api/v1/auth/register", json={"email": email, "password": "PasswordCorrecta123"})

    response = client.post("/api/v1/auth/login", json={"email": email, "password": "PasswordIncorrecta"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED