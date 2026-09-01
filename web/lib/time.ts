// Human-friendly relative time in Spanish (e.g. "hace un minuto",
// "hace 3 horas", "hace un día", "hace una semana", "hace un mes",
// "hace un año"). Used for ticket/comment timestamps.

interface Unidad {
  segundos: number;
  singular: string; // "hace un/una <unidad>"
  articulo: "un" | "una";
  plural: string; // "hace N <unidad>s"
}

// Ordered from largest to smallest so we pick the coarsest fitting unit.
const UNIDADES: Unidad[] = [
  { segundos: 31536000, singular: "año", articulo: "un", plural: "años" },
  { segundos: 2592000, singular: "mes", articulo: "un", plural: "meses" },
  { segundos: 604800, singular: "semana", articulo: "una", plural: "semanas" },
  { segundos: 86400, singular: "día", articulo: "un", plural: "días" },
  { segundos: 3600, singular: "hora", articulo: "una", plural: "horas" },
  { segundos: 60, singular: "minuto", articulo: "un", plural: "minutos" },
];

/**
 * Returns a relative time string in Spanish for an ISO date, relative to now.
 * Future dates and anything under a minute render as "hace un momento".
 */
export function tiempoRelativo(iso: string, ahora: Date = new Date()): string {
  const fecha = new Date(iso);
  const segundos = Math.floor((ahora.getTime() - fecha.getTime()) / 1000);

  if (!Number.isFinite(segundos) || segundos < 60) {
    return "hace un momento";
  }

  for (const u of UNIDADES) {
    if (segundos >= u.segundos) {
      const cantidad = Math.floor(segundos / u.segundos);
      return cantidad === 1
        ? `hace ${u.articulo} ${u.singular}`
        : `hace ${cantidad} ${u.plural}`;
    }
  }

  return "hace un momento";
}
