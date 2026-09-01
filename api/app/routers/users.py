"""
MÓDULO: routers/users.py - CRUD de usuarios (admin-only)

Define endpoints para gestionar usuarios: crear, listar, actualizar, eliminar.

IMPORTANTE: Todos estos endpoints requieren que el usuario sea administrador.
Eso se garantiza con `dependencies=[Depends(require_admin)]` en el router.

Endpoints:
- GET /api/users: Listar todos los usuarios
- POST /api/users: Crear un usuario
- GET /api/users/{user_id}: Obtener un usuario
- PATCH /api/users/{user_id}: Actualizar un usuario
- DELETE /api/users/{user_id}: Eliminar un usuario

Notas de seguridad:
- La contraseña se hashea con bcrypt antes de guardar
- Nunca devolvemos hashed_password en respuestas
- Los admins no pueden eliminarse a sí mismos
- El email es único en el sistema
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate
from app.security import hash_password

# Router: todos los endpoints requieren admin
router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(require_admin)]  # Todos los endpoints aquí necesitan admin
)


@router.get("", response_model=list[UserOut])
async def list_users(
    session: AsyncSession = Depends(get_session)
) -> list[User]:
    """
    Lista todos los usuarios del sistema.
    
    Require: Autenticación + Admin
    
    Returns:
        Lista de todos los usuarios (sin contraseñas)
        
    Ejemplo de respuesta:
        [
            {
                "id": 1,
                "email": "admin@deskly.com",
                "nombre": "Admin",
                "apellidos": "Deskly",
                "nombre_completo": "Admin Deskly",
                "is_admin": true,
                "creado_en": "2025-09-01T14:55:53.870Z"
            },
            ...
        ]
    """
    # Obtener todos los usuarios, ordenados por ID
    result = await session.scalars(
        select(User).order_by(User.id)
    )
    return list(result.all())


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Crea un nuevo usuario.
    
    Require: Autenticación + Admin
    
    Args:
        payload (UserCreate): { email, password, nombre, apellidos, is_admin }
        session (AsyncSession): Sesión de BD
        
    Returns:
        UserOut: Usuario creado (con is_admin reflejado)
        
    Raises:
        409: Si ya existe un usuario con ese email
        
    Ejemplo de request:
        POST /api/users
        {
            "email": "nuevo@deskly.com",
            "password": "password123",
            "nombre": "Juan",
            "apellidos": "García",
            "is_admin": false
        }
    """
    # Crear usuario
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),  # Hash con bcrypt
        nombre=payload.nombre,
        apellidos=payload.apellidos,
        is_admin=payload.is_admin,
    )
    session.add(user)
    
    try:
        # Guardar en BD
        await session.commit()
    except IntegrityError:
        # Email duplicado
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )
    
    # Refrescar objeto para obtener creado_en
    await session.refresh(user)
    return user


async def _get_user_or_404(session: AsyncSession, user_id: int) -> User:
    """
    Helper: obtiene un usuario o lanza 404.
    
    Evita repetir código en GET, PATCH y DELETE.
    
    Args:
        session: Sesión de BD
        user_id: ID del usuario
        
    Returns:
        Usuario si existe
        
    Raises:
        404: Si no existe
    """
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Obtiene un usuario específico.
    
    Require: Autenticación + Admin
    
    Args:
        user_id: ID del usuario
        session: Sesión de BD
        
    Returns:
        UserOut: Datos del usuario
        
    Raises:
        404: Si no existe
    """
    return await _get_user_or_404(session, user_id)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Actualiza parcialmente un usuario.
    
    Require: Autenticación + Admin
    
    Solo actualiza los campos presentes en payload. Los campos omitidos
    conservan su valor anterior.
    
    Args:
        user_id: ID del usuario
        payload (UserUpdate): Campos a actualizar (todos opcionales)
        session: Sesión de BD
        
    Returns:
        UserOut: Usuario actualizado
        
    Raises:
        404: Si no existe
        409: Si el nuevo email ya existe
        
    Ejemplo de request:
        PATCH /api/users/5
        { "nombre": "Nuevo Nombre" }  <- solo actualiza nombre
    """
    user = await _get_user_or_404(session, user_id)
    
    # Actualizar campos presentes
    if payload.email is not None:
        user.email = payload.email
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    if payload.nombre is not None:
        user.nombre = payload.nombre
    if payload.apellidos is not None:
        user.apellidos = payload.apellidos
    
    try:
        await session.commit()
    except IntegrityError:
        # Email duplicado
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )
    
    await session.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> None:
    """
    Elimina un usuario.
    
    Require: Autenticación + Admin
    
    Restricción: Un admin no puede eliminarse a sí mismo.
    
    Args:
        user_id: ID del usuario a eliminar
        session: Sesión de BD
        admin: Usuario autenticado (para verificar que no se auto-elimina)
        
    Raises:
        404: Si no existe
        400: Si intenta eliminarse a sí mismo
    """
    user = await _get_user_or_404(session, user_id)
    
    # No permitir que un admin se elimine a sí mismo
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propio usuario",
        )
    
    # Eliminar
    await session.delete(user)
    await session.commit()
