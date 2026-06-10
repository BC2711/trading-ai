import { CheckCircle2, CircleDashed, XCircle } from "lucide-react";

import type { StrategyEvaluationResponse } from "../../api/strategyBuilderApi";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";

export function EvaluationPanel({ result }: { result?: StrategyEvaluationResponse }) {
  if (!result) {
    return (
      <Card className="p-5">
        <h2 className="text-lg font-black text-slate-950 dark:text-white">Test Result</h2>
        <div className="mt-8 grid place-items-center rounded-[8px] border border-dashed border-white/20 p-8 text-center text-sm font-semibold text-slate-500 dark:text-white/45">
          Run a strategy test to see indicator values and matched rules.
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-black text-slate-950 dark:text-white">Test Result</h2>
          <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-white/50">{result.message}</p>
        </div>
        <Badge tone={result.action === "BUY" ? "success" : result.action === "SELL" ? "error" : "info"}>
          {result.action}
        </Badge>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {Object.entries(result.indicators).map(([label, value]) => (
          <div key={label} className="rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/[0.04]">
            <p className="text-xs font-bold text-slate-500 dark:text-white/45">{label}</p>
            <p className="mt-1 text-base font-black text-slate-950 dark:text-white">{formatNumber(value)}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-3">
        {result.evaluations.map((rule) => (
          <div key={rule.rule_id} className="rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/[0.04]">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                {rule.triggered ? <CheckCircle2 size={17} className="text-emerald-500" /> : <CircleDashed size={17} className="text-slate-400" />}
                <p className="text-sm font-black text-slate-900 dark:text-white">{rule.rule_name}</p>
              </div>
              <Badge tone={rule.triggered ? "success" : "neutral"}>{rule.action}</Badge>
            </div>
            <div className="mt-3 grid gap-2">
              {rule.conditions.map((condition) => (
                <div key={condition.condition_id} className="flex flex-wrap items-center justify-between gap-2 rounded-[8px] bg-white/10 px-3 py-2 text-xs font-semibold text-slate-600 dark:text-white/55">
                  <span>
                    {condition.indicator} {condition.operator} {formatNumber(condition.right_value)}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    {condition.passed ? <CheckCircle2 size={14} className="text-emerald-500" /> : <XCircle size={14} className="text-rose-500" />}
                    {formatNumber(condition.left_value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function formatNumber(value: number) {
  return Math.abs(value) >= 1000 ? value.toFixed(2) : value.toFixed(4);
}
