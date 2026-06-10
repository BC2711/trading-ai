import { Plus } from "lucide-react";

import type { StrategyAction, StrategyConditionInput, StrategyRuleInput } from "../../api/strategyBuilderApi";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { ConditionEditor } from "./ConditionEditor";

const actions: Array<{ label: string; value: StrategyAction }> = [
  { label: "Buy", value: "BUY" },
  { label: "Sell", value: "SELL" },
  { label: "Hold", value: "HOLD" },
  { label: "Close position", value: "CLOSE_POSITION" }
];

export function RuleEditor({
  rule,
  onChange
}: {
  rule: StrategyRuleInput;
  onChange: (rule: StrategyRuleInput) => void;
}) {
  const updateCondition = (index: number, condition: StrategyConditionInput) => {
    onChange({
      ...rule,
      conditions: rule.conditions.map((item, itemIndex) => itemIndex === index ? { ...condition, sequence: index + 1 } : item)
    });
  };

  const removeCondition = (index: number) => {
    if (rule.conditions.length <= 1) {
      return;
    }
    onChange({
      ...rule,
      conditions: rule.conditions.filter((_, itemIndex) => itemIndex !== index).map((condition, itemIndex) => ({ ...condition, sequence: itemIndex + 1 }))
    });
  };

  return (
    <div className="grid gap-4">
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_120px_180px]">
        <Input label="Rule name" value={rule.name} onChange={(event) => onChange({ ...rule, name: event.target.value })} />
        <Input label="Priority" type="number" min="1" value={rule.priority} onChange={(event) => onChange({ ...rule, priority: Number(event.target.value) || 1 })} />
        <Select
          label="THEN action"
          options={actions}
          value={rule.action.action}
          onChange={(event) => onChange({ ...rule, action: { ...rule.action, action: event.target.value as StrategyAction } })}
        />
      </div>

      <div className="grid gap-3">
        {rule.conditions.map((condition, index) => (
          <ConditionEditor
            key={`${condition.sequence}-${index}`}
            condition={condition}
            index={index}
            onChange={(nextCondition) => updateCondition(index, nextCondition)}
            onRemove={() => removeCondition(index)}
          />
        ))}
      </div>

      <div>
        <Button
          variant="outline"
          icon={Plus}
          onClick={() =>
            onChange({
              ...rule,
              conditions: [
                ...rule.conditions,
                {
                  sequence: rule.conditions.length + 1,
                  indicator: "EMA",
                  period: 20,
                  operator: ">",
                  value: null,
                  compare_indicator: "EMA",
                  compare_period: 50,
                  parameters: {}
                }
              ]
            })
          }
        >
          Add condition
        </Button>
      </div>
    </div>
  );
}
