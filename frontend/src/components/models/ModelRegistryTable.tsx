import type { AIModelResource } from "../../services/api";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

export function ModelRegistryTable({
  models,
  activatingId,
  onActivate,
  onSelect
}: {
  models: AIModelResource[];
  activatingId?: number;
  onActivate: (modelId: number) => void;
  onSelect: (modelId: number) => void;
}) {
  return (
    <Card className="p-0">
      <div className="border-b border-white/10 p-4">
        <h2 className="text-base font-black text-slate-950 dark:text-white">Model Registry</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[920px] text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-slate-500 dark:text-white/45">
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3">Version</th>
              <th className="px-4 py-3">Algorithm</th>
              <th className="px-4 py-3">Accuracy</th>
              <th className="px-4 py-3">Precision</th>
              <th className="px-4 py-3">Recall</th>
              <th className="px-4 py-3">F1</th>
              <th className="px-4 py-3">Profit Factor</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {models.map((model) => (
              <tr key={model.id} className="border-t border-white/10">
                <td className="px-4 py-3">
                  <button type="button" className="text-left font-black text-slate-950 dark:text-white" onClick={() => onSelect(model.id)}>
                    {model.name}
                  </button>
                  <p className="text-xs font-semibold text-slate-500 dark:text-white/45">
                    {model.symbol} / {model.timeframe}
                  </p>
                </td>
                <td className="px-4 py-3 font-bold text-slate-700 dark:text-white/70">v{model.version}</td>
                <td className="px-4 py-3 font-bold text-slate-700 dark:text-white/70">{model.model_type}</td>
                <td className="px-4 py-3">{formatMetric(model.metrics.accuracy)}</td>
                <td className="px-4 py-3">{formatMetric(model.metrics.precision)}</td>
                <td className="px-4 py-3">{formatMetric(model.metrics.recall)}</td>
                <td className="px-4 py-3">{formatMetric(model.metrics.f1)}</td>
                <td className="px-4 py-3">{formatNumber(model.metrics.profit_factor)}</td>
                <td className="px-4 py-3">
                  <Badge tone={model.deployed ? "success" : model.status === "disabled" ? "neutral" : "info"}>
                    {model.deployed ? "active" : model.status}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-right">
                  <Button variant="outline" loading={activatingId === model.id} disabled={model.deployed} onClick={() => onActivate(model.id)}>
                    Activate
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function formatMetric(value: unknown) {
  return `${(Number(value ?? 0) * 100).toFixed(1)}%`;
}

function formatNumber(value: unknown) {
  return Number(value ?? 0).toFixed(2);
}
