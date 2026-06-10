import type { LucideIcon } from "lucide-react";

import { Card } from "../ui/Card";
import { cn } from "../../utils/cn";

type PortfolioMetricCardProps = {
  label: string;
  value: string;
  detail?: string;
  icon: LucideIcon;
  tone?: "cyan" | "emerald" | "amber" | "violet" | "rose";
};

export function PortfolioMetricCard({ label, value, detail, icon: Icon, tone = "cyan" }: PortfolioMetricCardProps) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-bold text-slate-500 dark:text-white/50">{label}</p>
          <p className="mt-3 truncate text-2xl font-black text-slate-950 dark:text-white">{value}</p>
          {detail ? <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-white/40">{detail}</p> : null}
        </div>
        <span
          className={cn(
            "grid size-11 shrink-0 place-items-center rounded-[8px]",
            tone === "cyan" && "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100",
            tone === "emerald" && "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100",
            tone === "amber" && "bg-amber-400/15 text-amber-700 dark:text-amber-100",
            tone === "violet" && "bg-violet-400/15 text-violet-700 dark:text-violet-100",
            tone === "rose" && "bg-rose-400/15 text-rose-700 dark:text-rose-100"
          )}
        >
          <Icon size={20} aria-hidden />
        </span>
      </div>
    </Card>
  );
}
