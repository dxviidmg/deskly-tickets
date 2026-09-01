import type { Estado, Prioridad } from "./types";

export const ESTADOS: Estado[] = [
  "abierto",
  "en_progreso",
  "resuelto",
  "reabierto",
  "cerrado",
];

export const PRIORIDADES: Prioridad[] = ["baja", "media", "alta", "urgente"];

export const ESTADOS_LABELS: Record<Estado, string> = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  reabierto: "Reabierto",
  cerrado: "Cerrado",
};

export const PRIORIDADES_LABELS: Record<Prioridad, string> = {
  baja: "Baja",
  media: "Media",
  alta: "Alta",
  urgente: "Urgente",
};

export const ESTADOS_COLORS: Record<Estado, string> = {
  abierto: "bg-slate-100 text-slate-700",
  en_progreso: "bg-blue-100 text-blue-700",
  resuelto: "bg-green-100 text-green-700",
  reabierto: "bg-orange-100 text-orange-700",
  cerrado: "bg-gray-100 text-gray-600",
};

export const PRIORIDADES_COLORS: Record<Prioridad, string> = {
  baja: "bg-green-100 text-green-700",
  media: "bg-yellow-100 text-yellow-700",
  alta: "bg-orange-100 text-orange-700",
  urgente: "bg-red-100 text-red-700",
};
