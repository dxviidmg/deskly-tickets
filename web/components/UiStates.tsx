/**
 * Componentes para estados visuales de la UI.
 * 
 * Incluye:
 * - TableSkeleton: Placeholder animado durante la carga de tablas
 * - EmptyState: Estado vacío cuando no hay datos
 * - ErrorState: Estado de error con opción de reintentar
 * 
 * Cada estado tiene un diseño visual distintivo para que el usuario
 * pueda identificar rápidamente qué está pasando.
 */

/**
 * Skeleton animado para tablas.
 * Muestra un placeholder visual mientras cargan los datos.
 */
export function TableSkeleton() {
  return (
    <div className="animate-pulse space-y-2" aria-label="Cargando tickets">
      <div className="h-10 rounded bg-slate-200" />
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-12 rounded bg-slate-100" />
      ))}
    </div>
  );
}

/**
 * Estado vacío cuando no hay datos que mostrar.
 * 
 * @param mensaje - Texto principal que describe qué no hay
 */
export function EmptyState({ mensaje }: { mensaje: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white py-16 text-center">
      <div className="text-4xl">📭</div>
      <p className="mt-2 font-medium text-slate-700">{mensaje}</p>
      <p className="text-sm text-slate-500">
        No hay nada que mostrar por ahora.
      </p>
    </div>
  );
}

/**
 * Estado de error con opción de reintentar.
 * 
 * @param mensaje - Descripción del error ocurrido
 * @param onReintentar - Callback para el botón de reintentar (opcional)
 */
export function ErrorState({
  mensaje,
  onReintentar,
}: {
  mensaje: string;
  onReintentar?: () => void;
}) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 py-12 text-center">
      <div className="text-4xl">⚠️</div>
      <p className="mt-2 font-medium text-red-800">Ocurrió un error</p>
      <p className="text-sm text-red-600">{mensaje}</p>
      {onReintentar && (
        <button
          onClick={onReintentar}
          className="mt-4 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          Reintentar
        </button>
      )}
    </div>
  );
}
