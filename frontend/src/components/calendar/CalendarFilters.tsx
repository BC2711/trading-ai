import { Filter } from "lucide-react";

import type { CalendarFilters as CalendarFilterState } from "../../api/calendarApi";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

type CalendarFiltersProps = {
  filters: CalendarFilterState;
  onChange: (filters: CalendarFilterState) => void;
  onReset: () => void;
};

export function CalendarFilters({ filters, onChange, onReset }: CalendarFiltersProps) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="grid gap-4 lg:grid-cols-[1fr_160px_1fr_180px_180px_auto] lg:items-end">
        <Input
          label="Country"
          placeholder="United States"
          value={filters.country ?? ""}
          onChange={(event) => onChange({ ...filters, country: event.target.value })}
        />
        <Select
          label="Impact"
          value={filters.impact_level ?? ""}
          onChange={(event) => onChange({ ...filters, impact_level: event.target.value as CalendarFilterState["impact_level"] })}
          options={[
            { label: "All impact", value: "" },
            { label: "High", value: "high" },
            { label: "Medium", value: "medium" },
            { label: "Low", value: "low" }
          ]}
        />
        <Input
          label="Asset"
          placeholder="BTCUSDT"
          value={filters.asset ?? ""}
          onChange={(event) => onChange({ ...filters, asset: event.target.value.toUpperCase() })}
        />
        <Input
          label="Start"
          type="datetime-local"
          value={filters.start ?? ""}
          onChange={(event) => onChange({ ...filters, start: event.target.value })}
        />
        <Input
          label="End"
          type="datetime-local"
          value={filters.end ?? ""}
          onChange={(event) => onChange({ ...filters, end: event.target.value })}
        />
        <Button variant="outline" icon={Filter} onClick={onReset} className="min-h-11">
          Reset
        </Button>
      </div>
    </Card>
  );
}
