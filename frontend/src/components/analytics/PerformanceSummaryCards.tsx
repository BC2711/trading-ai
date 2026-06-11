import { Activity, BarChart3, CircleDollarSign, Percent, Trophy, TrendingDown, TrendingUp } from "lucide-react";

import type { PerformanceSummary } from "../../api/performanceAnalyticsApi";
import { Card } from "../ui/Card";

type SummaryItem = {
  label: string;
  value: string;
  detail: string;
  icon: typeof Activity;
  tone: string;
};

export function PerformanceSummaryCards({ summary }: { summary?: PerformanceSummary }) {
  const items: SummaryItem[] = [
    {
      label: "Win Rate",
      value: formatPercent(summary?.win_rate ?? 0),
      detail: `${summary?.winning_trades ?? 0} wins`,
      icon: Trophy,
      tone: "from-emerald-400 to-teal-500",
    },
    {
      label: "Loss Rate",
      value: formatPercent(summary?.loss_rate ?? 0),
      detail: `${summary?.losing_trades ?? 0} losses`,
      icon: TrendingDown,
      tone: "from-rose-400 to-pink-500",
    },
    {
      label: "Profit Factor",
      value: (summary?.profit_factor ?? 0).toFixed(2),
      detail: `${formatCurrency(summary?.gross_profit ?? 0)} gross profit`,
      icon: BarChart3,
      tone: "from-cyan-400 to-blue-500",
    },
    {
      label: "Sharpe Ratio",
      value: (summary?.sharpe_ratio ?? 0).toFixed(2),
      detail: "Realized trade returns",
      icon: Activity,
      tone: "from-violet-400 to-fuchsia-500",
    },
    {
      label: "Average Win",
      value: formatCurrency(summary?.average_win ?? 0),
      detail: "Mean winning trade",
      icon: TrendingUp,
      tone: "from-emerald-400 to-cyan-500",
    },
    {
      label: "Average Loss",
      value: formatCurrency(summary?.average_loss ?? 0),
      detail: "Mean losing trade",
      icon: TrendingDown,
      tone: "from-amber-300 to-orange-500",
    },
    {
      label: "Max Drawdown",
      value: formatPercent(summary?.max_drawdown ?? 0),
      detail: "Peak-to-trough equity",
      icon: Percent,
      tone: "from-rose-400 to-orange-500",
    },
    {
      label: "Net PnL",
      value: formatCurrency(summary?.net_pnl ?? 0),
      detail: `${summary?.total_trades ?? 0} closed trades`,
      icon: CircleDollarSign,
      tone: (summary?.net_pnl ?? 0) >= 0 ? "from-emerald-400 to-teal-500" : "from-rose-400 to-pink-500",
    },
  ];

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label} className="min-h-[132px] p-4 sm:p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-bold text-slate-500 dark:text-white/50">{item.label}</p>
              <strong className="mt-3 block truncate text-2xl font-black text-slate-950 dark:text-white">{item.value}</strong>
              <p className="mt-2 truncate text-xs font-semibold text-slate-500 dark:text-white/40">{item.detail}</p>
            </div>
            <span className={`grid size-11 shrink-0 place-items-center rounded-[8px] bg-gradient-to-br text-white shadow-xl ${item.tone}`}>
              <item.icon size={20} aria-hidden />
            </span>
          </div>
        </Card>
      ))}
    </section>
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
  return `${(value * 100).toFixed(1)}%`;
}
