"""
MÓDULO: config.py - Configuración de la aplicación

Este archivo define todas las variables de configuración que controlan
el comportamiento de la aplicación. Usa Pydantic Settings para:
- Cargar automáticamente variables de .env
- Validar los tipos de datos
- Documentar qué configuraciones existen

Pydantic es una librería que valida datos Python usando type hints.
Por ejemplo, si defines 'puerto: int', Pydantic se asegura de que
sea un entero y lanza error si alguien intenta pasar texto.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Clase que define todas las variables de configuración de la aplicación.
    
    Los valores vienen de:
    1. Variables de entorno (ej: DATABASE_URL=...)
    2. Archivo .env en la raíz del proyecto (ej: .env)
    3. Valores por defecto definidos aquí
    
    Ejemplo en .env:
        DATABASE_URL=postgresql+asyncpg://usuario:contraseña@localhost/base_datos
        REDIS_URL=redis://localhost:6379/0
        JWT_SECRET=mi-secreto-muy-seguro
    """

    # Configuración de Pydantic: de dónde cargar el archivo
    model_config = SettingsConfigDict(
        env_file=".env",                    # Archivo a leer
        env_file_encoding="utf-8",          # Codificación
        extra="forbid"                      # Rechazar variables no definidas
    )

    # ========== BASE DE DATOS ==========
    # URL de conexión a PostgreSQL con asyncpg (driver asíncrono para Python)
    # Formato: postgresql+asyncpg://usuario:contraseña@host:puerto/base_datos
    database_url: str = "postgresql+asyncpg://deskly:deskly@db:5432/deskly"

    # ========== REDIS ==========
    # URL para conectar a Redis (usado para pub/sub de WebSocket)
    # Redis es un almacén de datos en memoria muy rápido, ideal para eventos en tiempo real.
    # Si no está configurado, el WebSocket funciona solo localmente (sin fan-out entre instancias).
    redis_url: str = "redis://redis:6379/0"

    # ========== WEBHOOK ==========
    # Secreto compartido para verificar la firma HMAC-SHA256 de los webhooks
    # El cliente debe firmar cada petición con este secreto, y nosotros lo verificamos
    # para asegurar que la petición realmente viene de quien dice ser
    webhook_secret: str = "change-me"

    # Edad máxima (en segundos) que aceptamos para un timestamp de webhook
    # Esto protege contra ataques de replay: alguien no puede reutilizar una petición vieja
    webhook_max_age_seconds: int = 300

    # ========== CORS ==========
    # Lista de orígenes (dominios) permitidos para hacer requests a la API
    # Por defecto: solo localhost:3000 (el frontend local)
    # Múltiples orígenes se separan por coma: "http://localhost:3000, https://example.com"
    cors_origins: str = "http://localhost:3000"

    # ========== AUTENTICACIÓN (JWT) ==========
    # Secreto usado para firmar los tokens JWT (JSON Web Tokens)
    # Los tokens se usan para que el cliente no tenga que enviar contraseña en cada request
    # Formato JWT: header.payload.signature (la firma usa este secreto)
    jwt_secret: str = "change-me-too"

    # Algoritmo criptográfico para firmar JWT (recomendado: HS256 o RS256)
    jwt_algorithm: str = "HS256"

    # Tiempo en minutos hasta que un token JWT expira y deja de ser válido
    access_token_expire_minutes: int = 60

    # ========== SEED / DATOS INICIALES ==========
    # Email del usuario administrador que se crea al arrancar
    # Se puede cambiar aquí o en la variable de entorno ADMIN_EMAIL
    admin_email: str = "admin@deskly.com"

    # Contraseña inicial del administrador
    # IMPORTANTE: cambiar en producción
    admin_password: str = "admin123"

    @property
    def cors_origins_list(self) -> list[str]:
        """
        Convierte la cadena de orígenes CORS en una lista de strings.
        
        Ejemplo:
            Si cors_origins = "http://localhost:3000, https://example.com"
            Devuelve: ["http://localhost:3000", "https://example.com"]
        
        El .strip() elimina espacios en blanco alrededor de cada origen.
        El if o.strip() filtra cadenas vacías.
        
        Returns:
            Lista de orígenes permitidos para CORS
        """
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Devuelve una instancia cacheada de Settings.
    
    @lru_cache (Least Recently Used cache) asegura que:
    - La primera vez que se llama, se crea la instancia Settings (caro: lee .env, valida, etc.)
    - Las siguientes veces, se devuelve la misma instancia del caché
    - Esto es eficiente porque las settings no cambian durante la ejecución
    
    FastAPI llama a esta función automáticamente cuando ve:
        settings: Settings = Depends(get_settings)
    
    Returns:
        Instancia única de Settings con todas las configuraciones validadas
    """
    return Settings()
