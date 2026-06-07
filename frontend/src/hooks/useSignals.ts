import { useQuery } from "@tanstack/react-query";

import { fetchSignals } from "../services/api";

export function useSignals() {
  const query = useQuery({
    queryKey: ["signals"],
    queryFn: fetchSignals,
    refetchInterval: 30_000
  });

  return {
    signals: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError
  };
}
