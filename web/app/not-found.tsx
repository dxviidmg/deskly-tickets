import Link from "next/link";

export default function NotFound() {
  return (
    <div className="rounded-lg border bg-white py-16 text-center">
      <div className="text-4xl">🔍</div>
      <p className="mt-2 font-medium text-slate-700">Ticket no encontrado</p>
      <Link
        href="/"
        className="mt-4 inline-block text-sm text-blue-700 hover:underline"
      >
        ← Volver al listado
      </Link>
    </div>
  );
}
