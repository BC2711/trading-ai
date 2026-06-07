import { motion } from "framer-motion";
import {
  Activity,
  ArrowUpRight,
  Bot,
  Calendar,
  CircleDollarSign,
  Clock3,
  Download,
  Layers3,
  Play,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Wand2
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { SignalChart } from "../components/SignalChart";
import { EmptyState } from "../components/table/EmptyState";
import { DataTable } from "../components/table/DataTable";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input, FileUpload, ToggleSwitch } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/LoadingSpinner";
import { StatCard } from "../components/ui/StatCard";
import { Textarea } from "../components/ui/Textarea";
import {
  fetchCandles,
  fetchMarketDataSchedule,
  fetchRiskSettings,
  fetchStrategies,
  fetchSymbols,
  refreshMarketData
} from "../services/api";
import { useSignals } from "../hooks/useSignals";
import { useTradingStore } from "../store/useTradingStore";
import { cn } from "../utils/cn";

export function DashboardPage() {
  const { signals, isLoading, isError } = useSignals();
  const { timeframe, setTimeframe } = useTradingStore();
  const [strategyOpen, setStrategyOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("Live");
  const queryClient = useQueryClient();
  const symbolsQuery = useQuery({
    queryKey: ["symbols"],
    queryFn: fetchSymbols
  });
  const scheduleQuery = useQuery({
    queryKey: ["market-data-schedule"],
    queryFn: fetchMarketDataSchedule
  });
  const strategiesQuery = useQuery({
    queryKey: ["strategies"],
    queryFn: fetchStrategies
  });
  const riskSettingsQuery = useQuery({
    queryKey: ["risk-settings"],
    queryFn: fetchRiskSettings
  });

  const selectedSymbol = symbolsQuery.data?.[0]?.symbol ?? "BTCUSDT";
  const backendTimeframe = scheduleQuery.data?.timeframe ?? "15m";
  const candlesQuery = useQuery({
    queryKey: ["candles", selectedSymbol, backendTimeframe],
    queryFn: () => fetchCandles(selectedSymbol, backendTimeframe, 120),
    enabled: Boolean(selectedSymbol)
  });

  const syncMutation = useMutation({
    mutationFn: () =>
      refreshMarketData({
        symbols: scheduleQuery.data?.symbols ?? ["BTCUSDT", "ETHUSDT"],
        timeframe: scheduleQuery.data?.timeframe ?? backendTimeframe,
        limit: scheduleQuery.data?.limit ?? 500,
        regenerate_signals: true
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signals"] });
      queryClient.invalidateQueries({ queryKey: ["symbols"] });
      queryClient.invalidateQueries({ queryKey: ["candles"] });
    }
  });

  const latestCandle = candlesQuery.data?.at(-1);
  const previousCandle = candlesQuery.data?.at(-2);
  const priceChangePercent =
    latestCandle && previousCandle
      ? ((latestCandle.close - previousCandle.close) / previousCandle.close) * 100
      : 0;
  const riskSettings = riskSettingsQuery.data?.[0];
  const activeStrategy = strategiesQuery.data?.[0];
  const bestSignal = signals.reduce(
    (best, signal) => (signal.confidence > (best?.confidence ?? 0) ? signal : best),
    signals[0]
  );
  const confidenceSparkline = signals.length
    ? signals.map((signal) => Math.round(signal.confidence * 100)).slice(-7)
    : [12, 18, 16, 22, 20, 26, 24];

  const metrics = [
    {
      label: `${selectedSymbol} Last Close`,
      value: latestCandle ? formatCurrency(latestCandle.close) : "Loading",
      trend: `${priceChangePercent >= 0 ? "+" : ""}${priceChangePercent.toFixed(2)}% candle`,
      trendDirection: priceChangePercent > 0 ? ("up" as const) : priceChangePercent < 0 ? ("down" as const) : ("flat" as const),
      tone: "cyan" as const,
      icon: CircleDollarSign,
      sparkline: candlesToSparkline(candlesQuery.data)
    },
    {
      label: "Open Risk",
      value: riskSettings ? `${(riskSettings.max_risk_per_trade * 100).toFixed(1)}%` : "Loading",
      trend: riskSettings ? `${riskSettings.max_open_trades} max trades` : "Risk policy",
      trendDirection: "flat" as const,
      tone: "emerald" as const,
      icon: ShieldCheck,
      sparkline: [30, 26, 25, 22, 24, 20, 19]
    },
    {
      label: "Best Signal",
      value: bestSignal ? `${Math.round(bestSignal.confidence * 100)}%` : "0%",
      trend: bestSignal ? `${bestSignal.symbol} ${bestSignal.direction}` : "No active signal",
      trendDirection: bestSignal?.direction === "sell" ? ("down" as const) : bestSignal?.direction === "buy" ? ("up" as const) : ("flat" as const),
      tone: "violet" as const,
      icon: Bot,
      sparkline: confidenceSparkline
    },
    {
      label: "Market Sync",
      value: scheduleQuery.data ? `${scheduleQuery.data.interval_minutes}m` : "Loading",
      trend: scheduleQuery.data ? `${scheduleQuery.data.symbols.length} symbols watched` : "Schedule",
      trendDirection: "flat" as const,
      tone: "amber" as const,
      icon: Target,
      sparkline: [44, 39, 41, 36, 31, 28, 26]
    }
  ];

  const tableRows = useMemo(
    () =>
      signals.map((signal) => ({
        id: `${signal.id ?? signal.symbol}-${signal.created_at ?? signal.timeframe ?? "latest"}`,
        symbol: signal.symbol,
        direction: signal.direction,
        confidence: Math.round(signal.confidence * 100),
        exposure: signal.direction.toLowerCase().includes("sell") ? "Reduce" : signal.direction.toLowerCase().includes("buy") ? "Build" : "Observe",
        updated: signal.created_at ? formatRelativeTime(signal.created_at) : "Just now",
        timeframe: signal.timeframe ?? backendTimeframe,
        reason: signal.reason ?? "Generated by rule engine"
      })),
    [backendTimeframe, signals]
  );

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Sparkles size={14} aria-hidden />
              Live enterprise workspace
            </div>
            <h1 className="text-3xl font-black tracking-normal text-slate-950 dark:text-white sm:text-4xl">
              AI trading dashboard
            </h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Monitor synced market data, rule-based signals, strategy posture, and risk settings from one responsive glass control surface.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-[8px] border border-white/20 bg-white/10 p-1 shadow-xl shadow-slate-950/5 backdrop-blur-lg dark:shadow-black/20">
              {(["1h", "4h", "1d"] as const).map((item) => (
                <button
                  type="button"
                  className={cn(
                    "min-h-9 rounded-[8px] px-3 text-sm font-bold text-slate-500 transition-all duration-300 hover:text-slate-950 dark:text-white/50 dark:hover:text-white",
                    item === timeframe &&
                      "bg-white/20 text-slate-950 shadow-lg shadow-slate-950/5 dark:text-white dark:shadow-black/20"
                  )}
                  key={item}
                  onClick={() => setTimeframe(item)}
                >
                  {item}
                </button>
              ))}
            </div>
            <Button icon={Play}>Run backtest</Button>
            <Button variant="secondary" icon={Wand2} onClick={() => setStrategyOpen(true)}>
              Tune model
            </Button>
          </div>
        </div>
      </Card>

      {isError ? <Alert tone="error">Unable to load live signals. Cached controls remain available.</Alert> : null}
      {syncMutation.isError ? (
        <Alert tone="warning">Market data sync failed. Check backend network access to Binance and try again.</Alert>
      ) : null}
      {syncMutation.isSuccess ? (
        <Alert tone="success">
          Refreshed {syncMutation.data.results.reduce((total, result) => total + result.fetched, 0)} candles from {syncMutation.data.provider}; generated {syncMutation.data.generated_signal_count} signals.
        </Alert>
      ) : null}

      <motion.section
        className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-4"
        aria-label="Portfolio metrics"
        initial="hidden"
        animate="show"
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.06 } } }}
      >
        {metrics.map((metric) => (
          <StatCard key={metric.label} {...metric} />
        ))}
      </motion.section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(340px,0.8fr)] xl:gap-6">
        <Card className="p-4 sm:p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Signal Confidence</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">
                {isLoading ? "Loading signals" : `${signals.length} active opportunities`}
              </p>
            </div>
            <div className="flex rounded-[8px] border border-white/20 bg-white/10 p-1 backdrop-blur-lg">
              {["Live", "Sim", "Audit"].map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "min-h-9 rounded-[8px] px-3 text-sm font-bold text-slate-500 transition dark:text-white/50",
                    activeTab === tab && "bg-white/20 text-slate-950 shadow-lg shadow-slate-950/5 dark:text-white"
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
          {isLoading ? <Skeleton className="h-[280px]" /> : <SignalChart signals={signals} />}
        </Card>

        <Card className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Quick Actions</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">
                Backend controls for {scheduleQuery.data?.symbols.join(", ") ?? "configured symbols"}
              </p>
            </div>
            <Badge tone={scheduleQuery.isError ? "warning" : "success"}>
              {scheduleQuery.data ? `${scheduleQuery.data.interval_minutes}m sync` : "Loading"}
            </Badge>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            {[
              { label: "Deploy hedge", icon: ShieldAlert, tone: "bg-amber-400/15 text-amber-700 dark:text-amber-100" },
              { label: "Export report", icon: Download, tone: "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100" },
              { label: "Open research", icon: Layers3, tone: "bg-violet-400/15 text-violet-700 dark:text-violet-100" }
            ].map((action) => (
              <button
                key={action.label}
                type="button"
                className="group flex min-h-14 items-center gap-3 rounded-[8px] border border-white/10 bg-white/10 px-3 text-left font-bold text-slate-800 shadow-lg shadow-slate-950/5 backdrop-blur-lg transition hover:-translate-y-0.5 hover:bg-white/15 dark:bg-white/5 dark:text-white/80 dark:shadow-black/20"
              >
                <span className={cn("grid size-9 place-items-center rounded-[8px]", action.tone)}>
                  <action.icon size={17} aria-hidden />
                </span>
                <span className="flex-1">{action.label}</span>
                <ArrowUpRight size={16} className="text-slate-400 transition group-hover:text-cyan-500" aria-hidden />
              </button>
            ))}
            <Button
              variant="secondary"
              icon={TrendingUp}
              loading={syncMutation.isPending}
              onClick={() => syncMutation.mutate()}
              className="min-h-14 justify-start"
            >
              Refresh backend data
            </Button>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.7fr)] xl:gap-6">
        <DataTable
          columns={[
            {
              key: "symbol",
              label: "Symbol",
              render: (row) => <strong className="text-slate-950 dark:text-white">{row.symbol}</strong>
            },
            {
              key: "direction",
              label: "Direction",
              render: (row) => (
                <span
                  className={cn(
                    "rounded-[8px] px-2.5 py-1 text-xs font-black",
                    row.direction.toLowerCase().includes("sell")
                      ? "bg-rose-400/15 text-rose-700 dark:text-rose-100"
                      : "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100"
                  )}
                >
                  {row.direction}
                </span>
              )
            },
            {
              key: "confidence",
              label: "Confidence",
              align: "right",
              render: (row) => `${row.confidence}%`
            },
            { key: "timeframe", label: "Frame" },
            { key: "exposure", label: "Exposure" },
            {
              key: "reason",
              label: "Reason",
              render: (row) => <span className="line-clamp-1 text-slate-500 dark:text-white/50">{row.reason}</span>
            },
            { key: "updated", label: "Updated", align: "right" }
          ]}
          rows={tableRows}
          loading={isLoading}
          emptyTitle="No active signals"
        />

        <Card className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Backend Timeline</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">Live integration state</p>
            </div>
            <Clock3 size={18} className="text-slate-400 dark:text-white/40" aria-hidden />
          </div>
          <div className="mt-5 grid gap-4">
            {[
              {
                title: "Market data schedule",
                detail: scheduleQuery.data
                  ? `${scheduleQuery.data.symbols.join(", ")} every ${scheduleQuery.data.interval_minutes} minutes`
                  : "Loading scheduler configuration",
                time: scheduleQuery.data?.timeframe ?? backendTimeframe,
                icon: Clock3
              },
              {
                title: "Strategy engine",
                detail: activeStrategy?.description ?? "Loading default strategy",
                time: activeStrategy?.status ?? "loading",
                icon: Bot
              },
              {
                title: "Risk policy",
                detail: riskSettings
                  ? `${(riskSettings.max_daily_loss * 100).toFixed(1)}% max daily loss, ${(riskSettings.max_symbol_exposure * 100).toFixed(0)}% symbol exposure`
                  : "Loading risk settings",
                time: riskSettings?.status ?? "loading",
                icon: ShieldCheck
              }
            ].map((item, index) => (
              <motion.div
                key={item.title}
                className="relative grid grid-cols-[40px_1fr] gap-3"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.06 }}
              >
                <span className="grid size-10 place-items-center rounded-[8px] border border-white/20 bg-white/10 text-cyan-700 backdrop-blur-lg dark:text-cyan-100">
                  <item.icon size={17} aria-hidden />
                </span>
                <div className="rounded-[8px] border border-white/10 bg-white/10 p-3 backdrop-blur-md dark:bg-white/5">
                  <div className="flex items-start justify-between gap-3">
                    <strong className="text-sm text-slate-900 dark:text-white">{item.title}</strong>
                    <span className="text-xs font-bold text-slate-400 dark:text-white/40">{item.time}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500 dark:text-white/50">{item.detail}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-3 xl:gap-6">
        <Card className="p-4 sm:p-5 xl:col-span-2">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Backend Strategy Controls</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">
                Current defaults from `/api/strategies` and `/api/risk-settings`
              </p>
            </div>
            <Calendar size={18} className="text-slate-400 dark:text-white/40" aria-hidden />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Input label="Strategy name" value={activeStrategy?.name ?? ""} readOnly placeholder="Loading strategy" />
            <Select
              label="Market universe"
              options={(symbolsQuery.data?.map((symbol) => symbol.symbol) ?? ["BTCUSDT", "ETHUSDT"])}
              value={selectedSymbol}
              disabled
            />
            <Input
              label="Risk per trade"
              value={riskSettings ? `${(riskSettings.max_risk_per_trade * 100).toFixed(1)}%` : ""}
              readOnly
              placeholder="Loading risk"
            />
            <Select
              label="Refresh cadence"
              options={[scheduleQuery.data ? `${scheduleQuery.data.interval_minutes} minutes` : "Loading"]}
              value={scheduleQuery.data ? `${scheduleQuery.data.interval_minutes} minutes` : "Loading"}
              disabled
            />
            <div className="md:col-span-2">
              <Textarea
                label="Strategy description"
                value={activeStrategy?.description ?? ""}
                readOnly
                placeholder="Loading strategy description"
              />
            </div>
            <ToggleSwitch label="Auto-pause on anomaly" checked />
            <ToggleSwitch label="Send executive digest" />
            <div className="md:col-span-2">
              <FileUpload />
            </div>
          </div>
        </Card>

        <Card className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Backend Summary</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">Resource posture</p>
            </div>
            <Activity size={18} className="text-slate-400 dark:text-white/40" aria-hidden />
          </div>
          <div className="mt-5 grid gap-3">
            {[
              ["Symbols", `${symbolsQuery.data?.length ?? 0}`, "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100"],
              ["Candles", `${candlesQuery.data?.length ?? 0}`, "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100"],
              ["Strategies", `${strategiesQuery.data?.length ?? 0}`, "bg-violet-400/15 text-violet-700 dark:text-violet-100"],
              ["Max daily loss", riskSettings ? `${(riskSettings.max_daily_loss * 100).toFixed(1)}%` : "Loading", "bg-amber-400/15 text-amber-700 dark:text-amber-100"]
            ].map(([label, value, tone]) => (
              <div
                key={label}
                className="flex items-center justify-between rounded-[8px] border border-white/10 bg-white/10 p-3 backdrop-blur-md dark:bg-white/5"
              >
                <span className="text-sm font-semibold text-slate-600 dark:text-white/55">{label}</span>
                <Badge className={tone}>{value}</Badge>
              </div>
            ))}
          </div>
        </Card>
      </section>

      {!isLoading && signals.length === 0 ? (
        <Card>
          <EmptyState
            title="No market signals yet"
            message="The dashboard is ready. Connect a signal API or run a backtest to populate charts, tables, and activity feeds."
            action={<Button icon={TrendingUp}>Create signal source</Button>}
          />
        </Card>
      ) : null}

      <Modal
        open={strategyOpen}
        onClose={() => setStrategyOpen(false)}
        title="Tune Model"
        footer={
          <>
            <Button variant="ghost" onClick={() => setStrategyOpen(false)}>
              Cancel
            </Button>
            <Button icon={Play} onClick={() => setStrategyOpen(false)}>
              Apply tuning
            </Button>
          </>
        }
      >
        <div className="grid gap-4">
          <Alert tone="info">Changes apply to simulation first, then require approval for live deployment.</Alert>
          <Input label="Confidence floor" placeholder="68%" />
          <Select label="Model profile" options={["Balanced", "Defensive", "Aggressive"]} />
          <ToggleSwitch label="Require risk officer approval" checked />
        </div>
      </Modal>
    </div>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value > 1000 ? 0 : 2
  }).format(value);
}

function candlesToSparkline(candles?: Array<{ close: number }>) {
  if (!candles?.length) {
    return [16, 24, 19, 34, 31, 44, 38];
  }

  return candles.slice(-7).map((candle) => candle.close);
}

function formatRelativeTime(value: string) {
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return "Just now";
  }

  const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (seconds < 60) {
    return `${seconds}s ago`;
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }

  return `${Math.floor(hours / 24)}d ago`;
}
