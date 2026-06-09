import { motion } from "framer-motion";
import {
  Activity,
  ArrowUpRight,
  Bot,
  CircleDollarSign,
  Clock3,
  Download,
  Layers3,
  Play,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

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
  analyzeSignal,
  closePosition,
  createPaperOrder,
  fetchAIProviderStatus,
  fetchAIAnalyses,
  fetchBacktests,
  fetchCandles,
  fetchMarketDataSchedule,
  fetchOrders,
  fetchPositions,
  fetchRiskSettings,
  fetchStrategies,
  fetchSymbols,
  refreshMarketData,
  runBacktest,
  setAIProvider,
  updateRiskSettings,
  updateStrategy
} from "../services/api";
import type { AIAnalysis, AIProviderStatus } from "../services/api";
import { useSignals } from "../hooks/useSignals";
import { useTradingStore } from "../store/useTradingStore";
import { cn } from "../utils/cn";

export function DashboardPage() {
  const { signals, isLoading, isError } = useSignals();
  const { timeframe, setTimeframe } = useTradingStore();
  const [strategyOpen, setStrategyOpen] = useState(false);
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<AIAnalysis | null>(null);
  const [selectedAIProvider, setSelectedAIProvider] = useState("rules");
  const [activeTab, setActiveTab] = useState("Live");
  const [strategyForm, setStrategyForm] = useState({
    name: "",
    timeframe: "15m",
    status: "active",
    description: ""
  });
  const [riskForm, setRiskForm] = useState({
    maxRiskPerTrade: "1.0",
    maxDailyLoss: "3.0",
    maxOpenTrades: "3",
    maxSymbolExposure: "20.0"
  });
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
  const backtestsQuery = useQuery({
    queryKey: ["backtests"],
    queryFn: () => fetchBacktests(5)
  });
  const aiAnalysesQuery = useQuery({
    queryKey: ["ai-analyses"],
    queryFn: () => fetchAIAnalyses(5)
  });
  const aiProviderQuery = useQuery({
    queryKey: ["ai-provider-status"],
    queryFn: fetchAIProviderStatus,
    staleTime: 1000 * 60 * 5
  });
  const ordersQuery = useQuery({
    queryKey: ["orders"],
    queryFn: () => fetchOrders(8)
  });
  const positionsQuery = useQuery({
    queryKey: ["positions"],
    queryFn: () => fetchPositions()
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
  const backtestMutation = useMutation({
    mutationFn: () =>
      runBacktest({
        symbol: selectedSymbol,
        timeframe: backendTimeframe,
        initial_balance: 10000,
        lookback: 240
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backtests"] });
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
  const latestBacktest = backtestMutation.data ?? backtestsQuery.data?.[0];
  const latestAIAnalysis = selectedAnalysis ?? aiAnalysesQuery.data?.[0];
  const bestSignal = signals.reduce(
    (best, signal) => (signal.confidence > (best?.confidence ?? 0) ? signal : best),
    signals[0]
  );
  const confidenceSparkline = signals.length
    ? signals.map((signal) => Math.round(signal.confidence * 100)).slice(-7)
    : [12, 18, 16, 22, 20, 26, 24];

  useEffect(() => {
    if (activeStrategy) {
      setStrategyForm({
        name: activeStrategy.name,
        timeframe: activeStrategy.timeframe,
        status: activeStrategy.status,
        description: activeStrategy.description
      });
    }
  }, [activeStrategy]);

  useEffect(() => {
    if (riskSettings) {
      setRiskForm({
        maxRiskPerTrade: (riskSettings.max_risk_per_trade * 100).toFixed(1),
        maxDailyLoss: (riskSettings.max_daily_loss * 100).toFixed(1),
        maxOpenTrades: String(riskSettings.max_open_trades),
        maxSymbolExposure: (riskSettings.max_symbol_exposure * 100).toFixed(1)
      });
    }
  }, [riskSettings]);

  useEffect(() => {
    const syncRouteState = () => {
      if ((window.location.hash || "#/overview") === "#/overview/settings") {
        setStrategyOpen(true);
      }
    };

    syncRouteState();
    window.addEventListener("hashchange", syncRouteState);
    return () => window.removeEventListener("hashchange", syncRouteState);
  }, []);

  const settingsMutation = useMutation({
    mutationFn: async () => {
      if (!activeStrategy || !riskSettings) {
        throw new Error("Settings have not loaded yet");
      }

      const [strategy, risk] = await Promise.all([
        updateStrategy(activeStrategy.id, {
          name: strategyForm.name.trim(),
          timeframe: strategyForm.timeframe,
          status: strategyForm.status,
          description: strategyForm.description.trim()
        }),
        updateRiskSettings(riskSettings.id, {
          max_risk_per_trade: percentInputToDecimal(riskForm.maxRiskPerTrade),
          max_daily_loss: percentInputToDecimal(riskForm.maxDailyLoss),
          max_open_trades: Math.max(1, Number.parseInt(riskForm.maxOpenTrades, 10) || 1),
          max_symbol_exposure: percentInputToDecimal(riskForm.maxSymbolExposure)
        })
      ]);

      return { strategy, risk };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      queryClient.invalidateQueries({ queryKey: ["risk-settings"] });
      queryClient.invalidateQueries({ queryKey: ["backtests"] });
      setStrategyOpen(false);
    }
  });
  const analysisMutation = useMutation({
    mutationFn: analyzeSignal,
    onSuccess: (analysis) => {
      setSelectedAnalysis(analysis);
      queryClient.invalidateQueries({ queryKey: ["ai-analyses"] });
      setAnalysisOpen(true);
    }
  });
  const aiProviderStatus = aiProviderQuery.data;
  const aiProviderMutation = useMutation({
    mutationFn: (provider: string) => setAIProvider(provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-provider-status"] });
    }
  });

  useEffect(() => {
    if (aiProviderStatus?.provider) {
      setSelectedAIProvider(aiProviderStatus.provider);
    }
  }, [aiProviderStatus]);

  const activeAnalysis = selectedAnalysis ?? analysisMutation.data;
  const paperOrderMutation = useMutation({
    mutationFn: () => {
      if (!activeAnalysis) {
        throw new Error("AI analysis is required before creating a paper order");
      }

      return createPaperOrder({
        symbol: activeAnalysis.symbol,
        side: activeAnalysis.direction === "buy" || activeAnalysis.direction === "sell" ? activeAnalysis.direction : undefined,
        order_type: "market",
        signal_id: activeAnalysis.signal_id,
        ai_analysis_id: activeAnalysis.id
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["positions"] });
    }
  });
  const closePositionMutation = useMutation({
    mutationFn: closePosition,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["positions"] });
    }
  });

  const resetSettingsForm = () => {
    if (activeStrategy) {
      setStrategyForm({
        name: activeStrategy.name,
        timeframe: activeStrategy.timeframe,
        status: activeStrategy.status,
        description: activeStrategy.description
      });
    }

    if (riskSettings) {
      setRiskForm({
        maxRiskPerTrade: (riskSettings.max_risk_per_trade * 100).toFixed(1),
        maxDailyLoss: (riskSettings.max_daily_loss * 100).toFixed(1),
        maxOpenTrades: String(riskSettings.max_open_trades),
        maxSymbolExposure: (riskSettings.max_symbol_exposure * 100).toFixed(1)
      });
    }

    setStrategyOpen(false);
  };

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
      sparkline: latestBacktest ? backtestSparkline(latestBacktest.total_return) : [44, 39, 41, 36, 31, 28, 26]
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
        reason: signal.reason ?? "Generated by rule engine",
        signalId: signal.id ?? null,
        actions: "Explain"
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
            <Button icon={Play} loading={backtestMutation.isPending} onClick={() => backtestMutation.mutate()}>
              Run backtest
            </Button>
            <Button variant="secondary" icon={SlidersHorizontal} onClick={() => setStrategyOpen(true)}>
              Strategy controls
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
      {backtestMutation.isError ? (
        <Alert tone="warning">Backtest failed. Confirm there is enough candle history for {selectedSymbol} and try again.</Alert>
      ) : null}
      {backtestMutation.isSuccess ? (
        <Alert tone="success">
          Backtest completed for {backtestMutation.data.symbol}: {formatPercent(backtestMutation.data.total_return)} return, {formatPercent(backtestMutation.data.win_rate)} win rate.
        </Alert>
      ) : null}
      {settingsMutation.isError ? (
        <Alert tone="error">Unable to save strategy settings. Check the form values and try again.</Alert>
      ) : null}
      {settingsMutation.isSuccess ? <Alert tone="success">Strategy and risk settings saved.</Alert> : null}
      {analysisMutation.isError ? (
        <Alert tone="warning">Unable to explain this signal. Refresh market data and try again.</Alert>
      ) : null}
      {paperOrderMutation.isError ? (
        <Alert tone="error">Unable to create paper order. Check the linked AI analysis and current risk limits.</Alert>
      ) : null}
      {paperOrderMutation.isSuccess ? (
        <Alert tone={paperOrderMutation.data.status === "filled" ? "success" : "warning"}>
          Paper order {paperOrderMutation.data.status}: {paperOrderMutation.data.risk_message}
        </Alert>
      ) : null}
      {closePositionMutation.isError ? (
        <Alert tone="error">Unable to close paper position. Refresh positions and try again.</Alert>
      ) : null}
      {closePositionMutation.isSuccess ? (
        <Alert tone="success">
          Closed {closePositionMutation.data.symbol} {closePositionMutation.data.side} with realized PnL {formatCurrency(closePositionMutation.data.realized_pnl)}.
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
            <div className="rounded-[8px] border border-white/10 bg-white/10 p-4 backdrop-blur-lg dark:bg-white/5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-slate-900 dark:text-white">AI provider</p>
                  <p className="text-xs text-slate-500 dark:text-white/50">Choose the backend AI analysis provider.</p>
                </div>
                <Badge tone={aiProviderStatus?.provider === "openai" ? "success" : "info"}>
                  {aiProviderStatus?.provider ?? "loading..."}
                </Badge>
              </div>
              <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end">
                <div className="flex-1">
                  <Select
                    value={selectedAIProvider}
                    options={aiProviderStatus?.available_providers ?? ["rules", "openai"]}
                    onChange={(event) => setSelectedAIProvider(event.target.value)}
                    wrapperClassName="w-full"
                  />
                </div>
                <Button
                  loading={aiProviderMutation.isPending}
                  onClick={() => aiProviderMutation.mutate(selectedAIProvider)}
                  className="min-h-11"
                >
                  Set provider
                </Button>
              </div>
              <p className="mt-3 text-xs text-slate-500 dark:text-white/50">
                {aiProviderStatus
                  ? `OpenAI configured: ${aiProviderStatus.openai_available ? "yes" : "no"}.`
                  : "Loading provider configuration..."}
              </p>
            </div>
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
            { key: "updated", label: "Updated", align: "right" },
            {
              key: "actions",
              label: "AI",
              align: "right",
              render: (row) => (
                <Button
                  variant="outline"
                  icon={Sparkles}
                  loading={analysisMutation.isPending && analysisMutation.variables?.signal_id === (row.signalId ?? undefined)}
                  className="min-h-9 px-3"
                  onClick={() =>
                    analysisMutation.mutate({
                      signal_id: row.signalId ?? undefined,
                      symbol: row.symbol,
                      timeframe: row.timeframe,
                      lookback: 120
                    })
                  }
                >
                  Explain
                </Button>
              )
            }
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
                title: "Latest AI analysis",
                detail: latestAIAnalysis
                  ? `${latestAIAnalysis.symbol} ${latestAIAnalysis.direction.toUpperCase()} at ${formatUnsignedPercent(latestAIAnalysis.confidence)} confidence`
                  : "No AI explanation saved yet",
                time: latestAIAnalysis ? formatRelativeTime(latestAIAnalysis.generated_at) : "ready",
                icon: Sparkles
              },
              {
                title: "Paper trading",
                detail: `${positionsQuery.data?.length ?? 0} open positions, ${ordersQuery.data?.length ?? 0} recent orders`,
                time: ordersQuery.data?.[0] ? formatRelativeTime(ordersQuery.data[0].created_at) : "ready",
                icon: Target
              },
              {
                title: "Latest backtest",
                detail: latestBacktest
                  ? `${formatPercent(latestBacktest.total_return)} return, ${formatPercent(latestBacktest.win_rate)} win rate, ${latestBacktest.trades_count} trades`
                  : "No backtest run recorded yet",
                time: latestBacktest ? formatRelativeTime(latestBacktest.created_at) : "ready",
                icon: Play
              },
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
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Backend Strategy Controls</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">
                {strategyOpen
                  ? "Edit live strategy defaults and risk limits used by future backtests"
                  : "Current defaults from `/api/strategies` and `/api/risk-settings`"}
              </p>
            </div>
            {strategyOpen ? (
              <div className="flex flex-wrap items-center gap-2">
                <Button variant="ghost" onClick={resetSettingsForm}>
                  Cancel
                </Button>
                <Button
                  icon={Play}
                  loading={settingsMutation.isPending}
                  disabled={!activeStrategy || !riskSettings}
                  onClick={() => settingsMutation.mutate()}
                >
                  Save controls
                </Button>
              </div>
            ) : (
              <Button variant="secondary" icon={SlidersHorizontal} onClick={() => setStrategyOpen(true)}>
                Edit controls
              </Button>
            )}
          </div>

          {strategyOpen ? (
            <div className="grid gap-4">
              <Alert tone="info">Saved controls are applied to future backtests and dashboard risk summaries.</Alert>
              <div className="grid gap-4 md:grid-cols-2">
                <Input
                  label="Strategy name"
                  value={strategyForm.name}
                  onChange={(event) => setStrategyForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Strategy name"
                />
                <Select
                  label="Strategy timeframe"
                  options={["15m", "1h", "4h", "1d"]}
                  value={strategyForm.timeframe}
                  onChange={(event) => setStrategyForm((current) => ({ ...current, timeframe: event.target.value }))}
                />
                <Select
                  label="Strategy status"
                  options={["active", "draft", "paused"]}
                  value={strategyForm.status}
                  onChange={(event) => setStrategyForm((current) => ({ ...current, status: event.target.value }))}
                />
                <Input
                  label="Max open trades"
                  type="number"
                  min="1"
                  max="50"
                  value={riskForm.maxOpenTrades}
                  onChange={(event) => setRiskForm((current) => ({ ...current, maxOpenTrades: event.target.value }))}
                />
                <Input
                  label="Risk per trade (%)"
                  type="number"
                  min="0.1"
                  max="100"
                  step="0.1"
                  value={riskForm.maxRiskPerTrade}
                  onChange={(event) => setRiskForm((current) => ({ ...current, maxRiskPerTrade: event.target.value }))}
                />
                <Input
                  label="Daily loss limit (%)"
                  type="number"
                  min="0.1"
                  max="100"
                  step="0.1"
                  value={riskForm.maxDailyLoss}
                  onChange={(event) => setRiskForm((current) => ({ ...current, maxDailyLoss: event.target.value }))}
                />
                <Input
                  label="Symbol exposure (%)"
                  type="number"
                  min="0.1"
                  max="100"
                  step="0.1"
                  value={riskForm.maxSymbolExposure}
                  onChange={(event) => setRiskForm((current) => ({ ...current, maxSymbolExposure: event.target.value }))}
                />
                <Select
                  label="Market universe"
                  options={(symbolsQuery.data?.map((symbol) => symbol.symbol) ?? ["BTCUSDT", "ETHUSDT"])}
                  value={selectedSymbol}
                  disabled
                />
                <div className="md:col-span-2">
                  <Textarea
                    label="Strategy description"
                    value={strategyForm.description}
                    onChange={(event) => setStrategyForm((current) => ({ ...current, description: event.target.value }))}
                  />
                </div>
              </div>
            </div>
          ) : (
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
          )}
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
              ["AI analyses", `${aiAnalysesQuery.data?.length ?? 0}`, "bg-violet-400/15 text-violet-700 dark:text-violet-100"],
              ["Paper orders", `${ordersQuery.data?.length ?? 0}`, "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100"],
              ["Open positions", `${positionsQuery.data?.length ?? 0}`, "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100"],
              ["Backtest return", latestBacktest ? formatPercent(latestBacktest.total_return) : "Not run", "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100"],
              ["Max drawdown", latestBacktest ? formatPercent(latestBacktest.max_drawdown) : "Not run", "bg-rose-400/15 text-rose-700 dark:text-rose-100"],
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

          {aiAnalysesQuery.data?.length ? (
            <div className="mt-5 border-t border-white/10 pt-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-black text-slate-950 dark:text-white">Recent AI Insights</h3>
                <Badge tone="info">{aiAnalysesQuery.data.length}</Badge>
              </div>
              <div className="grid gap-2">
                {aiAnalysesQuery.data.slice(0, 3).map((analysis) => (
                  <button
                    key={analysis.id}
                    type="button"
                    onClick={() => {
                      setSelectedAnalysis(analysis);
                      setAnalysisOpen(true);
                    }}
                    className="group rounded-[8px] border border-white/10 bg-white/10 p-3 text-left backdrop-blur-md transition hover:bg-white/15 dark:bg-white/5"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-black text-slate-900 dark:text-white">
                        {analysis.symbol} {analysis.direction.toUpperCase()}
                      </span>
                      <span className="text-xs font-bold text-slate-400 transition group-hover:text-cyan-500 dark:text-white/40">
                        {formatRelativeTime(analysis.generated_at)}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs font-medium leading-5 text-slate-500 dark:text-white/50">
                      {analysis.suggested_action}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {ordersQuery.data?.length || positionsQuery.data?.length ? (
            <div className="mt-5 border-t border-white/10 pt-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-black text-slate-950 dark:text-white">Paper Trading</h3>
                <Badge tone={positionsQuery.data?.length ? "success" : "neutral"}>
                  {positionsQuery.data?.length ?? 0} open
                </Badge>
              </div>
              <div className="grid gap-2">
                {positionsQuery.data?.slice(0, 2).map((position) => (
                  <div
                    key={position.id}
                    className="rounded-[8px] border border-white/10 bg-white/10 p-3 backdrop-blur-md dark:bg-white/5"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-black text-slate-900 dark:text-white">
                        {position.symbol} {position.side.toUpperCase()}
                      </span>
                      <span className={cn("text-xs font-bold", position.unrealized_pnl >= 0 ? "text-emerald-600 dark:text-emerald-300" : "text-rose-600 dark:text-rose-300")}>
                        {formatCurrency(position.unrealized_pnl)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs font-medium text-slate-500 dark:text-white/50">
                      {position.quantity.toFixed(6)} @ {formatCurrency(position.avg_entry_price)}
                    </p>
                    <div className="mt-3 flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-slate-500 dark:text-white/45">
                        Mark {formatCurrency(position.mark_price)}
                      </span>
                      <Button
                        variant="outline"
                        className="min-h-8 px-3 py-1 text-xs"
                        loading={closePositionMutation.isPending && closePositionMutation.variables === position.id}
                        onClick={() => closePositionMutation.mutate(position.id)}
                      >
                        Close
                      </Button>
                    </div>
                  </div>
                ))}
                {ordersQuery.data?.slice(0, 2).map((order) => (
                  <div
                    key={order.id}
                    className="flex items-center justify-between rounded-[8px] border border-white/10 bg-white/10 p-3 backdrop-blur-md dark:bg-white/5"
                  >
                    <div>
                      <p className="text-sm font-black text-slate-900 dark:text-white">
                        {order.symbol} {order.side.toUpperCase()}
                      </p>
                      <p className="text-xs font-medium text-slate-500 dark:text-white/50">{order.risk_message}</p>
                    </div>
                    <Badge tone={order.status === "filled" ? "success" : "warning"}>{order.status}</Badge>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
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
        open={analysisOpen}
        onClose={() => setAnalysisOpen(false)}
        title={activeAnalysis ? `${activeAnalysis.symbol} AI Signal Analysis` : "AI Signal Analysis"}
        footer={
          <>
            <Button variant="ghost" onClick={() => setAnalysisOpen(false)}>
              Close
            </Button>
            <Button
              icon={Target}
              loading={paperOrderMutation.isPending}
              disabled={!activeAnalysis || !["buy", "sell"].includes(activeAnalysis.direction)}
              onClick={() => paperOrderMutation.mutate()}
            >
              Create paper order
            </Button>
          </>
        }
      >
        {activeAnalysis ? (
          <div className="grid gap-4">
            <Alert tone="info">
              {activeAnalysis.provider} analysis generated {formatRelativeTime(activeAnalysis.generated_at)}
            </Alert>
            <div className="rounded-[8px] border border-white/10 bg-white/10 p-4 backdrop-blur-lg dark:bg-white/5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={activeAnalysis.direction === "sell" ? "error" : activeAnalysis.direction === "buy" ? "success" : "info"}>
                  {activeAnalysis.direction.toUpperCase()}
                </Badge>
                <Badge>{formatUnsignedPercent(activeAnalysis.confidence)} confidence</Badge>
                <Badge>{activeAnalysis.timeframe}</Badge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-white/65">{activeAnalysis.explanation}</p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[8px] border border-white/10 bg-white/10 p-4 backdrop-blur-lg dark:bg-white/5">
                <h3 className="text-sm font-black text-slate-950 dark:text-white">Reasoning</h3>
                <ul className="mt-3 grid gap-2 text-sm text-slate-600 dark:text-white/60">
                  {activeAnalysis.reasoning.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-[8px] border border-white/10 bg-white/10 p-4 backdrop-blur-lg dark:bg-white/5">
                <h3 className="text-sm font-black text-slate-950 dark:text-white">Risk Notes</h3>
                <ul className="mt-3 grid gap-2 text-sm text-slate-600 dark:text-white/60">
                  {activeAnalysis.risk_notes.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="rounded-[8px] border border-white/10 bg-white/10 p-4 backdrop-blur-lg dark:bg-white/5">
              <h3 className="text-sm font-black text-slate-950 dark:text-white">Suggested Action</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-white/65">{activeAnalysis.suggested_action}</p>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {Object.entries(activeAnalysis.indicators).map(([label, value]) => (
                <div key={label} className="rounded-[8px] border border-white/10 bg-white/10 p-3 backdrop-blur-lg dark:bg-white/5">
                  <p className="text-xs font-bold uppercase text-slate-500 dark:text-white/40">{label.replace("_", " ")}</p>
                  <p className="mt-1 text-sm font-black text-slate-950 dark:text-white">{value.toFixed(2)}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <Skeleton className="h-48" />
        )}
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

function backtestSparkline(totalReturn: number) {
  const baseline = 36;
  const drift = Math.max(-18, Math.min(22, totalReturn * 220));

  return [baseline - 8, baseline - 4, baseline - 6, baseline + 2, baseline + drift * 0.35, baseline + drift * 0.7, baseline + drift];
}

function formatPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function formatUnsignedPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function percentInputToDecimal(value: string) {
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) {
    return 0.01;
  }

  return Math.min(1, Math.max(0.001, parsed / 100));
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
