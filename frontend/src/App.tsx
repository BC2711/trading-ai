import { lazy, Suspense, useEffect, useState } from "react";

import { AppLayout } from "./components/layout/AppLayout";
import { Card } from "./components/ui/Card";
import { LoadingSpinner } from "./components/ui/LoadingSpinner";
import {
  AiModelsPage,
  ApiKeysPage,
  BacktestsPage,
  LoginPage,
  LogsPage,
  NotificationsPage,
  OrdersPage,
  PositionsPage,
  RiskSettingsPage,
  StrategiesPage,
  TradeHistoryPage,
  UsersPage
} from "./pages/ProductionPages";

const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage }))
);
const TradingPage = lazy(() =>
  import("./pages/TradingPage").then((module) => ({ default: module.TradingPage }))
);
const ActivityPage = lazy(() =>
  import("./pages/ActivityPage").then((module) => ({ default: module.ActivityPage }))
);

export function App() {
  const [route, setRoute] = useState(getRoute());
  const [authenticated, setAuthenticated] = useState(() => Boolean(localStorage.getItem("trading_ai_token")));

  useEffect(() => {
    const handleHashChange = () => setRoute(getRoute());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  if (!authenticated) {
    return <LoginPage onAuthenticated={() => setAuthenticated(true)} />;
  }

  return (
    <AppLayout>
      <Suspense fallback={<PageFallback />}>
        {renderRoute(route)}
      </Suspense>
    </AppLayout>
  );
}

function PageFallback() {
  return (
    <Card className="grid min-h-[420px] place-items-center p-6">
      <div className="text-center">
        <LoadingSpinner className="mx-auto mb-4 size-10" />
        <p className="text-sm font-bold text-slate-500 dark:text-white/50">Loading workspace</p>
      </div>
    </Card>
  );
}

function renderRoute(route: string) {
  if (route.startsWith("users")) return <UsersPage />;
  if (route.startsWith("api-keys")) return <ApiKeysPage />;
  if (route.startsWith("strategies")) return <StrategiesPage />;
  if (route.startsWith("backtests")) return <BacktestsPage />;
  if (route.startsWith("ai-models")) return <AiModelsPage />;
  if (route.startsWith("risk-settings")) return <RiskSettingsPage />;
  if (route.startsWith("orders") || route === "trading/orders") return <OrdersPage />;
  if (route.startsWith("positions") || route === "trading/positions") return <PositionsPage />;
  if (route.startsWith("trade-history")) return <TradeHistoryPage />;
  if (route.startsWith("logs")) return <LogsPage />;
  if (route.startsWith("notifications")) return <NotificationsPage />;
  if (route.startsWith("trading")) return <TradingPage />;
  if (route.startsWith("activity")) return <ActivityPage />;
  return <DashboardPage />;
}

function getRoute() {
  return window.location.hash.replace(/^#\/?/, "") || "overview";
}
