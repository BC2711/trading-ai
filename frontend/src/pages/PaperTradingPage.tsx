import { useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCcw, Wallet } from "lucide-react";
import { useState } from "react";

import { closePaperTradingPosition, createPaperTradingOrder, resetPaperTradingAccount } from "../api/paperTradingApi";
import { PaperAccountCards } from "../components/paper/PaperAccountCards";
import { PaperOrderTicket } from "../components/paper/PaperOrderTicket";
import { PaperOrdersTable, PaperPositionsTable } from "../components/paper/PaperTradingTables";
import { PortfolioPerformanceChart } from "../components/portfolio/PortfolioCharts";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";
import { Select } from "../components/ui/Select";
import { usePaperAccount, usePaperOrders, usePaperPerformance, usePaperPositions } from "../hooks/usePaperTrading";

export function PaperTradingPage() {
  const queryClient = useQueryClient();
  const [positionStatus, setPositionStatus] = useState<"open" | "closed" | "all">("open");
  const accountQuery = usePaperAccount();
  const ordersQuery = usePaperOrders();
  const positionsQuery = usePaperPositions(positionStatus);
  const performanceQuery = usePaperPerformance();

  const invalidatePaperTrading = () => {
    queryClient.invalidateQueries({ queryKey: ["paper-trading"] });
    queryClient.invalidateQueries({ queryKey: ["portfolio"] });
    queryClient.invalidateQueries({ queryKey: ["orders"] });
    queryClient.invalidateQueries({ queryKey: ["positions"] });
  };

  const orderMutation = useMutation({
    mutationFn: createPaperTradingOrder,
    onSuccess: invalidatePaperTrading
  });
  const closeMutation = useMutation({
    mutationFn: closePaperTradingPosition,
    onSuccess: invalidatePaperTrading
  });
  const resetMutation = useMutation({
    mutationFn: () => resetPaperTradingAccount(10000),
    onSuccess: invalidatePaperTrading
  });

  const loading = accountQuery.isLoading || ordersQuery.isLoading || positionsQuery.isLoading || performanceQuery.isLoading;
  const hasError = accountQuery.isError || ordersQuery.isError || positionsQuery.isError || performanceQuery.isError;
  const performanceData = (performanceQuery.data?.points ?? []).map((point, index) => ({
    label: `T${index + 1}`,
    equity: point.paper_equity,
    totalPnl: point.realized_pnl + point.unrealized_pnl
  }));

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Wallet size={14} aria-hidden />
              Simulated execution
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Paper Trading</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Trade with a virtual wallet, simulated market fills, paper positions, and a separate paper performance ledger.
            </p>
          </div>
          <Button variant="danger" icon={RefreshCcw} loading={resetMutation.isPending} onClick={() => resetMutation.mutate()}>
            Reset paper account
          </Button>
        </div>
      </Card>

      {hasError ? <Alert tone="error">Unable to load paper trading data.</Alert> : null}
      {orderMutation.isError ? <Alert tone="warning">Paper order failed. Check symbol, quantity, and available virtual balance.</Alert> : null}
      {orderMutation.isSuccess ? (
        <Alert tone={orderMutation.data.status === "filled" ? "success" : "warning"}>
          Paper order {orderMutation.data.status}: {orderMutation.data.risk_message}
        </Alert>
      ) : null}
      {closeMutation.isError ? <Alert tone="error">Unable to close paper position.</Alert> : null}
      {closeMutation.isSuccess ? <Alert tone="success">Closed {closeMutation.data.symbol} with realized PnL {formatCurrency(closeMutation.data.realized_pnl)}.</Alert> : null}
      {resetMutation.isSuccess ? (
        <Alert tone="success">
          Reset paper account and cleared {resetMutation.data.reset_orders} orders, {resetMutation.data.reset_positions} positions, and {resetMutation.data.reset_ledger_entries} ledger entries.
        </Alert>
      ) : null}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-32" />)}
        </div>
      ) : (
        <PaperAccountCards account={accountQuery.data} />
      )}

      <section className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)] xl:gap-6">
        <PaperOrderTicket loading={orderMutation.isPending} onSubmit={(payload) => orderMutation.mutate(payload)} />
        <PortfolioPerformanceChart data={performanceData} />
      </section>

      <section className="grid gap-4 xl:grid-cols-2 xl:gap-6">
        <PaperOrdersTable orders={ordersQuery.data ?? []} />
        <div className="grid gap-3">
          <div className="flex justify-end">
            <Select
              aria-label="Paper position status"
              options={[
                { label: "Open positions", value: "open" },
                { label: "Closed positions", value: "closed" },
                { label: "All positions", value: "all" }
              ]}
              value={positionStatus}
              onChange={(event) => setPositionStatus(event.target.value as "open" | "closed" | "all")}
            />
          </div>
          <PaperPositionsTable
            positions={positionsQuery.data ?? []}
            closingId={closeMutation.isPending ? closeMutation.variables : undefined}
            onClose={(id) => closeMutation.mutate(id)}
          />
        </div>
      </section>
    </div>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: Math.abs(value) > 1000 ? 0 : 2
  }).format(value);
}
