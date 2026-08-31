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
filtros y paginación.

**Uso de LLM:** Le pedí al modelo que comparara ambas opciones para este caso
concreto. Quería una comparación, no una recomendación a ciegas.

**Salida del modelo:** Propuso PostgreSQL porque los datos son relacionales (un
ticket tiene muchos comentarios) y porque encaja bien con filtros y paginación.
Señaló que la flexibilidad de MongoDB no aporta aquí.

**Mi decisión:** Elegí PostgreSQL por dos razones simples:

1. **Los datos son relacionales.** Un ticket tiene comentarios asociados;
   modelarlo como tablas con una clave foránea es lo natural y me da integridad
   (si borro un ticket, sus comentarios se borran solos).
2. **Evita duplicados en el webhook de forma sencilla.** Marco la columna
   `event_id` como única (`UNIQUE`); así la propia base de datos impide guardar
   dos veces el mismo evento, sin código extra.

Descarté MongoDB porque su ventaja (esquema flexible) no la necesito: el modelo
de un ticket es estable. Si el requisito fuera guardar documentos muy variables
o escribir a gran escala sin relaciones, reconsideraría.

---

### [Decisión] Migraciones de esquema con Alembic

**Contexto:** Necesito crear las tablas del backend al levantar el sistema. Hay
dos caminos: crearlas automáticamente al arrancar (`create_all`) o usar Alembic,
la herramienta de migraciones estándar.

**Uso de LLM:** Le pregunté al modelo si valía la pena añadir Alembic para este
proyecto o si bastaba con crear las tablas al arrancar.

**Salida del modelo:** El modelo dijo que **para un prototipo Alembic no era
necesario**: bastaba con `create_all`, que es más simple. Señaló que Alembic
aporta versionado del esquema y poder deshacer cambios (`downgrade`), pero lo
presentó como algo opcional aquí.

**Mi decisión:** **Pedí usar Alembic**, en contra de la sugerencia del modelo. El
motivo es simple: **es el estándar en proyectos reales**. En un equipo, el
esquema evoluciona y hay que aplicar cambios de forma controlada y repetible;
empezar ya con migraciones versionadas es lo que haría en producción, no un
atajo que luego habría que rehacer. Beneficios concretos que valoro: cada cambio
de esquema queda registrado, se puede revertir, y la creación de tablas no
depende del arranque de la app.

Pedí entonces al modelo que configurara Alembic en modo async (un `env.py` que
lee la URL de la base de datos desde la configuración) y que autogenerara la
primera migración a partir de los modelos. Revisé el resultado y verifiqué el
flujo completo contra SQLite: `alembic upgrade head` crea el esquema,
`alembic current` muestra la versión, y `alembic downgrade base` lo revierte sin
errores. La migración se regeneró al cambiar las claves a enteros
autoincrementales (ver la entrada de IDs). En Docker se ejecutará
`alembic upgrade head` antes de arrancar la app.

---

### [Decisión] IDs autoincrementales (enteros) en lugar de UUID

**Contexto:** Cada tabla necesita una clave primaria (el identificador de cada
fila). Las dos opciones habituales son un número que crece solo (1, 2, 3…,
"autoincremental") o un UUID (un identificador largo tipo
`550e8400-e29b-41d4-...`).

**Uso de LLM:** Al principio el modelo propuso usar UUID y, para poder correr los
tests con SQLite, creó un tipo especial (`GUID`) que guardaba el UUID de forma
nativa en PostgreSQL y como texto en SQLite.

**Salida del modelo:** Entregó ese tipo `GUID` portable y lo usó en todas las
claves. Funcionaba, pero añadía una pieza extra al proyecto solo para que el
mismo identificador encajara en dos bases de datos distintas.

**Mi decisión:** Pedí cambiar todo a **IDs autoincrementales por simplicidad**.
Razones: son más cortos y legibles, funcionan igual en PostgreSQL y en SQLite sin
ningún tipo especial, y para un panel interno de soporte no necesito las ventajas
del UUID. Con esto **eliminé el tipo `GUID`** y su complejidad. Verifiqué que la
idempotencia del webhook **no se ve afectada**: no depende de la clave primaria,
sino de la columna `event_id` marcada como única, que se mantiene igual. Tras el
cambio regeneré la migración de Alembic (ahora las claves son enteros) y **los 14
tests siguen pasando**, incluido el de idempotencia.

Trade-off que asumo conscientemente: los IDs autoincrementales son "adivinables"
(alguien puede probar `/tickets/1`, `/tickets/2`…). Para este prototipo interno
es aceptable; si el sistema fuera público y hubiera que ocultar cuántos tickets
existen o evitar accesos por id, volvería a considerar UUID.

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