// Shared types mirroring the backend Pydantic schemas (manual end-to-end typing).

export type Estado = "abierto" | "en_progreso" | "resuelto" | "cerrado";
export type Prioridad = "baja" | "media" | "alta" | "urgente";

export interface Ticket {
  id: number;
  titulo: string;
  descripcion: string;
  prioridad: Prioridad;
  estado: Estado;
  asignado_a_id: number | null;
  asignado_a: string | null; // assigned user's email (read-only)
  creado_en: string;
  actualizado_en: string;
}

export interface User {
  id: number;
  email: string;
  is_admin: boolean;
  creado_en: string;
}

export interface UserOption {
  id: number;
  email: string;
}

export interface AuthUser {
  id: number;
  email: string;
  is_admin: boolean;
}

export interface Comment {
  id: number;
  ticket_id: number;
  autor: string;
  cuerpo: string;
  creado_en: string;
}

export interface TicketDetail extends Ticket {
  comments: Comment[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

// WebSocket event shape emitted by the backend.
export type EventoTipo =
  | "ticket.creado"
  | "ticket.actualizado"
  | "ticket.comentado";

export interface TicketEvent {
  tipo: EventoTipo;
  datos: Ticket;
}

// Valid state transitions, mirrored from the backend state machine so the UI
// only offers buttons that will succeed.
export const TRANSICIONES_VALIDAS: Record<Estado, Estado[]> = {
  abierto: ["en_progreso"],
  en_progreso: ["resuelto"],
  resuelto: ["cerrado", "abierto"],
  cerrado: [],
};

export const ESTADOS: Estado[] = [
  "abierto",
  "en_progreso",
  "resuelto",
  "cerrado",
];

export const PRIORIDADES: Prioridad[] = ["baja", "media", "alta", "urgente"];
