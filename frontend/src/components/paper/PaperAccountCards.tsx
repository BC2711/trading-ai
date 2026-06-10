import { CircleDollarSign, Landmark, TrendingUp, Wallet } from "lucide-react";

import type { PaperTradingAccount } from "../../api/paperTradingApi";
import { PortfolioMetricCard } from "../portfolio/PortfolioMetricCard";

export function PaperAccountCards({ account }: { account?: PaperTradingAccount }) {
  const totalPnl = account?.total_pnl ?? 0;
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <PortfolioMetricCard label="Paper Balance" value={formatCurrency(account?.cash_balance ?? 0)} detail="Virtual wallet cash" icon={Wallet} tone="cyan" />
      <PortfolioMetricCard label="Paper Equity" value={formatCurrency(account?.paper_equity ?? 0)} detail="Cash plus open PnL" icon={CircleDollarSign} tone="emerald" />
      <PortfolioMetricCard label="Paper PnL" value={formatCurrency(totalPnl)} detail={`Realized ${formatCurrency(account?.realized_pnl ?? 0)}`} icon={TrendingUp} tone={totalPnl >= 0 ? "emerald" : "rose"} />
      <PortfolioMetricCard label="Margin Used" value={formatCurrency(account?.margin_used ?? 0)} detail={`${formatCurrency(account?.margin_available ?? 0)} available`} icon={Landmark} tone="amber" />
    </section>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: Math.abs(value) > 1000 ? 0 : 2
  }).format(value);
}
