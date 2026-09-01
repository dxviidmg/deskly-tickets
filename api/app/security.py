"""
MÓDULO: security.py - Funciones de seguridad

Proporciona:
1. Hashing de contraseñas: bcrypt (algoritmo seguro)
2. Tokens JWT: para autenticación sin estado

JWT (JSON Web Token):
- El cliente hace login con email + contraseña
- El servidor verifica contraseña, genera JWT y lo devuelve
- El cliente envía JWT en cada request: Authorization: Bearer <token>
- El servidor valida JWT sin tocar la BD (stateless)

Ventajas JWT:
- No necesita sesiones en el servidor
- Escalable: múltiples servidores pueden validar el mismo token
- Expira automáticamente después de X minutos
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# Contexto de hashing con bcrypt
# El algoritmo bcrypt es muy seguro: se hace más lento intencionalmente
# para ralentizar ataques de fuerza bruta
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando bcrypt.
    
    Bcrypt:
    - Es un algoritmo one-way: no se puede revertir (eso es lo bueno)
    - Usa "salt" (número aleatorio) para que mismo password tenga hash diferente
    - Es lento intencionalmente (cada hash tarda ~100ms) para frenar ataques
    
    IMPORTANTE: nunca guardes contraseñas en texto plano. Siempre hashea.
    
    Args:
        password (str): Contraseña en texto plano que envía el usuario
        
    Returns:
        str: Hash de 60 caracteres (formato bcrypt estándar)
        
    Ejemplo:
        hashed = hash_password("mi_contraseña_123")
        # Resultado: "$2b$12$R9h/cIPz0gi.URNNWXYF0e..." (cada ejecución distinto)
    """
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica si una contraseña coincide con su hash.
    
    El proceso:
    1. Extrae el salt del hash
    2. Aplica el mismo algoritmo a plain con ese salt
    3. Compara los resultados
    
    NUNCA compares hashes directamente con ==
    Usa passlib/bcrypt que hace comparación a prueba de timing attacks.
    
    Args:
        plain (str): Contraseña que el usuario intenta usar
        hashed (str): Hash almacenado en la BD
        
    Returns:
        bool: True si coinciden, False si no
        
    Ejemplo:
        if verify_password("mi_contraseña_123", hash_almacenado):
            print("Contraseña correcta")
        else:
            print("Contraseña incorrecta")
    """
    return _pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    """
    Crea un token JWT firmado y listo para devolver al cliente.
    
    JWT contiene:
    - header: { "typ": "JWT", "alg": "HS256" }
    - payload: { "sub": subject (user_id), "exp": expiration_time }
    - signature: HMAC-SHA256(header + payload + secret)
    
    El cliente debe enviar este token en cada request:
        Authorization: Bearer <token_aquí>
    
    El token EXPIRA después de X minutos (configurable).
    Después de expirar, el usuario debe hacer login de nuevo.
    
    Args:
        subject (str): Identificador único (normalmente user_id como string)
        
    Returns:
        str: Token JWT codificado
        
    Ejemplo de token:
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMiLCJleHAiOjE3MDAwMDAwMDB9.xxx
    """
    # Calcular la fecha de expiración: ahora + minutes configurados
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    
    # Payload del JWT: quién eres (sub) y hasta cuándo es válido (exp)
    payload = {"sub": subject, "exp": expire}
    
    # Firmar el JWT con el secreto
    # Si alguien intenta modificar el payload, la firma no coincidirá
    # y el token será rechazado
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> str | None:
    """
    Decodifica un token JWT y devuelve el ID del usuario (subject).
    
    Si el token es inválido, expirado o fue modificado, devuelve None.
    
    Validaciones automáticas:
    - Firma debe coincidir (se detectan modificaciones)
    - Fecha de expiración no debe estar en el pasado
    - El formato debe ser válido
    
    Args:
        token (str): Token JWT que envió el cliente
        
    Returns:
        str | None: ID del usuario (subject) si el token es válido, None si no
        
    Ejemplo:
        user_id = decode_access_token(token_del_cliente)
        if user_id is None:
            return HTTPException(401, "Token inválido")
        user = db.get_user(user_id)
    """
    try:
        # Decodificar y verificar firma del JWT
        # Si algo falla, lanza JWTError
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        # Token inválido, expirado, modificado, etc.
        return None
    
    # Extraer el subject (user_id) del payload
    sub = payload.get("sub")
    
    # Convertir a string si existe, sino None
    return str(sub) if sub is not None else None
