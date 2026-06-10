import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrainCircuit, Gauge, Target, TrendingUp } from "lucide-react";
import { useMemo, useState } from "react";

import { activateModel, fetchModelEvaluation, fetchModelRegistry, predictWithModel } from "../api/modelRegistryApi";
import { ModelMetricCard } from "../components/models/ModelMetricCard";
import { ModelRegistryTable } from "../components/models/ModelRegistryTable";
import { EmptyState } from "../components/table/EmptyState";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";

export function ModelRegistryPage() {
  const queryClient = useQueryClient();
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const modelsQuery = useQuery({ queryKey: ["ai-models"], queryFn: fetchModelRegistry });
  const models = modelsQuery.data ?? [];
  const selectedModel = useMemo(() => models.find((model) => model.id === selectedModelId) ?? models[0] ?? null, [models, selectedModelId]);
  const evaluationQuery = useQuery({
    queryKey: ["ai-model-evaluation", selectedModel?.id],
    queryFn: () => fetchModelEvaluation(selectedModel!.id),
    enabled: Boolean(selectedModel)
  });
  const activateMutation = useMutation({
    mutationFn: activateModel,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-models"] })
  });
  const predictMutation = useMutation({
    mutationFn: () => {
      if (!selectedModel) throw new Error("No model selected");
      return predictWithModel({ model_id: selectedModel.id, symbol: selectedModel.symbol, timeframe: selectedModel.timeframe });
    }
  });

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <BrainCircuit size={14} aria-hidden />
              Active model selection
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Model Registry</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Review model versions, evaluation metrics, and activate the model used for inference.
            </p>
          </div>
          <Button disabled={!selectedModel} loading={predictMutation.isPending} onClick={() => predictMutation.mutate()}>
            Predict selected
          </Button>
        </div>
      </Card>

      {modelsQuery.isError ? <Alert tone="error">Unable to load model registry.</Alert> : null}
      {activateMutation.isSuccess ? <Alert tone="success">Model activated for its symbol, timeframe, and algorithm.</Alert> : null}
      {activateMutation.isError ? <Alert tone="error">Unable to activate model.</Alert> : null}
      {predictMutation.data ? (
        <Alert tone="info">
          Prediction: {predictMutation.data.symbol} {predictMutation.data.direction.toUpperCase()} at {(predictMutation.data.confidence * 100).toFixed(1)}% confidence.
        </Alert>
      ) : null}

      {modelsQuery.isLoading ? (
        <Skeleton className="h-[460px]" />
      ) : models.length ? (
        <>
          {evaluationQuery.data ? (
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <ModelMetricCard icon={Target} label="Accuracy" value={formatPercent(evaluationQuery.data.accuracy)} detail={`Samples ${evaluationQuery.data.samples}`} />
              <ModelMetricCard icon={Gauge} label="Precision" value={formatPercent(evaluationQuery.data.precision)} detail={`Recall ${formatPercent(evaluationQuery.data.recall)}`} />
              <ModelMetricCard icon={BrainCircuit} label="F1 Score" value={formatPercent(evaluationQuery.data.f1)} detail={`ROC AUC ${formatPercent(evaluationQuery.data.roc_auc)}`} />
              <ModelMetricCard icon={TrendingUp} label="Profit Factor" value={evaluationQuery.data.profit_factor.toFixed(2)} detail={`${evaluationQuery.data.feature_count} features`} />
            </section>
          ) : null}
          <ModelRegistryTable
            models={models}
            activatingId={activateMutation.isPending ? Number(activateMutation.variables) : undefined}
            onActivate={(modelId) => activateMutation.mutate(modelId)}
            onSelect={setSelectedModelId}
          />
        </>
      ) : (
        <Card className="p-6">
          <EmptyState title="No models trained" message="Train a model from the Model Training page to populate the registry." />
        </Card>
      )}
    </div>
  );
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}
