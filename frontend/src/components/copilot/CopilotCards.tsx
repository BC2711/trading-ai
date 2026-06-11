import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";

import type { CopilotInsightCard } from "../../api/copilotApi";
import { cn } from "../../utils/cn";

type CopilotCardsProps = {
  cards: CopilotInsightCard[];
};

export function CopilotCards({ cards }: CopilotCardsProps) {
  if (cards.length === 0) return null;

  return (
    <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => {
        const Icon = card.tone === "success" ? CheckCircle2 : card.tone === "warning" ? AlertTriangle : card.tone === "error" ? XCircle : Info;
        return (
          <div
            key={`${card.title}-${card.value}`}
            className={cn(
              "rounded-[8px] border p-3 backdrop-blur-md",
              "border-white/15 bg-white/10 dark:bg-white/5",
              card.tone === "success" && "text-emerald-700 dark:text-emerald-100",
              card.tone === "warning" && "text-amber-700 dark:text-amber-100",
              card.tone === "error" && "text-rose-700 dark:text-rose-100",
              (!card.tone || card.tone === "info") && "text-cyan-700 dark:text-cyan-100"
            )}
          >
            <div className="flex items-center gap-2">
              <Icon size={15} aria-hidden />
              <p className="text-xs font-black uppercase tracking-normal">{card.title}</p>
            </div>
            <p className="mt-2 text-lg font-black text-slate-950 dark:text-white">{card.value}</p>
            <p className="mt-1 text-xs font-semibold leading-5 text-slate-600 dark:text-white/55">{card.detail}</p>
          </div>
        );
      })}
    </div>
  );
}
