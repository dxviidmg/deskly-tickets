import type { ConnectionStatus } from "@/hooks/useTicketStream";

const STYLES: Record<ConnectionStatus, { dot: string; label: string }> = {
  conectando: { dot: "bg-amber-400", label: "Conectando…" },
  conectado: { dot: "bg-green-500", label: "En vivo" },
  desconectado: { dot: "bg-red-500", label: "Desconectado" },
};

export function ConnectionIndicator({ status }: { status: ConnectionStatus }) {
  const s = STYLES[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs text-slate-600"
      title={`WebSocket: ${s.label}`}
    >
      <span className={`h-2.5 w-2.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}
