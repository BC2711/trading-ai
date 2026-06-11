import { CircleDollarSign, ListChecks, Sigma, TrendingDown, TrendingUp } from "lucide-react";

import type { PerformanceSummary } from "../../api/performanceAnalyticsApi";
import { Card } from "../ui/Card";

export function TradeStatistics({ summary }: { summary?: PerformanceSummary }) {
  const rows = [
    { label: "Total trades", value: `${summary?.total_trades ?? 0}`, icon: ListChecks },
    { label: "Winning trades", value: `${summary?.winning_trades ?? 0}`, icon: TrendingUp },
    { label: "Losing trades", value: `${summary?.losing_trades ?? 0}`, icon: TrendingDown },
    { label: "Gross profit", value: formatCurrency(summary?.gross_profit ?? 0), icon: CircleDollarSign },
    { label: "Gross loss", value: formatCurrency(summary?.gross_loss ?? 0), icon: CircleDollarSign },
    { label: "Net PnL", value: formatCurrency(summary?.net_pnl ?? 0), icon: Sigma },
  ];

  return (
    <Card className="p-4 sm:p-5">
      <h2 className="text-lg font-black text-slate-950 dark:text-white">Trade Statistics</h2>
      <div className="mt-4 grid gap-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between gap-3 rounded-[8px] border border-white/10 bg-white/10 px-3 py-2.5 dark:bg-white/5">
            <span className="flex min-w-0 items-center gap-2 text-sm font-bold text-slate-600 dark:text-white/60">
              <row.icon size={15} aria-hidden />
              <span className="truncate">{row.label}</span>
            </span>
            <span className="text-sm font-black text-slate-950 dark:text-white">{row.value}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: Math.abs(value) > 1000 ? 0 : 2,
  }).format(value);
}
