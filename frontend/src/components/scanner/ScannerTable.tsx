import { motion } from "framer-motion";
import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";

import type { ScannerResult } from "../../api/scannerApi";
import { cn } from "../../utils/cn";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { Skeleton } from "../ui/LoadingSpinner";
import { EmptyState } from "../table/EmptyState";

type ScannerTableProps = {
  results: ScannerResult[];
  loading?: boolean;
};

export function ScannerTable({ results, loading = false }: ScannerTableProps) {
  return (
    <Card className="p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-4">
        <div>
          <h3 className="text-base font-bold text-slate-950 dark:text-white">Symbols</h3>
          <p className="text-xs font-medium text-slate-500 dark:text-white/50">
            Live scanner output across trend, momentum, risk, and volatility
          </p>
        </div>
        <span className="rounded-[8px] border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold text-slate-600 dark:text-white/60">
          {results.length} rows
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1040px] border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 z-10 bg-white/30 backdrop-blur-xl dark:bg-slate-950/40">
            <tr>
              {[
                "Symbol",
                "Price",
                "Signal",
                "Confidence",
                "Risk",
                "RSI",
                "MACD",
                "Trend",
                "Volatility",
                "Recommended Action",
                "Created"
              ].map((label) => (
                <th
                  key={label}
                  className="border-b border-white/10 px-4 py-3 text-left text-xs font-bold uppercase tracking-normal text-slate-500 dark:text-white/50"
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 5 }).map((_, index) => (
                  <tr key={index}>
                    <td colSpan={11} className="px-4 py-3">
                      <Skeleton className="h-11 w-full" />
                    </td>
                  </tr>
                ))
              : results.map((result) => (
                  <motion.tr
                    key={result.symbol}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="group transition-colors hover:bg-white/10 dark:hover:bg-white/5"
                  >
                    <td className="border-b border-white/10 px-4 py-4 font-black text-slate-950 dark:text-white">{result.symbol}</td>
                    <td className="border-b border-white/10 px-4 py-4 font-semibold text-slate-700 dark:text-white/75">
                      {formatPrice(result.current_price)}
                    </td>
                    <td className="border-b border-white/10 px-4 py-4">
                      <SignalBadge signal={result.signal} />
                    </td>
                    <td className="border-b border-white/10 px-4 py-4">
                      <ConfidenceBar value={result.confidence} />
                    </td>
                    <td className="border-b border-white/10 px-4 py-4">
                      <RiskBadge riskLevel={result.risk_level} />
                    </td>
                    <td className="border-b border-white/10 px-4 py-4 font-semibold text-slate-700 dark:text-white/75">
                      {result.rsi.toFixed(1)}
                    </td>
                    <td className="border-b border-white/10 px-4 py-4">
                      <Badge tone={result.macd_signal === "bullish" ? "success" : result.macd_signal === "bearish" ? "error" : "neutral"}>
                        {result.macd_signal}
                      </Badge>
                    </td>
                    <td className="border-b border-white/10 px-4 py-4">
                      <TrendLabel trend={result.trend_direction} />
                    </td>
                    <td className="border-b border-white/10 px-4 py-4 font-semibold text-slate-700 dark:text-white/75">
                      {formatPercent(result.volatility)}
                    </td>
                    <td className="max-w-[220px] border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/75">
                      <span className="line-clamp-2 font-semibold">{result.recommended_action}</span>
                    </td>
                    <td className="border-b border-white/10 px-4 py-4 text-xs font-semibold text-slate-500 dark:text-white/45">
                      {formatTime(result.created_at)}
                    </td>
                  </motion.tr>
                ))}
          </tbody>
        </table>
      </div>

      {!loading && results.length === 0 ? (
        <EmptyState title="No scanner rows" message="Adjust filters or run the scanner after market data is synced." />
      ) : null}
    </Card>
  );
}

function SignalBadge({ signal }: { signal: ScannerResult["signal"] }) {
  const Icon = signal === "buy" ? ArrowUpRight : signal === "sell" ? ArrowDownRight : ArrowRight;
  return (
    <Badge tone={signal === "buy" ? "success" : signal === "sell" ? "error" : "warning"} className="capitalize">
      <Icon size={13} aria-hidden />
      {signal}
    </Badge>
  );
}

function RiskBadge({ riskLevel }: { riskLevel: ScannerResult["risk_level"] }) {
  return (
    <Badge tone={riskLevel === "low" ? "success" : riskLevel === "medium" ? "warning" : "error"} className="capitalize">
      {riskLevel}
    </Badge>
  );
}

function TrendLabel({ trend }: { trend: ScannerResult["trend_direction"] }) {
  const Icon = trend === "uptrend" ? ArrowUpRight : trend === "downtrend" ? ArrowDownRight : ArrowRight;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-sm font-bold capitalize",
        trend === "uptrend" && "text-emerald-700 dark:text-emerald-200",
        trend === "downtrend" && "text-rose-700 dark:text-rose-200",
        trend === "sideways" && "text-slate-600 dark:text-white/60"
      )}
    >
      <Icon size={14} aria-hidden />
      {trend.replace("trend", " trend")}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  return (
    <div className="min-w-[130px]">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-black text-slate-700 dark:text-white/80">{formatPercent(value)}</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/15 dark:bg-white/10">
        <div
          className={cn("h-full rounded-full", value >= 0.75 ? "bg-emerald-400" : value >= 0.6 ? "bg-cyan-400" : "bg-amber-400")}
          style={{ width: `${Math.min(100, Math.max(2, value * 100))}%` }}
        />
      </div>
    </div>
  );
}

function formatPrice(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value > 1000 ? 2 : 4
  }).format(value);
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
