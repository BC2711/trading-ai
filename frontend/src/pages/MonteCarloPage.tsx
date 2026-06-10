import { useMutation } from "@tanstack/react-query";
import { BarChart3, Gauge, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { runMonteCarlo } from "../api/monteCarloApi";
import type { MonteCarloRequest, MonteCarloResponse } from "../api/monteCarloApi";
import { RiskMetricCard } from "../components/risk/RiskMetricCard";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";

type MonteCarloFormState = {
  starting_balance: string;
  win_rate: string;
  average_win: string;
  average_loss: string;
  number_of_trades: string;
  number_of_simulations: string;
  risk_per_trade: string;
};

export function MonteCarloPage() {
  const [form, setForm] = useState<MonteCarloFormState>({
    starting_balance: "10000",
    win_rate: "0.55",
    average_win: "1.5",
    average_loss: "1.0",
    number_of_trades: "100",
    number_of_simulations: "1000",
    risk_per_trade: "0.01"
  });
  const mutation = useMutation({ mutationFn: runMonteCarlo });
  const result = mutation.data;

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <BarChart3 size={14} aria-hidden />
              Risk simulation
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Monte Carlo</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Simulate thousands of trade paths to estimate drawdown, ruin probability, and ending equity distribution.
            </p>
          </div>
          <Button loading={mutation.isPending} onClick={() => mutation.mutate(toPayload(form))}>
            Run simulation
          </Button>
        </div>
      </Card>

      {mutation.isError ? <Alert tone="error">Monte Carlo simulation failed. Check input values and try again.</Alert> : null}
      {result ? <Alert tone="info">{result.risk_recommendation}</Alert> : null}

      <section className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)] xl:gap-6">
        <MonteCarloForm form={form} setForm={setForm} />
        <DistributionChart result={result} />
      </section>

      {result ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <RiskMetricCard label="Probability of Ruin" value={formatPercent(result.probability_of_ruin)} usage={result.probability_of_ruin} icon={Gauge} tone={result.probability_of_ruin > 0.1 ? "rose" : "emerald"} />
            <RiskMetricCard label="Expected Drawdown" value={formatPercent(result.expected_drawdown)} usage={result.expected_drawdown} icon={TrendingDown} tone="amber" />
            <RiskMetricCard label="Maximum Drawdown" value={formatPercent(result.maximum_drawdown)} usage={result.maximum_drawdown} icon={TrendingDown} tone="rose" />
            <RiskMetricCard label="Median Case" value={formatCurrency(result.median_case)} detail={`Run #${result.id}`} icon={Wallet} tone="cyan" />
            <RiskMetricCard label="Best Case" value={formatCurrency(result.best_case)} icon={TrendingUp} tone="emerald" />
            <RiskMetricCard label="Worst Case" value={formatCurrency(result.worst_case)} icon={TrendingDown} tone="rose" />
            <RiskMetricCard label="Simulations" value={String(result.number_of_simulations)} detail={`${result.number_of_trades} trades each`} icon={BarChart3} tone="violet" />
            <RiskMetricCard label="Risk per Trade" value={formatPercent(result.risk_per_trade)} icon={Gauge} tone="amber" />
          </section>
          <ResultTable result={result} />
        </>
      ) : null}
    </div>
  );
}

function MonteCarloForm({
  form,
  setForm
}: {
  form: MonteCarloFormState;
  setForm: React.Dispatch<React.SetStateAction<MonteCarloFormState>>;
}) {
  return (
    <Card className="p-4 sm:p-5">
      <h2 className="text-lg font-black text-slate-950 dark:text-white">Simulation Inputs</h2>
      <div className="mt-4 grid gap-3">
        <Input label="Starting balance" type="number" value={form.starting_balance} onChange={(event) => setForm((current) => ({ ...current, starting_balance: event.target.value }))} />
        <Input label="Win rate" type="number" min="0" max="1" step="0.01" value={form.win_rate} onChange={(event) => setForm((current) => ({ ...current, win_rate: event.target.value }))} />
        <Input label="Average win (R)" type="number" min="0" step="0.1" value={form.average_win} onChange={(event) => setForm((current) => ({ ...current, average_win: event.target.value }))} />
        <Input label="Average loss (R)" type="number" min="0" step="0.1" value={form.average_loss} onChange={(event) => setForm((current) => ({ ...current, average_loss: event.target.value }))} />
        <Input label="Number of trades" type="number" min="1" value={form.number_of_trades} onChange={(event) => setForm((current) => ({ ...current, number_of_trades: event.target.value }))} />
        <Input label="Simulations" type="number" min="1000" value={form.number_of_simulations} onChange={(event) => setForm((current) => ({ ...current, number_of_simulations: event.target.value }))} />
        <Input label="Risk per trade" type="number" min="0.001" max="1" step="0.001" value={form.risk_per_trade} onChange={(event) => setForm((current) => ({ ...current, risk_per_trade: event.target.value }))} />
      </div>
    </Card>
  );
}

function DistributionChart({ result }: { result?: MonteCarloResponse }) {
  return (
    <Card className="p-4 sm:p-5">
      <h2 className="text-lg font-black text-slate-950 dark:text-white">Ending Equity Distribution</h2>
      <div className="mt-4 h-[330px]">
        {result?.ending_equity_distribution.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={result.ending_equity_distribution} margin={{ top: 18, right: 12, bottom: 20, left: -4 }}>
              <CartesianGrid stroke="rgba(148, 163, 184, 0.22)" vertical={false} />
              <XAxis dataKey="bucket" tickLine={false} axisLine={false} tick={{ fill: "currentColor", fontSize: 11, fontWeight: 700 }} className="text-slate-500 dark:text-white/50" />
              <YAxis tickLine={false} axisLine={false} tick={{ fill: "currentColor", fontSize: 12, fontWeight: 700 }} className="text-slate-500 dark:text-white/50" />
              <Tooltip contentStyle={{ borderRadius: 8, background: "rgba(15,23,42,0.85)", color: "#fff", border: "1px solid rgba(255,255,255,0.2)" }} />
              <Bar dataKey="count" fill="#22d3ee" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="grid h-full place-items-center text-center text-sm font-semibold text-slate-500 dark:text-white/50">
            Run a simulation to view the distribution.
          </div>
        )}
      </div>
    </Card>
  );
}

function ResultTable({ result }: { result: MonteCarloResponse }) {
  const rows = [
    ["5% ending equity", result.confidence_intervals.ending_equity?.p05],
    ["25% ending equity", result.confidence_intervals.ending_equity?.p25],
    ["50% ending equity", result.confidence_intervals.ending_equity?.p50],
    ["75% ending equity", result.confidence_intervals.ending_equity?.p75],
    ["95% ending equity", result.confidence_intervals.ending_equity?.p95],
    ["95% drawdown", result.confidence_intervals.drawdown?.p95]
  ];
  return (
    <Card className="p-0">
      <div className="border-b border-white/10 p-4">
        <h2 className="text-base font-black text-slate-950 dark:text-white">Confidence Intervals</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={label} className="transition hover:bg-white/10 dark:hover:bg-white/5">
                <td className="border-b border-white/10 px-4 py-3 font-bold text-slate-700 dark:text-white/70">{label}</td>
                <td className="border-b border-white/10 px-4 py-3 text-right font-black text-slate-950 dark:text-white">{typeof value === "number" && String(label).includes("drawdown") ? formatPercent(value) : formatCurrency(Number(value ?? 0))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function toPayload(form: MonteCarloFormState): MonteCarloRequest {
  return {
    starting_balance: Number.parseFloat(form.starting_balance),
    win_rate: Number.parseFloat(form.win_rate),
    average_win: Number.parseFloat(form.average_win),
    average_loss: Number.parseFloat(form.average_loss),
    number_of_trades: Number.parseInt(form.number_of_trades, 10),
    number_of_simulations: Number.parseInt(form.number_of_simulations, 10),
    risk_per_trade: Number.parseFloat(form.risk_per_trade)
  };
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: Math.abs(value) > 1000 ? 0 : 2 }).format(value);
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}
