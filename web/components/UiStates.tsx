// Distinct UI states: a skeleton for loading, an empty state and an error state.
// Deliberately different visuals (not the same spinner for everything).

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
