import { AlertTriangle, CheckCircle2, Info } from "lucide-react";

import type { AuditLog } from "../../api/auditApi";
import { DataTable } from "../table/DataTable";
import { Badge } from "../ui/Badge";
import type { BadgeTone } from "../ui/Badge";

type AuditRow = {
  id: string;
  action: string;
  user: string;
  module: string;
  ip: string;
  dateTime: string;
  status: string;
  details: string;
  raw: AuditLog;
};

type AuditTableProps = {
  logs: AuditLog[];
  loading?: boolean;
};

export function AuditTable({ logs, loading }: AuditTableProps) {
  const rows = logs.map((log) => ({
    id: String(log.id),
    action: humanize(log.action || log.event_type),
    user: log.user ?? "anonymous",
    module: humanize(log.module || log.entity_type),
    ip: log.ip_address ?? "unavailable",
    dateTime: formatDateTime(log.created_at),
    status: log.status || log.severity,
    details: summarizeDetails(log),
    raw: log
  }));

  return (
    <DataTable
      title="Compliance Audit Logs"
      description={`${logs.length} matching records`}
      loading={loading}
      rows={rows}
      pageSize={10}
      emptyTitle="No audit logs"
      emptyMessage="No compliance events match the selected filters."
      columns={[
        { key: "action", label: "Action" },
        { key: "user", label: "User" },
        { key: "module", label: "Module", render: (row) => <Badge tone="neutral">{row.module}</Badge> },
        { key: "ip", label: "IP address" },
        { key: "dateTime", label: "Date/time" },
        { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
        { key: "details", label: "Metadata/details", render: (row) => <span title={JSON.stringify(row.raw.details || row.raw.metadata)}>{row.details}</span> }
      ]}
    />
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const Icon = normalized === "success" ? CheckCircle2 : normalized === "failed" || normalized === "rejected" || normalized === "error" ? AlertTriangle : Info;
  const tone: BadgeTone = normalized === "success" ? "success" : normalized === "failed" || normalized === "rejected" || normalized === "error" ? "error" : normalized === "warning" ? "warning" : "info";
  return (
    <Badge tone={tone}>
      <Icon size={12} aria-hidden />
      {humanize(status)}
    </Badge>
  );
}

function summarizeDetails(log: AuditLog) {
  const source = Object.keys(log.details ?? {}).length ? log.details : log.metadata;
  const entries = Object.entries(source).filter(([key]) => !["details", "user", "user_name", "ip_address"].includes(key));
  if (!entries.length) {
    return log.message;
  }
  return entries
    .slice(0, 3)
    .map(([key, value]) => `${humanize(key)}: ${formatValue(value)}`)
    .join(" | ");
}

function formatValue(value: unknown) {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
