import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrainCircuit, CheckCircle2, Database, FlaskConical, Layers3 } from "lucide-react";
import { useState } from "react";

import { MODEL_FEATURES, trainModel } from "../api/modelTrainingApi";
import type { ModelAlgorithm } from "../api/modelTrainingApi";
import { ModelMetricCard } from "../components/models/ModelMetricCard";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Skeleton } from "../components/ui/LoadingSpinner";
import { Select } from "../components/ui/Select";
import { fetchSymbols } from "../services/api";

export function ModelTrainingPage() {
  const queryClient = useQueryClient();
  const symbolsQuery = useQuery({ queryKey: ["symbols"], queryFn: fetchSymbols });
  const [form, setForm] = useState({
    name: "AI Direction Model",
    symbol: "BTCUSDT",
    timeframe: "15m",
    algorithm: "random_forest" as ModelAlgorithm,
    lookback: "240"
  });
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>(MODEL_FEATURES.slice(0, 16));
  const mutation = useMutation({
    mutationFn: () =>
      trainModel({
        name: form.name,
        symbol: form.symbol,
        timeframe: form.timeframe,
        model_type: form.algorithm,
        lookback: Number.parseInt(form.lookback, 10) || 240,
        selected_features: selectedFeatures
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-models"] })
  });
  const model = mutation.data;

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <BrainCircuit size={14} aria-hidden />
              AI pipeline
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Model Training</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Train versioned models from the shared feature store and register them for inference.
            </p>
          </div>
          <Button icon={FlaskConical} loading={mutation.isPending} disabled={!selectedFeatures.length} onClick={() => mutation.mutate()}>
            Start training
          </Button>
        </div>
      </Card>

      {mutation.isError ? <Alert tone="error">Training failed. Check market data depth, feature selection, and algorithm availability.</Alert> : null}
      {mutation.isPending ? <Alert tone="info">Training in progress. The model will appear in the registry when complete.</Alert> : null}
      {model ? <Alert tone="success">Training complete: {model.name} v{model.version} is registered.</Alert> : null}

      <section className="grid gap-4 xl:grid-cols-[380px_minmax(0,1fr)] xl:gap-6">
        <Card className="p-5">
          <h2 className="text-lg font-black text-slate-950 dark:text-white">Training Setup</h2>
          {symbolsQuery.isLoading ? (
            <Skeleton className="mt-4 h-72" />
          ) : (
            <div className="mt-4 grid gap-3">
              <Input label="Model name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
              <Select
                label="Symbol"
                value={form.symbol}
                options={(symbolsQuery.data?.length ? symbolsQuery.data : [{ symbol: "BTCUSDT" }]).map((symbol) => symbol.symbol)}
                onChange={(event) => setForm((current) => ({ ...current, symbol: event.target.value }))}
              />
              <Select label="Timeframe" value={form.timeframe} options={["1m", "5m", "15m", "1h", "4h", "1d"]} onChange={(event) => setForm((current) => ({ ...current, timeframe: event.target.value }))} />
              <Select
                label="Algorithm"
                value={form.algorithm}
                options={[
                  { label: "Random Forest", value: "random_forest" },
                  { label: "XGBoost", value: "xgboost" },
                  { label: "LightGBM", value: "lightgbm" },
                  { label: "LSTM placeholder", value: "lstm" },
                  { label: "Transformer placeholder", value: "transformer" }
                ]}
                onChange={(event) => setForm((current) => ({ ...current, algorithm: event.target.value as ModelAlgorithm }))}
              />
              <Input label="Training period" type="number" min="80" max="1000" value={form.lookback} onChange={(event) => setForm((current) => ({ ...current, lookback: event.target.value }))} />
            </div>
          )}
        </Card>

        <Card className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-black text-slate-950 dark:text-white">Feature Selection</h2>
              <p className="mt-1 text-sm font-semibold text-slate-500 dark:text-white/50">{selectedFeatures.length} selected</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setSelectedFeatures(MODEL_FEATURES)}>
                Select all
              </Button>
              <Button variant="ghost" onClick={() => setSelectedFeatures(MODEL_FEATURES.slice(0, 12))}>
                Core set
              </Button>
            </div>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {MODEL_FEATURES.map((feature) => (
              <label key={feature} className="flex min-h-10 items-center gap-2 rounded-[8px] border border-white/10 bg-white/10 px-3 py-2 text-sm font-semibold text-slate-700 dark:bg-white/[0.04] dark:text-white/65">
                <input
                  type="checkbox"
                  checked={selectedFeatures.includes(feature)}
                  onChange={(event) =>
                    setSelectedFeatures((current) => event.target.checked ? [...current, feature] : current.filter((item) => item !== feature))
                  }
                />
                <span>{feature}</span>
              </label>
            ))}
          </div>
        </Card>
      </section>

      {model ? (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ModelMetricCard icon={CheckCircle2} label="Status" value={model.status} detail={model.deployed ? "Active" : "Ready"} />
          <ModelMetricCard icon={Layers3} label="Version" value={`v${model.version}`} detail={model.model_type} />
          <ModelMetricCard icon={Database} label="Feature Rows" value={String(model.metrics.feature_rows ?? 0)} detail={`${model.feature_names.length} features`} />
          <ModelMetricCard icon={BrainCircuit} label="Accuracy" value={`${(Number(model.metrics.accuracy ?? 0) * 100).toFixed(1)}%`} detail={`F1 ${(Number(model.metrics.f1 ?? 0) * 100).toFixed(1)}%`} />
        </section>
      ) : null}
    </div>
  );
}
