import { motion } from "framer-motion";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
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
import { useMutation, useQueryClient } from "@tanstack/react-query";
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
import { syncMarketData } from "../services/api";
import { useSignals } from "../hooks/useSignals";
import { useTradingStore } from "../store/useTradingStore";
import { cn } from "../utils/cn";

const metrics = [
  {
    label: "Portfolio Equity",
    value: "$100,000",
    trend: "+1.8% today",
    trendDirection: "up" as const,
    tone: "cyan" as const,
    icon: CircleDollarSign,
    sparkline: [24, 30, 28, 42, 46, 51, 56]
  },
  {
    label: "Open Risk",
    value: "2.4%",
    trend: "Within target",
    trendDirection: "flat" as const,
    tone: "emerald" as const,
    icon: ShieldCheck,
    sparkline: [30, 26, 25, 22, 24, 20, 19]
  },
  {
    label: "Model Confidence",
    value: "69%",
    trend: "2 markets watched",
    trendDirection: "up" as const,
    tone: "violet" as const,
    icon: Bot,
    sparkline: [32, 34, 36, 35, 43, 47, 49]
  },
  {
    label: "Execution Drift",
    value: "0.7%",
    trend: "-0.2% vs plan",
    trendDirection: "down" as const,
    tone: "amber" as const,
    icon: Target,
    sparkline: [44, 39, 41, 36, 31, 28, 26]
  }
];

export function DashboardPage() {
  const { signals, isLoading, isError } = useSignals();
  const { timeframe, setTimeframe } = useTradingStore();
  const [strategyOpen, setStrategyOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("Live");
  const queryClient = useQueryClient();
  const syncMutation = useMutation({
    mutationFn: () =>
      syncMarketData({
        symbols: ["BTCUSDT", "ETHUSDT"],
        timeframe,
        limit: 500,
        regenerate_signals: true
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signals"] });
    }
  });

  const tableRows = useMemo(
    () =>
      signals.map((signal) => ({
        id: signal.symbol,
        symbol: signal.symbol,
        direction: signal.direction,
        confidence: Math.round(signal.confidence * 100),
        exposure: signal.direction.toLowerCase().includes("sell") ? "Reduce" : "Build",
        updated: "Just now"
      })),
    [signals]
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
              Monitor model confidence, risk exposure, execution quality, and active signals from one responsive glass control surface.
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
          Synced {syncMutation.data.results.reduce((total, result) => total + result.fetched, 0)} candles from {syncMutation.data.provider}.
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
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">Runbook controls</p>
            </div>
            <Badge tone="success">Online</Badge>
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
              Sync market data
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
            { key: "exposure", label: "Exposure" },
            { key: "updated", label: "Updated", align: "right" }
          ]}
          rows={tableRows}
          loading={isLoading}
          emptyTitle="No active signals"
        />

        <Card className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Activity Timeline</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">Recent activity</p>
            </div>
            <Clock3 size={18} className="text-slate-400 dark:text-white/40" aria-hidden />
          </div>
          <div className="mt-5 grid gap-4">
            {[
              { title: "Model retrained", detail: "Signal threshold tightened to 68%", time: "08:42", icon: Bot },
              { title: "Risk guard passed", detail: "Max drawdown remains below policy", time: "08:31", icon: ShieldCheck },
              { title: "Backtest completed", detail: "4h strategy produced 1.8 Sharpe", time: "08:12", icon: BarChart3 }
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
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Strategy Controls</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">Glass form inputs with validation-ready states</p>
            </div>
            <Calendar size={18} className="text-slate-400 dark:text-white/40" aria-hidden />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Input label="Strategy name" placeholder="Mean reversion v4" />
            <Select label="Market universe" options={["Crypto majors", "US equities", "FX liquid pairs"]} />
            <Input label="Risk limit" placeholder="2.5%" error="Review limit before deployment" />
            <Select label="Rebalance cadence" options={["15 minutes", "Hourly", "Daily"]} />
            <div className="md:col-span-2">
              <Textarea label="Research note" placeholder="Document thesis, invalidation level, and execution guardrails" />
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
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Summary</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">Operational posture</p>
            </div>
            <Activity size={18} className="text-slate-400 dark:text-white/40" aria-hidden />
          </div>
          <div className="mt-5 grid gap-3">
            {[
              ["Data quality", "98.4%", "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100"],
              ["Fill efficiency", "94.1%", "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100"],
              ["Alert load", "Normal", "bg-violet-400/15 text-violet-700 dark:text-violet-100"],
              ["Drawdown", "1.2%", "bg-amber-400/15 text-amber-700 dark:text-amber-100"]
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
