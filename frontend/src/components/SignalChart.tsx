import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import type { Signal } from "../types/signal";

type SignalChartProps = {
  signals: Signal[];
};

export function SignalChart({ signals }: SignalChartProps) {
  const data = signals.map((signal) => ({
    symbol: signal.symbol,
    confidence: Math.round(signal.confidence * 100)
  }));

  return (
    <div
      className="relative min-h-[280px] overflow-hidden rounded-[8px] border border-white/20 bg-white/10 p-4 shadow-xl shadow-slate-950/10 backdrop-blur-lg dark:border-white/10 dark:bg-white/5 dark:shadow-black/20"
      aria-label="Signal confidence chart"
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-300/10 via-transparent to-violet-400/10" />
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} margin={{ top: 18, right: 16, bottom: 0, left: -12 }}>
          <defs>
            <linearGradient id="confidenceGradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.95} />
              <stop offset="52%" stopColor="#6366f1" stopOpacity={0.8} />
              <stop offset="100%" stopColor="#a855f7" stopOpacity={0.45} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(148, 163, 184, 0.22)" vertical={false} />
          <XAxis
            dataKey="symbol"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }}
            className="text-slate-500 dark:text-white/50"
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
            tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }}
            className="text-slate-500 dark:text-white/50"
          />
          <Tooltip
            cursor={{ fill: "rgba(255, 255, 255, 0.08)" }}
            contentStyle={{
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: 8,
              background: "rgba(15, 23, 42, 0.72)",
              backdropFilter: "blur(18px)",
              color: "#fff",
              boxShadow: "0 24px 60px rgba(15, 23, 42, 0.24)"
            }}
            formatter={(value) => [`${value}%`, "Confidence"]}
            labelStyle={{ color: "rgba(255,255,255,0.72)", fontWeight: 700 }}
          />
          <Bar dataKey="confidence" fill="url(#confidenceGradient)" radius={[8, 8, 0, 0]} animationDuration={900} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
