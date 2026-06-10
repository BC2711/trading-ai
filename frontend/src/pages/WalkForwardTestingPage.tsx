import { useMutation, useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, BarChart3, FlaskConical, TrendingDown, TrendingUp } from "lucide-react";
import { useState } from "react";

import { runWalkForward } from "../api/walkForwardApi";
import type { WalkForwardRun } from "../api/walkForwardApi";
import { EmptyState } from "../components/table/EmptyState";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Skeleton } from "../components/ui/LoadingSpinner";
import { Select } from "../components/ui/Select";
import { fetchStrategies, fetchSymbols } from "../services/api";

export function WalkForwardTestingPage() {
  const strategiesQuery = useQuery({ queryKey: ["strategies"], queryFn: fetchStrategies });
  const symbolsQuery = useQuery({ queryKey: ["symbols"], queryFn: fetchSymbols });
  const [form, setForm] = useState({
    strategyId: "",
    symbol: "BTCUSDT",
    timeframe: "15m",
    initialBalance: "10000",
    trainingPeriod: "90",
    validationPeriod: "30",
    testPeriod: "30",
    rollingWindows: "3"
  });
  const mutation = useMutation({
    mutationFn: () =>
      runWalkForward({
        strategy_id: form.strategyId ? Number(form.strategyId) : null,
        symbol: form.symbol,
        timeframe: form.timeframe,
        initial_balance: Number(form.initialBalance) || 10000,
        training_period: Number(form.trainingPeriod) || 90,
        validation_period: Number(form.validationPeriod) || 30,
        test_period: Number(form.testPeriod) || 30,
        rolling_windows: Number(form.rollingWindows) || 3
      })
  });
  const result = mutation.data;

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <FlaskConical size={14} aria-hidden />
              Out-of-sample testing
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Walk-Forward Testing</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Optimize over training and validation windows, then measure each rolling test window out of sample.
            </p>
          </div>
          <Button icon={Activity} loading={mutation.isPending} onClick={() => mutation.mutate()}>
            Run test
          </Button>
        </div>
      </Card>

      {mutation.isError ? <Alert tone="error">Walk-forward test failed. Check candle history and period settings.</Alert> : null}
      {result?.warning ? (
        <Alert tone="warning">
          <span className="inline-flex items-center gap-2">
            <AlertTriangle size={16} aria-hidden />
            {result.warning}
          </span>
        </Alert>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[380px_minmax(0,1fr)] xl:gap-6">
        <Card className="p-5">
          <h2 className="text-lg font-black text-slate-950 dark:text-white">Configuration</h2>
          {strategiesQuery.isLoading || symbolsQuery.isLoading ? (
            <Skeleton className="mt-4 h-72" />
          ) : (
            <div className="mt-4 grid gap-3">
              <Select
                label="Strategy"
                value={form.strategyId}
                options={[
                  { label: "Default strategy", value: "" },
                  ...(strategiesQuery.data ?? []).map((strategy) => ({ label: strategy.name, value: String(strategy.id) }))
                ]}
                onChange={(event) => setForm((current) => ({ ...current, strategyId: event.target.value }))}
              />
              <Select
                label="Symbol"
                value={form.symbol}
                options={(symbolsQuery.data?.length ? symbolsQuery.data : [{ symbol: "BTCUSDT" }]).map((symbol) => symbol.symbol)}
                onChange={(event) => setForm((current) => ({ ...current, symbol: event.target.value }))}
              />
              <Select label="Timeframe" value={form.timeframe} options={["1m", "5m", "15m", "1h", "4h", "1d"]} onChange={(event) => setForm((current) => ({ ...current, timeframe: event.target.value }))} />
              <Input label="Initial balance" type="number" min="1" value={form.initialBalance} onChange={(event) => setForm((current) => ({ ...current, initialBalance: event.target.value }))} />
              <div className="grid gap-3 sm:grid-cols-2">
                <Input label="Train period" type="number" min="30" value={form.trainingPeriod} onChange={(event) => setForm((current) => ({ ...current, trainingPeriod: event.target.value }))} />
                <Input label="Validation period" type="number" min="10" value={form.validationPeriod} onChange={(event) => setForm((current) => ({ ...current, validationPeriod: event.target.value }))} />
                <Input label="Test period" type="number" min="10" value={form.testPeriod} onChange={(event) => setForm((current) => ({ ...current, testPeriod: event.target.value }))} />
                <Input label="Rolling windows" type="number" min="1" value={form.rollingWindows} onChange={(event) => setForm((current) => ({ ...current, rollingWindows: event.target.value }))} />
              </div>
            </div>
          )}
        </Card>

        <WalkForwardMetrics result={result} />
      </section>

      <WalkForwardResultsTable result={result} />
    </div>
  );
}

function WalkForwardMetrics({ result }: { result?: WalkForwardRun }) {
  if (!result) {
    return (
      <Card className="p-5">
        <h2 className="text-lg font-black text-slate-950 dark:text-white">Performance Metrics</h2>
        <EmptyState title="No walk-forward run" message="Run a test to view aggregated out-of-sample performance." />
      </Card>
    );
  }
  const aggregate = result.aggregated_result;
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-black text-slate-950 dark:text-white">Performance Metrics</h2>
          <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-white/50">
            {result.symbol} / {result.timeframe} across {aggregate.windows} rolling windows
          </p>
        </div>
        <Badge tone={aggregate.robustness_score >= 0.6 ? "success" : aggregate.robustness_score >= 0.35 ? "warning" : "error"}>
          Robustness {(aggregate.robustness_score * 100).toFixed(0)}%
        </Badge>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric icon={TrendingUp} label="Cumulative return" value={formatPercent(aggregate.cumulative_return)} tone={aggregate.cumulative_return >= 0 ? "text-emerald-600 dark:text-emerald-300" : "text-rose-600 dark:text-rose-300"} />
        <Metric icon={BarChart3} label="Avg OOS return" value={formatPercent(aggregate.average_test_return)} />
        <Metric icon={TrendingDown} label="Max drawdown" value={formatPercent(aggregate.max_drawdown)} />
        <Metric icon={Activity} label="Total trades" value={String(aggregate.total_trades)} />
        <Metric icon={BarChart3} label="Win rate" value={formatPercent(aggregate.average_win_rate)} />
        <Metric icon={BarChart3} label="Profit factor" value={aggregate.profit_factor.toFixed(2)} />
        <Metric icon={BarChart3} label="Sharpe" value={aggregate.sharpe_ratio.toFixed(2)} />
        <Metric icon={BarChart3} label="Validation avg" value={formatPercent(aggregate.average_validation_return)} />
      </div>
    </Card>
  );
}

function WalkForwardResultsTable({ result }: { result?: WalkForwardRun }) {
  return (
    <Card className="p-0">
      <div className="border-b border-white/10 p-4">
        <h2 className="text-base font-black text-slate-950 dark:text-white">Rolling Window Results</h2>
      </div>
      {result?.window_metrics.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-slate-500 dark:text-white/45">
                <th className="px-4 py-3">Window</th>
                <th className="px-4 py-3">Parameters</th>
                <th className="px-4 py-3">Validation</th>
                <th className="px-4 py-3">Out of sample</th>
                <th className="px-4 py-3">Drawdown</th>
                <th className="px-4 py-3">Trades</th>
                <th className="px-4 py-3">Score</th>
              </tr>
            </thead>
            <tbody>
              {result.window_metrics.map((window) => (
                <tr key={window.window} className="border-t border-white/10">
                  <td className="px-4 py-3 font-black text-slate-950 dark:text-white">#{window.window}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-white/60">
                    EMA {window.selected_parameters.fast_ema}/{window.selected_parameters.slow_ema}, RSI {window.selected_parameters.rsi_ceiling}
                  </td>
                  <td className="px-4 py-3 font-bold text-slate-700 dark:text-white/70">{formatPercent(window.validation_metrics.total_return)}</td>
                  <td className="px-4 py-3 font-bold text-slate-700 dark:text-white/70">{formatPercent(window.test_metrics.total_return)}</td>
                  <td className="px-4 py-3 font-bold text-slate-700 dark:text-white/70">{formatPercent(window.test_metrics.max_drawdown)}</td>
                  <td className="px-4 py-3 font-bold text-slate-700 dark:text-white/70">{window.test_metrics.trades_count}</td>
                  <td className="px-4 py-3 font-bold text-slate-700 dark:text-white/70">{window.optimization_score.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No windows yet" message="Walk-forward window metrics will appear after a completed run." />
      )}
    </Card>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  tone = "text-slate-950 dark:text-white"
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="rounded-[8px] border border-white/10 bg-white/10 p-4 dark:bg-white/[0.04]">
      <div className="flex items-center gap-2 text-slate-500 dark:text-white/45">
        <Icon size={15} aria-hidden />
        <p className="text-xs font-bold uppercase">{label}</p>
      </div>
      <p className={`mt-2 text-xl font-black ${tone}`}>{value}</p>
    </div>
  );
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}
