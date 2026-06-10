import type { RiskRejectedTrade } from "../../api/riskAnalyticsApi";
import { DataTable } from "../table/DataTable";
import { Badge } from "../ui/Badge";

type Row = { id: string; [key: string]: unknown };

export function RejectedTradesTable({ trades }: { trades: RiskRejectedTrade[] }) {
  return (
    <DataTable
      title="Recent Rejected Trades"
      description="Blocked by risk guard or circuit breaker"
      rows={trades.map((trade) => ({
        id: String(trade.id),
        symbol: trade.symbol,
        side: trade.side,
        quantity: trade.quantity.toFixed(6),
        message: trade.risk_message,
        created: new Date(trade.created_at).toLocaleString()
      }))}
      columns={[
        { key: "symbol", label: "Symbol" },
        { key: "side", label: "Side", render: (row: Row) => <Badge tone={row.side === "buy" ? "success" : "warning"}>{String(row.side)}</Badge> },
        { key: "quantity", label: "Qty" },
        { key: "message", label: "Reason" },
        { key: "created", label: "Created" }
      ]}
      emptyTitle="No rejected trades"
      emptyMessage="Rejected trades will appear here when limits block an order."
    />
  );
}
