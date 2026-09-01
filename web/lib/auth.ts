/**
 * Helpers para gestionar el token JWT en el navegador.
 * 
 * El JWT se guarda en una cookie para que esté disponible
 * durante las peticiones SSR (via next/headers cookies()).
 */

import { TOKEN_COOKIE } from "./api";

/**
 * Guarda el token JWT en una cookie.
 * 
 * Duración: 1 día.
 * SameSite: Lax (suficiente para uso SSR en el mismo sitio).
 */
export function setToken(token: string) {
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(
    token
  )}; path=/; max-age=86400; SameSite=Lax`;
}

/**
 * Elimina el token JWT de la cookie.
 */
export function clearToken() {
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

/**
 * Obtiene el token JWT de la cookie.
 * 
 * @returns El token si existe, null si no
 */
export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${TOKEN_COOKIE}=([^;]*)`)
  );
  return match ? decodeURIComponent(match[1]) : null;
}
