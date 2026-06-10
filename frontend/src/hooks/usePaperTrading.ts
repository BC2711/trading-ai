import { useQuery } from "@tanstack/react-query";

import {
  fetchPaperAccount,
  fetchPaperTradingOrders,
  fetchPaperTradingPerformance,
  fetchPaperTradingPositions
} from "../api/paperTradingApi";

export function usePaperAccount() {
  return useQuery({
    queryKey: ["paper-trading", "account"],
    queryFn: fetchPaperAccount,
    refetchInterval: 30_000
  });
}

export function usePaperOrders() {
  return useQuery({
    queryKey: ["paper-trading", "orders"],
    queryFn: () => fetchPaperTradingOrders(100),
    refetchInterval: 30_000
  });
}

export function usePaperPositions(status: "open" | "closed" | "all" = "open") {
  return useQuery({
    queryKey: ["paper-trading", "positions", status],
    queryFn: () => fetchPaperTradingPositions(status),
    refetchInterval: 30_000
  });
}

export function usePaperPerformance() {
  return useQuery({
    queryKey: ["paper-trading", "performance"],
    queryFn: fetchPaperTradingPerformance,
    refetchInterval: 30_000
  });
}
