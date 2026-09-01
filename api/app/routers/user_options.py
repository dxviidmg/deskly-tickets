"""Lightweight user lookup for populating selects.

Unlike the admin-only /api/users CRUD, this endpoint is available to any
authenticated user and returns only id + email (no sensitive fields).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas import UserOption

router = APIRouter(
    prefix="/api/users", tags=["users"], dependencies=[Depends(get_current_user)]
)


@router.get("/options", response_model=list[UserOption])
async def user_options(
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=50),
) -> list[User]:
    stmt = select(User)
    if q:
        stmt = stmt.where(func.lower(User.email).like(f"%{q.lower()}%"))
    stmt = stmt.order_by(User.email).limit(limit)
    result = await session.scalars(stmt)
    return list(result.all())
