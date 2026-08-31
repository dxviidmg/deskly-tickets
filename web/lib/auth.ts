// Browser-side token helpers. The JWT is kept in a cookie so it is also sent
// during SSR requests (via next/headers cookies()).

import { TOKEN_COOKIE } from "./api";

export function setToken(token: string) {
  // 1 day; SameSite=Lax is enough for same-site SSR usage.
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(
    token
  )}; path=/; max-age=86400; SameSite=Lax`;
}

export function clearToken() {
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${TOKEN_COOKIE}=([^;]*)`)
  );
  return match ? decodeURIComponent(match[1]) : null;
}
