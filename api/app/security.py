"""Funciones de seguridad: hashing de contraseñas y tokens JWT.

Proporciona las funciones necesarias para:
- Hashear contraseñas con bcrypt
- Verificar contraseñas contra hashes
- Crear tokens JWT para autenticación
- Decodificar y validar tokens JWT
"""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# Contexto de hashing con bcrypt
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt.
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash de la contraseña
    """
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica si una contraseña coincide con su hash.
    
    Args:
        plain: Contraseña en texto plano
        hashed: Hash almacenado
        
    Returns:
        True si la contraseña coincide, False en caso contrario
    """
    return _pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    """Crea un token JWT firmado.
    
    El token contiene el ID del usuario como "subject" y una
    fecha de expiración configurable.
    
    Args:
        subject: ID del usuario (como string)
        
    Returns:
        Token JWT codificado
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Decodifica un token JWT y devuelve el ID del usuario.
    
    Si el token es inválido, está expirado o no tiene el formato
    correcto, devuelve None.
    
    Args:
        token: Token JWT
        
    Returns:
        ID del usuario si el token es válido, None en caso contrario
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
    sub = payload.get("sub")
    return str(sub) if sub is not None else None
