import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import type { PaperTradingOrder, PaperTradingPosition } from "../api/paperTradingApi";
import type { PortfolioSummary } from "../api/portfolioApi";
import type { ScannerResult } from "../api/scannerApi";
import type { NotificationResource } from "../services/api";
import { ReconnectingWebSocketClient } from "../utils/websocketClient";

export type LivePrice = {
  symbol: string;
  price: number;
  change_pct: number;
  timeframe: string;
  updated_at: string;
};

export function useRealtimeStreams(enabled: boolean) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled) return;

    const clients = [
      new ReconnectingWebSocketClient<LivePrice[]>({
        path: "/api/ws/prices",
        onMessage: (message) => {
          if (Array.isArray(message.payload)) {
            queryClient.setQueryData(["live-prices"], message.payload);
          }
        }
      }),
      new ReconnectingWebSocketClient<ScannerResult[]>({
        path: "/api/ws/signals",
        onMessage: (message) => {
          if (Array.isArray(message.payload)) {
            queryClient.setQueryData(["scanner"], message.payload);
          }
        }
      }),
      new ReconnectingWebSocketClient<PaperTradingOrder[]>({
        path: "/api/ws/orders",
        onMessage: (message) => {
          if (Array.isArray(message.payload)) {
            queryClient.setQueryData(["orders"], message.payload);
            queryClient.setQueryData(["paper-trading", "orders"], message.payload);
            queryClient.setQueriesData({ queryKey: ["orders"] }, () => message.payload);
          }
        }
      }),
      new ReconnectingWebSocketClient<PaperTradingPosition[]>({
        path: "/api/ws/positions",
        onMessage: (message) => {
          if (Array.isArray(message.payload)) {
            queryClient.setQueryData(["positions"], message.payload);
            queryClient.setQueriesData({ queryKey: ["positions"] }, () => message.payload);
            queryClient.setQueryData(["paper-trading", "positions", "all"], message.payload);
            queryClient.setQueryData(["paper-trading", "positions", "open"], message.payload.filter((position) => position.status === "open"));
            queryClient.setQueryData(["paper-trading", "positions", "closed"], message.payload.filter((position) => position.status === "closed"));
          }
        }
      }),
      new ReconnectingWebSocketClient<PortfolioSummary>({
        path: "/api/ws/portfolio",
        onMessage: (message) => {
          if (message.payload && !Array.isArray(message.payload)) {
            queryClient.setQueryData(["portfolio", "summary"], message.payload);
          }
        }
      }),
      new ReconnectingWebSocketClient<NotificationResource[]>({
        path: "/api/ws/notifications",
        onMessage: (message) => {
          if (Array.isArray(message.payload)) {
            queryClient.setQueryData(["notifications", false], message.payload);
            queryClient.setQueryData(["notifications"], message.payload);
          }
        }
      })
    ];

    clients.forEach((client) => client.connect());
    return () => clients.forEach((client) => client.close());
  }, [enabled, queryClient]);
}
