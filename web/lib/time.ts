/**
 * Tiempo relativo en español (ej: "hace un minuto", "hace 3 horas").
 * 
 * Usado para mostrar timestamps de tickets y comentarios
 * de forma más legible para el usuario.
 */

interface Unidad {
  segundos: number;
  singular: string;
  articulo: "un" | "una";
  plural: string;
}

// Ordenadas de mayor a menor para elegir la unidad más apropiada
const UNIDADES: Unidad[] = [
  { segundos: 31536000, singular: "año", articulo: "un", plural: "años" },
  { segundos: 2592000, singular: "mes", articulo: "un", plural: "meses" },
  { segundos: 604800, singular: "semana", articulo: "una", plural: "semanas" },
  { segundos: 86400, singular: "día", articulo: "un", plural: "días" },
  { segundos: 3600, singular: "hora", articulo: "una", plural: "horas" },
  { segundos: 60, singular: "minuto", articulo: "un", plural: "minutos" },
];

/**
 * Devuelve el tiempo relativo en español para una fecha ISO.
 * 
 * Fechas futuras y menos de un minuto se muestran como "hace un momento".
 * 
 * @param iso - Fecha en formato ISO string
 * @param ahora - Fecha de referencia (por defecto, ahora)
 * @returns Texto como "hace un momento", "hace 5 minutos", "hace 2 días"
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
