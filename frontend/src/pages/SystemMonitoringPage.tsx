import { useQuery } from "@tanstack/react-query";
import { Activity, Database, RefreshCw, ServerCog, ShieldCheck, Signal, Wifi } from "lucide-react";

import { fetchMonitoringHealth, fetchMonitoringMetrics, fetchMonitoringWorkers } from "../api/monitoringApi";
import { MetricCard, QueueStatusPanel, StatusCard, WebSocketStatusCard } from "../components/monitoring";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";

const refreshInterval = 15_000;

export function SystemMonitoringPage() {
  const healthQuery = useQuery({
    queryKey: ["monitoring", "health"],
    queryFn: fetchMonitoringHealth,
    refetchInterval: refreshInterval
  });
  const metricsQuery = useQuery({
    queryKey: ["monitoring", "metrics"],
    queryFn: fetchMonitoringMetrics,
    refetchInterval: refreshInterval
  });
  const workersQuery = useQuery({
    queryKey: ["monitoring", "workers"],
    queryFn: fetchMonitoringWorkers,
    refetchInterval: refreshInterval
  });

  const health = healthQuery.data;
  const metrics = metricsQuery.data;
  const workers = workersQuery.data;
  const loading = healthQuery.isLoading || metricsQuery.isLoading || workersQuery.isLoading;
  const refreshing = healthQuery.isFetching || metricsQuery.isFetching || workersQuery.isFetching;

  const refetchAll = () => {
    void healthQuery.refetch();
    void metricsQuery.refetch();
    void workersQuery.refetch();
  };

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <ServerCog size={14} aria-hidden />
              Administration
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">System Monitoring</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Live backend, infrastructure, worker, broker, and trading observability for the operations console.
            </p>
          </div>
          <Button variant="secondary" icon={RefreshCw} loading={refreshing} onClick={refetchAll}>
            Refresh
          </Button>
        </div>
      </Card>

      {healthQuery.isError || metricsQuery.isError || workersQuery.isError ? (
        <Alert tone="error">Unable to load one or more monitoring feeds.</Alert>
      ) : null}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-56" />)}
        </div>
      ) : health && metrics && workers ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <StatusCard title="Backend Health" status={health.api} icon={Activity} />
            <StatusCard title="Database Status" status={health.database} icon={Database} />
            <StatusCard title="Redis Status" status={health.redis} icon={Wifi} />
            <StatusCard title="Celery Worker Status" status={health.celery_worker} icon={ServerCog} />
            <StatusCard title="Broker Status" status={health.broker_connection} icon={Signal} />
            <WebSocketStatusCard websocket={health.websocket} />
          </section>

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="API Latency" value={`${metrics.api_latency.average_ms.toFixed(1)} ms`} detail={`p95 ${metrics.api_latency.p95_ms.toFixed(1)} ms`} tone="info" />
            <MetricCard label="Error Rate" value={formatPercent(metrics.error_rate)} detail={`${metrics.errors_total} errors`} tone={metrics.error_rate > 0.05 ? "warning" : "success"} />
            <MetricCard label="Active Users" value={String(metrics.active_users)} detail="accounts" tone="violet" />
            <MetricCard label="AI Predictions" value={String(metrics.ai_prediction_count)} detail="total" tone="info" />
            <MetricCard label="Trade Success" value={formatPercent(metrics.trade_success_rate)} detail="paper/live" tone={metrics.trade_success_rate >= 0.5 ? "success" : "warning"} />
            <MetricCard label="Failed Trades" value={String(metrics.failed_trade_count)} detail="risk/rejected" tone={metrics.failed_trade_count ? "warning" : "success"} />
            <MetricCard label="WebSockets" value={String(metrics.websocket_connections)} detail="active" tone="neutral" />
            <MetricCard label="Queue Tasks" value={String(workers.active_task_count + workers.reserved_task_count + workers.scheduled_task_count)} detail="tracked" tone="neutral" />
          </section>

          <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px] xl:gap-6">
            <QueueStatusPanel queues={workers.queues} workers={workers.workers} />
            <Card className="p-4 sm:p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-black text-slate-950 dark:text-white">Runtime</h2>
                  <p className="mt-1 text-sm font-medium text-slate-500 dark:text-white/50">
                    Last update {formatDate(health.generated_at)}
                  </p>
                </div>
                <ShieldCheck className="text-cyan-600 dark:text-cyan-200" size={22} aria-hidden />
              </div>
              <div className="mt-4 grid gap-3">
                <RuntimeLine label="Overall health" value={health.status} />
                <RuntimeLine label="Requests" value={String(metrics.requests_total)} />
                <RuntimeLine label="Recent samples" value={String(metrics.api_latency.recent_request_count)} />
                <RuntimeLine label="Workers online" value={String(workers.workers.length)} />
              </div>
            </Card>
          </section>
        </>
      ) : null}
    </div>
  );
}

function RuntimeLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/5">
      <span className="text-sm font-semibold text-slate-600 dark:text-white/55">{label}</span>
      <span className="text-sm font-black text-slate-950 dark:text-white">{value}</span>
    </div>
  );
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "n/a";
  return date.toLocaleString();
}
