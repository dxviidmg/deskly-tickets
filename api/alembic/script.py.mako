"""
ARCHIVO: alembic/script.py.mako
PROPÓSITO: Plantilla (template) para generar archivos de migración

Mako es un motor de templates (similar a Jinja2).
Este archivo es plantilla: cuando Alembic genera un nuevo script de migración,
lo crea usando esta plantilla.

¿Cuándo se genera un script?
    alembic revision --autogenerate -m "Add username column"

Resultado:
    alembic/versions/0002_add_username_column.py
    (basado en script.py.mako con los placeholders rellenados)

Estructura de una migración:
```python
def upgrade() -> None:
    # Cambios a aplicar (CREATE TABLE, ALTER TABLE, etc.)
    pass

def downgrade() -> None:
    # Cómo deshacerla (DROP TABLE, DROP COLUMN, etc.)
    pass
```

Placeholders:
- ${message}: descripción de la migración (ej: "Add username column")
- ${up_revision}: ID de esta revisión (ej: "abcd123def")
- ${down_revision}: ID de la revisión anterior
- ${create_date}: fecha/hora de creación
- ${upgrades}: código de cambios (generado automáticamente)
- ${downgrades}: código para deshacer (generado automáticamente)

NOTA: Este es un template Mako, no Python ejecutable directamente.
Alembic lo procesa y genera .py real.
"""

# ${message}
# 
# Migración ID: ${up_revision}
# Revisión anterior: ${down_revision | comma,n}
# Fecha: ${create_date}

"""
Descripción de la migración
(comentario para documentar qué cambios se hacen)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# IDs de revisión usados por Alembic para rastrear el histórico
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """
    Aplicar cambios: este código se ejecuta cuando haces:
        alembic upgrade head
    
    Modifica la BD: crea tablas, columnas, índices, etc.
    ${upgrades if upgrades else "pass"}
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """
    Deshacer cambios: este código se ejecuta cuando haces:
        alembic downgrade -1
    
    Revierte la BD al estado anterior (ej: drop tables, undo columns).
    ${downgrades if downgrades else "pass"}
    """
    ${downgrades if downgrades else "pass"}


# ========== CONCEPTOS IMPORTANTES ==========
#
# 1. AUTODETECCIÓN
# Alembic compara Base.metadata (modelos Python) con la BD real
# y genera upgrade/downgrade automáticamente.
#
# 2. REVERSIBILIDAD
# Toda migración debe poder revertirse (downgrade).
# Si no es posible (ej: migración de datos), se hace manual.
#
# 3. IDEMPOTENCIA
# Una migración deve ser segura ejecutarla varias veces.
# Ej: "CREATE TABLE IF NOT EXISTS" en lugar de "CREATE TABLE"
#
# 4. EJEMPLO DE MIGRACIÓN GENERADA
#
# def upgrade() -> None:
#     op.create_table(
#         'tickets',
#         sa.Column('id', sa.Integer(), nullable=False),
#         sa.Column('titulo', sa.String(200), nullable=False),
#         sa.Column('estado', sa.String(20), nullable=False),
#         sa.PrimaryKeyConstraint('id')
#     )
#     op.create_index('ix_tickets_estado', 'tickets', ['estado'])
#
# def downgrade() -> None:
#     op.drop_index('ix_tickets_estado', table_name='tickets')
#     op.drop_table('tickets')
#
# ========== COMANDOS ALEMBIC COMUNES ==========
#
# alembic current
#     → Mostrar versión actual de BD
#
# alembic history
#     → Ver todas las migraciones (pasadas y presentes)
#
# alembic revision --autogenerate -m "Descripción"
#     → Generar migración automática detectando cambios
#
# alembic upgrade head
#     → Aplicar todas las migraciones pendientes
#
# alembic downgrade -1
#     → Deshacer última migración
#
# alembic upgrade abcd123 (ID específico)
#     → Ir a una versión específica
#
# alembic check
#     → Verificar que migraciones son válidas (usado en CI)
