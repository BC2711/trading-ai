import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardPage } from "./DashboardPage";
import { renderWithClient } from "../test/test-utils";
import { useSignals } from "../hooks/useSignals";
import * as api from "../services/api";

vi.mock("../components/SignalChart", () => ({
  SignalChart: ({ signals }: { signals: unknown[] }) => <div data-testid="signal-chart">{signals.length} chart signals</div>
}));

vi.mock("../hooks/useSignals", () => ({
  useSignals: vi.fn()
}));

vi.mock("../services/api", async () => {
  const actual = await vi.importActual<typeof import("../services/api")>("../services/api");
  return {
    ...actual,
    fetchSymbols: vi.fn(),
    fetchMarketDataSchedule: vi.fn(),
    fetchStrategies: vi.fn(),
    fetchRiskSettings: vi.fn(),
    fetchBacktests: vi.fn(),
    fetchAIAnalyses: vi.fn(),
    fetchAIProviderStatus: vi.fn(),
    fetchOrders: vi.fn(),
    fetchPositions: vi.fn(),
    fetchCandles: vi.fn(),
    refreshMarketData: vi.fn(),
    runBacktest: vi.fn(),
    updateStrategy: vi.fn(),
    updateRiskSettings: vi.fn(),
    analyzeSignal: vi.fn(),
    createPaperOrder: vi.fn(),
    closePosition: vi.fn()
  };
});

const now = "2026-06-16T00:00:00Z";

function mockDashboardApi() {
  vi.mocked(api.fetchSymbols).mockResolvedValue([
    { id: 1, symbol: "BTCUSDT", base_asset: "BTC", quote_asset: "USDT", market: "crypto", exchange: "binance", status: "active", created_at: now }
  ]);
  vi.mocked(api.fetchMarketDataSchedule).mockResolvedValue({
    enabled: true,
    job_id: "market-sync",
    interval_minutes: 15,
    symbols: ["BTCUSDT"],
    timeframe: "15m",
    limit: 500,
    regenerate_signals: true
  });
  vi.mocked(api.fetchStrategies).mockResolvedValue([
    { id: 1, name: "EMA RSI", description: "Default", timeframe: "15m", status: "active", parameters: {}, enabled: true, performance: {}, created_at: now }
  ]);
  vi.mocked(api.fetchRiskSettings).mockResolvedValue([
    {
      id: 1,
      name: "Default Paper Risk",
      max_risk_per_trade: 0.01,
      max_daily_loss: 0.03,
      max_weekly_loss: 0.08,
      max_drawdown: 0.15,
      max_open_trades: 3,
      max_symbol_exposure: 0.2,
      max_leverage: 1,
      max_consecutive_losses: 3,
      emergency_stop: false,
      live_trading_enabled: false,
      status: "active",
      created_at: now
    }
  ]);
  vi.mocked(api.fetchBacktests).mockResolvedValue([]);
  vi.mocked(api.fetchAIAnalyses).mockResolvedValue([]);
  vi.mocked(api.fetchAIProviderStatus).mockResolvedValue({ provider: "rules", openai_available: false, available_providers: ["rules"] });
  vi.mocked(api.fetchOrders).mockResolvedValue([]);
  vi.mocked(api.fetchPositions).mockResolvedValue([]);
  vi.mocked(api.fetchCandles).mockResolvedValue([
    { id: 1, symbol: "BTCUSDT", timeframe: "15m", opened_at: now, open: 65000, high: 65100, low: 64900, close: 65000, volume: 10, spread: 1 },
    { id: 2, symbol: "BTCUSDT", timeframe: "15m", opened_at: now, open: 65000, high: 65200, low: 64950, close: 65100, volume: 12, spread: 1 }
  ]);
}

describe("DashboardPage states", () => {
  beforeEach(() => {
    mockDashboardApi();
    vi.mocked(useSignals).mockReturnValue({
      signals: [],
      isLoading: false,
      isError: false
    });
  });

  it("shows loading copy while dashboard signals load", () => {
    vi.mocked(useSignals).mockReturnValue({
      signals: [],
      isLoading: true,
      isError: false
    });

    renderWithClient(<DashboardPage />);

    expect(screen.getByText(/loading signals/i)).toBeInTheDocument();
    expect(screen.getByText(/ai trading dashboard/i)).toBeInTheDocument();
  });

  it("shows an empty state when there are no market signals", async () => {
    renderWithClient(<DashboardPage />);

    expect(await screen.findByText(/no market signals yet/i)).toBeInTheDocument();
    expect(screen.getByText(/create signal source/i)).toBeInTheDocument();
  });

  it("shows API error handling when live signals fail", async () => {
    vi.mocked(useSignals).mockReturnValue({
      signals: [],
      isLoading: false,
      isError: true
    });

    renderWithClient(<DashboardPage />);

    expect(await screen.findByText(/unable to load live signals/i)).toBeInTheDocument();
  });
});
