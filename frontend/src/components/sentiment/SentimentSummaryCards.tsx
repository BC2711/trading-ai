import { BarChart3, Gauge, Newspaper, Radio } from "lucide-react";

import type { SentimentResponse } from "../../api/sentimentApi";
import { cn } from "../../utils/cn";
import { Card } from "../ui/Card";

type SentimentSummaryCardsProps = {
  data?: SentimentResponse;
};

export function SentimentSummaryCards({ data }: SentimentSummaryCardsProps) {
  const items = data?.items ?? [];
  const uniqueSources = new Set(items.map((item) => item.source)).size;
  const highImpact = items.filter((item) => item.impact_level === "high").length;

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <SummaryCard
        label="Market Sentiment"
        value={data ? `${(data.market_sentiment_score * 100).toFixed(1)}%` : "0.0%"}
        detail={data?.market_status ?? "neutral"}
        icon={Gauge}
        tone={data?.market_status === "bullish" ? "emerald" : data?.market_status === "bearish" ? "rose" : "amber"}
      />
      <SummaryCard label="Bullish Items" value={String(data?.bullish_count ?? 0)} detail="Positive news flow" icon={BarChart3} tone="emerald" />
      <SummaryCard label="Bearish Items" value={String(data?.bearish_count ?? 0)} detail="Negative news flow" icon={Radio} tone="rose" />
      <SummaryCard label="Sources" value={String(uniqueSources)} detail={`${highImpact} high-impact items`} icon={Newspaper} tone="cyan" />
    </section>
  );
}

function SummaryCard({
  label,
  value,
  detail,
  icon: Icon,
  tone
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof Gauge;
  tone: "cyan" | "emerald" | "amber" | "rose";
}) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-bold text-slate-500 dark:text-white/50">{label}</p>
          <p className="mt-3 truncate text-2xl font-black text-slate-950 dark:text-white">{value}</p>
          <p className="mt-1 text-xs font-semibold capitalize text-slate-500 dark:text-white/40">{detail}</p>
        </div>
        <span
          className={cn(
            "grid size-11 shrink-0 place-items-center rounded-[8px]",
            tone === "cyan" && "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100",
            tone === "emerald" && "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100",
            tone === "amber" && "bg-amber-400/15 text-amber-700 dark:text-amber-100",
            tone === "rose" && "bg-rose-400/15 text-rose-700 dark:text-rose-100"
          )}
        >
          <Icon size={20} aria-hidden />
        </span>
      </div>
    </Card>
  );
}
