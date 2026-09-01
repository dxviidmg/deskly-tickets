/**
 * Badges visuales para Estado y Prioridad de tickets.
 * 
 * Muestran etiquetas con colores distintivos que permiten
 * identificar rápidamente el estado y prioridad de un ticket.
 */

import type { Estado, Prioridad } from "@/lib/types";

/** Colores de fondo y texto para cada estado */
const ESTADO_STYLES: Record<Estado, string> = {
  abierto: "bg-blue-100 text-blue-800",
  en_progreso: "bg-amber-100 text-amber-800",
  resuelto: "bg-green-100 text-green-800",
  reabierto: "bg-orange-100 text-orange-800",
  cerrado: "bg-slate-200 text-slate-700",
};

/** Labels en español para cada estado */
const ESTADO_LABEL: Record<Estado, string> = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  reabierto: "Reabierto",
  cerrado: "Cerrado",
};

/** Colores de fondo y texto para cada prioridad */
const PRIORIDAD_STYLES: Record<Prioridad, string> = {
  baja: "bg-green-100 text-green-800",
  media: "bg-yellow-100 text-yellow-800",
  alta: "bg-orange-100 text-orange-800",
  urgente: "bg-red-100 text-red-800",
};

/**
 * Badge que muestra el estado de un ticket.
 * 
 * @param estado - Estado del ticket (abierto, en_progreso, resuelto, reabierto, cerrado)
 */
export function EstadoBadge({ estado }: { estado: Estado }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${ESTADO_STYLES[estado]}`}
    >
      {ESTADO_LABEL[estado]}
    </span>
  );
}

/**
 * Badge que muestra la prioridad de un ticket.
 * 
 * @param prioridad - Prioridad del ticket (baja, media, alta, urgente)
 */
export function PrioridadBadge({ prioridad }: { prioridad: Prioridad }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${PRIORIDAD_STYLES[prioridad]}`}
    >
      {prioridad}
    </span>
  );
}
