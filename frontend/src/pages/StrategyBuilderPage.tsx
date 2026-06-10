import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, FlaskConical, Layers3, Play, Save, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  activateStrategy,
  createStrategyBuilder,
  deactivateStrategy,
  evaluateStrategy,
  fetchStrategyBuilders,
  updateStrategyRules
} from "../api/strategyBuilderApi";
import type { StrategyBuilder, StrategyRuleInput, StrategyRuleRead } from "../api/strategyBuilderApi";
import { EmptyState } from "../components/table/EmptyState";
import { EvaluationPanel } from "../components/strategy-builder/EvaluationPanel";
import { RuleEditor } from "../components/strategy-builder/RuleEditor";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Skeleton } from "../components/ui/LoadingSpinner";
import { Select } from "../components/ui/Select";

export function StrategyBuilderPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [strategyForm, setStrategyForm] = useState({
    name: "RSI EMA Builder",
    description: "Rule-based strategy created in the builder.",
    timeframe: "15m",
    enabled: false
  });
  const [rule, setRule] = useState<StrategyRuleInput>(defaultRule());
  const [testForm, setTestForm] = useState({ symbol: "BTCUSDT", timeframe: "15m", lookback: "240" });

  const buildersQuery = useQuery({ queryKey: ["strategies", "builder"], queryFn: fetchStrategyBuilders });
  const builders = buildersQuery.data ?? [];
  const selected = useMemo(() => builders.find((item) => item.id === selectedId) ?? null, [builders, selectedId]);

  useEffect(() => {
    if (!selectedId && builders.length) {
      setSelectedId(builders[0].id);
    }
  }, [builders, selectedId]);

  useEffect(() => {
    if (!selected) return;
    setStrategyForm({
      name: selected.name,
      description: selected.description,
      timeframe: selected.timeframe,
      enabled: selected.enabled
    });
    setRule(ruleReadToInput(selected.rules[0] ?? null));
  }, [selected]);

  const createMutation = useMutation({
    mutationFn: () => createStrategyBuilder({ ...strategyForm, rules: [rule] }),
    onSuccess: (created) => {
      setSelectedId(created.id);
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
    }
  });
  const saveRulesMutation = useMutation<StrategyBuilder | StrategyRuleRead[]>({
    mutationFn: () => selectedId ? updateStrategyRules(selectedId, [rule]) : createStrategyBuilder({ ...strategyForm, rules: [rule] }),
    onSuccess: (result) => {
      if (!Array.isArray(result)) {
        setSelectedId(result.id);
      }
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
    }
  });
  const toggleMutation = useMutation({
    mutationFn: () => {
      if (!selected) throw new Error("Select a strategy first");
      return selected.enabled ? deactivateStrategy(selected.id) : activateStrategy(selected.id);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies"] })
  });
  const evaluateMutation = useMutation({
    mutationFn: () => {
      if (!selectedId) throw new Error("Save a strategy before testing");
      return evaluateStrategy(selectedId, {
        symbol: testForm.symbol,
        timeframe: testForm.timeframe,
        lookback: Number.parseInt(testForm.lookback, 10) || 240
      });
    }
  });

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Layers3 size={14} aria-hidden />
              Rule-based strategies
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Strategy Builder</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Build IF / AND / THEN trading rules from technical indicators, save them, and test them against recent market data.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button icon={Save} loading={saveRulesMutation.isPending || createMutation.isPending} onClick={() => selectedId ? saveRulesMutation.mutate() : createMutation.mutate()}>
              {selectedId ? "Save rules" : "Create strategy"}
            </Button>
            <Button variant={selected?.enabled ? "danger" : "success"} icon={ShieldCheck} disabled={!selected} loading={toggleMutation.isPending} onClick={() => toggleMutation.mutate()}>
              {selected?.enabled ? "Deactivate" : "Activate"}
            </Button>
          </div>
        </div>
      </Card>

      {buildersQuery.isError ? <Alert tone="error">Unable to load strategy builders.</Alert> : null}
      {createMutation.isError || saveRulesMutation.isError ? <Alert tone="error">Unable to save strategy rules. Check required fields and strategy name uniqueness.</Alert> : null}
      {toggleMutation.isSuccess ? <Alert tone="success">Strategy activation state updated.</Alert> : null}
      {evaluateMutation.isError ? <Alert tone="error">Unable to evaluate strategy. Save the strategy and make sure candle data is available.</Alert> : null}

      {buildersQuery.isLoading ? (
        <Skeleton className="h-[520px]" />
      ) : (
        <section className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)] xl:gap-6">
          <Card className="p-5">
            <h2 className="text-lg font-black text-slate-950 dark:text-white">Strategies</h2>
            <div className="mt-4 grid gap-3">
              {builders.length ? (
                <Select
                  label="Existing builders"
                  value={selectedId ?? ""}
                  options={builders.map((builder) => ({ label: builder.name, value: String(builder.id) }))}
                  onChange={(event) => setSelectedId(Number(event.target.value))}
                />
              ) : (
                <EmptyState title="No builder strategies" message="Create the first rule-based strategy from the form." />
              )}
              <Input label="Strategy name" value={strategyForm.name} onChange={(event) => setStrategyForm((current) => ({ ...current, name: event.target.value }))} />
              <Input label="Description" value={strategyForm.description} onChange={(event) => setStrategyForm((current) => ({ ...current, description: event.target.value }))} />
              <Select label="Timeframe" value={strategyForm.timeframe} options={["1m", "5m", "15m", "1h", "4h", "1d"]} onChange={(event) => setStrategyForm((current) => ({ ...current, timeframe: event.target.value }))} />
              <div className="rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/[0.04]">
                <p className="text-xs font-bold uppercase text-slate-500 dark:text-white/45">Status</p>
                <div className="mt-2 flex items-center justify-between gap-3">
                  <Badge tone={selected?.enabled ? "success" : "neutral"}>{selected?.enabled ? "active" : "inactive"}</Badge>
                  <span className="text-xs font-semibold text-slate-500 dark:text-white/45">{selected ? `ID ${selected.id}` : "New strategy"}</span>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-black text-slate-950 dark:text-white">Rule</h2>
                <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-white/50">IF conditions pass, THEN execute the selected action.</p>
              </div>
              <Button variant="outline" icon={Activity} onClick={() => setRule(defaultRule())}>
                Reset draft
              </Button>
            </div>
            <RuleEditor rule={rule} onChange={setRule} />
          </Card>
        </section>
      )}

      <section className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)] xl:gap-6">
        <Card className="p-5">
          <h2 className="text-lg font-black text-slate-950 dark:text-white">Test Strategy</h2>
          <div className="mt-4 grid gap-3">
            <Input label="Symbol" value={testForm.symbol} onChange={(event) => setTestForm((current) => ({ ...current, symbol: event.target.value.toUpperCase() }))} />
            <Select label="Timeframe" value={testForm.timeframe} options={["1m", "5m", "15m", "1h", "4h", "1d"]} onChange={(event) => setTestForm((current) => ({ ...current, timeframe: event.target.value }))} />
            <Input label="Lookback candles" type="number" min="30" max="1000" value={testForm.lookback} onChange={(event) => setTestForm((current) => ({ ...current, lookback: event.target.value }))} />
            <Button icon={FlaskConical} loading={evaluateMutation.isPending} disabled={!selectedId} onClick={() => evaluateMutation.mutate()}>
              Test strategy
            </Button>
            <Button variant="ghost" icon={Play} disabled={!selectedId} onClick={() => saveRulesMutation.mutate()}>
              Save before testing
            </Button>
          </div>
        </Card>
        <EvaluationPanel result={evaluateMutation.data} />
      </section>
    </div>
  );
}

function defaultRule(): StrategyRuleInput {
  return {
    name: "Oversold trend continuation",
    logic_operator: "AND",
    priority: 1,
    enabled: true,
    conditions: [
      { sequence: 1, indicator: "RSI", period: 14, operator: "<", value: 30, parameters: {} },
      { sequence: 2, indicator: "EMA", period: 20, operator: ">", value: null, compare_indicator: "EMA", compare_period: 50, parameters: {} }
    ],
    action: { action: "BUY", parameters: {} }
  };
}

function ruleReadToInput(rule: StrategyRuleRead | null): StrategyRuleInput {
  if (!rule) return defaultRule();
  return {
    name: rule.name,
    logic_operator: "AND",
    priority: rule.priority,
    enabled: rule.enabled,
    conditions: rule.conditions.map((condition) => ({
      sequence: condition.sequence,
      indicator: condition.indicator,
      operator: condition.operator,
      value: condition.value ?? null,
      period: condition.period ?? null,
      compare_indicator: condition.compare_indicator ?? null,
      compare_period: condition.compare_period ?? null,
      parameters: condition.parameters ?? {}
    })),
    action: { action: rule.actions[0]?.action ?? "BUY", parameters: rule.actions[0]?.parameters ?? {} }
  };
}
