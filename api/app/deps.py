"""
MÓDULO: deps.py - Dependencias de FastAPI

"Dependencias" en FastAPI son funciones que FastAPI llama automáticamente
para:
- Extraer datos de requests
- Validar usuarios autenticados
- Inyectar en handlers

Ejemplo de uso en un endpoint:
    @router.get("/me")
    async def get_me(current_user = Depends(get_current_user)):
        return current_user

FastAPI automáticamente:
1. Busca el header "Authorization: Bearer <token>"
2. Llama a get_current_user(<token>)
3. Si falla, devuelve 401
4. Si funciona, pasa current_user al handler

Ventajas:
- Reutilizable: varios endpoints usan get_current_user
- Centralizado: la lógica de autenticación está aquí, no en cada endpoint
- Testeable: puedes mocker la dependencia en tests
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.security import decode_access_token

# Esquema OAuth2: le dice a FastAPI dónde esperar el token
# tokenUrl: endpoint donde el cliente obtiene tokens (aparece en /docs)
# El cliente envía: Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Error estándar: credenciales inválidas o token expirado
_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependencia que obtiene el usuario actual autenticado.
    
    Proceso:
    1. Extrae el token del header Authorization
    2. Decodifica el token JWT (valida firma, expiración, etc.)
    3. Obtiene el ID del usuario del token (subject)
    4. Busca el usuario en la BD
    5. Si todo falló en algún paso, lanza 401
    
    Uso:
        @router.get("/me")
        async def get_me(current_user = Depends(get_current_user)):
            return current_user  # El usuario autenticado
    
    Args:
        token (str): Token JWT del header Authorization (inyectado por oauth2_scheme)
        session (AsyncSession): Sesión de BD (inyectada por get_session)
        
    Returns:
        User: El usuario autenticado
        
    Raises:
        HTTPException(401): Si el token es inválido, expirado, o el usuario no existe
    """
    # Decodificar el token JWT
    # decode_access_token devuelve el user_id o None
    subject = decode_access_token(token)
    if subject is None:
        raise _credentials_error
    
    # Convertir el ID a entero
    try:
        user_id = int(subject)
    except ValueError:
        raise _credentials_error
    
    # Buscar el usuario en la BD
    user = await session.get(User, user_id)
    if user is None:
        raise _credentials_error
    
    return user


async def require_admin(current: User = Depends(get_current_user)) -> User:
    """
    Dependencia que requiere que el usuario sea administrador.
    
    Se apila sobre get_current_user: primero valida autenticación,
    luego valida permisos de admin.
    
    Uso:
        @router.delete("/users/{user_id}")
        async def delete_user(user_id: int, admin = Depends(require_admin)):
            # Solo llega aquí si el usuario está autenticado Y es admin
    
    Args:
        current (User): Usuario autenticado (inyectado por get_current_user)
        
    Returns:
        User: El usuario si es admin
        
    Raises:
        HTTPException(403): Si el usuario no es admin
    """
    if not current.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return current
