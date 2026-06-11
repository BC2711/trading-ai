import type { StrategyComparison } from "../../api/performanceAnalyticsApi";
import { EmptyState } from "../table/EmptyState";
import { Card } from "../ui/Card";

export function StrategyComparisonTable({ strategies }: { strategies: StrategyComparison[] }) {
  return (
    <Card className="p-0">
      <div className="border-b border-white/10 p-4">
        <h2 className="text-lg font-black text-slate-950 dark:text-white">Strategy Comparison</h2>
        <p className="text-sm font-medium text-slate-500 dark:text-white/50">Backtest-first comparison with signal coverage fallback</p>
      </div>
      {strategies.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-separate border-spacing-0 text-sm">
            <thead className="bg-white/20 dark:bg-white/[0.03]">
              <tr>
                {["Strategy", "Trades", "Win rate", "Return", "Profit factor", "Sharpe", "Max DD", "Source"].map((label) => (
                  <th key={label} className="border-b border-white/10 px-4 py-3 text-left text-xs font-black uppercase tracking-normal text-slate-500 dark:text-white/45">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {strategies.map((row) => (
                <tr key={row.id} className="transition-colors hover:bg-white/10 dark:hover:bg-white/5">
                  <td className="border-b border-white/10 px-4 py-3 font-black text-slate-950 dark:text-white">{row.strategy}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{row.total_trades}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{formatPercent(row.win_rate)}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{formatPercent(row.total_return)}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{row.profit_factor.toFixed(2)}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{row.sharpe_ratio.toFixed(2)}</td>
                  <td className="border-b border-white/10 px-4 py-3 text-slate-600 dark:text-white/65">{formatPercent(row.max_drawdown)}</td>
                  <td className="border-b border-white/10 px-4 py-3">
                    <span className="rounded-[8px] bg-cyan-400/15 px-2 py-1 text-xs font-black text-cyan-700 dark:text-cyan-100">{row.source}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No strategies yet" message="Backtests and generated signals will populate comparison rows." />
      )}
    </Card>
  );
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}
