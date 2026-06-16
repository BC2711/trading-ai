import { act, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { createTestQueryClient } from "./test/test-utils";
import * as api from "./services/api";

vi.mock("./hooks/useRealtimeStreams", () => ({
  useRealtimeStreams: vi.fn()
}));

vi.mock("./components/layout/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <div data-testid="app-layout">{children}</div>
}));

vi.mock("./pages/ProductionPages", () => ({
  LoginPage: ({ onAuthenticated }: { onAuthenticated: () => void }) => (
    <main>
      <h1>Mock Login</h1>
      <button onClick={onAuthenticated}>Complete login</button>
    </main>
  ),
  UsersPage: () => <h1>Users Route</h1>,
  AiModelsPage: () => <h1>AI Models Route</h1>,
  ApiKeysPage: () => <h1>API Keys Route</h1>,
  BacktestsPage: () => <h1>Backtests Route</h1>,
  LogsPage: () => <h1>Logs Route</h1>,
  NotificationsPage: () => <h1>Notifications Route</h1>,
  OrdersPage: () => <h1>Orders Route</h1>,
  PositionsPage: () => <h1>Positions Route</h1>,
  RiskSettingsPage: () => <h1>Risk Settings Route</h1>,
  StrategiesPage: () => <h1>Strategies Route</h1>,
  TradeHistoryPage: () => <h1>Trade History Route</h1>
}));

vi.mock("./services/api", async () => {
  const actual = await vi.importActual<typeof import("./services/api")>("./services/api");
  return {
    ...actual,
    ensureActiveSession: vi.fn(),
    hasStoredAccessToken: vi.fn(),
    onAuthExpired: vi.fn()
  };
});

function renderApp() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <App />
    </QueryClientProvider>
  );
}

describe("App route protection", () => {
  beforeEach(() => {
    window.location.hash = "#/users";
    vi.mocked(api.onAuthExpired).mockReturnValue(() => undefined);
  });

  it("shows login for protected routes when there is no active session", async () => {
    vi.mocked(api.hasStoredAccessToken).mockReturnValue(false);
    vi.mocked(api.ensureActiveSession).mockResolvedValue(false);

    renderApp();

    expect(await screen.findByRole("heading", { name: /mock login/i })).toBeInTheDocument();
    expect(screen.queryByTestId("app-layout")).not.toBeInTheDocument();
  });

  it("renders a protected route after session validation succeeds", async () => {
    vi.mocked(api.hasStoredAccessToken).mockReturnValue(true);
    vi.mocked(api.ensureActiveSession).mockResolvedValue(true);

    renderApp();

    expect(await screen.findByRole("heading", { name: /users route/i })).toBeInTheDocument();
    expect(screen.getByTestId("app-layout")).toBeInTheDocument();
  });

  it("returns to login when the auth-expired event callback fires", async () => {
    let expireCallback: (() => void) | undefined;
    vi.mocked(api.hasStoredAccessToken).mockReturnValue(true);
    vi.mocked(api.ensureActiveSession).mockResolvedValue(true);
    vi.mocked(api.onAuthExpired).mockImplementation((callback) => {
      expireCallback = callback;
      return () => undefined;
    });

    renderApp();
    expect(await screen.findByRole("heading", { name: /users route/i })).toBeInTheDocument();
    act(() => {
      expireCallback?.();
    });

    await waitFor(() => expect(screen.getByRole("heading", { name: /mock login/i })).toBeInTheDocument());
  });
});
