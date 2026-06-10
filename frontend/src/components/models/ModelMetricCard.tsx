import type { LucideIcon } from "lucide-react";

import { Card } from "../ui/Card";

export function ModelMetricCard({
  label,
  value,
  detail,
  icon: Icon
}: {
  label: string;
  value: string;
  detail?: string;
  icon: LucideIcon;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 text-slate-500 dark:text-white/45">
        <Icon size={15} aria-hidden />
        <p className="text-xs font-bold uppercase">{label}</p>
      </div>
      <p className="mt-2 text-xl font-black text-slate-950 dark:text-white">{value}</p>
      {detail ? <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-white/45">{detail}</p> : null}
    </Card>
  );
}
