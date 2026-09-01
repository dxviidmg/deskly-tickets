"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-md py-12 text-center">
      <h2 className="mb-4 text-lg font-semibold text-slate-800">
        Algo salió mal
      </h2>
      <p className="mb-6 text-sm text-slate-600">{error.message}</p>
      <button
        onClick={reset}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
      >
        Reintentar
      </button>
    </div>
  );
}
