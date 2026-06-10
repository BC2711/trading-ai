import { Activity, CircleDollarSign, Landmark, PieChart, ShieldCheck, TrendingUp, Wallet } from "lucide-react";

import { PortfolioPerformanceChart, PortfolioPieChart } from "../components/portfolio/PortfolioCharts";
import { PortfolioMetricCard } from "../components/portfolio/PortfolioMetricCard";
import { OpenPositionAllocation, PortfolioPerformanceTable } from "../components/portfolio/PortfolioTables";
import { Alert } from "../components/ui/Alert";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";
import {
  usePortfolioAllocation,
  usePortfolioExposure,
  usePortfolioPerformance,
  usePortfolioPnl,
  usePortfolioSummary
} from "../hooks/usePortfolio";

export function PortfolioPage() {
  const summaryQuery = usePortfolioSummary();
  const performanceQuery = usePortfolioPerformance();
  const exposureQuery = usePortfolioExposure();
  const allocationQuery = usePortfolioAllocation();
  const pnlQuery = usePortfolioPnl();

  const summary = summaryQuery.data;
  const pnl = pnlQuery.data;
  const hasError = summaryQuery.isError || performanceQuery.isError || exposureQuery.isError || allocationQuery.isError || pnlQuery.isError;
  const isLoading = summaryQuery.isLoading || performanceQuery.isLoading || exposureQuery.isLoading || allocationQuery.isLoading || pnlQuery.isLoading;
  const exposureData = (exposureQuery.data?.items ?? summary?.exposure_by_symbol ?? []).map((item) => ({
    name: item.symbol,
    value: item.notional_value,
    percentage: item.exposure_pct
  }));
  const allocationData = (allocationQuery.data?.by_asset ?? summary?.allocation_by_asset ?? []).map((item) => ({
    name: item.asset,
    value: item.value,
    percentage: item.percentage
  }));
  const performanceData = (performanceQuery.data?.points ?? []).map((point, index) => ({
    label: `T${index + 1}`,
    equity: point.equity,
    totalPnl: point.total_pnl
  }));

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Wallet size={14} aria-hidden />
              Portfolio management
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Portfolio</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Track equity, available balance, margin, realized PnL, unrealized PnL, exposure, and open position allocation.
            </p>
          </div>
          <div className="grid min-w-[220px] gap-1 rounded-[8px] border border-white/10 bg-white/10 p-3 text-right backdrop-blur-md dark:bg-white/5">
            <span className="text-xs font-bold uppercase text-slate-500 dark:text-white/40">Open positions</span>
            <span className="text-2xl font-black text-slate-950 dark:text-white">{summary?.open_positions ?? 0}</span>
          </div>
        </div>
      </Card>

      {hasError ? <Alert tone="error">Unable to load portfolio data. Check the backend API and authentication state.</Alert> : null}

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
      ) : (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <PortfolioMetricCard label="Total Equity" value={formatCurrency(summary?.total_equity ?? 0)} detail="Realized plus open PnL" icon={CircleDollarSign} tone="cyan" />
          <PortfolioMetricCard label="Available Balance" value={formatCurrency(summary?.available_balance ?? 0)} detail="Equity after margin used" icon={Wallet} tone="emerald" />
          <PortfolioMetricCard label="Margin Used" value={formatCurrency(summary?.margin_used ?? 0)} detail={`${formatCurrency(summary?.margin_available ?? 0)} available`} icon={Landmark} tone="amber" />
          <PortfolioMetricCard label="Daily PnL" value={formatCurrency(pnl?.daily_pnl ?? summary?.daily_pnl ?? 0)} detail={`Weekly ${formatCurrency(pnl?.weekly_pnl ?? summary?.weekly_pnl ?? 0)}`} icon={Activity} tone={(pnl?.daily_pnl ?? summary?.daily_pnl ?? 0) >= 0 ? "emerald" : "rose"} />
          <PortfolioMetricCard label="Monthly PnL" value={formatCurrency(pnl?.monthly_pnl ?? summary?.monthly_pnl ?? 0)} detail={`Total ${formatCurrency(pnl?.total_pnl ?? 0)}`} icon={TrendingUp} tone={(pnl?.monthly_pnl ?? summary?.monthly_pnl ?? 0) >= 0 ? "emerald" : "rose"} />
          <PortfolioMetricCard label="Realized PnL" value={formatCurrency(pnl?.total_realized_pnl ?? summary?.total_realized_pnl ?? 0)} detail={`${summary?.closed_positions ?? 0} closed positions`} icon={ShieldCheck} tone="violet" />
          <PortfolioMetricCard label="Unrealized PnL" value={formatCurrency(pnl?.total_unrealized_pnl ?? summary?.total_unrealized_pnl ?? 0)} detail="Current open positions" icon={PieChart} tone={(pnl?.total_unrealized_pnl ?? summary?.total_unrealized_pnl ?? 0) >= 0 ? "emerald" : "rose"} />
          <PortfolioMetricCard label="Total Exposure" value={formatCurrency(exposureQuery.data?.total_exposure ?? summary?.total_exposure ?? 0)} detail={`Win rate ${formatPercent(pnl?.win_rate ?? summary?.win_rate ?? 0)}`} icon={Activity} tone="cyan" />
        </section>
      )}

      <section className="grid gap-4 xl:grid-cols-2 xl:gap-6">
        <PortfolioPieChart title="Exposure by Symbol" description="Open notional exposure grouped by symbol" data={exposureData} />
        <PortfolioPieChart title="Allocation by Asset" description="Open position value grouped by base asset" data={allocationData} />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)] xl:gap-6">
        <PortfolioPerformanceChart data={performanceData} />
        <OpenPositionAllocation positions={allocationQuery.data?.open_positions ?? summary?.open_position_allocation ?? []} />
      </section>

      <PortfolioPerformanceTable points={performanceQuery.data?.points ?? []} />
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
  return `${(value * 100).toFixed(1)}%`;
}
