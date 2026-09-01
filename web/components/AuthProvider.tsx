/**
 * Provider de autenticación para la aplicación.
 * 
 * Gestiona el estado del usuario autenticado:
 * - Login: guarda token JWT en cookie y obtiene usuario
 * - Logout: elimina token y limpia estado
 * - Detección de sesión caducada (401)
 * 
 * Usa un Context de React para disponibilizar el estado
 * en cualquier componente de la app.
 */
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api } from "@/lib/api";
import { clearToken, getToken, setToken } from "@/lib/auth";
import type { AuthUser } from "@/lib/types";

/** Valor del contexto de autenticación */
interface AuthContextValue {
  /** Usuario autenticado actual (null si no hay sesión) */
  user: AuthUser | null;
  /** Indica si se está verificando el token inicial */
  loading: boolean;
  /** Inicia sesión con email y contraseña */
  login: (email: string, password: string) => Promise<void>;
  /** Cierra la sesión del usuario */
  logout: () => void;
  /** Indica si la sesión ha caducado (para mostrar mensaje en login) */
  sessionExpired: boolean;
  /** Limpia el flag de sesión caducada */
  clearSessionExpired: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Provider que gestiona el estado de autenticación.
 * 
 * Al montarse, verifica si hay un token en cookies y obtiene
 * el usuario correspondiente. Si el token es inválido (401),
 * marca la sesión como caducada.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  // Al montar, verificar si hay token y obtener usuario
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me(token)
      .then(setUser)
      .catch((err) => {
        // Si es 401, marca sesión como caducada
        if (err?.status === 401) {
          setSessionExpired(true);
        }
        clearToken();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  /** Inicia sesión con email y contraseña */
  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await api.login(email, password);
    setToken(access_token);
    const me = await api.me(access_token);
    setUser(me);
    setSessionExpired(false);
  }, []);

  /** Cierra la sesión eliminando el token y el usuario */
  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  /** Limpia el flag de sesión caducada */
  const clearSessionExpired = useCallback(() => {
    setSessionExpired(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        sessionExpired,
        clearSessionExpired,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook para acceder al contexto de autenticación.
 * 
 * @throws Error si se usa fuera de AuthProvider
 * @returns Valor del contexto de autenticación
 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
