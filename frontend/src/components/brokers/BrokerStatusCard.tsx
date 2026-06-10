import { KeyRound, Link2, Unlink } from "lucide-react";

import type { BrokerStatus } from "../../api/brokerApi";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

export function BrokerStatusCard({
  broker,
  loading,
  onConnect,
  onDisconnect
}: {
  broker: BrokerStatus;
  loading?: boolean;
  onConnect: (broker: string) => void;
  onDisconnect: (broker: string) => void;
}) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="mb-3 inline-flex size-11 items-center justify-center rounded-[8px] bg-cyan-400/15 text-cyan-700 dark:text-cyan-100">
            <KeyRound size={20} aria-hidden />
          </div>
          <h2 className="text-lg font-black text-slate-950 dark:text-white">{broker.display_name}</h2>
          <p className="mt-1 text-sm font-medium text-slate-500 dark:text-white/50">{broker.message}</p>
        </div>
        <Badge tone={broker.connected ? "success" : "neutral"}>{broker.status}</Badge>
      </div>

      <div className="mt-4 grid gap-2 rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/5">
        <StatusLine label="API key" value={broker.api_key_configured ? "Configured" : "Missing"} tone={broker.api_key_configured ? "success" : "warning"} />
        <StatusLine label="Last sync" value={broker.last_sync_at ? formatDate(broker.last_sync_at) : "Never"} />
      </div>

      <div className="mt-4 flex gap-2">
        {broker.connected ? (
          <Button variant="outline" icon={Unlink} loading={loading} onClick={() => onDisconnect(broker.name)}>
            Disconnect
          </Button>
        ) : (
          <Button icon={Link2} loading={loading} disabled={!broker.api_key_configured && broker.name === "binance"} onClick={() => onConnect(broker.name)}>
            Connect
          </Button>
        )}
      </div>
    </Card>
  );
}

function StatusLine({ label, value, tone }: { label: string; value: string; tone?: "success" | "warning" }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs font-bold uppercase text-slate-500 dark:text-white/40">{label}</span>
      {tone ? <Badge tone={tone}>{value}</Badge> : <span className="text-xs font-semibold text-slate-600 dark:text-white/55">{value}</span>}
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Never";
  }
  return date.toLocaleString();
}
