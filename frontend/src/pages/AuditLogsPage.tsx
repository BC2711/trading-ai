import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, CheckCircle2, FileSearch } from "lucide-react";
import { useMemo, useState } from "react";

import type { AuditFilters as AuditFilterState } from "../api/auditApi";
import { fetchAuditLogs } from "../api/auditApi";
import { AuditFilters, AuditTable } from "../components/audit";
import { Alert } from "../components/ui/Alert";
import { Card } from "../components/ui/Card";

const defaultFilters: AuditFilterState = {
  scope: "all",
  limit: 100
};

export function AuditLogsPage() {
  const [filters, setFilters] = useState<AuditFilterState>(defaultFilters);
  const auditQuery = useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: () => fetchAuditLogs(filters)
  });

  const logs = auditQuery.data ?? [];
  const modules = useMemo(() => unique(logs.map((log) => log.module || log.entity_type)), [logs]);
  const actions = useMemo(() => unique(logs.map((log) => log.action || log.event_type)), [logs]);
  const statuses = useMemo(() => unique(logs.map((log) => log.status || log.severity)), [logs]);
  const successCount = logs.filter((log) => log.status === "success").length;
  const issueCount = logs.filter((log) => ["failed", "rejected", "error"].includes(log.status)).length;

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <FileSearch size={14} aria-hidden />
              Compliance center
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Audit Logs</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Review authentication, administration, trading, risk, strategy, and AI actions with user, IP, status, and metadata context.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <AuditMetric icon={Activity} label="Records" value={String(logs.length)} />
            <AuditMetric icon={CheckCircle2} label="Success" value={String(successCount)} />
            <AuditMetric icon={AlertTriangle} label="Issues" value={String(issueCount)} />
          </div>
        </div>
      </Card>

      {auditQuery.isError ? <Alert tone="error">Unable to load audit logs.</Alert> : null}
      <AuditFilters value={filters} modules={modules} actions={actions} statuses={statuses} onChange={setFilters} />
      <AuditTable logs={logs} loading={auditQuery.isLoading} />
    </div>
  );
}

function AuditMetric({ icon: Icon, label, value }: { icon: typeof Activity; label: string; value: string }) {
  return (
    <div className="min-w-[148px] rounded-[8px] border border-white/10 bg-white/10 p-3 text-right backdrop-blur-md dark:bg-white/5">
      <div className="mb-2 flex justify-end">
        <Icon size={16} className="text-cyan-600 dark:text-cyan-200" aria-hidden />
      </div>
      <span className="block text-xs font-bold uppercase text-slate-500 dark:text-white/40">{label}</span>
      <span className="text-2xl font-black text-slate-950 dark:text-white">{value}</span>
    </div>
  );
}

function unique(values: string[]) {
  return Array.from(new Set(values.filter(Boolean))).sort();
}
