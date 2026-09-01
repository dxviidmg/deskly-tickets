import type { Estado, Prioridad } from "@/lib/types";

const ESTADO_STYLES: Record<Estado, string> = {
  abierto: "bg-blue-100 text-blue-800",
  en_progreso: "bg-amber-100 text-amber-800",
  resuelto: "bg-green-100 text-green-800",
  cerrado: "bg-slate-200 text-slate-700",
};

const ESTADO_LABEL: Record<Estado, string> = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  cerrado: "Cerrado",
};

const PRIORIDAD_STYLES: Record<Prioridad, string> = {
  baja: "bg-green-100 text-green-800",
  media: "bg-yellow-100 text-yellow-800",
  alta: "bg-orange-100 text-orange-800",
  urgente: "bg-red-100 text-red-800",
};

export function EstadoBadge({ estado }: { estado: Estado }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${ESTADO_STYLES[estado]}`}
    >
      {ESTADO_LABEL[estado]}
    </span>
  );
}

export function PrioridadBadge({ prioridad }: { prioridad: Prioridad }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${PRIORIDAD_STYLES[prioridad]}`}
    >
      {prioridad}
    </span>
  );
}
