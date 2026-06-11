import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { AnalyticsEquityCurve } from "../../api/performanceAnalyticsApi";
import { EmptyState } from "../table/EmptyState";
import { Card } from "../ui/Card";

export function EquityCurveChart({ curve }: { curve?: AnalyticsEquityCurve }) {
  const data = (curve?.points ?? []).map((point, index) => ({
    label: formatDate(point.timestamp, index),
    equity: point.equity,
    realizedPnl: point.realized_pnl,
  }));

  return (
    <Card className="p-4 sm:p-5">
      <Header title="Equity Curve" detail={`${formatCurrency(curve?.starting_equity ?? 0)} starting equity`} />
      {data.length ? (
        <div className="mt-4 h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 18, right: 16, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="analyticsEquity" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(148, 163, 184, 0.22)" vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }} className="text-slate-500 dark:text-white/50" />
              <YAxis tickLine={false} axisLine={false} tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }} className="text-slate-500 dark:text-white/50" tickFormatter={(value) => `$${Math.round(Number(value))}`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [formatCurrency(Number(value)), name === "equity" ? "Equity" : "Realized PnL"]} />
              <Area type="monotone" dataKey="equity" stroke="#22d3ee" strokeWidth={3} fill="url(#analyticsEquity)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyState title="No equity curve yet" message="Closed trades will populate realized performance." />
      )}
    </Card>
  );
}

export function DrawdownChart({ curve }: { curve?: AnalyticsEquityCurve }) {
  const data = (curve?.points ?? []).map((point, index) => ({
    label: formatDate(point.timestamp, index),
    drawdown: -point.drawdown * 100,
  }));

  return (
    <Card className="p-4 sm:p-5">
      <Header title="Drawdown" detail={`Max drawdown ${formatPercent(curve?.max_drawdown ?? 0)}`} />
      {data.length ? (
        <div className="mt-4 h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 18, right: 16, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="analyticsDrawdown" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#fb7185" stopOpacity={0.1} />
                  <stop offset="100%" stopColor="#fb7185" stopOpacity={0.45} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(148, 163, 184, 0.22)" vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }} className="text-slate-500 dark:text-white/50" />
              <YAxis tickLine={false} axisLine={false} tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }} className="text-slate-500 dark:text-white/50" tickFormatter={(value) => `${Number(value).toFixed(1)}%`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`${Number(value).toFixed(2)}%`, "Drawdown"]} />
              <Area type="monotone" dataKey="drawdown" stroke="#fb7185" strokeWidth={2} fill="url(#analyticsDrawdown)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyState title="No drawdown yet" message="Closed trades will create a drawdown path." />
      )}
    </Card>
  );
}

function Header({ title, detail }: { title: string; detail: string }) {
  return (
    <div>
      <h2 className="text-lg font-black text-slate-950 dark:text-white">{title}</h2>
      <p className="text-sm font-medium text-slate-500 dark:text-white/50">{detail}</p>
    </div>
  );
}

const tooltipStyle = {
  border: "1px solid rgba(255,255,255,0.2)",
  borderRadius: 8,
  background: "rgba(15, 23, 42, 0.86)",
  color: "#fff",
  boxShadow: "0 24px 60px rgba(15, 23, 42, 0.24)",
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: Math.abs(value) > 1000 ? 0 : 2,
  }).format(value);
}

function formatDate(value: string, index: number) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return `T${index + 1}`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}
