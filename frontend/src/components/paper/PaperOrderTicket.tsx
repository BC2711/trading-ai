import { Send } from "lucide-react";
import { useState } from "react";

import type { PaperTradingOrderRequest } from "../../api/paperTradingApi";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

export function PaperOrderTicket({
  loading,
  onSubmit
}: {
  loading?: boolean;
  onSubmit: (payload: PaperTradingOrderRequest) => void;
}) {
  const [form, setForm] = useState({ symbol: "BTCUSDT", side: "buy" as "buy" | "sell", quantity: "0.01" });

  return (
    <Card className="p-4 sm:p-5">
      <div className="mb-4">
        <h2 className="text-lg font-black text-slate-950 dark:text-white">Paper Order Ticket</h2>
        <p className="text-sm font-medium text-slate-500 dark:text-white/50">Market orders are simulated from stored candle prices only.</p>
      </div>
      <div className="grid gap-3">
        <Input label="Symbol" value={form.symbol} onChange={(event) => setForm((current) => ({ ...current, symbol: event.target.value.toUpperCase() }))} />
        <Select
          label="Side"
          options={[
            { label: "Buy / Long", value: "buy" },
            { label: "Sell / Short", value: "sell" }
          ]}
          value={form.side}
          onChange={(event) => setForm((current) => ({ ...current, side: event.target.value as "buy" | "sell" }))}
        />
        <Input label="Quantity" type="number" min="0.000001" step="0.000001" value={form.quantity} onChange={(event) => setForm((current) => ({ ...current, quantity: event.target.value }))} />
        <Button
          icon={Send}
          loading={loading}
          onClick={() =>
            onSubmit({
              symbol: form.symbol.trim().toUpperCase(),
              side: form.side,
              order_type: "market",
              quantity: Number.parseFloat(form.quantity)
            })
          }
        >
          Submit paper order
        </Button>
      </div>
    </Card>
  );
}
