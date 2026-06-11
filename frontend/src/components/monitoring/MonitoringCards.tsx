import type { LucideIcon } from "lucide-react";
import { CheckCircle2, CircleAlert, CircleHelp, XCircle } from "lucide-react";

import type { ComponentStatus, QueueStatus, WebSocketStatus, WorkerStatus } from "../../api/monitoringApi";
import { Badge } from "../ui/Badge";
import type { BadgeTone } from "../ui/Badge";
import { Card } from "../ui/Card";

export function StatusCard({
  title,
  status,
  icon: Icon
}: {
  title: string;
  status: ComponentStatus;
  icon: LucideIcon;
}) {
  const tone = statusTone(status);
  const StatusIcon = statusIcon(status);
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="mb-3 inline-grid size-11 place-items-center rounded-[8px] bg-cyan-400/15 text-cyan-700 dark:text-cyan-100">
            <Icon size={20} aria-hidden />
          </div>
          <h2 className="text-base font-black text-slate-950 dark:text-white">{title}</h2>
          <p className="mt-1 line-clamp-2 text-sm font-medium text-slate-500 dark:text-white/50">{status.message}</p>
        </div>
        <Badge tone={tone}>
          <StatusIcon size={13} aria-hidden />
          {status.status}
        </Badge>
      </div>
      <div className="mt-4 grid gap-2 rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/5">
        <StatusLine label="Latency" value={formatLatency(status.latency_ms)} />
        <StatusLine label="Checked" value={formatTime(status.last_checked_at)} />
      </div>
    </Card>
  );
}

export function WebSocketStatusCard({ websocket }: { websocket: WebSocketStatus }) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-black text-slate-950 dark:text-white">WebSocket Status</h2>
          <p className="mt-1 text-sm font-medium text-slate-500 dark:text-white/50">
            {websocket.total_connections} active connection{websocket.total_connections === 1 ? "" : "s"}
          </p>
        </div>
        <Badge tone={websocket.healthy ? "success" : "error"}>{websocket.status}</Badge>
      </div>
      <div className="mt-4 grid gap-2">
        {Object.entries(websocket.streams).length ? (
          Object.entries(websocket.streams).map(([stream, count]) => (
            <StatusLine key={stream} label={stream.replace("market_data:", "market ")} value={String(count)} />
          ))
        ) : (
          <StatusLine label="Streams" value="No active streams" />
        )}
      </div>
    </Card>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  tone = "neutral"
}: {
  label: string;
  value: string;
  detail?: string;
  tone?: BadgeTone;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-bold uppercase text-slate-500 dark:text-white/40">{label}</span>
        <Badge tone={tone}>{detail ?? "live"}</Badge>
      </div>
      <p className="mt-3 text-2xl font-black text-slate-950 dark:text-white">{value}</p>
    </Card>
  );
}

export function QueueStatusPanel({ queues, workers }: { queues: QueueStatus[]; workers: WorkerStatus[] }) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-black text-slate-950 dark:text-white">Worker Queue Status</h2>
          <p className="mt-1 text-sm font-medium text-slate-500 dark:text-white/50">
            {workers.length} worker{workers.length === 1 ? "" : "s"} reporting queue activity
          </p>
        </div>
        <Badge tone={workers.length ? "success" : "warning"}>{workers.length ? "online" : "offline"}</Badge>
      </div>

      <div className="mt-4 overflow-hidden rounded-[8px] border border-white/10">
        <div className="grid grid-cols-[1fr_110px_120px] bg-white/10 px-3 py-2 text-xs font-bold uppercase text-slate-500 dark:bg-white/5 dark:text-white/40">
          <span>Queue</span>
          <span>Depth</span>
          <span>Status</span>
        </div>
        {(queues.length ? queues : [{ name: "celery", depth: null, status: "unknown", message: "Queue status unavailable." }]).map((queue) => (
          <div key={queue.name} className="grid grid-cols-[1fr_110px_120px] items-center gap-2 border-t border-white/10 px-3 py-3 text-sm">
            <span className="min-w-0 truncate font-bold text-slate-800 dark:text-white/80">{queue.name}</span>
            <span className="font-semibold text-slate-600 dark:text-white/55">{queue.depth ?? "n/a"}</span>
            <Badge tone={queue.status === "ok" ? "success" : "warning"}>{queue.status}</Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}

function StatusLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs font-bold uppercase text-slate-500 dark:text-white/40">{label}</span>
      <span className="min-w-0 truncate text-right text-xs font-semibold text-slate-700 dark:text-white/60">{value}</span>
    </div>
  );
}

function statusTone(status: ComponentStatus): BadgeTone {
  if (status.healthy) return "success";
  if (status.status === "degraded" || status.status === "unknown") return "warning";
  return "error";
}

function statusIcon(status: ComponentStatus) {
  if (status.healthy) return CheckCircle2;
  if (status.status === "degraded") return CircleAlert;
  if (status.status === "unknown") return CircleHelp;
  return XCircle;
}

function formatLatency(value: number | null) {
  return typeof value === "number" ? `${value.toFixed(1)} ms` : "n/a";
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "n/a";
  return date.toLocaleTimeString();
}
