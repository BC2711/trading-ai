import { apiClient } from "../services/api";

export type AuditStatus = "success" | "failed" | "rejected" | "info" | "warning" | "error";
export type AuditScope = "all" | "trades" | "users" | "ai" | "risk";

export type AuditLog = {
  id: number;
  event_type: string;
  entity_type: string;
  entity_id: number | null;
  severity: "info" | "warning" | "error";
  message: string;
  metadata: Record<string, unknown>;
  action: string;
  user: string | null;
  module: string;
  ip_address: string | null;
  status: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type AuditFilters = {
  scope?: AuditScope;
  limit?: number;
  start_date?: string;
  end_date?: string;
  user?: string;
  module?: string;
  action_type?: string;
  status?: string;
};

const scopePath: Record<AuditScope, string> = {
  all: "/api/audit",
  trades: "/api/audit/trades",
  users: "/api/audit/users",
  ai: "/api/audit/ai",
  risk: "/api/audit/risk"
};

export async function fetchAuditLogs(filters: AuditFilters = {}): Promise<AuditLog[]> {
  const scope = filters.scope ?? "all";
  const params = {
    limit: filters.limit ?? 100,
    start_date: dateStart(filters.start_date),
    end_date: dateEnd(filters.end_date),
    user: filters.user || undefined,
    module: scope === "all" ? filters.module || undefined : undefined,
    action_type: filters.action_type || undefined,
    status: filters.status || undefined
  };
  const response = await apiClient.get<AuditLog[]>(scopePath[scope], { params });
  return response.data;
}

function dateStart(value?: string) {
  return value ? `${value}T00:00:00` : undefined;
}

function dateEnd(value?: string) {
  return value ? `${value}T23:59:59` : undefined;
}
