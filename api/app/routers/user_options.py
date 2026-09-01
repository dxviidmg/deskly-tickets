"""
MÓDULO: routers/user_options.py - Búsqueda y selección de usuarios

Endpoint ligero para obtener usuarios para populates (selects/dropdowns).

Diferencia con /api/users:
- /api/users (admin-only): CRUD completo, devuelve todos los campos
- /api/users/options (autenticado): búsqueda, solo id + email

Use case:
En el frontend, cuando haces "Asignar a: <dropdown>", se llama a
/api/users/options?q=juan&limit=5 para obtener sugerencias mientras escribes.

Búsqueda:
Se busca en:
- Email: "juan@company.com" → match si escribes "juan"
- Nombre: "Juan" → match
- Apellidos: "García" → match
- Nombre completo: "Juan García" → match
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas import UserOption

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)],  # Requiere autenticación
)


@router.get("/options", response_model=list[UserOption])
async def user_options(
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=50),
) -> list[User]:
    """
    Búsqueda de usuarios para populating selects/dropdowns.
    
    Require: Autenticación (cualquier usuario autenticado)
    
    Query params:
    - q: Texto de búsqueda (opcional)
    - limit: Máximo de resultados (por defecto 5, máximo 50)
    
    Returns:
        Lista de usuarios (id, email, nombre_completo)
        
    Búsqueda:
    Si q="juan", devuelve usuarios donde:
    - Email contiene "juan" (case-insensitive)
    - Nombre contiene "juan"
    - Apellidos contiene "juan"
    - Nombre completo contiene "juan"
    
    Ejemplo:
        GET /api/users/options?q=juan&limit=10
        
    Respuesta:
        [
            {
                "id": 3,
                "email": "juan@company.com",
                "nombre_completo": "Juan García López"
            },
            {
                "id": 7,
                "email": "juan.alt@company.com",
                "nombre_completo": "Juan Altíssimo"
            }
        ]
    """
    # Comenzar con query básica
    stmt = select(User)
    
    # Si hay texto de búsqueda, aplicar filtros
    if q:
        # Normalizar búsqueda a minúsculas para case-insensitive
        needle = f"%{q.lower()}%"
        
        # Campo de búsqueda: nombre + espacio + apellidos (nombre completo)
        full = func.lower(User.nombre + " " + User.apellidos)
        
        # Buscar en: email, nombre, apellidos, o nombre completo
        stmt = stmt.where(
            func.lower(User.email).like(needle)
            | func.lower(User.nombre).like(needle)
            | func.lower(User.apellidos).like(needle)
            | full.like(needle)
        )
    
    # Ordenar por nombre y apellidos (para consistencia)
    # Limitar resultados
    stmt = stmt.order_by(User.nombre, User.apellidos).limit(limit)
    
    # Ejecutar y devolver
    result = await session.scalars(stmt)
    return list(result.all())
