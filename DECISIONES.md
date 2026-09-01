# DECISIONES

Registro de las decisiones técnicas de Deskly. Cada entrada tiene el mismo
formato: **Contexto**, **Uso de LLM**, **Salida del modelo** y **Mi decisión**.
El objetivo es explicar *por qué* se hizo cada cosa, en lenguaje claro.

Sobre el uso de LLM: usé un asistente de código (Kiro) para escribir y diagnosticar
más rápido. Está permitido por el reto. Lo importante es que las decisiones son
mías y puedo defenderlas. Cuando el modelo propuso una cosa y yo pedí cambiarla,
lo digo tal cual. Las frases de verificación ("14 tests pasan", "Redis funciona")
son ejecuciones reales de esta sesión, no suposiciones.

---

### [Decisión] Base de datos: PostgreSQL en lugar de MongoDB

**Contexto:** El reto me deja elegir entre PostgreSQL o MongoDB. Los datos son
tickets con comentarios, con filtros y paginación.

**Uso de LLM:** Le pedí que comparara las dos opciones para este caso.

**Salida del modelo:** Recomendó PostgreSQL porque los datos son relacionales (un
ticket tiene varios comentarios) y encaja bien con filtros y paginación.

**Mi decisión:** Elegí PostgreSQL, por dos razones fáciles:
1. Los datos están relacionados: un ticket tiene comentarios. Con tablas y una
   clave foránea es lo natural, y si borro un ticket sus comentarios se borran
   solos.
2. Evita duplicados en el webhook sin esfuerzo: marco `event_id` como único y la
   base de datos ya impide guardar dos veces el mismo evento.

Descarté MongoDB porque su punto fuerte (esquema flexible) no lo necesito: un
ticket siempre tiene los mismos campos.

---

### [Decisión] Migraciones con Alembic (el modelo dijo que no hacía falta; yo lo pedí)

**Contexto:** Hay que crear las tablas al levantar el backend. Se puede hacer
automáticamente al arrancar, o con Alembic, que es la herramienta estándar de
migraciones.

**Uso de LLM:** Le pregunté si valía la pena usar Alembic o bastaba con crear las
tablas al arrancar.

**Salida del modelo:** Dijo que para un prototipo **no era necesario** Alembic, que
bastaba con crear las tablas al arrancar (más simple). Así lo dejó al principio.

**Mi decisión:** **Le pedí cambiarlo y usar Alembic.** Mi razón: es el estándar en
proyectos reales. En un equipo el esquema cambia con el tiempo, y tener las
migraciones versionadas desde el principio es lo correcto, no un atajo que después
toca rehacer. Con Alembic cada cambio queda registrado y se puede deshacer.
Configuramos Alembic, generamos la primera migración y comprobé que funciona:
crea las tablas y también las revierte sin errores. En Docker se ejecuta antes de
arrancar la app.

---

### [Decisión] IDs numéricos autoincrementales (el modelo usó UUID; yo lo pedí cambiar)

**Contexto:** Cada tabla necesita un identificador. Puede ser un número que crece
solo (1, 2, 3…) o un UUID (un código largo como `550e8400-e29b-...`).

**Uso de LLM:** Le pedí el modelo de datos.

**Salida del modelo:** Al principio usó **UUID** y, para que los tests con SQLite
funcionaran, tuvo que crear un tipo especial de columna que guardaba el UUID de
forma distinta en PostgreSQL y en SQLite. Funcionaba, pero era una pieza extra.

**Mi decisión:** **Le pedí cambiar todo a IDs numéricos autoincrementales, por
simplicidad.** Son más cortos, más fáciles de leer y funcionan igual en PostgreSQL
y SQLite sin ningún tipo especial, que se pudo eliminar. Para un panel interno de
soporte no necesito lo que aporta el UUID. Comprobé que la idempotencia del webhook
**no se ve afectada**, porque depende de la columna `event_id` (única), no del
identificador de la fila. Tras el cambio, los 14 tests siguen pasando.

Lo que asumo: los IDs numéricos son "adivinables" (se puede probar `/tickets/1`,
`/tickets/2`…). Para un prototipo interno es aceptable; si fuera público y quisiera
ocultar esa información, volvería a UUID.

---

### [Decisión] Webhook: primero la firma (401), luego el contenido (422)

**Contexto:** El webhook debe responder 401 si la firma es inválida y 422 si el
contenido está mal. Como una misma petición puede fallar en las dos cosas, el orden
importa.

**Uso de LLM:** Sin LLM. Fue un requisito del enunciado que decidí yo.

**Salida del modelo:** Sin LLM en esta decisión.

**Mi decisión:** Primero compruebo la firma; solo si es válida reviso el contenido.
Es una cuestión de seguridad: a quien no demuestra ser un remitente legítimo no le
doy pistas sobre el formato del mensaje, lo corto con 401. El secreto de la firma
vive en una variable de entorno (`.env`), nunca en el código, y la comparación se
hace de forma segura para no filtrar información.

---

### [Decisión] Tiempo real con Redis (el modelo lo hizo en memoria; yo pedí Redis)

**Contexto:** Cuando se crea, actualiza o comenta un ticket, hay que avisar en el
momento a los agentes conectados por WebSocket. Cada instancia del backend guarda
sus conexiones en su propia memoria, así que con más de una instancia un aviso
generado en una no llegaría a los clientes de otra.

**Uso de LLM:** Le pedí el sistema de avisos en tiempo real.

**Salida del modelo:** Al principio lo implementó **en memoria**: una lista de
conexiones a la que se le manda el aviso, con desconexión limpia (si un cliente
falla, se quita en vez de romper). Comentó que Redis quedaba "fuera de alcance".

**Mi decisión:** **Le pedí cambiarlo para usar Redis.** Mis razones: **escalabilidad**
(permite tener varias instancias del backend a la vez) y porque **es lo habitual en
proyectos reales** de tiempo real. Con Redis, los avisos se publican en un canal y
todas las instancias lo escuchan; cada una reenvía el aviso a sus propios clientes,
así llega a todos. Mantuve la desconexión limpia.

Lo dejé tolerante a fallos: si Redis no está disponible (por ejemplo en los tests o
en local sin Redis), el sistema avisa solo a los clientes de esa instancia y todo
sigue funcionando. Lo verifiqué de verdad: levanté un Redis en Docker y comprobé que
un aviso publicado llega al cliente; y que los 14 tests pasan sin Redis.

---

### [Decisión] Entorno de desarrollo: Python 3.12 con `uv` (mi máquina trae 3.14)

**Contexto:** Mi máquina tiene Python 3.14 por defecto. Al instalar las
dependencias fallaban dos de ellas porque todavía no son compatibles con 3.14.

**Uso de LLM:** Le pedí que diagnosticara el error y propusiera una salida sin tocar
el Python del sistema.

**Salida del modelo:** Explicó que dos librerías no soportan aún 3.14. Vio que la
herramienta `uv` ya estaba instalada y propuso usarla para instalar un Python 3.12
aparte.

**Mi decisión:** No toqué el Python del sistema. Usé `uv` para instalar un Python
3.12 aislado y ahí monté el entorno; con eso instalé todo y ejecuté los tests
(14 pasan). Además 3.12 es la misma versión que usa la imagen de Docker, así que lo
que verifico en local coincide con lo que correrá en el contenedor.

---

### [Decisión] Tests: cómo conecto la app a una base de datos de prueba

**Contexto:** Los tests del webhook necesitan que la app use una base de datos de
prueba (SQLite) en vez de PostgreSQL.

**Uso de LLM:** Le pedí la configuración de los tests (`conftest.py`).

**Salida del modelo:** El primer intento recargaba módulos por dentro para cambiar
la base de datos. Al ejecutarlo **falló** con un error de "tabla ya definida".

**Mi decisión:** Descarté ese primer enfoque (frágil) y usé la forma recomendada de
FastAPI: sustituir la dependencia de la base de datos por una SQLite en memoria solo
para los tests. Reconozco que la primera versión estaba mal; lo detecté al ejecutar
los tests, no leyéndolos. Después del cambio, los 14 tests pasan sin avisos.

---

### [Decisión] Estados y prioridades guardados como texto

**Contexto:** `estado` y `prioridad` solo pueden tomar unos pocos valores fijos. PostgreSQL tiene un tipo especial para esto (`ENUM`).

**Uso de LLM:** Sin LLM; lo decidí al modelar las tablas.

**Salida del modelo:** Sin LLM en esta decisión.

**Mi decisión:** Los guardo como texto y valido los valores en la aplicación (con los enumerados de Python y con Pydantic). El tipo `ENUM` de PostgreSQL es incómodo de cambiar (añadir un estado nuevo es molesto) y no funciona en SQLite, que uso en los tests. La validación real ya la hacen la aplicación y la máquina de estados, así que no la necesito también en la columna.

---

### [Decisión] Configuración por `.env` y archivo `.env.example`

**Contexto:** El secreto que usa el webhook para verificar la firma tenía en el código un valor por defecto (`change-me`). Ese campo ya se leía desde una variable de entorno, pero no había un archivo que dejara claras todas las variables de configuración del proyecto ni cómo rellenarlas.

**Uso de LLM:** Ninguno para tomar la decisión; me pediste centralizar la configuración en `.env` y yo preparé el archivo de ejemplo.

**Salida del modelo:** Sin propuesta del modelo; fue una petición tuya.

**Mi decisión:** A tu petición, dejé claro que la configuración viene de un archivo `.env` y añadí un **`.env.example`** en la raíz con todos los valores: la conexión a la base de datos, el secreto del webhook (como marcador `change-me`, con aviso de cambiarlo), la URL de Redis, los orígenes permitidos (CORS), el interruptor de datos de ejemplo y las URLs del frontend. El `.env` real **no se sube** al repositorio (está ignorado en git); solo se versiona el `.env.example`. Así no hay ningún secreto en el repositorio y cualquiera puede arrancar el proyecto copiando el ejemplo (`cp .env.example .env`) y ajustando los valores.

---

### [Decisión] Frontend sin librería de estado (React Query u otras)

**Contexto:** El frontend tiene que listar tickets, filtrarlos, ver el detalle y actualizarse en vivo. Una opción habitual es añadir una librería de datos como React Query.

**Uso de LLM:** Le pedí el frontend con Next.js 14.

**Salida del modelo:** Propuso resolverlo con las herramientas propias de Next y React (componentes de servidor para la carga inicial y `fetch`), sin añadir librerías extra.

**Mi decisión:** Acepté no meter React Query ni un store global. Para este alcance, los componentes de servidor de Next (para la carga inicial) y `useState`/`useEffect` (para la interacción y el tiempo real) son suficientes. Menos dependencias, menos cosas que explicar y defender. Si la app creciera (mucha caché, sincronización compleja), reconsideraría una librería de datos.

---

### [Decisión] SSR solo en el detalle; dashboard interactivo en el cliente

**Contexto:** El reto pide que el **detalle** `/tickets/[id]` sea renderizado en el servidor (SSR). El dashboard, en cambio, necesita filtro y actualización en vivo.

**Uso de LLM:** Le pedí las dos páginas.

**Salida del modelo:** Planteó el detalle como componente de servidor (SSR) y el dashboard con interacción en el cliente.

**Mi decisión:** El detalle se renderiza en el servidor: la primera carga ya trae el ticket y sus comentarios (mejor para SSR y para enlaces directos). La interacción del detalle (cambiar estado, comentar, tiempo real) va en un componente de cliente aparte. El dashboard lo hice de cliente porque combina filtro, paginación y actualización en vivo, que son inherentemente interactivos. Así cada página usa el enfoque que mejor le encaja.

---

### [Decisión] Reconexión automática del WebSocket

**Contexto:** La conexión de tiempo real puede caerse (red, reinicio del backend). Si no se hace nada, el usuario deja de recibir avisos sin enterarse.

**Uso de LLM:** Le pedí el hook de WebSocket con limpieza correcta.

**Salida del modelo:** Entregó un hook que abre la conexión, la limpia al desmontar y expone el estado de conexión.

**Mi decisión:** Además de la limpieza, añadí **reconexión automática** con una espera creciente (hasta 5 s) cuando la conexión se pierde, y un **indicador visible**
(En vivo / Conectando / Desconectado) para que el usuario sepa el estado. Al recibir un evento, el dashboard recarga la lista y el detalle recarga ese ticket: es lo más simple y siempre muestra datos consistentes con el servidor (preferí esto antes que aplicar cambios parciales en el cliente, que es más frágil).

---

### [Decisión] Usuarios, autenticación e `is_admin` (ampliación del alcance)

**Contexto:** El campo obligatorio `asignado_a` sugiere que un humano atiende el
ticket. El enunciado no pide usuarios ni login, pero decidí que en un producto
real (tipo Jira o Flokzu) "asignado a" es un usuario con credenciales y permisos.

**Uso de LLM:** Le pedí que evaluara el impacto de añadir usuarios y autenticación,
y luego que lo implementara.

**Salida del modelo:** Advirtió que añadir usuarios + login + permisos es un
subsistema completo (toca modelo, todos los endpoints, el frontend y los tests) y
que, al ser alcance extra no pedido, sólo compensa si se puede defender bien. Fue
mi decisión seguir adelante.

**Mi decisión:** Añadí una tabla `users` con **email**, **contraseña hasheada** y un
permiso **`is_admin`** (si puede administrar a otros usuarios). La contraseña se
guarda con **bcrypt** (nunca en claro). El acceso se hace con **JWT**: al iniciar
sesión se entrega un token que luego autoriza las peticiones. Con esto:

- Los endpoints de tickets requieren estar autenticado.
- El CRUD de usuarios (`/api/users`) solo lo puede usar un `is_admin`.
- `asignado_a` pasó a ser una **referencia al id de un usuario** (antes era texto),
  y el autor de un comentario es el usuario autenticado.
- El **webhook sigue usando su firma HMAC** (no JWT), porque es una integración
  máquina-a-máquina, no una persona.
- El **usuario admin inicial se crea en el seed**, para poder entrar la primera vez.

Asumo el trade-off: es bastante más trabajo y amplía el alcance. Lo prioricé
**después** de tener el resto funcionando, para no arriesgar el arranque.

---

### [Decisión] Detalle técnico: bcrypt fijado a 4.0.1 por compatibilidad con passlib

**Contexto:** Al hashear contraseñas con `passlib`, los tests fallaban con errores
extraños de bcrypt ("password cannot be longer than 72 bytes" y un fallo al leer
la versión de bcrypt).

**Uso de LLM:** Le pedí que diagnosticara el fallo.

**Salida del modelo:** Identificó que las versiones recientes de la librería
`bcrypt` (≥ 4.1) rompen la compatibilidad con `passlib 1.7.4`, que es la última
versión estable de passlib.

**Mi decisión:** Fijé **`bcrypt==4.0.1`** en las dependencias, que es la versión
compatible con passlib 1.7.4. Es un ajuste pequeño pero real; lo detecté al
ejecutar los tests, y tras fijarlo la suite pasa completa (21 tests). Lo dejo
documentado para que quien mantenga el proyecto sepa por qué esa versión está
clavada.

---

### [Decisión] Frontend: token en cookie para que el SSR también esté autenticado

**Contexto:** Con la API protegida por JWT, el frontend necesita enviar el token
en cada petición. El detalle `/tickets/[id]` se renderiza en el servidor (SSR),
así que el servidor también necesita el token para pedir el ticket.

**Uso de LLM:** Le pedí el login y la protección de rutas en el frontend.

**Salida del modelo:** La opción más simple era guardar el token en
`localStorage`, pero eso solo existe en el navegador: el servidor no podría leerlo
durante el SSR y la página de detalle fallaría con 401.

**Mi decisión:** Guardo el token en una **cookie** (`deskly_token`) en lugar de
`localStorage`. Así el navegador lo envía en sus peticiones y, en el SSR, el
servidor lo lee de la cookie (`next/headers`) y hace la petición autenticada. Un
contexto de autenticación (`AuthProvider`) mantiene el usuario actual, y un guard
(`RequireAuth`) redirige a `/login` si no hay sesión y bloquea `/users` a los no
administradores. Es una protección de conveniencia en el cliente; la seguridad
real la impone el backend, que valida el JWT en cada endpoint.

---

### [Decisión] Transición inválida: corregir un 500 a 409 (bug encontrado en auditoría)

**Contexto:** El enunciado exige que una transición de estado inválida devuelva un
error claro, **no un 500 genérico**. Los tests unitarios de la máquina de estados
pasaban, pero al probar el flujo completo en Docker la petición HTTP devolvía
**500**.

**Uso de LLM:** Le pedí que diagnosticara por qué el endpoint devolvía 500 en vez
de 409.

**Salida del modelo:** Encontró la causa raíz: el estado del ticket se guarda como
**texto** en la base de datos, así que un ticket leído de la DB trae `estado` como
un `str`, no como el enum `Estado`. Al construir el error, el código hacía
`.value` sobre ese texto y lanzaba `AttributeError` **antes** de que el manejador
pudiera convertirlo en 409, produciendo un 500.

**Mi decisión:** Acepté el diagnóstico y lo corregí en la raíz: la máquina de
estados ahora **normaliza** las entradas a `Estado`, así funciona tanto si recibe
el enum como el texto de la DB. Añadí **tests de regresión** para que no vuelva a
pasar: uno a nivel de función (con entradas de texto) y otro a nivel HTTP que
comprueba que la transición inválida devuelve **409**. El fallo lo detecté yo al
auditar el arranque real (los tests unitarios no lo cubrían porque usaban el enum
directamente); lo dejo documentado con honestidad porque muestra por qué conviene
probar el camino completo, no solo las funciones aisladas.

---

### [Decisión] Pipeline de CI (GitHub Actions) con lint y tests

**Contexto:** Es un bonus del enunciado. Quería una red de seguridad que revise el
código en cada cambio.

**Uso de LLM:** Le pedí un workflow con lint y tests para backend y frontend.

**Salida del modelo:** Propuso dos trabajos: backend (lint + tests con Python) y
frontend (lint + build con Node).

**Mi decisión:** Lo acepté y lo dejé afinado para que salga en verde de verdad,
verificándolo localmente antes de subirlo. En el backend uso **ruff** para el lint
y **pytest** para los tests; configuré ruff con reglas de problemas reales en vez
de activar todas las reglas opinionadas (por ejemplo, permito los `except`
genéricos del gestor de WebSocket, que son intencionales para la desconexión
limpia). En el frontend uso **ESLint** (`next lint`) y `next build`, que además
comprueba los tipos. Verifiqué los cuatro pasos en local (23 tests, lint limpio en
ambos, build correcto). Nota honesta: el workflow no se ha ejecutado aún en
GitHub Actions real porque no hay repositorio remoto en este entorno, pero cada
paso usa los mismos comandos que probé.

---

### [Decisión] Asignación de ticket: endpoint de "opciones" y autocompletado propio

**Contexto:** En el detalle del ticket quería un selector con búsqueda (estilo
Autocomplete de MUI) para cambiar el usuario asignado, con "Asignarme a mí" como
primera opción y mostrando los primeros 5 usuarios. Problema: el CRUD de usuarios
(`GET /api/users`) es **solo para administradores**, así que un agente normal no
podría llenar ese selector.

**Uso de LLM:** Le pedí la funcionalidad y que resolviera cómo obtener la lista de
usuarios para el selector sin abrir el CRUD de administración.

**Salida del modelo:** Propuso dos caminos: (a) crear un endpoint ligero de
"opciones" accesible a cualquier usuario autenticado que devuelva solo lo
necesario, o (b) relajar el `GET /api/users` para todos.

**Mi decisión:** Elegí la opción (a): un endpoint nuevo
`GET /api/users/options?q=&limit=5` disponible para **cualquier usuario
autenticado**, que devuelve **solo `id` y `email`** (sin exponer `is_admin` ni
otros datos). El resto de la administración de usuarios sigue siendo solo-admin.
La búsqueda es del lado del servidor (filtra por email, máximo 5). Sobre la UI:
descarté instalar MUI (era solo una referencia) y construí un componente propio
con Tailwind (`UserAutocomplete`), coherente con el resto de la interfaz y sin
añadir dependencias. La primera opción es "Asignarme a mí" (usa el id del usuario
en sesión); al elegir, hace `PATCH /api/tickets/{id}` con `asignado_a_id` y
refresca sin recargar. Detalle técnico: registré el endpoint de opciones **antes**
que el CRUD de usuarios para que la ruta `/api/users/options` no choque con
`/api/users/{id}`. Seguí SDD: escribí requisitos y diseño antes de implementar.

---

### [Decisión] Nombre y apellidos en usuarios; idioma del dominio en español

**Contexto:** Los usuarios solo tenían email. Un ticket "asignado a" una persona
debería mostrar su nombre, no solo el correo. Al añadir los campos noté además
"spanglish" en el código: mezclaba nombres en español (los del enunciado:
`titulo`, `estado`, `asignado_a`…) con inglés que yo había introducido
(`full_name`).

**Uso de LLM:** Le pedí añadir `nombre` y `apellidos` (obligatorios), un
"nombre completo" y que la búsqueda de usuarios encontrara por email y por
nombre/apellidos. También le pedí resolver la inconsistencia de idioma.

**Salida del modelo:** Implementó los campos y propuso tres criterios de idioma:
(A) todo el dominio en inglés (rompe el contrato del enunciado), (B) dominio en
español como pide el enunciado y tecnicismos en inglés, (C) inglés solo en los
campos nuevos.

**Mi decisión:** Elegí **(B)**. El enunciado fija los campos del ticket en español
(`titulo`, `descripcion`, `estado`, etc.), así que mantengo el **dominio en
español** por coherencia con ese contrato y renombré lo que yo había puesto en
inglés: `full_name → nombre_completo`. Dejo en inglés solo los **tecnicismos** que
no son campos de negocio (`email`, `is_admin`, `hashed_password`), que es una
convención habitual. `nombre` y `apellidos` son obligatorios; `nombre_completo`
es una propiedad calculada (`"{nombre} {apellidos}"`). La búsqueda de
`/api/users/options` filtra por email, nombre, apellidos y por la concatenación
"nombre apellidos" (para que "victor hernandez" encuentre a Victor Hernandez), y
el seed incluye a ese usuario de ejemplo. Al ser cambios de esquema en un
prototipo, actualicé la **migración inicial** (en vez de una incremental), lo que
obliga a recrear la base de datos en desarrollo.

### [Decisión] Reinicio de migraciones y seed con 10 usuarios

**Contexto:** En desarrollo la base de datos se recrea entera, así que no tiene
sentido arrastrar historial de migraciones incrementales. Se pidió reiniciar las
migraciones y ampliar el seed a 10 usuarios.

**Uso de LLM:** Le pedí consolidar el historial de Alembic en una única migración
inicial limpia y actualizar el seed para crear 10 usuarios de ejemplo.

**Salida del modelo:** Eliminó la migración previa (`347a30492066`) y creó una
única migración inicial `0001_initial_schema` con `down_revision = None` (mismo
esquema: users, tickets, comments, webhook_events e índices). Reescribió el seed
con una lista `SAMPLE_USERS` idempotente (lookup por email antes de insertar).

**Mi decisión:** Acepté el reinicio a una sola migración inicial: en un prototipo
donde la DB se recrea, un historial plano es más simple de mantener. El seed
siembra 10 usuarios en total: el admin de `settings` (`admin@deskly.com`) más 9
entradas en `SAMPLE_USERS` (incluye `agente@deskly.com` y `victor@deskly.com` que
ya existían, más otros 7). Uno de los nuevos (`camila@deskly.com`) es admin para
tener más de un administrador de prueba. Los tickets de ejemplo se siguen
asignando al primer agente (`agente@deskly.com`). El seed es idempotente, así que
reiniciar el proyecto y volver a sembrar no duplica usuarios.

### [Decisión] 100 tickets de ejemplo en el seed

**Contexto:** Con solo 3 tickets no se podían probar bien la paginación ni los
filtros por estado/prioridad. Se pidió sembrar 100 tickets variados.

**Uso de LLM:** Le pedí generar 100 tickets con distintos estados y prioridades.

**Salida del modelo:** Genera 100 tickets ciclando por `list(Estado)` y
`list(Prioridad)` (así aparecen las 4 combinaciones de forma pareja), con
asignaciones repartidas entre los 10 usuarios y "sin asignar", usando un
`random.Random(42)` para que sea determinista.

**Mi decisión:** Lo acepté. Los estados se fijan directamente en la creación (no
vía la máquina de estados) para tener tickets ya en `resuelto`/`cerrado` con los
que probar filtros y badges. Mantengo la guarda de idempotencia: solo siembra si
la tabla de tickets está vacía, por lo que hay que recrear la BD para regenerar.

### [Decisión] Colores de prioridad por severidad

**Contexto:** La prioridad se distinguía poco visualmente. Se pidió color por
prioridad.

**Uso de LLM:** Le pedí rojo/naranja/amarillo y, al añadir `urgente`, colores
coherentes para los cuatro niveles.

**Salida del modelo:** Propuso una escala de severidad creciente:
baja=verde, media=amarillo, alta=naranja, urgente=rojo.

**Mi decisión:** Elegí la escala verde→amarillo→naranja→rojo. Con las cuatro
prioridades del enum, cuatro colores distintos son más legibles que reutilizar
rojo para alta y urgente. El cambio vive en un único sitio (`PrioridadBadge`), así
que aplica igual en el listado y en el detalle.

### [Decisión] Asignación inline y filtros en el listado

**Contexto:** Para asignar un ticket había que entrar a su detalle. Se pidió
poder asignar desde la tabla y filtrar también por prioridad, además de mostrar
la antigüedad del ticket.

**Uso de LLM:** Le pedí reutilizar el autocompletado de usuarios en la tabla, un
filtro por prioridad y un "creado hace" en lenguaje natural.

**Salida del modelo:** Reutilizó `UserAutocomplete` en cada fila (mismo endpoint
`PATCH /api/tickets/{id}`), añadió el `select` de prioridad cableado al query
param que ya soportaba el backend, y una utilidad `tiempoRelativo` en español.

**Mi decisión:** Lo acepté. Reutilizar el mismo componente y endpoint evita
duplicar lógica. Hice el ancho de `UserAutocomplete` configurable (`className`)
para que encaje tanto en la tabla como en el detalle. El tiempo relativo se
calcula en cliente (`lib/time.ts`) con escalas minuto→año y muestra la fecha
exacta en el `title`. No añadí endpoints nuevos: el backend ya filtraba por
prioridad y aceptaba `PATCH` parcial.

### [Decisión] Detalle de ticket editable (estilo Jira) y reordenado

**Contexto:** El detalle mostraba título y descripción como texto fijo, y el
orden ponía el título arriba y los controles debajo. Se pidió edición inline y
reorganizar para que estado, prioridad, transición y asignación queden juntos y
arriba.

**Uso de LLM:** Le pedí convertir título en `input` y descripción en `textarea`
con guardado, y reordenar las secciones.

**Salida del modelo:** Movió el bloque de controles encima del título; agrupó
estado, prioridad, "Cambiar estado" y "Asignado a" como columnas de una misma
tarjeta; e hizo el título/descripción editables con un botón "Guardar" que solo
se habilita cuando hay cambios (`dirty`) y un "Cancelar" que revierte.

**Mi decisión:** Lo acepté. El `PATCH /api/tickets/{id}` ya aceptaba `titulo` y
`descripcion` en `TicketUpdate`, así que no toqué el backend: solo amplié el tipo
del cliente. Para que el título/descripción reaccionen a cambios en vivo, el
render pasó de SSR (en `page.tsx`) al componente cliente, que ya sincroniza el
ticket por WebSocket. Límite conocido: un evento entrante puede sobrescribir
ediciones locales sin guardar; aceptable en un prototipo.
