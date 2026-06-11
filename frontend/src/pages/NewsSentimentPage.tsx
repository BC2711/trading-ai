import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Newspaper, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";

import type { SentimentResponse } from "../api/sentimentApi";
import { analyzeSentiment, fetchSentiment } from "../api/sentimentApi";
import { SentimentSummaryCards } from "../components/sentiment/SentimentSummaryCards";
import { SentimentTable } from "../components/sentiment/SentimentTable";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Skeleton } from "../components/ui/LoadingSpinner";

export function NewsSentimentPage() {
  const queryClient = useQueryClient();
  const [symbol, setSymbol] = useState("");
  const sentimentQuery = useQuery({ queryKey: ["sentiment"], queryFn: fetchSentiment, refetchInterval: 60_000 });
  const analyzeMutation = useMutation({
    mutationFn: () => analyzeSentiment(symbol.trim().toUpperCase() || undefined),
    onSuccess: (data) => {
      queryClient.setQueryData<SentimentResponse>(["sentiment"], data);
    }
  });

  const filteredItems = useMemo(() => {
    const value = symbol.trim().toUpperCase();
    const items = sentimentQuery.data?.items ?? [];
    if (!value || analyzeMutation.isSuccess) return items;
    return items.filter((item) => item.symbol.includes(value) || item.related_asset.includes(value));
  }, [analyzeMutation.isSuccess, sentimentQuery.data?.items, symbol]);

  const isLoading = sentimentQuery.isLoading || analyzeMutation.isPending;

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Newspaper size={14} aria-hidden />
              News and social intelligence
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">News Sentiment</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Track placeholder news, X, Reddit, and CryptoPanic sentiment by symbol, impact level, source, and related asset.
            </p>
          </div>
          <div className="grid gap-3 sm:min-w-[360px] sm:grid-cols-[1fr_auto] sm:items-end">
            <Input
              label="Symbol"
              placeholder="BTCUSDT"
              value={symbol}
              onChange={(event) => {
                setSymbol(event.target.value.toUpperCase());
                if (analyzeMutation.isSuccess) {
                  analyzeMutation.reset();
                }
              }}
            />
            <Button icon={RefreshCw} loading={analyzeMutation.isPending} onClick={() => analyzeMutation.mutate()} className="min-h-11">
              Analyze
            </Button>
          </div>
        </div>
      </Card>

      {sentimentQuery.isError ? <Alert tone="error">Unable to load news sentiment.</Alert> : null}
      {analyzeMutation.isError ? <Alert tone="error">Unable to analyze sentiment for that symbol.</Alert> : null}
      {analyzeMutation.isSuccess ? <Alert tone="success">Sentiment analysis refreshed for {symbol.trim() || "the market"}.</Alert> : null}

      {sentimentQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
      ) : (
        <SentimentSummaryCards data={sentimentQuery.data} />
      )}

      <SentimentTable items={filteredItems} loading={isLoading} />
    </div>
  );
}
