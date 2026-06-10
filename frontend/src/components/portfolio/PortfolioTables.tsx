import { EmptyState } from "../table/EmptyState";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import type { OpenPositionAllocationItem, PortfolioPerformancePoint } from "../../api/portfolioApi";
import { cn } from "../../utils/cn";

export function PortfolioPerformanceTable({ points }: { points: PortfolioPerformancePoint[] }) {
  return (
    <Card className="p-0">
      <PanelHeader title="Performance History" description={`${points.length} portfolio events`} />
      {points.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="bg-white/20 text-xs uppercase text-slate-500 backdrop-blur-lg dark:bg-white/5 dark:text-white/45">
              <tr>
                {["Event", "Equity", "Realized", "Unrealized", "Total PnL", "Time"].map((header) => (
                  <th key={header} className="border-b border-white/10 px-4 py-3 text-left font-black">{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {points.map((point, index) => (
                <tr key={`${point.timestamp}-${index}`} className="transition hover:bg-white/10 dark:hover:bg-white/5">
                  <td className="border-b border-white/10 px-4 py-4 font-black text-slate-950 dark:text-white">{point.event}</td>
                  <td className="border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/70">{formatCurrency(point.equity)}</td>
                  <MoneyCell value={point.realized_pnl} />
                  <MoneyCell value={point.unrealized_pnl} />
                  <MoneyCell value={point.total_pnl} />
                  <td className="border-b border-white/10 px-4 py-4 text-slate-500 dark:text-white/50">{formatDate(point.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No performance records" message="Run paper trades and close positions to build history." />
      )}
    </Card>
  );
}

export function OpenPositionAllocation({ positions }: { positions: OpenPositionAllocationItem[] }) {
  return (
    <Card className="p-4 sm:p-5">
      <PanelHeader title="Open Position Allocation" description={`${positions.length} open positions`} compact />
      {positions.length ? (
        <div className="mt-4 grid gap-3">
          {positions.map((position) => (
            <div key={position.id} className="rounded-[8px] border border-white/10 bg-white/10 p-3 backdrop-blur-md dark:bg-white/5">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-black text-slate-950 dark:text-white">{position.symbol}</p>
                    <Badge tone={position.side === "long" ? "success" : "warning"}>{position.side}</Badge>
                  </div>
                  <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-white/45">{position.quantity.toFixed(6)} units</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-black text-slate-950 dark:text-white">{formatCurrency(position.value)}</p>
                  <p className={cn("text-xs font-bold", position.unrealized_pnl >= 0 ? "text-emerald-600 dark:text-emerald-300" : "text-rose-600 dark:text-rose-300")}>
                    {formatCurrency(position.unrealized_pnl)}
                  </p>
                </div>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/15 dark:bg-white/10">
                <div className="h-full rounded-full bg-cyan-400" style={{ width: `${Math.min(100, Math.max(2, position.percentage * 100))}%` }} />
              </div>
              <p className="mt-1 text-right text-[11px] font-bold text-slate-500 dark:text-white/40">{formatPercent(position.percentage)}</p>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="No open positions" message="Paper order fills will appear here as position allocation." />
      )}
    </Card>
  );
}

function PanelHeader({ title, description, compact = false }: { title: string; description: string; compact?: boolean }) {
  return (
    <div className={cn("flex items-center justify-between gap-3", compact ? "" : "border-b border-white/10 p-4")}>
      <div>
        <h2 className="text-base font-black text-slate-950 dark:text-white">{title}</h2>
        <p className="text-xs font-medium text-slate-500 dark:text-white/50">{description}</p>
      </div>
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

function formatDate(value: string) {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) {
    return "n/a";
  }
  return timestamp.toLocaleString();
}
