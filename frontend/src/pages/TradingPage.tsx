import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Ban, CheckCircle2, Clock3, Coins, ShieldAlert, TrendingUp, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";
import { Select } from "../components/ui/Select";
import {
  cancelOrder,
  closePosition,
  fetchEquityCurve,
  fetchOrders,
  fetchPortfolioSummary,
  fetchPositions
} from "../services/api";
import type { EquityCurvePoint, OrderStatusFilter, PaperOrder, PaperPosition, PositionStatusFilter } from "../services/api";
import { cn } from "../utils/cn";

export function TradingPage() {
  const queryClient = useQueryClient();
  const [orderStatus, setOrderStatus] = useState<OrderStatusFilter>("all");
  const [positionStatus, setPositionStatus] = useState<PositionStatusFilter>("open");

  const ordersQuery = useQuery({
    queryKey: ["orders", orderStatus],
    queryFn: () => fetchOrders(50, orderStatus)
  });
  const positionsQuery = useQuery({
    queryKey: ["positions", positionStatus],
    queryFn: () => fetchPositions(positionStatus)
  });
  const portfolioSummaryQuery = useQuery({
    queryKey: ["portfolio-summary"],
    queryFn: fetchPortfolioSummary
  });
  const equityCurveQuery = useQuery({
    queryKey: ["equity-curve"],
    queryFn: fetchEquityCurve
  });

  const closeMutation = useMutation({
    mutationFn: closePosition,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-summary"] });
      queryClient.invalidateQueries({ queryKey: ["equity-curve"] });
    }
  });

  const cancelMutation = useMutation({
    mutationFn: cancelOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    }
  });

  const summary = useMemo(() => buildSummary(positionsQuery.data ?? [], ordersQuery.data ?? []), [ordersQuery.data, positionsQuery.data]);
  const portfolioSummary = portfolioSummaryQuery.data;

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Activity size={14} aria-hidden />
              Paper execution workspace
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Trading book</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Manage paper orders, open positions, realized PnL, and risk-blocked attempts from a dedicated operational surface.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Select
              aria-label="Position status"
              options={[
                { label: "Open positions", value: "open" },
                { label: "Closed positions", value: "closed" },
                { label: "All positions", value: "all" }
              ]}
              value={positionStatus}
              onChange={(event) => setPositionStatus(event.target.value as PositionStatusFilter)}
            />
            <Select
              aria-label="Order status"
              options={[
                { label: "All orders", value: "all" },
                { label: "Filled", value: "filled" },
                { label: "Rejected", value: "rejected" },
                { label: "Cancelled", value: "cancelled" }
              ]}
              value={orderStatus}
              onChange={(event) => setOrderStatus(event.target.value as OrderStatusFilter)}
            />
          </div>
        </div>
      </Card>

      {closeMutation.isSuccess ? (
        <Alert tone="success">
          Closed {closeMutation.data.symbol} {closeMutation.data.side}; realized PnL {formatCurrency(closeMutation.data.realized_pnl)}.
        </Alert>
      ) : null}
      {closeMutation.isError ? <Alert tone="error">Unable to close position.</Alert> : null}
      {cancelMutation.isSuccess ? <Alert tone="success">Order {cancelMutation.data.id} cancelled.</Alert> : null}
      {cancelMutation.isError ? <Alert tone="warning">Unable to cancel this order.</Alert> : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Open Exposure" value={formatCurrency(portfolioSummary?.total_exposure ?? summary.openExposure)} icon={Coins} tone="cyan" />
        <SummaryCard label="Unrealized PnL" value={formatCurrency(portfolioSummary?.unrealized_pnl ?? summary.unrealizedPnl)} icon={TrendingUp} tone={(portfolioSummary?.unrealized_pnl ?? summary.unrealizedPnl) >= 0 ? "emerald" : "rose"} />
        <SummaryCard label="Realized PnL" value={formatCurrency(portfolioSummary?.realized_pnl ?? summary.realizedPnl)} icon={CheckCircle2} tone={(portfolioSummary?.realized_pnl ?? summary.realizedPnl) >= 0 ? "emerald" : "rose"} />
        <SummaryCard label="Win Rate" value={formatPercent(portfolioSummary?.win_rate ?? 0)} icon={ShieldAlert} tone="amber" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)] xl:gap-6">
        <Card className="p-4 sm:p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Equity Curve</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">Realized paper PnL over closed positions</p>
            </div>
            <Badge tone="info">{equityCurveQuery.data?.points.length ?? 0} closes</Badge>
          </div>
          {equityCurveQuery.isLoading ? (
            <Skeleton className="h-[260px]" />
          ) : (
            <EquityCurveChart points={equityCurveQuery.data?.points ?? []} startingEquity={equityCurveQuery.data?.starting_equity ?? 10000} />
          )}
        </Card>

        <Card className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Order Quality</h2>
              <p className="text-sm font-medium text-slate-500 dark:text-white/50">Execution and risk outcomes</p>
            </div>
            <Activity size={18} className="text-slate-400 dark:text-white/40" aria-hidden />
          </div>
          <div className="mt-5 grid gap-3">
            {[
              ["Filled", `${portfolioSummary?.filled_orders ?? 0}`, "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100"],
              ["Rejected", `${portfolioSummary?.rejected_orders ?? 0}`, "bg-rose-400/15 text-rose-700 dark:text-rose-100"],
              ["Cancelled", `${portfolioSummary?.cancelled_orders ?? 0}`, "bg-white/10 text-slate-600 dark:text-white/70"],
              ["Closed trades", `${portfolioSummary?.closed_positions ?? 0}`, "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100"],
              ["Best trade", portfolioSummary?.best_trade_pnl == null ? "n/a" : formatCurrency(portfolioSummary.best_trade_pnl), "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100"],
              ["Worst trade", portfolioSummary?.worst_trade_pnl == null ? "n/a" : formatCurrency(portfolioSummary.worst_trade_pnl), "bg-rose-400/15 text-rose-700 dark:text-rose-100"]
            ].map(([label, value, tone]) => (
              <div key={label} className="flex items-center justify-between rounded-[8px] border border-white/10 bg-white/10 p-3 backdrop-blur-md dark:bg-white/5">
                <span className="text-sm font-semibold text-slate-600 dark:text-white/55">{label}</span>
                <Badge className={tone}>{value}</Badge>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] xl:gap-6">
        <Card className="p-0">
          <PanelHeader title="Positions" description={`${positionsQuery.data?.length ?? 0} matching paper positions`} />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="bg-white/20 text-xs uppercase text-slate-500 backdrop-blur-lg dark:bg-white/5 dark:text-white/45">
                <tr>
                  {["Symbol", "Side", "Qty", "Entry", "Mark", "Unrealized", "Realized", "Status", "Action"].map((header) => (
                    <th key={header} className="border-b border-white/10 px-4 py-3 text-left font-black">{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {positionsQuery.isLoading ? (
                  <LoadingRows columns={9} />
                ) : positionsQuery.data?.length ? (
                  positionsQuery.data.map((position) => (
                    <tr key={position.id} className="transition hover:bg-white/10 dark:hover:bg-white/5">
                      <td className="border-b border-white/10 px-4 py-4 font-black text-slate-950 dark:text-white">{position.symbol}</td>
                      <td className="border-b border-white/10 px-4 py-4"><Badge tone={position.side === "long" ? "success" : "warning"}>{position.side}</Badge></td>
                      <td className="border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/70">{position.quantity.toFixed(6)}</td>
                      <td className="border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/70">{formatCurrency(position.avg_entry_price)}</td>
                      <td className="border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/70">{formatCurrency(position.mark_price)}</td>
                      <MoneyCell value={position.unrealized_pnl} />
                      <MoneyCell value={position.realized_pnl} />
                      <td className="border-b border-white/10 px-4 py-4"><Badge tone={position.status === "open" ? "info" : "neutral"}>{position.status}</Badge></td>
                      <td className="border-b border-white/10 px-4 py-4">
                        <Button
                          variant="outline"
                          className="min-h-9 px-3"
                          disabled={position.status !== "open"}
                          loading={closeMutation.isPending && closeMutation.variables === position.id}
                          onClick={() => closeMutation.mutate(position.id)}
                        >
                          Close
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <EmptyRow columns={9} message="No positions match this filter." />
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <Card className="p-0">
          <PanelHeader title="Orders" description={`${ordersQuery.data?.length ?? 0} recent paper orders`} />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="bg-white/20 text-xs uppercase text-slate-500 backdrop-blur-lg dark:bg-white/5 dark:text-white/45">
                <tr>
                  {["Symbol", "Side", "Qty", "Price", "Status", "Risk", "Created", "Action"].map((header) => (
                    <th key={header} className="border-b border-white/10 px-4 py-3 text-left font-black">{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ordersQuery.isLoading ? (
                  <LoadingRows columns={8} />
                ) : ordersQuery.data?.length ? (
                  ordersQuery.data.map((order) => (
                    <tr key={order.id} className="transition hover:bg-white/10 dark:hover:bg-white/5">
                      <td className="border-b border-white/10 px-4 py-4 font-black text-slate-950 dark:text-white">{order.symbol}</td>
                      <td className="border-b border-white/10 px-4 py-4"><Badge tone={order.side === "buy" ? "success" : "warning"}>{order.side}</Badge></td>
                      <td className="border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/70">{order.quantity.toFixed(6)}</td>
                      <td className="border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/70">{formatCurrency(order.fill_price ?? order.requested_price)}</td>
                      <td className="border-b border-white/10 px-4 py-4"><OrderStatusBadge order={order} /></td>
                      <td className="max-w-[240px] border-b border-white/10 px-4 py-4 text-xs leading-5 text-slate-500 dark:text-white/50">{order.risk_message}</td>
                      <td className="border-b border-white/10 px-4 py-4 text-slate-500 dark:text-white/50">{formatRelativeTime(order.created_at)}</td>
                      <td className="border-b border-white/10 px-4 py-4">
                        <Button
                          variant="ghost"
                          className="min-h-9 px-3"
                          disabled={order.status === "filled" || order.status === "cancelled"}
                          loading={cancelMutation.isPending && cancelMutation.variables === order.id}
                          onClick={() => cancelMutation.mutate(order.id)}
                        >
                          Cancel
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <EmptyRow columns={8} message="No orders match this filter." />
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </section>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  icon: Icon,
  tone
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  tone: "cyan" | "emerald" | "amber" | "rose";
}) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-slate-500 dark:text-white/50">{label}</p>
          <p className="mt-3 text-2xl font-black text-slate-950 dark:text-white">{value}</p>
        </div>
        <span
          className={cn(
            "grid size-11 place-items-center rounded-[8px]",
            tone === "cyan" && "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100",
            tone === "emerald" && "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100",
            tone === "amber" && "bg-amber-400/15 text-amber-700 dark:text-amber-100",
            tone === "rose" && "bg-rose-400/15 text-rose-700 dark:text-rose-100"
          )}
        >
          <Icon size={20} aria-hidden />
        </span>
      </div>
    </Card>
  );
}

function PanelHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex items-center justify-between border-b border-white/10 p-4">
      <div>
        <h2 className="text-base font-black text-slate-950 dark:text-white">{title}</h2>
        <p className="text-xs font-medium text-slate-500 dark:text-white/50">{description}</p>
      </div>
      <Clock3 size={18} className="text-slate-400 dark:text-white/40" aria-hidden />
    </div>
  );
}

function EquityCurveChart({ points, startingEquity }: { points: EquityCurvePoint[]; startingEquity: number }) {
  const data = points.length
    ? points.map((point, index) => ({
        label: `T${index + 1}`,
        equity: point.equity,
        pnl: point.realized_pnl
      }))
    : [{ label: "Start", equity: startingEquity, pnl: 0 }];

  return (
    <div className="relative min-h-[260px] overflow-hidden rounded-[8px] border border-white/20 bg-white/10 p-4 shadow-xl shadow-slate-950/10 backdrop-blur-lg dark:border-white/10 dark:bg-white/5 dark:shadow-black/20">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-300/10 via-transparent to-emerald-400/10" />
      <ResponsiveContainer width="100%" height={235}>
        <LineChart data={data} margin={{ top: 18, right: 16, bottom: 0, left: -4 }}>
          <defs>
            <linearGradient id="equityGradient" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.95} />
              <stop offset="100%" stopColor="#34d399" stopOpacity={0.95} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(148, 163, 184, 0.22)" vertical={false} />
          <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }} className="text-slate-500 dark:text-white/50" />
          <YAxis tickLine={false} axisLine={false} tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }} className="text-slate-500 dark:text-white/50" tickFormatter={(value) => `$${Math.round(value)}`} />
          <Tooltip
            cursor={{ stroke: "rgba(34, 211, 238, 0.35)" }}
            contentStyle={{
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: 8,
              background: "rgba(15, 23, 42, 0.72)",
              backdropFilter: "blur(18px)",
              color: "#fff",
              boxShadow: "0 24px 60px rgba(15, 23, 42, 0.24)"
            }}
            formatter={(value, name) => [formatCurrency(Number(value)), name === "equity" ? "Equity" : "Realized PnL"]}
            labelStyle={{ color: "rgba(255,255,255,0.72)", fontWeight: 700 }}
          />
          <Line type="monotone" dataKey="equity" stroke="url(#equityGradient)" strokeWidth={3} dot={{ r: 4, fill: "#22d3ee" }} activeDot={{ r: 6 }} animationDuration={900} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function MoneyCell({ value }: { value: number }) {
  return (
    <td className={cn("border-b border-white/10 px-4 py-4 font-bold", value >= 0 ? "text-emerald-600 dark:text-emerald-300" : "text-rose-600 dark:text-rose-300")}>
      {formatCurrency(value)}
    </td>
  );
}

function OrderStatusBadge({ order }: { order: PaperOrder }) {
  if (order.status === "filled") {
    return <Badge tone="success"><CheckCircle2 size={12} aria-hidden /> filled</Badge>;
  }
  if (order.status === "cancelled") {
    return <Badge tone="neutral"><Ban size={12} aria-hidden /> cancelled</Badge>;
  }
  return <Badge tone="warning"><XCircle size={12} aria-hidden /> {order.status}</Badge>;
}

function LoadingRows({ columns }: { columns: number }) {
  return (
    <>
      {Array.from({ length: 4 }).map((_, index) => (
        <tr key={index}>
          <td colSpan={columns} className="px-4 py-3">
            <Skeleton className="h-11 w-full" />
          </td>
        </tr>
      ))}
    </>
  );
}

function EmptyRow({ columns, message }: { columns: number; message: string }) {
  return (
    <tr>
      <td colSpan={columns} className="px-4 py-10 text-center text-sm font-semibold text-slate-500 dark:text-white/50">
        {message}
      </td>
    </tr>
  );
}

function buildSummary(positions: PaperPosition[], orders: PaperOrder[]) {
  return {
    openExposure: positions
      .filter((position) => position.status === "open")
      .reduce((total, position) => total + position.quantity * position.mark_price, 0),
    unrealizedPnl: positions.reduce((total, position) => total + position.unrealized_pnl, 0),
    realizedPnl: positions.reduce((total, position) => total + position.realized_pnl, 0),
    blockedOrders: orders.filter((order) => order.risk_status === "blocked" || order.status === "rejected").length
  };
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
