// Typed API client for the Deskly backend.
//
// Works from both the server (SSR) and the browser. The JWT is stored in a
// cookie named "deskly_token" so it is available during SSR too. On the
// browser we read it from document.cookie; on the server the caller passes it
// explicitly (from next/headers cookies()).

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

export const TOKEN_COOKIE = "deskly_token";

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

function browserToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${TOKEN_COOKIE}=([^;]*)`)
  );
  return match ? decodeURIComponent(match[1]) : null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions extends RequestInit {
  token?: string | null; // explicit token (used during SSR)
}

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
      // keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export interface ListParams {
  page?: number;
  size?: number;
  estado?: Estado | "";
  prioridad?: Prioridad | "";
  asignado_a_id?: number | null;
}

export const api = {
  // --- Auth ---
  login(email: string, password: string): Promise<{ access_token: string }> {
    return request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
  me(token?: string | null): Promise<AuthUser> {
    return request<AuthUser>("/api/auth/me", { token });
  },

  // --- Tickets ---
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
  getTicket(id: number, token?: string | null): Promise<TicketDetail> {
    return request<TicketDetail>(`/api/tickets/${id}`, { token });
  },
  transition(id: number, nuevo_estado: Estado): Promise<Ticket> {
    return request<Ticket>(`/api/tickets/${id}/transicion`, {
      method: "POST",
      body: JSON.stringify({ nuevo_estado }),
    });
  },
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
  addComment(id: number, cuerpo: string): Promise<Comment> {
    return request<Comment>(`/api/tickets/${id}/comentarios`, {
      method: "POST",
      body: JSON.stringify({ cuerpo }),
    });
  },

  // --- Users (admin only) ---
  listUsers(): Promise<User[]> {
    return request<User[]>("/api/users");
  },
  // Lightweight lookup available to any authenticated user (for selects).
  listUserOptions(q?: string, limit = 5): Promise<UserOption[]> {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    params.set("limit", String(limit));
    return request<UserOption[]>(`/api/users/options?${params.toString()}`);
  },
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
  deleteUser(id: number): Promise<void> {
    return request<void>(`/api/users/${id}`, { method: "DELETE" });
  },
};
