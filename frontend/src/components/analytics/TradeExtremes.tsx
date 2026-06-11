import { ArrowDownRight, ArrowUpRight } from "lucide-react";

import type { AnalyticsTrade } from "../../api/performanceAnalyticsApi";
import { Card } from "../ui/Card";

export function TradeExtremes({ best, worst }: { best?: AnalyticsTrade | null; worst?: AnalyticsTrade | null }) {
  return (
    <Card className="p-4 sm:p-5">
      <h2 className="text-lg font-black text-slate-950 dark:text-white">Best / Worst Trade</h2>
      <div className="mt-4 grid gap-3">
        <ExtremeRow label="Best trade" trade={best} icon={ArrowUpRight} tone="text-emerald-600 dark:text-emerald-300" />
        <ExtremeRow label="Worst trade" trade={worst} icon={ArrowDownRight} tone="text-rose-600 dark:text-rose-300" />
      </div>
    </Card>
  );
}

function ExtremeRow({
  label,
  trade,
  icon: Icon,
  tone,
}: {
  label: string;
  trade?: AnalyticsTrade | null;
  icon: typeof ArrowUpRight;
  tone: string;
}) {
  return (
    <div className="rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/5">
      <div className="flex items-center justify-between gap-3">
        <span className="flex items-center gap-2 text-sm font-black text-slate-950 dark:text-white">
          <Icon size={16} className={tone} aria-hidden />
          {label}
        </span>
        <span className={`text-sm font-black ${tone}`}>{formatCurrency(trade?.realized_pnl ?? 0)}</span>
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2 text-xs font-semibold text-slate-500 dark:text-white/45">
        <span className="truncate">{trade?.symbol ?? "No trade"}</span>
        <span className="truncate">{trade?.side ?? "n/a"}</span>
        <span className="text-right">{formatPercent(trade?.return_pct ?? 0)}</span>
      </div>
    </div>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: Math.abs(value) > 1000 ? 0 : 2,
  }).format(value);
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}
