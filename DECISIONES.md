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

### Base de datos: PostgreSQL en lugar de MongoDB

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

### Migraciones con Alembic (el modelo dijo que no hacía falta; yo lo pedí)

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

### IDs numéricos autoincrementales (el modelo usó UUID; yo lo pedí cambiar)

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

### Webhook: primero la firma (401), luego el contenido (422)

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

### Tiempo real con Redis (el modelo lo hizo en memoria; yo pedí Redis)

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

### Entorno de desarrollo: Python 3.12 con `uv` (mi máquina trae 3.14)

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

### Tests: cómo conecto la app a una base de datos de prueba

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

### Estados y prioridades guardados como texto

**Contexto:** `estado` y `prioridad` solo pueden tomar unos pocos valores fijos. PostgreSQL tiene un tipo especial para esto (`ENUM`).

**Uso de LLM:** Sin LLM; lo decidí al modelar las tablas.

**Salida del modelo:** Sin LLM en esta decisión.

**Mi decisión:** Los guardo como texto y valido los valores en la aplicación (con los enumerados de Python y con Pydantic). El tipo `ENUM` de PostgreSQL es incómodo de cambiar (añadir un estado nuevo es molesto) y no funciona en SQLite, que uso en los tests. La validación real ya la hacen la aplicación y la máquina de estados, así que no la necesito también en la columna.

---

### Configuración por `.env` y archivo `.env.example`

**Contexto:** El secreto que usa el webhook para verificar la firma tenía en el código un valor por defecto (`change-me`). Ese campo ya se leía desde una variable de entorno, pero no había un archivo que dejara claras todas las variables de configuración del proyecto ni cómo rellenarlas.

**Uso de LLM:** Ninguno para tomar la decisión; me pediste centralizar la configuración en `.env` y yo preparé el archivo de ejemplo.

**Salida del modelo:** Sin propuesta del modelo; fue una petición tuya.

**Mi decisión:** A tu petición, dejé claro que la configuración viene de un archivo `.env` y añadí un **`.env.example`** en la raíz con todos los valores: la conexión a la base de datos, el secreto del webhook (como marcador `change-me`, con aviso de cambiarlo), la URL de Redis, los orígenes permitidos (CORS), el interruptor de datos de ejemplo y las URLs del frontend. El `.env` real **no se sube** al repositorio (está ignorado en git); solo se versiona el `.env.example`. Así no hay ningún secreto en el repositorio y cualquiera puede arrancar el proyecto copiando el ejemplo (`cp .env.example .env`) y ajustando los valores.

---

### Frontend sin librería de estado (React Query u otras)

**Contexto:** El frontend tiene que listar tickets, filtrarlos, ver el detalle y actualizarse en vivo. Una opción habitual es añadir una librería de datos como React Query.

**Uso de LLM:** Le pedí el frontend con Next.js 14.

**Salida del modelo:** Propuso resolverlo con las herramientas propias de Next y React (componentes de servidor para la carga inicial y `fetch`), sin añadir librerías extra.

**Mi decisión:** Acepté no meter React Query ni un store global. Para este alcance, los componentes de servidor de Next (para la carga inicial) y `useState`/`useEffect` (para la interacción y el tiempo real) son suficientes. Menos dependencias, menos cosas que explicar y defender. Si la app creciera (mucha caché, sincronización compleja), reconsideraría una librería de datos.

---

### SSR solo en el detalle; dashboard interactivo en el cliente

**Contexto:** El reto pide que el **detalle** `/tickets/[id]` sea renderizado en el servidor (SSR). El dashboard, en cambio, necesita filtro y actualización en vivo.

**Uso de LLM:** Le pedí las dos páginas.

**Salida del modelo:** Planteó el detalle como componente de servidor (SSR) y el dashboard con interacción en el cliente.

**Mi decisión:** El detalle se renderiza en el servidor: la primera carga ya trae el ticket y sus comentarios (mejor para SSR y para enlaces directos). La interacción del detalle (cambiar estado, comentar, tiempo real) va en un componente de cliente aparte. El dashboard lo hice de cliente porque combina filtro, paginación y actualización en vivo, que son inherentemente interactivos. Así cada página usa el enfoque que mejor le encaja.

---

### Reconexión automática del WebSocket

**Contexto:** La conexión de tiempo real puede caerse (red, reinicio del backend). Si no se hace nada, el usuario deja de recibir avisos sin enterarse.

**Uso de LLM:** Le pedí el hook de WebSocket con limpieza correcta.

**Salida del modelo:** Entregó un hook que abre la conexión, la limpia al desmontar y expone el estado de conexión.

**Mi decisión:** Además de la limpieza, añadí **reconexión automática** con una espera creciente (hasta 5 s) cuando la conexión se pierde, y un **indicador visible**
(En vivo / Conectando / Desconectado) para que el usuario sepa el estado. Al recibir un evento, el dashboard recarga la lista y el detalle recarga ese ticket: es lo más simple y siempre muestra datos consistentes con el servidor (preferí esto antes que aplicar cambios parciales en el cliente, que es más frágil).

---

### Usuarios, autenticación e `is_admin` (ampliación del alcance)

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

### Detalle técnico: bcrypt fijado a 4.0.1 por compatibilidad con passlib

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
