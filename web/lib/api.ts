// Typed API client for the Deskly backend.
//
// Works from both the server (SSR) and the browser. On the server we prefer the
// internal Docker URL (API_INTERNAL_URL); in the browser we use the public URL
// (NEXT_PUBLIC_API_URL).

import type {
  Comment,
  Estado,
  Page,
  Ticket,
  TicketDetail,
} from "./types";

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

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl()}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // ignore parse errors, keep statusText
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
}

export const api = {
  listTickets(params: ListParams = {}): Promise<Page<Ticket>> {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("size", String(params.size ?? 10));
    if (params.estado) q.set("estado", params.estado);
    return request<Page<Ticket>>(`/api/tickets?${q.toString()}`);
  },

  getTicket(id: number): Promise<TicketDetail> {
    return request<TicketDetail>(`/api/tickets/${id}`);
  },

  transition(id: number, nuevo_estado: Estado): Promise<Ticket> {
    return request<Ticket>(`/api/tickets/${id}/transicion`, {
      method: "POST",
      body: JSON.stringify({ nuevo_estado }),
    });
  },

  addComment(id: number, autor: string, cuerpo: string): Promise<Comment> {
    return request<Comment>(`/api/tickets/${id}/comentarios`, {
      method: "POST",
      body: JSON.stringify({ autor, cuerpo }),
    });
  },
};
