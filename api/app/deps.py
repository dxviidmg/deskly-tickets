"""Authentication dependencies."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.security import decode_access_token

# tokenUrl is where clients obtain a token (used by the OpenAPI docs UI).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    subject = decode_access_token(token)
    if subject is None:
        raise _credentials_error
    try:
        user_id = int(subject)
    except ValueError:
        raise _credentials_error
    user = await session.get(User, user_id)
    if user is None:
        raise _credentials_error
    return user


async def require_admin(current: User = Depends(get_current_user)) -> User:
    """Allow only users that can manage other users (is_admin)."""
    if not current.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return current
