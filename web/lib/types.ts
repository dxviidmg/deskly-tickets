/**
 * Tipos TypeScript espejo de los schemas Pydantic del backend.
 * 
 * Tipado manual end-to-end para asegurar consistencia
 * entre frontend y backend.
 */

/** Estados posibles de un ticket */
export type Estado = "abierto" | "en_progreso" | "resuelto" | "reabierto" | "cerrado";

/** Niveles de prioridad de un ticket */
export type Prioridad = "baja" | "media" | "alta" | "urgente";

/** Ticket resumido (listado) */
export interface Ticket {
  id: number;
  titulo: string;
  descripcion: string;
  prioridad: Prioridad;
  estado: Estado;
  asignado_a_id: number | null;
  asignado_a: string | null; // email del usuario asignado (solo lectura)
  creado_en: string;
  actualizado_en: string;
}

/** Usuario completo */
export interface User {
  id: number;
  email: string;
  nombre: string;
  apellidos: string;
  nombre_completo: string;
  is_admin: boolean;
  creado_en: string;
}

/** Usuario para selectores/autocompletado */
export interface UserOption {
  id: number;
  email: string;
  nombre_completo: string;
}

/** Usuario autenticado (desde JWT) */
export interface AuthUser {
  id: number;
  email: string;
  is_admin: boolean;
}

/** Comentario de un ticket */
export interface Comment {
  id: number;
  ticket_id: number;
  autor: string;
  cuerpo: string;
  creado_en: string;
}

/** Entrada del historial de cambios de estado */
export interface StateLog {
  id: number;
  mensaje: string;
  usuario_id: number | null;
  creado_en: string;
}

/** Ticket con detalle completo (comentarios e historial) */
export interface TicketDetail extends Ticket {
  comments: Comment[];
  state_log: StateLog[];
}

/** Página de resultados paginados */
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

/** Tipos de eventos WebSocket emitidos por el backend */
export type EventoTipo =
  | "ticket.creado"
  | "ticket.actualizado"
  | "ticket.comentado";

/** Evento WebSocket de ticket */
export interface TicketEvent {
  tipo: EventoTipo;
  datos: Ticket;
}

/**
 * Transiciones de estado válidas.
 * 
 * Espejo de la máquina de estados del backend para que
 * la UI solo ofrezca botones que tendrán éxito.
 */
export const TRANSICIONES_VALIDAS: Record<Estado, Estado[]> = {
  abierto: ["en_progreso"],
  en_progreso: ["resuelto"],
  resuelto: ["cerrado", "reabierto"],
  reabierto: ["en_progreso"],
  cerrado: [],
};

/** Lista de todos los estados posibles */
export const ESTADOS: Estado[] = [
  "abierto",
  "en_progreso",
  "resuelto",
  "reabierto",
  "cerrado",
];

/** Lista de todas las prioridades posibles */
export const PRIORIDADES: Prioridad[] = ["baja", "media", "alta", "urgente"];
