import { useQuery } from "@tanstack/react-query";

import {
  fetchPortfolioAllocation,
  fetchPortfolioExposure,
  fetchPortfolioPerformance,
  fetchPortfolioPnl,
  fetchPortfolioSummary
} from "../api/portfolioApi";

export function usePortfolioSummary() {
  return useQuery({
    queryKey: ["portfolio", "summary"],
    queryFn: fetchPortfolioSummary,
    refetchInterval: 30_000
  });
}

export function usePortfolioPerformance() {
  return useQuery({
    queryKey: ["portfolio", "performance"],
    queryFn: fetchPortfolioPerformance,
    refetchInterval: 30_000
  });
}

export function usePortfolioExposure() {
  return useQuery({
    queryKey: ["portfolio", "exposure"],
    queryFn: fetchPortfolioExposure,
    refetchInterval: 30_000
  });
}

export function usePortfolioAllocation() {
  return useQuery({
    queryKey: ["portfolio", "allocation"],
    queryFn: fetchPortfolioAllocation,
    refetchInterval: 30_000
  });
}

export function usePortfolioPnl() {
  return useQuery({
    queryKey: ["portfolio", "pnl"],
    queryFn: fetchPortfolioPnl,
    refetchInterval: 30_000
  });
}
