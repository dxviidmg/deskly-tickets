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

**Actualización (reaparición en runtime):** El problema volvió a aparecer al
levantar el stack con Docker: el login devolvía **500** con el mismo
`ValueError: password cannot be longer than 72 bytes`. La causa fue que el pin
estaba en un comentario/nota pero **no en una línea efectiva** de
`requirements.txt`, así que `pip` instaló `bcrypt 5.0.0` (la última), de nuevo
incompatible con passlib 1.7.4. La solución fue añadir la línea real
`bcrypt==4.0.1` a `requirements.txt` (además de `passlib[bcrypt]==1.7.4`) y
reconstruir la imagen. Confirmado: `pip show bcrypt` reporta `4.0.1` y el login
responde 200 con `access_token`. Aprendizaje: un pin transitivo hay que fijarlo
como dependencia directa explícita, no confiar en el extra `passlib[bcrypt]`.

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

### [Decisión] Estado reabierto en la máquina de estados

**Contexto:** Se pidió agregar un estado "reabierto" como alternativa desde
"resuelto", permitiendo volver a trabajar en un ticket cerrado si se descubre un
problema.

**Uso de LLM:** Le pedí implementar el estado reabierto en la máquina de estados
y en el frontend.

**Salida del modelo:** Agregó `reabierto` al enum `Estado`, actualizó
`TRANSICIONES_VALIDAS` con `resuelto → reabierto` y `reabierto → en_progreso`,
y actualizó etiquetas/colores en frontend.

**Mi decisión:** Lo acepté. La lógica es clara: un ticket resuelto puede
reabrirse si se encuentra un problema, y desde reabierto vuelve a estar en
progreso. Color naranja para diferenciarlo visualmente de resuelto (verde).

### [Decisión] Modal de transición con comentario (estilo Jira)

**Contexto:** Los cambios de estado eran instantáneos sin contexto. Se pidió un
modal que pida un comentario explicativo antes de aplicar la transición.

**Uso de LLM:** Le pedí implementar un modal que capture comentarios opcionales y
los agregue automáticamente con contexto del cambio.

**Salida del modelo:** Modal con transición visual (estado anterior → nuevo),
textarea para comentario opcional, botones Confirmar/Cancelar. Al confirmar,
aplica transición y agrega comentario con contexto del cambio (ej.
"Estado: Abierto → En progreso\n<usuario comment>").

**Mi decisión:** Acepté. Comentarios opcionales (no obligatorios) para no
bloquear, pero con contexto automático del cambio para trazabilidad. Las dos
llamadas (transición + comentario) son independientes; una falla no bloquea la
otra (límite conocido de idempotencia, aceptable en prototipo).

### [Decisión] Manejo de sesión caducada (401 Unauthorized)

**Contexto:** Cuando un token expiraba, los errores eran genéricos. Se pidió
redirigir a login con un mensaje claro "Sesión caducada".

**Uso de LLM:** Le pedí implementar detección de 401 y redirección con mensaje.

**Salida del modelo:** `AuthProvider` detecta 401 en `api.me()`, marca
`sessionExpired=true`. `RequireAuth` redirige a `/login?reason=session_expired`.
Login muestra el mensaje específico.

**Mi decisión:** Lo acepté. Diferencia clara entre "credenciales inválidas" (fallo
de login) y "sesión caducada" (token expirado durante la sesión). Mejora UX.

### [Decisión] Filtro por usuario asignado en el listado

**Contexto:** El listado tenía filtros por estado/prioridad pero no por usuario
asignado. Se pidió filtrar por asignado.

**Uso de LLM:** Le pedí agregar el filtro al backend y un select dinámico en
frontend.

**Salida del modelo:** Backend: parámetro `asignado_a_id` en GET /api/tickets.
Frontend: carga lista de usuarios al montar, renderiza select con opciones
"Todos"/"Sin asignar"/[usuarios]. Muestra nombre_completo + email.

**Mi decisión:** Acepté. Select en lugar de autocomplete (como estado/prioridad)
para consistencia UI. Limit=50 (máximo del backend, no 100). Carga una sola vez
al montar la página.

### [Decisión] Registro de auditoría de estado (state_log) vía listeners de SQLAlchemy

**Contexto:** No existía trazabilidad histórica de los cambios de estado y de
asignación de un ticket. Se pidió un registro de auditoría (audit trail) que
quedara asociado a cada ticket y se mostrara en su detalle.

**Uso de LLM:** Le pedí crear una tabla de auditoría y registrar automáticamente
los cambios de `estado` y `asignado_a_id`.

**Salida del modelo:** Tabla `state_log` (migración `0002_add_state_log`) con
`ticket_id` (FK CASCADE), `mensaje`, `usuario_id` (FK SET NULL) e índices en
`ticket_id` y `creado_en`. Modelo `StateLog` con relación `delete-orphan` desde
`Ticket`, schema `StateLogOut`, y carga vía `selectinload` en el detalle. El
registro se dispara con listeners `after_insert`/`after_update` sobre `Ticket`,
usando `get_history` para detectar los cambios. Ademas generó un `logs.py` con
helpers `log_estado_change`/`log_assignment`.

**Mi decisión:** Acepté la tabla y los listeners, pero descarté `logs.py`: era
código muerto (nadie lo importaba) que duplicaba el mecanismo de los listeners;
tener dos caminos para lo mismo confunde. Los listeners son transparentes para
los routers. Límite conocido: el `usuario_id` del cambio de estado queda en
`None` porque el listener no tiene acceso al usuario autenticado del request;
para el prototipo es aceptable, atribuirlo requeriría pasar el actor al listener.
Detecté también que el LLM reescribió `events.py` eliminando las constantes de
eventos WebSocket (`TICKET_CREATED/UPDATED/COMMENTED`) que aún importan los
routers; las restauré en el mismo módulo para no romper el arranque de la API.

### [Decisión] Modal de historial de cambios por ticket

**Contexto:** La tabla `state_log` ya se exponía en `GET /api/tickets/{id}`, pero
no había forma de verla en el frontend. Se pidió un modal que muestre el historial
por ticket vía API.

**Uso de LLM:** Le pedí implementar un modal en el detalle del ticket que liste el
`state_log` que devuelve la API.

**Salida del modelo:** Tipo `StateLog` en `types.ts` y campo `state_log` en
`TicketDetail`. Botón "Historial (N)" junto al indicador de conexión que abre un
modal con la lista de logs (mensaje + tiempo relativo), ordenados como los
devuelve el backend (más recientes primero). Reutiliza `tiempoRelativo` de
`lib/time.ts` y el patrón visual del modal de transición.

**Mi decisión:** Acepté. El modal no hace un fetch propio: consume el `state_log`
que ya viene en el `TicketDetail` cargado (misma API que alimenta el detalle), y
se refresca junto con el ticket tras cada transición/asignación/evento WebSocket.
Evita una llamada extra y mantiene la consistencia con el estado ya cargado.
Actualicé la spec (`requirements.md`, criterio 5) para reflejar el modal en lugar
de una sección fija, y dejé anotado el límite conocido (el mensaje de estado no
guarda el estado anterior y `usuario_id` puede quedar `null`).

### [Decisión] Seed con historial de transiciones y comentarios escalonados

**Contexto:** El seed creaba los 100 tickets de ejemplo directamente en su estado
final. Con la tabla `state_log` y los comentarios ya en marcha, ese enfoque dejaba
tickets "resuelto"/"cerrado" con un historial vacío o incoherente (un único log de
creación) y sin comentarios, lo que no refleja el uso real. Se pidió que cada
cambio de status genere un log y un comentario, con un minuto de diferencia entre
cada cambio.

**Uso de LLM:** Le pedí reescribir `bootstrap.py` para que cada ticket recorra sus
transiciones desde `abierto` hasta su estado objetivo, insertando un `state_log` y
un `comment` por cada cambio, con timestamps escalonados de 1 minuto.

**Salida del modelo:** Rutas de ciclo de vida por estado objetivo
(`abierto → en_progreso → resuelto → {cerrado, reabierto}`); por cada paso inserta
`state_log` (`"Cambio de status: {estado}"`, mismo formato que los listeners) y un
`comment` narrativo (autor = usuario asignado, o `sistema@deskly.com` si el ticket
está sin asignar). Los `creado_en` se escalonan con `timedelta(minutes=1)` desde un
instante base por ticket.

**Mi decisión:** Acepté. Punto clave: los inserts se hacen con sentencias **Core**
(`insert(...)`) en lugar de `session.add` del ORM, porque los listeners de
`events.py` fijan `creado_en = now()` en cada `after_insert`/`after_update` y
además duplicarían los logs. Los inserts Core no disparan esos listeners, así que
el seed controla los timestamps y emite él mismo el log inicial de creación. El
seed sigue siendo idempotente (solo siembra si no hay tickets) y determinista
(`random.Random(42)`). Actualicé la spec (`requirements.md` y `design.md` §8.1)
antes de tocar el código, según SDD.

### [Decisión] Filtro "Sin asignar" (asignado_a_id = -1 → IS NULL)

**Contexto:** El filtro de asignación en el dashboard devolvía resultados vacíos
al seleccionar "Sin asignar". El frontend enviaba `0` como value, pero en SQL
`asignado_a_id = 0` (donde 0 sería un user id) no es lo mismo que
`asignado_a_id IS NULL`.

**Solución:** Usar `-1` como sentinela: el frontend envía `-1` cuando selecciona
"Sin asignar", y el backend interpreta `asignado_a_id = -1` como
`Ticket.asignado_a_id.is_(None)` para filtrar correctamente. Así se distingue
entre "filtro desactivado" (no envía parámetro), "usuario específico" (ID > 0) y
"sin asignar" (-1).

**Mi decisión:** Implementé el fix. Patrón limpio y evita ambigüedad con IDs reales.

### [Decisión] Lógica de asignación en seed: abiertos 50/50

**Contexto:** El seed asignaba usuarios aleatoriamente a todos los tickets. En la
realidad, los tickets "abiertos" pueden estar sin asignar (esperando que un agente
los tome), pero en estados posteriores (en_progreso, resuelto, etc.) siempre hay
un agente trabajando.

**Solución:** En el seed, si `estado == abierto`:
- Índices pares (i % 2 == 0): asignado a un usuario aleatorio.
- Índices impares (i % 2 == 1): sin asignar (NULL).
Para otros estados: siempre asignado. El autor del comentario es el email del
asignado o `sistema@deskly.com` si está sin asignar.

**Mi decisión:** Implementé. 50/50 en abiertos es realista para un prototipo con
100 tickets.

### [Decisión] Modal de historial: fecha completa + orden cronológico

**Contexto:** El modal mostraba solo el tiempo relativo ("hace una semana"),
visible al pasar mouse en el title. El orden estaba descendente (más reciente
primero), cuando es más natural leer el historial del principio al final.

**Solución:** 
- Frontend: Mostrar fecha completa (`toLocaleString()`) + separador + tiempo relativo
  (ej: "01/09/2026, 08:06:10 · hace una semana").
- Backend: Cambiar `order_by="StateLog.creado_en.desc()"` a `.asc()` en el modelo
  `Ticket.state_log`, para que devuelva logs de más antiguo a más reciente.

**Mi decisión:** Implementé ambos cambios. Mejora UX: la fecha nunca queda oculta
y el flujo temporal es intuitivo (inicio → fin del ciclo de vida del ticket).

### [Decisión] Eventos de dominio tipados con StrEnum

**Contexto:** Los eventos WebSocket se definían como strings literales sueltos
(`TICKET_CREATED = "ticket.creado"`), propensos a typos y sin autocompletado.

**Uso de LLM:** Propuso usar `StrEnum` de Python para type-safety.

**Salida del modelo:** Crear `DomainEvent` como StrEnum con los tres eventos,
re-exportando las constantes para mantener compatibilidad con imports existentes.

**Mi decisión:** Acepté. Añadí `DomainEvent` a `enums.py` y refactoricé `events.py`
para usar el enum. Mantuve las constantes exportadas para no romper los routers
que las importan. Beneficio: type-safety, autocompletado en IDEs, single source
of truth para los nombres de eventos.

### [Decisión] Health check extendido con verificación de dependencias

**Contexto:** El endpoint `/health` solo devolvía `{"status": "ok"}` sin verificar
que la base de datos o Redis estuvieran accesibles.

**Uso de LLM:** Propuso verificar conectividad de DB y Redis en el health check.

**Salida del modelo:** Ejecutar `SELECT 1` contra la base de datos y `PING` contra
Redis, devolviendo estado detallado por componente.

**Mi decisión:** Acepté. El health check ahora devuelve:
- `{"status": "ok", "db": "ok", "redis": "ok"}` si todo funciona
- `{"status": "degraded", "db": "error", ...}` si algo falla
- `redis: "not_configured"` si Redis no está configurado (es opcional)

Esto permite detectar problemas de infraestructura antes de que afecten a usuarios.

### [Decisión] Repository Pattern para desacoplar lógica de negocio

**Contexto:** El router `tickets.py` tenía 185 LOC con lógica de negocio mezclada:
validación de asignatario, filtros, paginación, transiciones de estado. Difícil
de testear y reutilizar.

**Uso de LLM:** Propuso extraer la lógica a una clase `TicketRepository` siguiendo
el patrón Repository.

**Salida del modelo:** Crear `app/repositories/ticket.py` con métodos para cada
operación: `create`, `update`, `transition`, `add_comment`, `list_with_filters`,
etc. El router se reduce a orchestar la llamada y el broadcast WebSocket.

**Mi decisión:** Acepté. El router pasó de 185 LOC a 111 LOC. Beneficios:
- Lógica de negocio testeable independientemente (unit tests del repositorio)
- Reutilizable en otros contextos (CLI, background tasks, otros routers)
- Router delgado que solo maneja HTTP y eventos
- Separación clara de responsabilidades (SRP)

El repositorio se inyecta via `Depends(get_repo)`, siguiendo el patrón de
dependencias de FastAPI.

### [Decisión] Environment validation con `extra="forbid"`

**Contexto:** Las variables de entorno se aceptaban sin validación. Un typo en
`.env` (ej: `DATABSE_URL` en lugar de `DATABASE_URL`) fallaba silenciosamente
usando el valor por defecto.

**Uso de LLM:** Propuse cambiar `extra="ignore"` a `extra="forbid"` en Pydantic
Settings.

**Salida del modelo:** Rechazar variables desconocidas obliga a documentar todas
las vars y detecta typos al arrancar.

**Mi decisión:** Acepté. Ahora si hay una variable no definida en `Settings`,
la app falla al arrancar con un error claro. Beneficio: fail-fast, sin
comportamiento sorpresivo en producción.

### [Decisión] Migrations check en CI

**Contexto:** No había validación automática de que las migraciones Alembic son
consistentes con el modelo.

**Uso de LLM:** Propuse añadir `alembic check` al pipeline de CI.

**Salida del modelo:** El comando detecta drift entre modelos y migraciones,
y conflictos en migraciones pendientes.

**Mi decisión:** Acepté. Añadí el paso antes de los tests. Beneficio: detecta
problemas de esquema antes del merge, no en producción.

### [Decisión] Type-safety end-to-end con OpenAPI

**Contexto:** Los tipos TypeScript en `lib/types.ts` se escribían a mano y
podían desincronizarse del backend.

**Uso de LLM:** Propuse generar tipos automáticamente desde el schema OpenAPI
de FastAPI.

**Salida del modelo:** Usar `openapi-typescript` para generar `lib/api-types.ts`
desde `/openapi.json`, con un script `npm run types:gen`.

**Mi decisión:** Acepté. Añadí el script y la dependencia. Beneficio: tipos
siempre sincronizados, sin mantenimiento manual. Se puede integrar en CI o
ejecutar manualmente cuando cambie la API.

---

## Mejoras de Frontend

### [Decisión] Zod para validación de formularios

**Contexto:** Los formularios validaban manualmente con `useState` y condicionales,
repetitivo y propenso a errores.

**Uso de LLM:** Propuse usar Zod + react-hook-form para validación declarativa.

**Salida del modelo:** Crear `lib/schemas.ts` con schemas Zod para login, usuarios
y tickets. Refactorizar login para usar `useForm` con `zodResolver`.

**Mi decisión:** Acepté. Añadí las dependencias y creé schemas tipados. El login
ahora tiene validación automática con mensajes de error inline. Beneficio:
types inferidos de los schemas, validación consistente, menos código.

### [Decisión] React Query para cache y sincronización

**Contexto:** Cada página hacia fetch manual + useState para loading/error/data,
con código repetitivo y sin cache.

**Uso de LLM:** Propuse React Query para manejar estado de servidor.

**Salida del modelo:** Crear `QueryProvider` con configuración sensible
(staleTime 1min, sin refetchOnWindowFocus) y envolver la app.

**Mi decisión:** Acepté. Instalé @tanstack/react-query y creé el provider.
Beneficio: cache automático, deduplicación de requests, optimistic updates,
menos boilerplate. Los hooks pueden migrarse gradualmente.

### [Decisión] Constants centralizadas

**Contexto:** Labels y colores de estados/prioridades repetidos en componentes.

**Uso de LLM:** Propuse centralizar en `lib/constants.ts`.

**Salida del modelo:** Un archivo con ESTADOS, PRIORIDADES, sus labels y colores,
exportados como Records tipados.

**Mi decisión:** Acepté. Beneficio: single source of truth, fácil de localizar,
consistencia en toda la app.

### [Decisión] Error Boundary por página

**Contexto:** Sin manejo de errores a nivel de página. Un error podía romper
toda la app.

**Uso de LLM:** Propuse usar el error.tsx de Next.js 14.

**Salida del modelo:** Crear `app/error.tsx` con UI simple y botón de reintentar.

**Mi decisión:** Acepté. Beneficio: UX controlada ante errores, sin pantallas
blancas, integración nativa con Next.js.

### [Decisión] Toasts para feedback de acciones

**Contexto:** Feedback solo con mensajes inline o alerts bloqueantes.

**Uso de LLM:** Propuse usar sonner para toasts no bloqueantes.

**Salida del modelo:** Instalar sonner y añadir `<Toaster />` al layout.

**Mi decisión:** Acepté. Beneficio: feedback visual profesional, no bloqueante,
consistentes en toda la app. Se puede usar con `toast.success()` y
`toast.error()`.

### [Decisión] DataTable abstracto reutilizable

**Contexto:** La lógica de tablas (loading, empty, render) estaba en Dashboard
con 396 LOC.

**Uso de LLM:** Propuse extraer un componente DataTable genérico.

**Salida del modelo:** Crear `components/DataTable.tsx` con tipado genérico,
columnas configurables, estados de loading/empty, y soporte para flash visual.

**Mi decisión:** Acepté. Beneficio: componente reusable en cualquier listado,
reduce complejidad de páginas, consistencia visual.

### [Decisión] Corrección de requirements.txt y Suspense boundary

**Contexto:** Al intentar levantar el proyecto con Docker, el build fallaba porque
`requirements.txt` contenía paquetes del sistema Ubuntu (aptdaemon, python-apt, etc.)
que no son dependencias del proyecto. Además, el build del frontend fallaba por un
prerender error en `/login` debido al uso de `useSearchParams()` sin Suspense boundary.

**Uso de LLM:** Le pedí que diagnosticara los errores de build y reconstruyera las
dependencias correctas a partir de los imports del código.

**Salida del modelo:** Identificó las dependencias reales del proyecto (FastAPI,
SQLAlchemy, Redis, Pydantic, etc.) y propuso un requirements.txt limpio. También
detectó que `useSearchParams` requiere Suspense boundary en Next.js 14.

**Mi decisión:**
1. Sobrescribí `requirements.txt` con las dependencias correctas del proyecto,
   eliminando los paquetes de sistema que habían contaminado el archivo.
2. Añadí `python-jose[cryptography]` para JWT (el código importa de `jose`, no de
   `jwt`) y `email-validator` para validación de emails en Pydantic.
3. Envolví el componente de login en un Suspense boundary para cumplir con los
   requisitos de Next.js 14 con `useSearchParams`.

Commits atómicos: uno para requirements.txt, otro para Suspense boundary.

### [Decisión] Webhook: tickets siempre sin asignar

**Contexto:** El campo `asignado_a_id` aparecía en el payload del webhook como
opcional, pero según el diseño los tickets externos deben llegar sin asignar
para que un agente los tome manualmente desde la interfaz.

**Uso de LLM:** Sin LLM; fue una decisión de diseño basada en el flujo real de
trabajo.

**Salida del modelo:** N/A.

**Mi decisión:** Eliminé `asignado_a_id` del schema `WebhookTicketIn` y de todos
los ejemplos de prueba. El webhook ahora ignora cualquier intento de asignar y
fuerza `asignado_a_id = NULL` en la creación. Actualicé README y especificaciones
para documentar que la asignación es manual tras la creación.

### [Decisión] Dashboard: actualización in-place con highlight visual

**Contexto:** Al asignar un ticket desde la tabla, se recargaba toda la lista
mostrando el skeleton de carga, lo que interrumpía la navegación.

**Uso de LLM:** Le pedí que la asignación inline actualizara solo la fila
afectada y añadierá un indicador visual del cambio.

**Salida del modelo:** Propuso actualizar el estado local de la fila en lugar
de llamar a `load()`, y añadir un flash CSS de 1.2s que se elimina solo.

**Mi decisión:** Acepté. El estado se actualiza in-place (`setData` con map),
y si el ticket actualizado ya no matchea los filtros activos, se elimina de
la lista. Añadí una animación CSS (`ticket-row-flash`) que pinta la fila de
azul brevemente, con soporte para `prefers-reduced-motion`. Mejora UX sin
añadir dependencias.

---

### [Decisión] Dos modos de arranque: Docker completo (Modo A) y desarrollo híbrido (Modo B)

**Contexto:** La prueba pide arrancar todo con `docker compose up` (Modo A). Pero
para desarrollar cómodamente quiero editar backend y frontend con recarga en vivo
sin reconstruir imágenes en cada cambio (Modo B). El conflicto real no era el
puerto (siempre 5432), sino el **host** de la base de datos: dentro de Docker el
backend se conecta al servicio `db`, pero en local se conecta a `localhost`.
Tener `DATABASE_URL` fija en el `.env` compartido rompía uno de los dos modos
(de hecho, causaba el `ConnectionRefusedError` inicial: `localhost` dentro del
contenedor apunta al propio contenedor, no a la db).

**Uso de LLM:** Le pedí un diseño que soportara ambos modos sin editar archivos a mano cada vez.

**Salida del modelo:** Propuso sacar `DATABASE_URL`/`REDIS_URL` del `.env`
compartido para que cada modo aporte su propio host, y verificó que sin esas
variables `pydantic` aplica el default del código (`@db:5432`), correcto para Docker.

**Mi decisión:** Adopté ese enfoque. En el `.env` dejé `DATABASE_URL` y
`REDIS_URL` **comentadas** (con una nota que explica por qué). Así:
- **Modo A (Docker):** el contenedor `api` usa el default `@db:5432` del
  `docker-compose.yml`. Es lo que ejecuta el evaluador con `docker compose up`.
- **Modo B (local):** tres scripts (`dev-infra.sh`, `dev-api.sh`, `dev-web.sh`)
  levantan Postgres+Redis en Docker y arrancan backend y frontend en local con
  hot reload. `dev-api.sh` carga `api/.env.local` (host `localhost:5432`) antes
  de uvicorn.

`api/.env.local` está en `.gitignore`, así que el Modo B no interfiere con la
entrega (Modo A). El puerto es 5432 en ambos casos; lo único que cambia es el host.

---

### [Decisión] Bug en el login: `PasswordInput` no reenviaba el `ref` a react-hook-form

**Contexto:** El formulario de login mostraba "Invalid input: expected string,
received undefined" bajo el campo de contraseña. El schema Zod y el backend
estaban bien; el email validaba correctamente pero la contraseña no.

**Uso de LLM:** Le pedí que diagnosticara por qué solo fallaba la contraseña.

**Salida del modelo:** Identificó que `PasswordInput` era una función-componente
normal (sin `forwardRef`) que además interceptaba `value`/`onChange`. Al hacer
`<PasswordInput {...register("password")} />`, el `ref` que react-hook-form usa
para leer el valor del input (modo no controlado) nunca llegaba al `<input>`, así
que el valor llegaba como `undefined` y Zod fallaba. El email funcionaba porque
usa `<input {...register("email")} />` directo.

**Mi decisión:** Reescribí `PasswordInput` con **`forwardRef`**, reenviando el
`ref` al `<input>` real y dejando que `name`/`onChange`/`onBlur`/`value` fluyan
por `...rest`. Así es compatible tanto con react-hook-form (login, no controlado)
como con uso controlado (`users/page.tsx`, con `value`/`onChange`). Verificado con
`npx tsc --noEmit` (sin errores) y probando el login end-to-end.

---

### [Decisión] Bug en la transición de estado: `History` no tiene atributo `.modified`

**Contexto:** Al cambiar el estado de un ticket, el endpoint de transición
devolvía **500** con `AttributeError: 'History' object has no attribute 'modified'`
en el listener `receive_ticket_after_update` de `app/events.py`.

**Uso de LLM:** Le pedí que localizara la causa del `AttributeError`.

**Salida del modelo:** El listener comprobaba
`if estado_history.has_changes() and estado_history.modified:`, pero el objeto
`History` que devuelve `get_history()` de SQLAlchemy solo expone `added`,
`deleted`, `unchanged` y el método `has_changes()`. `.modified` no existe (el
comentario del código incluso lo describía mal). El bloque análogo para
`asignado_a_id`, unas líneas más abajo, ya usaba solo `has_changes()`
correctamente.

**Mi decisión:** Eliminé el `and estado_history.modified` y dejé la condición como
`if estado_history.has_changes():`, que es lo que se pretendía y es consistente
con el resto del listener. Actualicé el comentario para dejar claro qué atributos
tiene realmente `History`. Verifiqué con grep que no había otros usos de
`.modified` en el backend.
