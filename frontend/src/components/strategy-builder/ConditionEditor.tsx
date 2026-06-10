import { Trash2 } from "lucide-react";

import type { StrategyConditionInput, StrategyIndicator, StrategyOperator } from "../../api/strategyBuilderApi";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

const indicators: Array<{ label: string; value: StrategyIndicator }> = [
  { label: "RSI", value: "RSI" },
  { label: "MACD", value: "MACD" },
  { label: "EMA", value: "EMA" },
  { label: "SMA", value: "SMA" },
  { label: "Bollinger Bands", value: "BOLLINGER_BANDS" },
  { label: "ATR", value: "ATR" },
  { label: "Volume", value: "VOLUME" },
  { label: "Price change", value: "PRICE_CHANGE" }
];

const operators: Array<{ label: string; value: StrategyOperator }> = [
  { label: "<", value: "<" },
  { label: "<=", value: "<=" },
  { label: ">", value: ">" },
  { label: ">=", value: ">=" },
  { label: "=", value: "==" },
  { label: "!=", value: "!=" }
];

export function ConditionEditor({
  condition,
  index,
  onChange,
  onRemove
}: {
  condition: StrategyConditionInput;
  index: number;
  onChange: (condition: StrategyConditionInput) => void;
  onRemove: () => void;
}) {
  const targetMode = condition.compare_indicator ? "indicator" : "value";

  return (
    <div className="grid gap-3 rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/[0.04]">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-black uppercase text-slate-500 dark:text-white/45">
          {index === 0 ? "IF" : "AND"} condition {index + 1}
        </p>
        <Button variant="ghost" icon={Trash2} className="min-h-9 px-3" onClick={onRemove}>
          Remove
        </Button>
      </div>

      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_96px_96px_minmax(0,1fr)]">
        <Select
          label="Indicator"
          options={indicators}
          value={condition.indicator}
          onChange={(event) => onChange({ ...condition, indicator: event.target.value as StrategyIndicator })}
        />
        <Input
          label="Period"
          type="number"
          min="1"
          value={condition.period ?? ""}
          onChange={(event) => onChange({ ...condition, period: event.target.value ? Number(event.target.value) : null })}
        />
        <Select
          label="Operator"
          options={operators}
          value={condition.operator}
          onChange={(event) => onChange({ ...condition, operator: event.target.value as StrategyOperator })}
        />
        <Select
          label="Target"
          options={[
            { label: "Numeric value", value: "value" },
            { label: "Another indicator", value: "indicator" }
          ]}
          value={targetMode}
          onChange={(event) =>
            onChange({
              ...condition,
              value: event.target.value === "value" ? condition.value ?? 30 : null,
              compare_indicator: event.target.value === "indicator" ? condition.compare_indicator ?? "EMA" : null,
              compare_period: event.target.value === "indicator" ? condition.compare_period ?? 50 : null
            })
          }
        />
      </div>

      {targetMode === "indicator" ? (
        <div className="grid gap-3 md:grid-cols-2">
          <Select
            label="Compare indicator"
            options={indicators}
            value={condition.compare_indicator ?? "EMA"}
            onChange={(event) => onChange({ ...condition, compare_indicator: event.target.value as StrategyIndicator })}
          />
          <Input
            label="Compare period"
            type="number"
            min="1"
            value={condition.compare_period ?? ""}
            onChange={(event) => onChange({ ...condition, compare_period: event.target.value ? Number(event.target.value) : null })}
          />
        </div>
      ) : (
        <Input
          label="Value"
          type="number"
          step="0.0001"
          value={condition.value ?? ""}
          onChange={(event) => onChange({ ...condition, value: event.target.value ? Number(event.target.value) : null })}
        />
      )}
    </div>
  );
}
