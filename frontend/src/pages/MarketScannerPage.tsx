import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Radar, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";

import type { ScannerFilters as ScannerFilterState } from "../api/scannerApi";
import { fetchScannerResults, runScanner } from "../api/scannerApi";
import { ScannerFilters } from "../components/scanner/ScannerFilters";
import { ScannerSummaryCards } from "../components/scanner/ScannerSummaryCards";
import { ScannerTable } from "../components/scanner/ScannerTable";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";

const defaultFilters: ScannerFilterState = {
  symbol: "",
  signal: "",
  min_confidence: 0,
  risk_level: "",
  timeframe: "15m"
};

export function MarketScannerPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ScannerFilterState>(defaultFilters);
  const scannerQuery = useQuery({
    queryKey: ["scanner"],
    queryFn: () => fetchScannerResults({ timeframe: "15m" }),
    refetchInterval: 30_000
  });
  const runMutation = useMutation({
    mutationFn: () => runScanner({ timeframe: "15m", lookback: 240 }),
    onSuccess: (results) => {
      queryClient.setQueryData(["scanner"], results);
      queryClient.invalidateQueries({ queryKey: ["scanner"] });
    }
  });

  const filteredResults = useMemo(() => {
    const symbolFilter = (filters.symbol ?? "").trim().toUpperCase();
    return (scannerQuery.data ?? []).filter((result) => {
      const matchesSymbol = !symbolFilter || result.symbol.includes(symbolFilter);
      const matchesSignal = !filters.signal || result.signal === filters.signal;
      const matchesConfidence = result.confidence >= (filters.min_confidence ?? 0);
      const matchesRisk = !filters.risk_level || result.risk_level === filters.risk_level;
      return matchesSymbol && matchesSignal && matchesConfidence && matchesRisk;
    });
  }, [filters, scannerQuery.data]);

  const isLoading = scannerQuery.isLoading || runMutation.isPending;

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Radar size={14} aria-hidden />
              Market intelligence
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Market Scanner</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Scan symbols for price, signal quality, RSI, MACD, trend direction, volatility, risk level, and recommended action.
            </p>
          </div>
          <Button
            icon={RefreshCw}
            loading={runMutation.isPending}
            onClick={() => runMutation.mutate()}
            className="min-h-11"
          >
            Run scanner
          </Button>
        </div>
      </Card>

      {scannerQuery.isError ? <Alert tone="error">Unable to load scanner results.</Alert> : null}
      {runMutation.isSuccess ? <Alert tone="success">Scanner completed with {runMutation.data.length} symbols.</Alert> : null}
      {runMutation.isError ? <Alert tone="error">Unable to run the market scanner.</Alert> : null}

      {scannerQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
      ) : (
        <ScannerSummaryCards results={filteredResults} />
      )}

      <ScannerFilters filters={filters} onChange={setFilters} onReset={() => setFilters(defaultFilters)} />
      <ScannerTable results={filteredResults} loading={isLoading} />
    </div>
  );
}
