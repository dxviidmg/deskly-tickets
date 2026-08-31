# DECISIONES

Bitácora de decisiones técnicas de Deskly. Cada entrada sigue el formato pedido
en el enunciado: contexto, uso de LLM (qué pedí y por qué), salida del modelo, y
mi decisión (qué acepté, modifiqué o descarté y con qué criterio).

Nota sobre el uso de LLM en este proyecto: usé un asistente de código (Kiro,
sobre un modelo tipo Claude) para acelerar la escritura y el diagnóstico. La
política del reto permite su uso sin límite; lo relevante es que pueda defender
cada línea. Donde acepté algo sin comprenderlo del todo, o donde hubo un ida y
vuelta (p. ej. Alembic), lo digo explícitamente. Las afirmaciones de verificación
("14 tests pasan", "upgrade/downgrade de Alembic funcionan") corresponden a
ejecuciones reales realizadas en esta sesión, no a suposiciones.

---

### [Decisión] Base de datos: PostgreSQL en lugar de MongoDB

**Contexto:** El enunciado deja la base de datos a mi elección (PostgreSQL o
MongoDB) y pide justificar la decisión. El dominio son tickets con comentarios,
filtros, paginación y un webhook idempotente.

**Uso de LLM:** Le pedí al modelo que contrastara ambas opciones para este
dominio concreto, enfocándose en integridad referencial, idempotencia del
webhook y consultas con filtro/paginación. Quería un contraste, no una
recomendación ciega.

**Salida del modelo:** Propuso PostgreSQL argumentando que el modelo es
relacional (ticket 1—N comentarios), que la unicidad de `event_id` para
idempotencia se resuelve con una constraint `UNIQUE`, y que los filtros del
listado se benefician de índices B-tree. Señaló que MongoDB aportaría esquema
flexible que aquí no se necesita.

**Mi decisión:** Acepté PostgreSQL. El criterio decisivo para mí fue la
**idempotencia del webhook**: con una constraint `UNIQUE(event_id)` delego la
garantía a la base de datos en vez de implementar verificaciones manuales
propensas a condiciones de carrera. La alternativa (MongoDB) la descarté porque
su flexibilidad de esquema no aporta valor a un modelo estable y complicaría la
relación con comentarios. Puedo defender el trade-off: si el requisito fuera
documentos heterogéneos o escritura masiva sin relaciones, reconsideraría.

---

### [Decisión] Migraciones de esquema con Alembic

**Contexto:** Necesito crear las tablas del backend de forma reproducible al
levantar el sistema. Barajé dos enfoques: `Base.metadata.create_all` en el
arranque (simple) o Alembic (migraciones versionadas, estándar de producción).

**Uso de LLM:** Le pedí al modelo que contrastara ambos para un prototipo y, tras
decidir por Alembic, que configurara el entorno async de Alembic (`env.py` que
lee la URL desde settings y usa `Base.metadata` como target) y autogenerara la
migración inicial.

**Salida del modelo:** Indicó que `create_all` es más simple pero no gestiona la
evolución del esquema, mientras que Alembic aporta versionado y `upgrade`/
`downgrade`. Generó el `env.py` async, la plantilla de scripts y, vía
`alembic revision --autogenerate`, una migración inicial que detectó las tres
tablas y los índices.

**Mi decisión:** Este punto tuvo un ida y vuelta real que documento con
honestidad: primero opté por `create_all` por simplicidad, luego reconsideré y
**decidí usar Alembic** como mecanismo definitivo. Criterios: (1) es el estándar
que esperaría un equipo que "usa Docker, FastAPI y Next.js"; (2) deja el esquema
versionado y con `downgrade`; (3) separa la creación del esquema del arranque de
la app. Ajusté la migración autogenerada a mano en un punto: añadí
`import app.types` porque el autogenerador referencia `app.types.GUID()` sin
importarlo, y sin ese import la migración falla. Verifiqué el flujo completo
contra SQLite: `alembic upgrade head` crea el esquema, `alembic current` reporta
la cabeza, y `alembic downgrade base` revierte sin errores. En Docker, el
contenedor ejecuta `alembic upgrade head` antes de arrancar uvicorn. El
`create_all` quedó solo en la suite de tests (ver entrada sobre el wiring de
tests), no en el arranque de producción.

---

### [Decisión] Tipo `GUID` portable en lugar de `UUID` nativo de PostgreSQL

**Contexto:** Los modelos usan UUID como PK. El tipo `UUID` de
`sqlalchemy.dialects.postgresql` solo funciona en PostgreSQL, pero quiero correr
los tests unitarios sin levantar PostgreSQL (más rápido y sin dependencias).

**Uso de LLM:** Le pedí al modelo un `TypeDecorator` que usara UUID nativo en
PostgreSQL y un equivalente en SQLite, para que el mismo esquema corriera en la
suite de tests con SQLite en memoria/archivo.

**Salida del modelo:** Propuso un `TypeDecorator` sobre `CHAR(36)` que delega a
`UUID(as_uuid=True)` cuando el dialecto es `postgresql` y a `CHAR(36)` en otros
casos, con conversión de ida y vuelta a `uuid.UUID`.

**Mi decisión:** Acepté el patrón, que conozco y puedo defender: es el enfoque
canónico documentado por SQLAlchemy para tipos backend-agnósticos. El criterio
fue **poder testear sin PostgreSQL**. Verifiqué que la lógica de `bind`/`result`
convierte correctamente entre `str` y `uuid.UUID`. Trade-off: en SQLite el UUID
se almacena como texto (CHAR(36)), lo cual es aceptable porque SQLite solo se usa
en la suite de tests (en memoria con `StaticPool`). La verificación real lo
confirma: los 14 tests corren sobre este tipo sin PostgreSQL.

---

### [Decisión] Orden de verificación en el webhook: firma (401) antes que forma (422)

**Contexto:** El webhook debe devolver 401 si la firma HMAC es inválida y 422 si
el payload está malformado. El orden de las comprobaciones cambia el código de
respuesta ante una petición que falla en ambas.

**Uso de LLM:** Ninguno directo en esta decisión; fue un requisito explícito del
enunciado que interpreté yo.

**Salida del modelo:** Sin LLM.

**Mi decisión:** Verifico **primero la firma sobre el cuerpo crudo** y solo si es
válida valido el payload con Pydantic. Criterio de seguridad: no se debe dar
información sobre la forma del payload a un cliente que ni siquiera prueba ser
legítimo. Por eso un payload malformado con firma inválida devuelve 401, no 422.
Uso `hmac.compare_digest` para comparar en tiempo constante y evitar ataques de
temporización.

---

### [Decisión] WebSocket con `ConnectionManager` en memoria (sin Redis pub/sub)

**Contexto:** Hay que emitir eventos en tiempo real a los agentes conectados.
Una solución escalable a múltiples procesos usaría un bus externo (Redis).

**Uso de LLM:** Le pedí al modelo un `ConnectionManager` que registrara
conexiones y difundiera eventos, con desconexión limpia (sin errores silenciosos
cuando un cliente cae).

**Salida del modelo:** Propuso una clase con un conjunto de conexiones protegido
por un lock asíncrono, un método `broadcast` que serializa el evento y elimina
las conexiones que fallan al enviar.

**Mi decisión:** Acepté la estructura y añadí el criterio de "desconexión limpia"
del enunciado: si `send_json` falla, marco esa conexión para eliminarla en lugar
de propagar el error. Descarté Redis pub/sub **conscientemente**: el enunciado no
pide escalado horizontal y añadiría un servicio más al `docker-compose`. Lo
documento como limitación conocida: el manager vive en la memoria de un proceso;
con múltiples workers habría que externalizar el estado.

---

### [Decisión] Python 3.12 gestionado con `uv` (la máquina tiene 3.14 por defecto)

**Contexto:** Mi máquina tiene **Python 3.14 por defecto**. Al intentar instalar
las dependencias en local, `pydantic-core` (PyO3 ≤ 3.13) y `asyncpg` no tienen
wheels ni compilan para 3.14 (además faltaban cabeceras `Python.h`). No podía
crear el entorno ni correr los tests con el intérprete del sistema.

**Uso de LLM:** Le pedí al modelo que diagnosticara el error de compilación y que
propusiera una forma de obtener un intérprete compatible sin modificar el sistema.

**Salida del modelo:** Diagnosticó que PyO3 0.22 no soporta 3.14 (rompe
`pydantic-core`) y que faltaban cabeceras para compilar `asyncpg`. Detectó que
`uv` ya estaba instalado y propuso usarlo para instalar un Python 3.12 gestionado
y crear el venv con él.

**Mi decisión:** No degradé ni parcheé el Python del sistema. Usé
`uv python install 3.12` + `uv venv --python 3.12` para obtener un intérprete
3.12 aislado y ahí instalé las dependencias (todas con wheels precompiladas) y
**ejecuté la suite: 14 tests pasan** (máquina de estados válida/inválida y
webhook con firma válida/inválida, payload malformado e idempotencia). Criterio:
3.12 es además la versión de la imagen base del contenedor (`python:3.12-slim`),
así que el entorno local de verificación coincide con el de Docker. Fijo las
dependencias pensando en 3.12.

---

### [Decisión] Wiring de tests: `dependency_overrides` tras descartar `importlib.reload`

**Contexto:** Los tests del webhook necesitan que la app FastAPI use una base de
datos de test (SQLite) en lugar de PostgreSQL. Mi primer intento reconfiguraba el
módulo de DB recargándolo con `importlib.reload`.

**Uso de LLM:** Le pedí al modelo un `conftest.py` que apuntara la app a SQLite
para los tests. La primera propuesta usaba `importlib.reload` de los módulos de
DB y modelos.

**Salida del modelo:** Primero entregó el enfoque con `importlib.reload`. Al
ejecutarlo falló con `Table 'tickets' is already defined for this MetaData
instance`, porque recargar `models` redefine las tablas sobre el mismo
`Base.metadata`.

**Mi decisión:** Descarté el enfoque de recarga (frágil y con efectos colaterales
sobre el metadata global) y lo reemplacé por el patrón idiomático de FastAPI:
`app.dependency_overrides[get_session]` apuntando a un `AsyncSession` sobre un
engine SQLite en memoria con `StaticPool`, y `Base.metadata.create_all` una sola
vez por test. Reconozco abiertamente que la primera versión estaba mal; la detecté
al ejecutar la suite (no por inspección). Tras el cambio: **14 tests pasan sin
warnings**. Aprovecho `StaticPool` para que la única conexión en memoria persista
durante todo el test.

---

### [Decisión] Enums de dominio como `String(20)` en lugar del tipo `ENUM` nativo

**Contexto:** `estado` y `prioridad` son conjuntos cerrados de valores. PostgreSQL
ofrece un tipo `ENUM` nativo; SQLAlchemy también puede mapear `Enum` de Python.

**Uso de LLM:** Sin LLM en esta decisión concreta; la tomé al modelar las tablas.

**Salida del modelo:** Sin LLM.

**Mi decisión:** Almaceno los enums como `String(20)` y valido los valores en la
capa de aplicación con los `Enum` de Python (`app/enums.py`) y con Pydantic. El
criterio: el tipo `ENUM` nativo de PostgreSQL es incómodo de evolucionar (añadir
un estado exige `ALTER TYPE ... ADD VALUE`, que tiene restricciones dentro de
transacciones) y no es portable a SQLite, que uso en los tests. La validación real
la garantizan Pydantic (entrada) y la máquina de estados (transiciones), no la
columna. Trade-off aceptado: la base de datos por sí sola no impide un valor
fuera del conjunto; confío esa garantía a la capa de aplicación, que además ya
la necesita para la lógica de transiciones.