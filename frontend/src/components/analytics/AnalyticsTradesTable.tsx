import type { AnalyticsTrade } from "../../api/performanceAnalyticsApi";
import { EmptyState } from "../table/EmptyState";
import { Card } from "../ui/Card";

export function AnalyticsTradesTable({ trades }: { trades: AnalyticsTrade[] }) {
  return (
    <Card className="p-0">
      <div className="border-b border-white/10 p-4">
        <h2 className="text-lg font-black text-slate-950 dark:text-white">Analytics Trades</h2>
        <p className="text-sm font-medium text-slate-500 dark:text-white/50">{trades.length} closed paper trades</p>
      </div>
      {trades.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-separate border-spacing-0 text-sm">
            <thead className="bg-white/20 dark:bg-white/[0.03]">
              <tr>
                {["Symbol", "Side", "Qty", "Entry", "Exit", "PnL", "Return", "Closed"].map((label) => (
                  <th key={label} className="border-b border-white/10 px-4 py-3 text-left text-xs font-black uppercase tracking-normal text-slate-500 dark:text-white/45">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id} className="transition-colors hover:bg-white/10 dark:hover:bg-white/5">
                  <td className="border-b border-white/10 px-4 py-3 font-black text-slate-950 dark:text-white">{trade.symbol}</td>
                  <td className="border-b border-white/10 px-4 py-3 capitalize text-slate-600 dark:text-white/65">{trade.side}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{trade.quantity.toFixed(6)}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{formatCurrency(trade.entry_price)}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{formatCurrency(trade.exit_price)}</td>
                  <td className={`border-b border-white/10 px-4 py-3 font-black ${trade.realized_pnl >= 0 ? "text-emerald-600 dark:text-emerald-300" : "text-rose-600 dark:text-rose-300"}`}>{formatCurrency(trade.realized_pnl)}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{formatPercent(trade.return_pct)}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{formatDate(trade.closed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No closed trades" message="Close a paper position to create analytics trade rows." />
      )}
    </Card>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: Math.abs(value) > 1000 ? 0 : 4,
  }).format(value);
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "n/a";
  return date.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
