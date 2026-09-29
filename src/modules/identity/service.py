# Archivo: src/modules/identity/service.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from .model import User, PlanType
from .schema import UserCreate
# from src.core.security import get_password_hash # TODO: Implementar hashing

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_in: UserCreate) -> Optional[User]:
        """
        Crea un nuevo usuario en la base de datos.
        Maneja explícitamente excepciones de integridad (ej. email duplicado).
        """
        try:
            # TODO: Sustituir por lógica real de hashing (ej. Passlib / bcrypt)
            hashed_pw = f"hashed_{user_in.password}" 
            
            new_user = User(
                email=user_in.email,
                password_hash=hashed_pw,
                plan_type=PlanType(user_in.plan_type)
            )
            
            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)
            return new_user
            
        except IntegrityError as e:
            self.db.rollback()
            # TODO: Implementar log system (ej. logger.error(...))
            print(f"Error de Integridad (Email duplicado): {e}")
            raise ValueError("El correo electrónico ya está registrado.")
        except Exception as e:
            self.db.rollback()
            # Nunca silenciar la excepción genérica
            print(f"Error interno de base de datos: {e}")
            raise RuntimeError("Error al crear el usuario en la base de datos.")

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Recupera un usuario por su email.
        """
        try:
            return self.db.query(User).filter(User.email == email).first()
        except Exception as e:
            # TODO: Log error
            raise RuntimeError("Error al consultar el usuario.")