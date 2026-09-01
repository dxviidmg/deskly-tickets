/**
 * Constantes centralizadas para estados y prioridades.
 * 
 * Define:
 * - Listas de valores posibles (ESTADOS, PRIORIDADES)
 * - Etiquetas en español para mostrar en la UI
 * - Clases de Tailwind para colores de badges
 * 
 * Usar estas constantes en lugar de strings literales asegura
 * consistencia en toda la aplicación.
 */
import type { Estado, Prioridad } from "./types";

/** Lista de todos los estados posibles de un ticket */
export const ESTADOS: Estado[] = [
  "abierto",
  "en_progreso",
  "resuelto",
  "reabierto",
  "cerrado",
];

/** Lista de todos los niveles de prioridad */
export const PRIORIDADES: Prioridad[] = ["baja", "media", "alta", "urgente"];

/** Etiquetas en español para mostrar en la UI */
export const ESTADOS_LABELS: Record<Estado, string> = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  reabierto: "Reabierto",
  cerrado: "Cerrado",
};

/** Etiquetas en español para prioridades */
export const PRIORIDADES_LABELS: Record<Prioridad, string> = {
  baja: "Baja",
  media: "Media",
  alta: "Alta",
  urgente: "Urgente",
};

/** Clases de Tailwind para colorear badges de estado */
export const ESTADOS_COLORS: Record<Estado, string> = {
  abierto: "bg-slate-100 text-slate-700",
  en_progreso: "bg-blue-100 text-blue-700",
  resuelto: "bg-green-100 text-green-700",
  reabierto: "bg-orange-100 text-orange-700",
  cerrado: "bg-gray-100 text-gray-600",
};

/** Clases de Tailwind para colorear badges de prioridad */
export const PRIORIDADES_COLORS: Record<Prioridad, string> = {
  baja: "bg-green-100 text-green-700",
  media: "bg-yellow-100 text-yellow-700",
  alta: "bg-orange-100 text-orange-700",
  urgente: "bg-red-100 text-red-700",
};
