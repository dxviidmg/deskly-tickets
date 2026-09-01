/**
 * Cliente API tipado para el backend de Deskly.
 * 
 * Funciona tanto desde el servidor (SSR) como desde el navegador.
 * El JWT se almacena en una cookie llamada "deskly_token" para que
 * esté disponible durante el SSR. En el navegador se lee de
 * document.cookie; en el servidor se pasa explícitamente.
 * 
 * Métodos principales:
 * - login: Iniciar sesión y obtener token
 * - me: Obtener usuario autenticado
 * - listTickets: Listar tickets con filtros y paginación
 * - getTicket: Obtener detalle de un ticket
 * - updateTicket: Actualizar parcialmente un ticket
 * - transition: Cambiar estado de un ticket
 * - addComment: Añadir comentario a un ticket
 * - listUsers: Listar usuarios (solo admin)
 * - createUser: Crear usuario (solo admin)
 */
import type {
  AuthUser,
  Comment,
  Estado,
  Page,
  Prioridad,
  Ticket,
  TicketDetail,
  User,
  UserOption,
} from "./types";

/** Nombre de la cookie que almacena el token JWT */
export const TOKEN_COOKIE = "deskly_token";

/**
 * Devuelve la URL base de la API.
 * - En el servidor: usa API_INTERNAL_URL o NEXT_PUBLIC_API_URL
 * - En el navegador: usa NEXT_PUBLIC_API_URL
 */
function baseUrl(): string {
  if (typeof window === "undefined") {
    return (
      process.env.API_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000"
    );
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

/**
 * Lee el token JWT de las cookies del navegador.
 * Devuelve null si no hay token o no está en el navegador.
 */
function browserToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${TOKEN_COOKIE}=([^;]*)`)
  );
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Error personalizado para respuestas HTTP con error.
 * Incluye el código de estado HTTP y el mensaje de detalle.
 */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions extends RequestInit {
  token?: string | null; // Token explícito (usado en SSR)
}

/**
 * Realiza una petición HTTP a la API.
 * 
 * - Añade automáticamente el token JWT si está disponible
 * - Convierte respuestas de error en ApiError
 * - Maneja respuestas 204 (sin contenido)
 * 
 * @param path - Ruta de la API (ej: /api/tickets)
 * @param opts - Opciones de fetch + token opcional
 * @returns Respuesta parseada como JSON
 * @throws ApiError si la respuesta no es ok
 */
async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { token, headers, ...init } = opts;
  const authToken = token ?? browserToken();

  const res = await fetch(`${baseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(headers || {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
    } catch {
      // Mantener statusText si no hay body
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Parámetros para listar tickets con filtros y paginación */
export interface ListParams {
  page?: number;
  size?: number;
  estado?: Estado | "";
  prioridad?: Prioridad | "";
  asignado_a_id?: number | null; // -1 = sin asignar
}

/** Objeto con todos los métodos de la API */
export const api = {
  // --- Autenticación ---

  /** Inicia sesión y devuelve un token JWT */
  login(email: string, password: string): Promise<{ access_token: string }> {
    return request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  /** Obtiene el usuario autenticado actual */
  me(token?: string | null): Promise<AuthUser> {
    return request<AuthUser>("/api/auth/me", { token });
  },

  // --- Tickets ---

  /** Lista tickets con filtros opcionales y paginación */
  listTickets(params: ListParams = {}, token?: string | null): Promise<Page<Ticket>> {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("size", String(params.size ?? 10));
    if (params.estado) q.set("estado", params.estado);
    if (params.prioridad) q.set("prioridad", params.prioridad);
    if (params.asignado_a_id !== undefined && params.asignado_a_id !== null)
      q.set("asignado_a_id", String(params.asignado_a_id));
    return request<Page<Ticket>>(`/api/tickets?${q.toString()}`, { token });
  },

  /** Obtiene el detalle de un ticket con comentarios e historial */
  getTicket(id: number, token?: string | null): Promise<TicketDetail> {
    return request<TicketDetail>(`/api/tickets/${id}`, { token });
  },

  /** Cambia el estado de un ticket */
  transition(id: number, nuevo_estado: Estado): Promise<Ticket> {
    return request<Ticket>(`/api/tickets/${id}/transicion`, {
      method: "POST",
      body: JSON.stringify({ nuevo_estado }),
    });
  },

  /** Actualiza parcialmente un ticket (título, descripción, asignado) */
  updateTicket(
    id: number,
    patch: {
      asignado_a_id?: number | null;
      titulo?: string;
      descripcion?: string;
    }
  ): Promise<Ticket> {
    return request<Ticket>(`/api/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
  },

  /** Añade un comentario a un ticket */
  addComment(id: number, cuerpo: string): Promise<Comment> {
    return request<Comment>(`/api/tickets/${id}/comentarios`, {
      method: "POST",
      body: JSON.stringify({ cuerpo }),
    });
  },

  // --- Usuarios (solo administradores) ---

  /** Lista todos los usuarios (solo admin) */
  listUsers(): Promise<User[]> {
    return request<User[]>("/api/users");
  },

  /** Busca usuarios por email/nombre para selects (cualquier usuario autenticado) */
  listUserOptions(q?: string, limit = 5): Promise<UserOption[]> {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    params.set("limit", String(limit));
    return request<UserOption[]>(`/api/users/options?${params.toString()}`);
  },

  /** Crea un usuario nuevo (solo admin) */
  createUser(data: {
    email: string;
    password: string;
    nombre: string;
    apellidos: string;
    is_admin: boolean;
  }): Promise<User> {
    return request<User>("/api/users", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /** Elimina un usuario (solo admin) */
  deleteUser(id: number): Promise<void> {
    return request<void>(`/api/users/${id}`, { method: "DELETE" });
  },
};
