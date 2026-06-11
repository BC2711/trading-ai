import { useQuery } from "@tanstack/react-query";
import { BarChart3 } from "lucide-react";

import {
  fetchAnalyticsEquityCurve,
  fetchAnalyticsTrades,
  fetchPerformanceSummary,
  fetchStrategyComparison,
} from "../api/performanceAnalyticsApi";
import {
  AnalyticsTradesTable,
  DrawdownChart,
  EquityCurveChart,
  PerformanceSummaryCards,
  StrategyComparisonTable,
  TradeExtremes,
  TradeStatistics,
} from "../components/analytics";
import { Alert } from "../components/ui/Alert";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";

export function PerformanceAnalyticsPage() {
  const summaryQuery = useQuery({ queryKey: ["analytics", "performance"], queryFn: fetchPerformanceSummary, refetchInterval: 30_000 });
  const curveQuery = useQuery({ queryKey: ["analytics", "equity-curve"], queryFn: fetchAnalyticsEquityCurve, refetchInterval: 30_000 });
  const strategiesQuery = useQuery({ queryKey: ["analytics", "strategies"], queryFn: fetchStrategyComparison, refetchInterval: 45_000 });
  const tradesQuery = useQuery({ queryKey: ["analytics", "trades"], queryFn: fetchAnalyticsTrades, refetchInterval: 30_000 });
  const hasError = summaryQuery.isError || curveQuery.isError || strategiesQuery.isError || tradesQuery.isError;

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <BarChart3 size={14} aria-hidden />
              Analytics
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Performance Analytics</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Review realized trading performance, equity progression, drawdown, and strategy-level outcomes.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <HeaderStat label="Trades" value={`${summaryQuery.data?.total_trades ?? 0}`} />
            <HeaderStat label="Net PnL" value={formatCurrency(summaryQuery.data?.net_pnl ?? 0)} />
            <HeaderStat label="Ending Equity" value={formatCurrency(curveQuery.data?.ending_equity ?? 0)} />
          </div>
        </div>
      </Card>

      {hasError ? <Alert tone="error">Unable to load performance analytics.</Alert> : null}

      {summaryQuery.isLoading ? (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} className="h-32" />)}
        </section>
      ) : (
        <PerformanceSummaryCards summary={summaryQuery.data} />
      )}

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px] xl:gap-6">
        <EquityCurveChart curve={curveQuery.data} />
        <div className="grid gap-4">
          <TradeStatistics summary={summaryQuery.data} />
          <TradeExtremes best={summaryQuery.data?.best_trade} worst={summaryQuery.data?.worst_trade} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px] xl:gap-6">
        <StrategyComparisonTable strategies={strategiesQuery.data?.strategies ?? []} />
        <DrawdownChart curve={curveQuery.data} />
      </section>

      <AnalyticsTradesTable trades={tradesQuery.data ?? []} />
    </div>
  );
}

function HeaderStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-[112px] rounded-[8px] border border-white/10 bg-white/10 px-3 py-2 text-right dark:bg-white/5">
      <p className="text-xs font-bold text-slate-500 dark:text-white/45">{label}</p>
      <p className="mt-1 truncate text-sm font-black text-slate-950 dark:text-white">{value}</p>
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
