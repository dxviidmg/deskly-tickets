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
    
    Ejemplo de variables en el .env (los valores reales NUNCA se ponen aquí en
    el código; ver api/.env.example para las claves y api/.env para los valores):
        DATABASE_URL, REDIS_URL, JWT_SECRET, WEBHOOK_SECRET, ...
    """

    # Configuración de Pydantic: de dónde cargar el archivo
    model_config = SettingsConfigDict(
        env_file=".env",                    # Archivo a leer (api/.env)
        env_file_encoding="utf-8",          # Codificación
        # "ignore": ignora variables del .env que no son campos de Settings.
        # api/.env es compartido: contiene también POSTGRES_USER/PASSWORD/DB, que
        # los lee el contenedor de Postgres pero NO la app. Con "forbid" pydantic
        # las rechazaría. "ignore" permite un único .env por servicio sin duplicar.
        extra="ignore",
    )

    # ========== BASE DE DATOS ==========
    # URL de conexión a PostgreSQL con asyncpg (driver asíncrono para Python)
    # Formato: postgresql+asyncpg://usuario:contraseña@host:puerto/base_datos
    # Obligatorio: sin valor por defecto. Debe venir del .env (o del entorno).
    database_url: str

    # ========== REDIS ==========
    # URL para conectar a Redis (usado para pub/sub de WebSocket)
    # Redis es un almacén de datos en memoria muy rápido, ideal para eventos en tiempo real.
    # Obligatorio: debe venir del .env (o del entorno).
    redis_url: str

    # ========== WEBHOOK ==========
    # Secreto compartido para verificar la firma HMAC-SHA256 de los webhooks.
    # Obligatorio y SIN default: un secreto nunca debe tener valor por defecto en
    # el código (si se olvida configurarlo, la app arrancaría insegura). Al no
    # tener default, la app falla al arrancar si falta, forzando a definirlo en
    # el .env. Debe coincidir con el secreto del proveedor que envía el webhook.
    webhook_secret: str

    # Edad máxima (en segundos) que aceptamos para un timestamp de webhook
    # Esto protege contra ataques de replay: alguien no puede reutilizar una petición vieja
    # Obligatorio: debe venir del .env.
    webhook_max_age_seconds: int

    # ========== CORS ==========
    # Lista de orígenes (dominios) permitidos para hacer requests a la API.
    # Múltiples orígenes se separan por coma: "http://localhost:3000, https://example.com"
    # Obligatorio: debe venir del .env.
    cors_origins: str

    # ========== AUTENTICACIÓN (JWT) ==========
    # Secreto usado para firmar los tokens JWT (JSON Web Tokens).
    # Obligatorio y SIN default: igual que webhook_secret, un secreto de firma
    # nunca debe tener valor por defecto. Con default, cualquiera que conozca ese
    # valor (estaría en el repo) podría falsificar tokens y suplantar usuarios.
    jwt_secret: str

    # Algoritmo criptográfico para firmar JWT (recomendado: HS256 o RS256)
    # Obligatorio: debe venir del .env.
    jwt_algorithm: str

    # Tiempo en minutos hasta que un token JWT expira y deja de ser válido
    # Obligatorio: debe venir del .env.
    access_token_expire_minutes: int

    # ========== SEED / DATOS INICIALES ==========
    # Email y contraseña del usuario administrador que se crea al arrancar.
    # Obligatorios: deben venir del .env. La contraseña, en particular, no debe
    # tener default en el código.
    admin_email: str
    admin_password: str

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
