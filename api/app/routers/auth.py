"""
MÓDULO: routers/auth.py - Endpoints de autenticación

Define los endpoints para login y obtener información del usuario actual.

Endpoints:
- POST /api/auth/login: Autentica un usuario y devuelve JWT
- GET /api/auth/me: Devuelve datos del usuario autenticado

¿Cómo funciona login?
1. Cliente POST a /login con email + contraseña
2. Buscamos el usuario en la BD
3. Verificamos que la contraseña coincide (usando bcrypt)
4. Generamos un token JWT con la ID del usuario
5. Devolvemos el token al cliente
6. Cliente almacena el token (localStorage, cookies, etc.)
7. Cliente envía el token en requests posteriores: Authorization: Bearer <token>

Router: 
- prefix="/api/auth": todos los endpoints comienzan con /api/auth
- tags=["auth"]: agrupa endpoints en la documentación /docs
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginIn, Token, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)

# Hash señuelo para mitigar timing attacks en el login: cuando el email no
# existe, verificamos la contraseña contra este hash para que el coste de
# cómputo (y por tanto el tiempo de respuesta) sea comparable al de un usuario
# real. Se calcula una sola vez al importar el módulo.
_DUMMY_HASH = hash_password("timing-attack-mitigation-dummy-password")


@router.post("/login", response_model=Token)
async def login(
    payload: LoginIn,
    session: AsyncSession = Depends(get_session)
) -> Token:
    """
    Endpoint de login: autentica un usuario y devuelve un token JWT.
    
    Proceso:
    1. Buscar usuario por email
    2. Si no existe: devolver 401
    3. Si existe: verificar contraseña
    4. Si contraseña incorrecta: devolver 401
    5. Si correcta: generar JWT y devolver
    
    El cliente guarda el token y lo envía en requests posteriores:
        Authorization: Bearer <token>
    
    El token expira después de X minutos (configurable en config.py)
    
    Args:
        payload (LoginIn): { email: str, password: str }
        session (AsyncSession): Sesión de BD (inyectada)
        
    Returns:
        Token: { access_token: str, token_type: "bearer" }
        
    Ejemplo de request:
        POST /api/auth/login
        { "email": "admin@deskly.com", "password": "admin123" }
    
    Ejemplo de respuesta:
        {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "token_type": "bearer"
        }
    """
    # Buscar el usuario por email
    user = await session.scalar(
        select(User).where(User.email == payload.email)
    )

    # Verificación de contraseña con mitigación de "timing attack":
    # Si el usuario NO existe, igualmente ejecutamos verify_password contra un
    # hash señuelo (_DUMMY_HASH). Así el tiempo de respuesta es similar exista o
    # no el usuario, evitando que un atacante deduzca qué emails están
    # registrados midiendo la latencia. El resultado siempre será 401.
    if user is None:
        verify_password(payload.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    # Generar token JWT
    token = create_access_token(subject=str(user.id))

    # Devolver token
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)) -> User:
    """
    Endpoint que devuelve los datos del usuario actual autenticado.
    
    Sirve para:
    - Verificar que el token es válido (si devuelve 401, token expirado)
    - Obtener información del usuario (email, nombre, etc.)
    - Usualmente el frontend lo llama al cargar para saber quién está logueado
    
    Require autenticación: el cliente debe enviar un header válido:
        Authorization: Bearer <token_aquí>
    
    Args:
        current (User): Usuario autenticado (inyectado por get_current_user)
        
    Returns:
        UserOut: Datos del usuario (sin contraseña)
        
    Ejemplo de request:
        GET /api/auth/me
        Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
    
    Ejemplo de respuesta:
        {
            "id": 1,
            "email": "admin@deskly.com",
            "nombre": "Admin",
            "apellidos": "Deskly",
            "nombre_completo": "Admin Deskly",
            "is_admin": true,
            "creado_en": "2025-09-01T14:55:53.870Z"
        }
    """
    return current
