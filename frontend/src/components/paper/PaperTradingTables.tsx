import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { DataTable } from "../table/DataTable";
import type { PaperTradingOrder, PaperTradingPosition } from "../../api/paperTradingApi";

type Row = { id: string; [key: string]: unknown };

export function PaperOrdersTable({ orders }: { orders: PaperTradingOrder[] }) {
  return (
    <DataTable
      title="Paper Orders"
      description="Simulated fills from the paper trading engine"
      rows={orders.map((order) => ({
        id: String(order.id),
        symbol: order.symbol,
        side: order.side,
        quantity: order.quantity.toFixed(6),
        price: order.fill_price == null ? "n/a" : formatCurrency(order.fill_price),
        status: order.status,
        risk: order.risk_message
      }))}
      columns={[
        { key: "symbol", label: "Symbol" },
        { key: "side", label: "Side", render: (row: Row) => <Badge tone={row.side === "buy" ? "success" : "warning"}>{String(row.side)}</Badge> },
        { key: "quantity", label: "Qty" },
        { key: "price", label: "Fill" },
        { key: "status", label: "Status", render: (row: Row) => <Badge tone={row.status === "filled" ? "success" : "warning"}>{String(row.status)}</Badge> },
        { key: "risk", label: "Message" }
      ]}
      emptyTitle="No paper orders"
      emptyMessage="Submit a simulated order to populate the paper ledger."
    />
  );
}

export function PaperPositionsTable({
  positions,
  closingId,
  onClose
}: {
  positions: PaperTradingPosition[];
  closingId?: number;
  onClose: (id: number) => void;
}) {
  return (
    <DataTable
      title="Paper Positions"
      description="Open and closed virtual positions"
      rows={positions.map((position) => ({
        id: String(position.id),
        symbol: position.symbol,
        side: position.side,
        quantity: position.quantity.toFixed(6),
        entry: formatCurrency(position.avg_entry_price),
        mark: formatCurrency(position.mark_price),
        pnl: formatCurrency(position.status === "open" ? position.unrealized_pnl : position.realized_pnl),
        status: position.status,
        positionId: position.id
      }))}
      columns={[
        { key: "symbol", label: "Symbol" },
        { key: "side", label: "Side", render: (row: Row) => <Badge tone={row.side === "long" ? "success" : "warning"}>{String(row.side)}</Badge> },
        { key: "quantity", label: "Qty" },
        { key: "entry", label: "Entry" },
        { key: "mark", label: "Mark" },
        { key: "pnl", label: "PnL" },
        { key: "status", label: "Status", render: (row: Row) => <Badge tone={row.status === "open" ? "info" : "neutral"}>{String(row.status)}</Badge> },
        {
          key: "positionId",
          label: "Action",
          align: "right",
          render: (row: Row) => (
            <Button
              variant="outline"
              className="min-h-9 px-3"
              disabled={row.status !== "open"}
              loading={closingId === Number(row.positionId)}
              onClick={() => onClose(Number(row.positionId))}
            >
              Close
            </Button>
          )
        }
      ]}
      emptyTitle="No paper positions"
      emptyMessage="Filled paper orders will create virtual positions."
    />
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: Math.abs(value) > 1000 ? 0 : 2
  }).format(value);
}
