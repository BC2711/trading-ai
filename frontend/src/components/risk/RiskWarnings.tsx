import { AlertTriangle } from "lucide-react";

import { EmptyState } from "../table/EmptyState";
import { Alert } from "../ui/Alert";
import { Card } from "../ui/Card";

export function RiskWarnings({ warnings }: { warnings: string[] }) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="mb-4 flex items-center gap-2">
        <AlertTriangle size={18} className="text-amber-500" aria-hidden />
        <h2 className="text-lg font-black text-slate-950 dark:text-white">Risk Warnings</h2>
      </div>
      {warnings.length ? (
        <div className="grid gap-2">
          {warnings.map((warning) => (
            <Alert key={warning} tone="warning">{warning}</Alert>
          ))}
        </div>
      ) : (
        <EmptyState title="No active warnings" message="Risk usage is currently within configured limits." />
      )}
    </Card>
  );
}
