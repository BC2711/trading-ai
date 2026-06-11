import { Filter } from "lucide-react";

import type { AuditFilters as AuditFilterState, AuditScope } from "../../api/auditApi";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

type AuditFiltersProps = {
  value: AuditFilterState;
  modules: string[];
  actions: string[];
  statuses: string[];
  onChange: (value: AuditFilterState) => void;
};

export function AuditFilters({ value, modules, actions, statuses, onChange }: AuditFiltersProps) {
  const setValue = (changes: Partial<AuditFilterState>) => onChange({ ...value, ...changes });

  return (
    <Card className="p-4">
      <div className="grid gap-3 lg:grid-cols-6">
        <Select
          label="View"
          value={value.scope ?? "all"}
          options={[
            { label: "All audit", value: "all" },
            { label: "Trades", value: "trades" },
            { label: "Users", value: "users" },
            { label: "AI", value: "ai" },
            { label: "Risk", value: "risk" }
          ]}
          onChange={(event) => setValue({ scope: event.target.value as AuditScope })}
        />
        <Input label="Start date" type="date" value={value.start_date ?? ""} onChange={(event) => setValue({ start_date: event.target.value })} />
        <Input label="End date" type="date" value={value.end_date ?? ""} onChange={(event) => setValue({ end_date: event.target.value })} />
        <Input label="User" value={value.user ?? ""} placeholder="email or id" onChange={(event) => setValue({ user: event.target.value })} />
        <Select
          label="Module"
          value={value.module ?? ""}
          disabled={value.scope !== "all"}
          options={[{ label: "All modules", value: "" }, ...modules.map((module) => ({ label: humanize(module), value: module }))]}
          onChange={(event) => setValue({ module: event.target.value })}
        />
        <Select
          label="Status"
          value={value.status ?? ""}
          options={[{ label: "All statuses", value: "" }, ...statuses.map((status) => ({ label: humanize(status), value: status }))]}
          onChange={(event) => setValue({ status: event.target.value })}
        />
      </div>
      <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto]">
        <Select
          label="Action type"
          value={value.action_type ?? ""}
          options={[{ label: "All actions", value: "" }, ...actions.map((action) => ({ label: humanize(action), value: action }))]}
          onChange={(event) => setValue({ action_type: event.target.value })}
        />
        <div className="flex items-end">
          <Button
            variant="outline"
            icon={Filter}
            onClick={() => onChange({ scope: value.scope ?? "all", limit: value.limit ?? 100 })}
          >
            Reset filters
          </Button>
        </div>
      </div>
    </Card>
  );
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
