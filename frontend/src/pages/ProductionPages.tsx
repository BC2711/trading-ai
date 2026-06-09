import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Bell, Bot, KeyRound, Layers3, Lock, ShieldCheck, Users } from "lucide-react";
import { useMemo, useState } from "react";

import { DataTable } from "../components/table/DataTable";
import { EmptyState } from "../components/table/EmptyState";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/LoadingSpinner";
import {
  createApiCredential,
  createStrategy,
  deleteApiCredential,
  deleteStrategy,
  deleteUser,
  disableStrategy,
  enableStrategy,
  fetchAIModels,
  fetchApiCredentials,
  fetchBacktests,
  fetchNotifications,
  fetchOrders,
  fetchPositions,
  fetchRiskSettings,
  fetchStrategies,
  fetchSystemLogs,
  fetchUsers,
  login,
  logout,
  markNotificationRead,
  predictAIModel,
  register,
  runBacktest,
  trainAIModel,
  updateRiskSettings,
  updateUser
} from "../services/api";
import type { OrderStatusFilter, PositionStatusFilter } from "../services/api";

type Row = { id: string; [key: string]: unknown };

export function LoginPage({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", fullName: "", password: "" });
  const authMutation = useMutation({
    mutationFn: async () => {
      if (mode === "register") {
        await register({ email: form.email, full_name: form.fullName || "Trading Admin", password: form.password, role: "admin" });
      }
      await login({ email: form.email, password: form.password });
    },
    onSuccess: onAuthenticated
  });

  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 p-4 text-white">
      <Card className="w-full max-w-md p-6">
        <div className="mb-5">
          <div className="mb-3 inline-flex size-12 items-center justify-center rounded-[8px] bg-cyan-400/15 text-cyan-100">
            <Lock size={22} aria-hidden />
          </div>
          <h1 className="text-2xl font-black text-slate-950 dark:text-white">Trading AI Access</h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-white/55">
            {mode === "login" ? "Sign in to manage the trading workspace." : "Create the first admin or a trader account."}
          </p>
        </div>
        {authMutation.isError ? <Alert tone="error">Authentication failed. Check your details and try again.</Alert> : null}
        <div className="mt-4 grid gap-3">
          <Input label="Email" type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} />
          {mode === "register" ? (
            <Input label="Full name" value={form.fullName} onChange={(event) => setForm((current) => ({ ...current, fullName: event.target.value }))} />
          ) : null}
          <Input label="Password" type="password" value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} />
          <Button loading={authMutation.isPending} onClick={() => authMutation.mutate()}>
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
          <Button variant="ghost" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "Register first user" : "Back to sign in"}
          </Button>
        </div>
      </Card>
    </main>
  );
}

export function UsersPage() {
  const queryClient = useQueryClient();
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: fetchUsers });
  const deleteMutation = useMutation({ mutationFn: deleteUser, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }) });
  const updateMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) => updateUser(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] })
  });
  return (
    <EntityPage title="Users" icon={Users} loading={usersQuery.isLoading} error={usersQuery.isError}>
      <DataTable
        title="Users"
        rows={(usersQuery.data ?? []).map((user) => ({ id: String(user.id), email: user.email, name: user.full_name, role: user.role, status: user.is_active ? "active" : "disabled", userId: user.id, active: user.is_active }))}
        columns={[
          { key: "email", label: "Email" },
          { key: "name", label: "Name" },
          { key: "role", label: "Role" },
          { key: "status", label: "Status", render: (row) => <Badge tone={row.active ? "success" : "neutral"}>{String(row.status)}</Badge> },
          {
            key: "userId",
            label: "Actions",
            align: "right",
            render: (row) => (
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => updateMutation.mutate({ id: Number(row.userId), is_active: !row.active })}>{row.active ? "Deactivate" : "Activate"}</Button>
                <Button variant="danger" onClick={() => deleteMutation.mutate(Number(row.userId))}>Delete</Button>
              </div>
            )
          }
        ]}
      />
    </EntityPage>
  );
}

export function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ exchange: "binance", api_key: "", api_secret: "", mode: "paper" as "paper" | "live" });
  const credentialsQuery = useQuery({ queryKey: ["api-credentials"], queryFn: fetchApiCredentials });
  const createMutation = useMutation({
    mutationFn: () => createApiCredential(form),
    onSuccess: () => {
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["api-credentials"] });
    }
  });
  const deleteMutation = useMutation({ mutationFn: deleteApiCredential, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["api-credentials"] }) });
  return (
    <EntityPage title="API Keys" icon={KeyRound} loading={credentialsQuery.isLoading} error={credentialsQuery.isError} action={<Button icon={KeyRound} onClick={() => setOpen(true)}>Add key</Button>}>
      {createMutation.isError ? <Alert tone="error">Unable to save credentials. Live keys require risk safety settings.</Alert> : null}
      <DataTable
        title="Exchange Credentials"
        rows={(credentialsQuery.data ?? []).map((item) => ({ id: String(item.id), exchange: item.exchange, apiKey: item.api_key, mode: item.mode, status: item.is_active ? "active" : "inactive", credentialId: item.id }))}
        columns={[
          { key: "exchange", label: "Exchange" },
          { key: "apiKey", label: "API key" },
          { key: "mode", label: "Mode" },
          { key: "status", label: "Status" },
          { key: "credentialId", label: "Actions", align: "right", render: (row) => <Button variant="danger" onClick={() => deleteMutation.mutate(Number(row.credentialId))}>Delete</Button> }
        ]}
        emptyTitle="No API credentials"
      />
      <Modal open={open} onClose={() => setOpen(false)} title="Add API Key" footer={<Button loading={createMutation.isPending} onClick={() => createMutation.mutate()}>Save key</Button>}>
        <div className="grid gap-3">
          <Input label="Exchange" value={form.exchange} onChange={(event) => setForm((current) => ({ ...current, exchange: event.target.value }))} />
          <Input label="API key" value={form.api_key} onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))} />
          <Input label="API secret" type="password" value={form.api_secret} onChange={(event) => setForm((current) => ({ ...current, api_secret: event.target.value }))} />
          <Select label="Mode" options={["paper", "live"]} value={form.mode} onChange={(event) => setForm((current) => ({ ...current, mode: event.target.value as "paper" | "live" }))} />
        </div>
      </Modal>
    </EntityPage>
  );
}

export function StrategiesPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("Momentum Guard");
  const strategiesQuery = useQuery({ queryKey: ["strategies"], queryFn: fetchStrategies });
  const createMutation = useMutation({ mutationFn: () => createStrategy({ name, description: "Managed strategy", timeframe: "15m", status: "draft", enabled: false }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies"] }) });
  const enableMutation = useMutation({ mutationFn: enableStrategy, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies"] }) });
  const disableMutation = useMutation({ mutationFn: disableStrategy, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies"] }) });
  const deleteMutation = useMutation({ mutationFn: deleteStrategy, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies"] }) });
  return (
    <EntityPage title="Strategies" icon={Layers3} loading={strategiesQuery.isLoading} error={strategiesQuery.isError} action={<div className="flex gap-2"><Input value={name} onChange={(event) => setName(event.target.value)} /><Button onClick={() => createMutation.mutate()}>Create</Button></div>}>
      <DataTable
        title="Strategy Registry"
        rows={(strategiesQuery.data ?? []).map((item) => ({ id: String(item.id), name: item.name, timeframe: item.timeframe, status: item.status, enabled: item.enabled, strategyId: item.id }))}
        columns={[
          { key: "name", label: "Name" },
          { key: "timeframe", label: "Frame" },
          { key: "status", label: "Status" },
          { key: "enabled", label: "Enabled", render: (row) => <Badge tone={row.enabled ? "success" : "neutral"}>{row.enabled ? "yes" : "no"}</Badge> },
          { key: "strategyId", label: "Actions", align: "right", render: (row) => <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => (row.enabled ? disableMutation : enableMutation).mutate(Number(row.strategyId))}>{row.enabled ? "Disable" : "Enable"}</Button><Button variant="danger" onClick={() => deleteMutation.mutate(Number(row.strategyId))}>Delete</Button></div> }
        ]}
      />
    </EntityPage>
  );
}

export function BacktestsPage() {
  const queryClient = useQueryClient();
  const backtestsQuery = useQuery({ queryKey: ["backtests", 50], queryFn: () => fetchBacktests(50) });
  const runMutation = useMutation({ mutationFn: () => runBacktest({ symbol: "BTCUSDT", timeframe: "15m", initial_balance: 10000, lookback: 240 }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["backtests"] }) });
  return (
    <EntityPage title="Backtests" icon={Activity} loading={backtestsQuery.isLoading} error={backtestsQuery.isError} action={<Button loading={runMutation.isPending} onClick={() => runMutation.mutate()}>Run backtest</Button>}>
      <DataTable title="Backtest Reports" rows={(backtestsQuery.data ?? []).map((run) => ({ id: String(run.id), symbol: run.symbol, return: `${(run.total_return * 100).toFixed(2)}%`, winRate: `${(run.win_rate * 100).toFixed(1)}%`, sharpe: run.sharpe_ratio.toFixed(2), profitFactor: run.profit_factor.toFixed(2) }))} columns={[{ key: "symbol", label: "Symbol" }, { key: "return", label: "Return" }, { key: "winRate", label: "Win rate" }, { key: "sharpe", label: "Sharpe" }, { key: "profitFactor", label: "Profit factor" }]} />
    </EntityPage>
  );
}

export function AiModelsPage() {
  const queryClient = useQueryClient();
  const [prediction, setPrediction] = useState<string | null>(null);
  const modelsQuery = useQuery({ queryKey: ["ai-models"], queryFn: fetchAIModels });
  const trainMutation = useMutation({ mutationFn: () => trainAIModel({ name: "BTC Direction Model", symbol: "BTCUSDT", timeframe: "15m", lookback: 240 }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-models"] }) });
  const predictMutation = useMutation({ mutationFn: predictAIModel, onSuccess: (result) => setPrediction(`${result.symbol} ${result.direction.toUpperCase()} ${(result.confidence * 100).toFixed(1)}%`) });
  return (
    <EntityPage title="AI Models" icon={Bot} loading={modelsQuery.isLoading} error={modelsQuery.isError} action={<Button loading={trainMutation.isPending} onClick={() => trainMutation.mutate()}>Train model</Button>}>
      {prediction ? <Alert tone="info">Prediction: {prediction}</Alert> : null}
      <DataTable title="Model Registry" rows={(modelsQuery.data ?? []).map((model) => ({ id: String(model.id), name: model.name, symbol: model.symbol, status: model.status, accuracy: `${Number(model.metrics.accuracy ?? 0).toFixed(2)}`, modelId: model.id }))} columns={[{ key: "name", label: "Name" }, { key: "symbol", label: "Symbol" }, { key: "status", label: "Status" }, { key: "accuracy", label: "Accuracy" }, { key: "modelId", label: "Actions", align: "right", render: (row) => <Button variant="outline" loading={predictMutation.isPending && predictMutation.variables === Number(row.modelId)} onClick={() => predictMutation.mutate(Number(row.modelId))}>Predict</Button> }]} emptyTitle="No trained models" />
    </EntityPage>
  );
}

export function RiskSettingsPage() {
  const queryClient = useQueryClient();
  const riskQuery = useQuery({ queryKey: ["risk-settings"], queryFn: fetchRiskSettings });
  const risk = riskQuery.data?.[0];
  const updateMutation = useMutation({ mutationFn: () => risk ? updateRiskSettings(risk.id, { emergency_stop: !risk.emergency_stop }) : Promise.reject(new Error("No risk settings")), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["risk-settings"] }) });
  return (
    <EntityPage title="Risk Settings" icon={ShieldCheck} loading={riskQuery.isLoading} error={riskQuery.isError} action={<Button variant={risk?.emergency_stop ? "success" : "danger"} loading={updateMutation.isPending} disabled={!risk} onClick={() => updateMutation.mutate()}>{risk?.emergency_stop ? "Clear kill switch" : "Emergency stop"}</Button>}>
      {risk ? (
        <div className="grid gap-3 md:grid-cols-3">
          <RiskCard label="Risk per trade" value={`${(risk.max_risk_per_trade * 100).toFixed(1)}%`} />
          <RiskCard label="Daily loss" value={`${(risk.max_daily_loss * 100).toFixed(1)}%`} />
          <RiskCard label="Open trades" value={String(risk.max_open_trades)} />
          <RiskCard label="Symbol exposure" value={`${(risk.max_symbol_exposure * 100).toFixed(1)}%`} />
          <RiskCard label="Loss streak stop" value={String(risk.max_consecutive_losses)} />
          <RiskCard label="Live trading" value={risk.live_trading_enabled ? "enabled" : "disabled"} />
        </div>
      ) : <EmptyState title="No risk settings" message="Create default settings from the backend startup seed." />}
    </EntityPage>
  );
}

export function OrdersPage() {
  return <OrdersLikePage title="Orders" status="all" />;
}

export function TradeHistoryPage() {
  return <OrdersLikePage title="Trade History" status="filled" />;
}

function OrdersLikePage({ title, status }: { title: string; status: OrderStatusFilter }) {
  const ordersQuery = useQuery({ queryKey: ["orders", title, status], queryFn: () => fetchOrders(100, status) });
  return <EntityPage title={title} icon={Activity} loading={ordersQuery.isLoading} error={ordersQuery.isError}><DataTable title={title} rows={(ordersQuery.data ?? []).map((order) => ({ id: String(order.id), symbol: order.symbol, side: order.side, quantity: order.quantity.toFixed(6), status: order.status, risk: order.risk_message }))} columns={[{ key: "symbol", label: "Symbol" }, { key: "side", label: "Side" }, { key: "quantity", label: "Qty" }, { key: "status", label: "Status" }, { key: "risk", label: "Risk" }]} /></EntityPage>;
}

export function PositionsPage() {
  const [status, setStatus] = useState<PositionStatusFilter>("open");
  const positionsQuery = useQuery({ queryKey: ["positions", "page", status], queryFn: () => fetchPositions(status) });
  return <EntityPage title="Positions" icon={Activity} loading={positionsQuery.isLoading} error={positionsQuery.isError} action={<Select value={status} options={["open", "closed", "all"]} onChange={(event) => setStatus(event.target.value as PositionStatusFilter)} />}><DataTable title="Positions" rows={(positionsQuery.data ?? []).map((position) => ({ id: String(position.id), symbol: position.symbol, side: position.side, quantity: position.quantity.toFixed(6), status: position.status, pnl: position.realized_pnl || position.unrealized_pnl }))} columns={[{ key: "symbol", label: "Symbol" }, { key: "side", label: "Side" }, { key: "quantity", label: "Qty" }, { key: "status", label: "Status" }, { key: "pnl", label: "PnL" }]} /></EntityPage>;
}

export function LogsPage() {
  const logsQuery = useQuery({ queryKey: ["system-logs"], queryFn: () => fetchSystemLogs(100) });
  return <EntityPage title="System Logs" icon={Activity} loading={logsQuery.isLoading} error={logsQuery.isError}><DataTable title="Logs" rows={(logsQuery.data ?? []).map((log) => ({ id: String(log.id), level: log.level, source: log.source, message: log.message, created: formatRelativeTime(log.created_at) }))} columns={[{ key: "level", label: "Level" }, { key: "source", label: "Source" }, { key: "message", label: "Message" }, { key: "created", label: "Created" }]} emptyTitle="No system logs" /></EntityPage>;
}

export function NotificationsPage() {
  const queryClient = useQueryClient();
  const notificationsQuery = useQuery({ queryKey: ["notifications"], queryFn: () => fetchNotifications(false) });
  const readMutation = useMutation({ mutationFn: markNotificationRead, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }) });
  return <EntityPage title="Notifications" icon={Bell} loading={notificationsQuery.isLoading} error={notificationsQuery.isError}><DataTable title="Notifications" rows={(notificationsQuery.data ?? []).map((notification) => ({ id: String(notification.id), title: notification.title, severity: notification.severity, status: notification.is_read ? "read" : "unread", notificationId: notification.id }))} columns={[{ key: "title", label: "Title" }, { key: "severity", label: "Severity" }, { key: "status", label: "Status" }, { key: "notificationId", label: "Actions", align: "right", render: (row) => <Button variant="outline" disabled={row.status === "read"} onClick={() => readMutation.mutate(Number(row.notificationId))}>Mark read</Button> }]} /></EntityPage>;
}

function EntityPage({ title, icon: Icon, loading, error, action, children }: { title: string; icon: typeof Activity; loading?: boolean; error?: boolean; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Icon size={14} aria-hidden />
              Production module
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">{title}</h1>
          </div>
          {action}
        </div>
      </Card>
      {error ? <Alert tone="error">Unable to load {title.toLowerCase()}.</Alert> : null}
      {loading ? <Skeleton className="h-[360px]" /> : children}
    </div>
  );
}

function RiskCard({ label, value }: { label: string; value: string }) {
  return <Card className="p-4"><p className="text-xs font-bold uppercase text-slate-500 dark:text-white/45">{label}</p><p className="mt-2 text-xl font-black text-slate-950 dark:text-white">{value}</p></Card>;
}

function formatRelativeTime(value: string) {
  const timestamp = new Date(value).getTime();
  const minutes = Math.floor(Math.max(0, Date.now() - timestamp) / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`;
}
