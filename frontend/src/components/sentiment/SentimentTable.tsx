import { motion } from "framer-motion";

import type { SentimentItem } from "../../api/sentimentApi";
import { Card } from "../ui/Card";
import { Skeleton } from "../ui/LoadingSpinner";
import { EmptyState } from "../table/EmptyState";
import { ImpactBadge, SentimentBadge } from "./SentimentBadges";

type SentimentTableProps = {
  items: SentimentItem[];
  loading?: boolean;
};

export function SentimentTable({ items, loading = false }: SentimentTableProps) {
  return (
    <Card className="p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-4">
        <div>
          <h3 className="text-base font-bold text-slate-950 dark:text-white">News Feed</h3>
          <p className="text-xs font-medium text-slate-500 dark:text-white/50">
            Placeholder feeds from news, X, Reddit, and CryptoPanic scored by symbol
          </p>
        </div>
        <span className="rounded-[8px] border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold text-slate-600 dark:text-white/60">
          {items.length} items
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[960px] border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 z-10 bg-white/30 backdrop-blur-xl dark:bg-slate-950/40">
            <tr>
              {["Symbol", "Score", "Status", "Headline", "Source", "Date", "Impact", "Related Asset"].map((label) => (
                <th
                  key={label}
                  className="border-b border-white/10 px-4 py-3 text-left text-xs font-bold uppercase tracking-normal text-slate-500 dark:text-white/50"
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 5 }).map((_, index) => (
                  <tr key={index}>
                    <td colSpan={8} className="px-4 py-3">
                      <Skeleton className="h-11 w-full" />
                    </td>
                  </tr>
                ))
              : items.map((item) => (
                  <motion.tr
                    key={`${item.symbol}-${item.source}-${item.date}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="group transition-colors hover:bg-white/10 dark:hover:bg-white/5"
                  >
                    <td className="border-b border-white/10 px-4 py-4 font-black text-slate-950 dark:text-white">{item.symbol}</td>
                    <td className="border-b border-white/10 px-4 py-4 font-semibold text-slate-700 dark:text-white/75">
                      {(item.sentiment_score * 100).toFixed(1)}%
                    </td>
                    <td className="border-b border-white/10 px-4 py-4">
                      <SentimentBadge status={item.status} />
                    </td>
                    <td className="max-w-[320px] border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/75">
                      <span className="line-clamp-2 font-semibold">{item.headline}</span>
                    </td>
                    <td className="border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/75">{item.source}</td>
                    <td className="border-b border-white/10 px-4 py-4 text-xs font-semibold text-slate-500 dark:text-white/45">
                      {formatDate(item.date)}
                    </td>
                    <td className="border-b border-white/10 px-4 py-4">
                      <ImpactBadge impact={item.impact_level} />
                    </td>
                    <td className="border-b border-white/10 px-4 py-4 font-semibold text-slate-700 dark:text-white/75">
                      {item.related_asset}
                    </td>
                  </motion.tr>
                ))}
          </tbody>
        </table>
      </div>

      {!loading && items.length === 0 ? (
        <EmptyState title="No sentiment items" message="Run analysis or choose another symbol to populate the news sentiment feed." />
      ) : null}
    </Card>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
