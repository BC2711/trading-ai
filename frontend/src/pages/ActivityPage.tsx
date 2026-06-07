import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, CheckCircle2, Clock3, Info, Search } from "lucide-react";
import { useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";
import { Select } from "../components/ui/Select";
import { fetchAuditEvents } from "../services/api";
import type { AuditEvent } from "../services/api";
import { cn } from "../utils/cn";

type SeverityFilter = "all" | "info" | "warning" | "error";

export function ActivityPage() {
  const [severity, setSeverity] = useState<SeverityFilter>("all");
  const [entityType, setEntityType] = useState("all");

  const eventsQuery = useQuery({
    queryKey: ["audit-events", severity, entityType],
    queryFn: () =>
      fetchAuditEvents({
        limit: 80,
        severity: severity === "all" ? undefined : severity,
        entity_type: entityType === "all" ? undefined : entityType
      })
  });

  const events = eventsQuery.data ?? [];
  const entityTypes = Array.from(new Set(events.map((event) => event.entity_type))).sort();

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Activity size={14} aria-hidden />
              Audit trail
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Activity timeline</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Review AI analyses, backtests, paper order decisions, position lifecycle events, and settings changes in one traceable timeline.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Select
              aria-label="Severity"
              options={[
                { label: "All severities", value: "all" },
                { label: "Info", value: "info" },
                { label: "Warning", value: "warning" },
                { label: "Error", value: "error" }
              ]}
              value={severity}
              onChange={(event) => setSeverity(event.target.value as SeverityFilter)}
            />
            <Select
              aria-label="Entity type"
              options={[
                { label: "All entities", value: "all" },
                ...entityTypes.map((type) => ({ label: humanize(type), value: type }))
              ]}
              value={entityType}
              onChange={(event) => setEntityType(event.target.value)}
            />
          </div>
        </div>
      </Card>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px] xl:gap-6">
        <Card className="p-0">
          <div className="flex items-center justify-between border-b border-white/10 p-4">
            <div>
              <h2 className="text-base font-black text-slate-950 dark:text-white">Events</h2>
              <p className="text-xs font-medium text-slate-500 dark:text-white/50">{events.length} matching audit records</p>
            </div>
            <Clock3 size={18} className="text-slate-400 dark:text-white/40" aria-hidden />
          </div>

          <div className="grid gap-0">
            {eventsQuery.isLoading ? (
              Array.from({ length: 6 }).map((_, index) => (
                <div key={index} className="border-b border-white/10 p-4">
                  <Skeleton className="h-16 w-full" />
                </div>
              ))
            ) : events.length ? (
              events.map((event) => <AuditEventRow key={event.id} event={event} />)
            ) : (
              <div className="grid min-h-[260px] place-items-center p-8 text-center">
                <div>
                  <Search className="mx-auto mb-3 text-slate-400 dark:text-white/35" size={28} aria-hidden />
                  <p className="text-sm font-bold text-slate-600 dark:text-white/60">No audit events match these filters.</p>
                </div>
              </div>
            )}
          </div>
        </Card>

        <Card className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Event Mix</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">Current filter distribution</p>
            </div>
            <Activity size={18} className="text-slate-400 dark:text-white/40" aria-hidden />
          </div>
          <div className="mt-5 grid gap-3">
            {[
              ["Info", events.filter((event) => event.severity === "info").length, "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100"],
              ["Warnings", events.filter((event) => event.severity === "warning").length, "bg-amber-400/15 text-amber-700 dark:text-amber-100"],
              ["Errors", events.filter((event) => event.severity === "error").length, "bg-rose-400/15 text-rose-700 dark:text-rose-100"],
              ["Entities", entityTypes.length, "bg-violet-400/15 text-violet-700 dark:text-violet-100"]
            ].map(([label, value, tone]) => (
              <div key={label} className="flex items-center justify-between rounded-[8px] border border-white/10 bg-white/10 p-3 backdrop-blur-md dark:bg-white/5">
                <span className="text-sm font-semibold text-slate-600 dark:text-white/55">{label}</span>
                <Badge className={String(tone)}>{value}</Badge>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </div>
  );
}

function AuditEventRow({ event }: { event: AuditEvent }) {
  const Icon = event.severity === "warning" ? AlertTriangle : event.severity === "error" ? AlertTriangle : event.event_type.includes("completed") || event.event_type.includes("filled") ? CheckCircle2 : Info;

  return (
    <div className="grid gap-3 border-b border-white/10 p-4 transition hover:bg-white/10 dark:hover:bg-white/5 sm:grid-cols-[44px_1fr_auto]">
      <span
        className={cn(
          "grid size-11 place-items-center rounded-[8px] border border-white/10",
          event.severity === "info" && "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100",
          event.severity === "warning" && "bg-amber-400/15 text-amber-700 dark:text-amber-100",
          event.severity === "error" && "bg-rose-400/15 text-rose-700 dark:text-rose-100"
        )}
      >
        <Icon size={18} aria-hidden />
      </span>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={event.severity === "warning" ? "warning" : event.severity === "error" ? "error" : "info"}>{event.severity}</Badge>
          <Badge tone="neutral">{humanize(event.entity_type)}</Badge>
          <span className="text-xs font-bold text-slate-400 dark:text-white/35">{event.event_type}</span>
        </div>
        <p className="mt-2 text-sm font-semibold leading-6 text-slate-800 dark:text-white/75">{event.message}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {Object.entries(event.metadata).slice(0, 5).map(([key, value]) => (
            <span key={key} className="rounded-[8px] bg-white/10 px-2 py-1 text-[11px] font-bold text-slate-500 dark:text-white/45">
              {humanize(key)}: {String(value)}
            </span>
          ))}
        </div>
      </div>

      <div className="text-left sm:text-right">
        <p className="text-xs font-bold text-slate-400 dark:text-white/40">{formatRelativeTime(event.created_at)}</p>
        {event.entity_id ? <p className="mt-1 text-[11px] font-semibold text-slate-400 dark:text-white/30">#{event.entity_id}</p> : null}
      </div>
    </div>
  );
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatRelativeTime(value: string) {
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return "Just now";
  }

  const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (seconds < 60) {
    return `${seconds}s ago`;
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }

  return `${Math.floor(hours / 24)}d ago`;
}
