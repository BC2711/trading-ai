import { Filter } from "lucide-react";

import type { ScannerFilters as ScannerFilterState } from "../../api/scannerApi";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

type ScannerFiltersProps = {
  filters: ScannerFilterState;
  onChange: (filters: ScannerFilterState) => void;
  onReset: () => void;
};

export function ScannerFilters({ filters, onChange, onReset }: ScannerFiltersProps) {
  const confidence = filters.min_confidence ?? 0;

  return (
    <Card className="p-4 sm:p-5">
      <div className="grid gap-4 lg:grid-cols-[minmax(180px,1fr)_160px_180px_160px_auto] lg:items-end">
        <Input
          label="Symbol"
          placeholder="BTCUSDT"
          value={filters.symbol ?? ""}
          onChange={(event) => onChange({ ...filters, symbol: event.target.value.toUpperCase() })}
        />
        <Select
          label="Signal"
          value={filters.signal ?? ""}
          onChange={(event) => onChange({ ...filters, signal: event.target.value as ScannerFilterState["signal"] })}
          options={[
            { label: "All signals", value: "" },
            { label: "Buy", value: "buy" },
            { label: "Sell", value: "sell" },
            { label: "Hold", value: "hold" }
          ]}
        />
        <label className="grid gap-1.5">
          <span className="text-xs font-bold uppercase tracking-normal text-slate-500 dark:text-white/50">
            Confidence {Math.round(confidence * 100)}%
          </span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={confidence}
            onChange={(event) => onChange({ ...filters, min_confidence: Number(event.target.value) })}
            className="h-11 w-full accent-cyan-500"
          />
        </label>
        <Select
          label="Risk"
          value={filters.risk_level ?? ""}
          onChange={(event) => onChange({ ...filters, risk_level: event.target.value as ScannerFilterState["risk_level"] })}
          options={[
            { label: "All risk", value: "" },
            { label: "Low", value: "low" },
            { label: "Medium", value: "medium" },
            { label: "High", value: "high" }
          ]}
        />
        <Button variant="outline" icon={Filter} onClick={onReset} className="min-h-11">
          Reset
        </Button>
      </div>
    </Card>
  );
}
