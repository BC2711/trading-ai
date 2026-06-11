import { Activity, Gauge, Radar, ShieldAlert } from "lucide-react";

import type { ScannerResult } from "../../api/scannerApi";
import { cn } from "../../utils/cn";
import { Card } from "../ui/Card";

type ScannerSummaryCardsProps = {
  results: ScannerResult[];
};

export function ScannerSummaryCards({ results }: ScannerSummaryCardsProps) {
  const actionable = results.filter((result) => result.signal === "buy" || result.signal === "sell");
  const averageConfidence = results.length
    ? results.reduce((total, result) => total + result.confidence, 0) / results.length
    : 0;
  const highRisk = results.filter((result) => result.risk_level === "high").length;
  const topSignal = results[0];

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <SummaryCard
        label="Symbols Scanned"
        value={String(results.length)}
        detail={`${actionable.length} actionable signals`}
        icon={Radar}
        tone="cyan"
      />
      <SummaryCard
        label="Average Confidence"
        value={formatPercent(averageConfidence)}
        detail="Across current scan"
        icon={Gauge}
        tone={averageConfidence >= 0.7 ? "emerald" : "amber"}
        usage={averageConfidence}
      />
      <SummaryCard
        label="High Risk"
        value={String(highRisk)}
        detail={`${results.length - highRisk} within low or medium risk`}
        icon={ShieldAlert}
        tone={highRisk > 0 ? "rose" : "emerald"}
      />
      <SummaryCard
        label="Top Signal"
        value={topSignal ? topSignal.symbol : "None"}
        detail={topSignal ? `${topSignal.signal.toUpperCase()} - ${formatPercent(topSignal.confidence)}` : "No scanner rows"}
        icon={Activity}
        tone={topSignal?.signal === "buy" ? "emerald" : topSignal?.signal === "sell" ? "rose" : "violet"}
      />
    </section>
  );
}

function SummaryCard({
  label,
  value,
  detail,
  usage,
  icon: Icon,
  tone
}: {
  label: string;
  value: string;
  detail: string;
  usage?: number;
  icon: typeof Radar;
  tone: "cyan" | "emerald" | "amber" | "rose" | "violet";
}) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-bold text-slate-500 dark:text-white/50">{label}</p>
          <p className="mt-3 truncate text-2xl font-black text-slate-950 dark:text-white">{value}</p>
          <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-white/40">{detail}</p>
        </div>
        <span
          className={cn(
            "grid size-11 shrink-0 place-items-center rounded-[8px]",
            tone === "cyan" && "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100",
            tone === "emerald" && "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100",
            tone === "amber" && "bg-amber-400/15 text-amber-700 dark:text-amber-100",
            tone === "rose" && "bg-rose-400/15 text-rose-700 dark:text-rose-100",
            tone === "violet" && "bg-violet-400/15 text-violet-700 dark:text-violet-100"
          )}
        >
          <Icon size={20} aria-hidden />
        </span>
      </div>
      {usage != null ? (
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/15 dark:bg-white/10">
          <div
            className={cn("h-full rounded-full", usage >= 0.75 ? "bg-emerald-400" : usage >= 0.6 ? "bg-cyan-400" : "bg-amber-400")}
            style={{ width: `${Math.min(100, Math.max(2, usage * 100))}%` }}
          />
        </div>
      ) : null}
    </Card>
  );
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}
