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
 * - createTicket: Crear un ticket nuevo
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
 * - En el servidor (SSR): usa API_INTERNAL_URL, o NEXT_PUBLIC_API_URL como respaldo.
 * - En el navegador: usa NEXT_PUBLIC_API_URL.
 *
 * Regla del proyecto: ninguna URL se hardcodea en el código. Si la variable de
 * entorno no está definida, lanzamos un error claro (fail-fast) en vez de usar
 * una URL por defecto oculta. Las variables se definen en web/.env (runtime SSR)
 * y como build args NEXT_PUBLIC_* (build-time del navegador).
 */
function baseUrl(): string {
  if (typeof window === "undefined") {
    const url = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL;
    if (!url) {
      throw new Error(
        "Falta configuración: define API_INTERNAL_URL o NEXT_PUBLIC_API_URL (ver web/.env)."
      );
    }
    return url;
  }
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) {
    throw new Error(
      "Falta configuración: define NEXT_PUBLIC_API_URL en build-time (ver web/.env)."
    );
  }
  return url;
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

  /**
   * Crea un ticket nuevo (requiere autenticación).
   *
   * Los tickets se crean siempre **sin asignar** (`asignado_a_id = null`), igual
   * que los que entran por webhook. La asignación se hace después desde el
   * listado o el detalle del ticket.
   *
   * @param data - Datos del ticket: título, descripción y prioridad opcional.
   *   La prioridad por defecto la aplica el backend ("media").
   * @returns El ticket creado (con id, estado inicial "abierto" y timestamps).
   *
   * @example
   * const ticket = await api.createTicket({
   *   titulo: "No carga la página",
   *   descripcion: "Error 500 al abrir el detalle",
   *   prioridad: "alta",
   * });
   */
  createTicket(data: {
    titulo: string;
    descripcion: string;
    prioridad?: Prioridad;
  }): Promise<Ticket> {
    return request<Ticket>("/api/tickets", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

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
