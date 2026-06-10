import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { EmptyState } from "../table/EmptyState";
import { Card } from "../ui/Card";

type PieDatum = {
  name: string;
  value: number;
  percentage: number;
};

type PerformanceDatum = {
  label: string;
  equity: number;
  totalPnl: number;
};

const chartColors = ["#22d3ee", "#34d399", "#f59e0b", "#8b5cf6", "#f43f5e", "#14b8a6"];

export function PortfolioPieChart({ title, description, data }: { title: string; description: string; data: PieDatum[] }) {
  return (
    <Card className="p-4 sm:p-5">
      <ChartHeader title={title} description={description} />
      {data.length ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_190px]">
          <div className="h-[260px] min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="value" nameKey="name" innerRadius={54} outerRadius={92} paddingAngle={3}>
                  {data.map((item, index) => (
                    <Cell key={item.name} fill={chartColors[index % chartColors.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, _name, item) => [formatCurrency(Number(value)), `${item.payload.name} (${formatPercent(item.payload.percentage)})`]}
                  contentStyle={tooltipStyle}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid content-center gap-2">
            {data.map((item, index) => (
              <div key={item.name} className="flex items-center justify-between gap-3 rounded-[8px] border border-white/10 bg-white/10 px-3 py-2 dark:bg-white/5">
                <span className="flex min-w-0 items-center gap-2 text-sm font-bold text-slate-700 dark:text-white/70">
                  <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: chartColors[index % chartColors.length] }} />
                  <span className="truncate">{item.name}</span>
                </span>
                <span className="text-xs font-black text-slate-500 dark:text-white/45">{formatPercent(item.percentage)}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState title="No allocation yet" message="Open paper positions will populate this chart." />
      )}
    </Card>
  );
}

export function PortfolioPerformanceChart({ data }: { data: PerformanceDatum[] }) {
  return (
    <Card className="p-4 sm:p-5">
      <ChartHeader title="Portfolio Performance" description="Equity and total PnL over closed position events" />
      {data.length ? (
        <div className="mt-4 h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 18, right: 14, bottom: 0, left: -2 }}>
              <defs>
                <linearGradient id="portfolioEquity" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(148, 163, 184, 0.22)" vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }} className="text-slate-500 dark:text-white/50" />
              <YAxis tickLine={false} axisLine={false} tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }} className="text-slate-500 dark:text-white/50" tickFormatter={(value) => `$${Math.round(Number(value))}`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [formatCurrency(Number(value)), name === "equity" ? "Equity" : "Total PnL"]} />
              <Area type="monotone" dataKey="equity" stroke="#22d3ee" strokeWidth={3} fill="url(#portfolioEquity)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyState title="No performance history" message="Closed positions will create portfolio performance records." />
      )}
    </Card>
  );
}

function ChartHeader({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h2 className="text-lg font-black text-slate-950 dark:text-white">{title}</h2>
      <p className="text-sm font-medium text-slate-500 dark:text-white/50">{description}</p>
    </div>
  );
}

const tooltipStyle = {
  border: "1px solid rgba(255,255,255,0.2)",
  borderRadius: 8,
  background: "rgba(15, 23, 42, 0.82)",
  color: "#fff",
  boxShadow: "0 24px 60px rgba(15, 23, 42, 0.24)"
};

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
