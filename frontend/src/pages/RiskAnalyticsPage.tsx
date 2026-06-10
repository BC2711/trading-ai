import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, AlertTriangle, Gauge, ShieldAlert, ShieldCheck, TrendingDown, Wallet } from "lucide-react";

import { disableCircuitBreaker, enableCircuitBreaker, fetchRiskSummary } from "../api/riskAnalyticsApi";
import { RejectedTradesTable } from "../components/risk/RejectedTradesTable";
import { RiskMetricCard } from "../components/risk/RiskMetricCard";
import { RiskWarnings } from "../components/risk/RiskWarnings";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";

export function RiskAnalyticsPage() {
  const queryClient = useQueryClient();
  const summaryQuery = useQuery({ queryKey: ["risk", "summary"], queryFn: fetchRiskSummary, refetchInterval: 30_000 });
  const summary = summaryQuery.data;
  const enableMutation = useMutation({
    mutationFn: enableCircuitBreaker,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["risk"] })
  });
  const disableMutation = useMutation({
    mutationFn: disableCircuitBreaker,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["risk"] })
  });

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <ShieldCheck size={14} aria-hidden />
              Advanced risk engine
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Risk Analytics</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Monitor loss usage, drawdown, exposure, leverage, rejected trades, and circuit-breaker status.
            </p>
          </div>
          {summary?.circuit_breaker_enabled ? (
            <Button variant="success" loading={disableMutation.isPending} onClick={() => disableMutation.mutate()}>
              Disable circuit breaker
            </Button>
          ) : (
            <Button variant="danger" loading={enableMutation.isPending} onClick={() => enableMutation.mutate()}>
              Enable circuit breaker
            </Button>
          )}
        </div>
      </Card>

      {summaryQuery.isError ? <Alert tone="error">Unable to load risk analytics.</Alert> : null}
      {enableMutation.isSuccess ? <Alert tone="warning">Circuit breaker enabled. New trades will be blocked.</Alert> : null}
      {disableMutation.isSuccess ? <Alert tone="success">Circuit breaker disabled.</Alert> : null}

      {summaryQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} className="h-32" />)}
        </div>
      ) : (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <RiskMetricCard label="Current Risk Score" value={`${(summary?.risk_score ?? 0).toFixed(1)}/100`} detail={summary?.circuit_breaker_enabled ? "Circuit breaker enabled" : "Circuit breaker clear"} usage={(summary?.risk_score ?? 0) / 100} icon={Gauge} tone={(summary?.risk_score ?? 0) > 75 ? "rose" : "cyan"} />
          <RiskMetricCard label="Daily Loss Usage" value={formatCurrency(summary?.daily_loss ?? 0)} detail={`Limit ${formatCurrency(summary?.max_loss_limit ?? 0)}`} usage={summary?.daily_loss_usage ?? 0} icon={TrendingDown} tone="amber" />
          <RiskMetricCard label="Drawdown" value={formatPercent(summary?.drawdown ?? 0)} detail={`Limit ${formatPercent(summary?.max_drawdown_limit ?? 0)}`} usage={summary?.drawdown_usage ?? 0} icon={Activity} tone="violet" />
          <RiskMetricCard label="Exposure" value={formatCurrency(summary?.total_exposure ?? 0)} detail={`${summary?.open_trades ?? 0}/${summary?.max_open_trades ?? 0} open trades`} usage={summary?.exposure_usage ?? 0} icon={Wallet} tone="cyan" />
          <RiskMetricCard label="Max Loss Limit" value={formatCurrency(summary?.max_loss_limit ?? 0)} detail={`Weekly ${formatCurrency(summary?.max_weekly_loss_limit ?? 0)}`} icon={ShieldAlert} tone="rose" />
          <RiskMetricCard label="Leverage" value={`${(summary?.leverage ?? 0).toFixed(2)}x`} detail={`Max ${(summary?.max_leverage ?? 0).toFixed(2)}x`} usage={(summary?.leverage ?? 0) / Math.max(1, summary?.max_leverage ?? 1)} icon={Gauge} tone="amber" />
          <RiskMetricCard label="Circuit Breaker" value={summary?.circuit_breaker_enabled ? "Enabled" : "Disabled"} detail="Emergency trade block" icon={AlertTriangle} tone={summary?.circuit_breaker_enabled ? "rose" : "emerald"} />
          <RiskMetricCard label="Weekly Loss Usage" value={formatCurrency(summary?.weekly_loss ?? 0)} detail={`Limit ${formatCurrency(summary?.max_weekly_loss_limit ?? 0)}`} usage={summary?.weekly_loss_usage ?? 0} icon={TrendingDown} tone="amber" />
        </section>
      )}

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px] xl:gap-6">
        <RejectedTradesTable trades={summary?.recent_rejected_trades ?? []} />
        <RiskWarnings warnings={summary?.warnings ?? []} />
      </section>
    </div>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: Math.abs(value) > 1000 ? 0 : 2
  }).format(value);
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}
