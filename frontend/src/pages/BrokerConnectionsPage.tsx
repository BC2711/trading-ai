import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";

import { connectBroker, disconnectBroker, fetchBrokerBalance, fetchBrokers } from "../api/brokerApi";
import { BrokerBalancePanel } from "../components/brokers/BrokerBalancePanel";
import { BrokerStatusCard } from "../components/brokers/BrokerStatusCard";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";

export function BrokerConnectionsPage() {
  const queryClient = useQueryClient();
  const [selectedBroker, setSelectedBroker] = useState("binance");
  const brokersQuery = useQuery({ queryKey: ["brokers"], queryFn: fetchBrokers, refetchInterval: 30_000 });
  const brokers = brokersQuery.data ?? [];
  const activeBroker = useMemo(() => brokers.find((broker) => broker.name === selectedBroker) ?? brokers[0], [brokers, selectedBroker]);
  const balanceQuery = useQuery({
    queryKey: ["brokers", activeBroker?.name, "balance"],
    queryFn: () => fetchBrokerBalance(activeBroker?.name ?? "binance"),
    enabled: Boolean(activeBroker?.connected),
    retry: false
  });

  const connectMutation = useMutation({
    mutationFn: connectBroker,
    onSuccess: (result) => {
      setSelectedBroker(result.broker.name);
      queryClient.invalidateQueries({ queryKey: ["brokers"] });
    }
  });
  const disconnectMutation = useMutation({
    mutationFn: disconnectBroker,
    onSuccess: (result) => {
      setSelectedBroker(result.broker.name);
      queryClient.invalidateQueries({ queryKey: ["brokers"] });
    }
  });

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <KeyRound size={14} aria-hidden />
              Multi-broker execution layer
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Broker Connections</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Manage broker adapter connectivity and live API key readiness without exposing broker secrets.
            </p>
          </div>
          <div className="rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/5">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-white/70">
              <ShieldCheck size={16} aria-hidden />
              Secrets hidden
            </div>
            <p className="mt-1 text-xs font-medium text-slate-500 dark:text-white/45">Only configured/missing status is shown.</p>
          </div>
        </div>
      </Card>

      {brokersQuery.isError ? <Alert tone="error">Unable to load broker connections.</Alert> : null}
      {connectMutation.isError ? <Alert tone="warning">Unable to connect broker. Confirm live API credentials and broker availability.</Alert> : null}
      {disconnectMutation.isError ? <Alert tone="error">Unable to disconnect broker.</Alert> : null}
      {balanceQuery.isError ? <Alert tone="warning">Connected broker did not return balance data yet.</Alert> : null}

      {brokersQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} className="h-64" />)}
        </div>
      ) : (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {brokers.map((broker) => (
            <div key={broker.name} className="text-left" onClick={() => setSelectedBroker(broker.name)}>
              <BrokerStatusCard
                broker={broker}
                loading={(connectMutation.isPending && connectMutation.variables === broker.name) || (disconnectMutation.isPending && disconnectMutation.variables === broker.name)}
                onConnect={(name) => connectMutation.mutate(name)}
                onDisconnect={(name) => disconnectMutation.mutate(name)}
              />
            </div>
          ))}
        </section>
      )}

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px] xl:gap-6">
        <BrokerBalancePanel brokerName={activeBroker?.display_name} balances={balanceQuery.data?.balances ?? []} />
        <Card className="p-4 sm:p-5">
          <h2 className="text-lg font-black text-slate-950 dark:text-white">Selected Broker</h2>
          <div className="mt-4 grid gap-3">
            <Detail label="Broker" value={activeBroker?.display_name ?? "None"} />
            <Detail label="Status" value={activeBroker?.status ?? "unknown"} badgeTone={activeBroker?.connected ? "success" : "neutral"} />
            <Detail label="Mode" value={activeBroker?.mode ?? "testnet"} badgeTone={activeBroker?.mode === "live" ? "warning" : "neutral"} />
            <Detail label="API key" value={activeBroker?.api_key_configured ? "Configured" : "Missing"} badgeTone={activeBroker?.api_key_configured ? "success" : "warning"} />
            <Detail label="Last sync" value={activeBroker?.last_sync_at ? new Date(activeBroker.last_sync_at).toLocaleString() : "Never"} />
          </div>
        </Card>
      </section>
    </div>
  );
}

function Detail({ label, value, badgeTone }: { label: string; value: string; badgeTone?: "success" | "warning" | "neutral" }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/5">
      <span className="text-sm font-semibold text-slate-600 dark:text-white/55">{label}</span>
      {badgeTone ? <Badge tone={badgeTone}>{value}</Badge> : <span className="text-sm font-bold text-slate-900 dark:text-white">{value}</span>}
    </div>
  );
}
