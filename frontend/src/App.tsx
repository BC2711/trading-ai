import { lazy, Suspense, useEffect, useState } from "react";

import { AppLayout } from "./components/layout/AppLayout";
import { Card } from "./components/ui/Card";
import { LoadingSpinner } from "./components/ui/LoadingSpinner";
import { useRealtimeStreams } from "./hooks/useRealtimeStreams";
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
const StrategyBuilderPage = lazy(() =>
  import("./pages/StrategyBuilderPage").then((module) => ({ default: module.StrategyBuilderPage }))
);
const WalkForwardTestingPage = lazy(() =>
  import("./pages/WalkForwardTestingPage").then((module) => ({ default: module.WalkForwardTestingPage }))
);
const ModelTrainingPage = lazy(() =>
  import("./pages/ModelTrainingPage").then((module) => ({ default: module.ModelTrainingPage }))
);
const ModelRegistryPage = lazy(() =>
  import("./pages/ModelRegistryPage").then((module) => ({ default: module.ModelRegistryPage }))
);
const CopilotPage = lazy(() =>
  import("./pages/CopilotPage").then((module) => ({ default: module.CopilotPage }))
);
const TradingPage = lazy(() =>
  import("./pages/TradingPage").then((module) => ({ default: module.TradingPage }))
);
const PortfolioPage = lazy(() =>
  import("./pages/PortfolioPage").then((module) => ({ default: module.PortfolioPage }))
);
const PaperTradingPage = lazy(() =>
  import("./pages/PaperTradingPage").then((module) => ({ default: module.PaperTradingPage }))
);
const BrokerConnectionsPage = lazy(() =>
  import("./pages/BrokerConnectionsPage").then((module) => ({ default: module.BrokerConnectionsPage }))
);
const MarketScannerPage = lazy(() =>
  import("./pages/MarketScannerPage").then((module) => ({ default: module.MarketScannerPage }))
);
const NewsSentimentPage = lazy(() =>
  import("./pages/NewsSentimentPage").then((module) => ({ default: module.NewsSentimentPage }))
);
const EconomicCalendarPage = lazy(() =>
  import("./pages/EconomicCalendarPage").then((module) => ({ default: module.EconomicCalendarPage }))
);
const NotificationSettingsPage = lazy(() =>
  import("./pages/NotificationSettingsPage").then((module) => ({ default: module.NotificationSettingsPage }))
);
const RolesPermissionsPage = lazy(() =>
  import("./pages/RolesPermissionsPage").then((module) => ({ default: module.RolesPermissionsPage }))
);
const AuditLogsPage = lazy(() =>
  import("./pages/AuditLogsPage").then((module) => ({ default: module.AuditLogsPage }))
);
const SystemMonitoringPage = lazy(() =>
  import("./pages/SystemMonitoringPage").then((module) => ({ default: module.SystemMonitoringPage }))
);
const RiskAnalyticsPage = lazy(() =>
  import("./pages/RiskAnalyticsPage").then((module) => ({ default: module.RiskAnalyticsPage }))
);
const PerformanceAnalyticsPage = lazy(() =>
  import("./pages/PerformanceAnalyticsPage").then((module) => ({ default: module.PerformanceAnalyticsPage }))
);
const MonteCarloPage = lazy(() =>
  import("./pages/MonteCarloPage").then((module) => ({ default: module.MonteCarloPage }))
);
const ActivityPage = lazy(() =>
  import("./pages/ActivityPage").then((module) => ({ default: module.ActivityPage }))
);

export function App() {
  const [route, setRoute] = useState(getRoute());
  const [authenticated, setAuthenticated] = useState(() => Boolean(localStorage.getItem("trading_ai_token")));
  useRealtimeStreams(authenticated);

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
  if (route.startsWith("administration/roles-permissions") || route.startsWith("roles-permissions")) return <RolesPermissionsPage />;
  if (route.startsWith("administration/audit-logs") || route === "activity/audit") return <AuditLogsPage />;
  if (route.startsWith("administration/system-monitoring") || route.startsWith("system-monitoring")) return <SystemMonitoringPage />;
  if (route.startsWith("api-keys")) return <ApiKeysPage />;
  if (route.startsWith("strategies/builder")) return <StrategyBuilderPage />;
  if (route.startsWith("strategies")) return <StrategiesPage />;
  if (route.startsWith("backtests/walk-forward")) return <WalkForwardTestingPage />;
  if (route.startsWith("backtests")) return <BacktestsPage />;
  if (route.startsWith("ai/model-training")) return <ModelTrainingPage />;
  if (route.startsWith("ai/model-registry")) return <ModelRegistryPage />;
  if (route.startsWith("ai/copilot") || route.startsWith("copilot")) return <CopilotPage />;
  if (route.startsWith("ai-models")) return <AiModelsPage />;
  if (route.startsWith("risk-settings")) return <RiskSettingsPage />;
  if (route.startsWith("risk-analytics")) return <RiskAnalyticsPage />;
  if (route.startsWith("analytics/performance") || route.startsWith("performance-analytics")) return <PerformanceAnalyticsPage />;
  if (route.startsWith("risk/monte-carlo") || route.startsWith("monte-carlo")) return <MonteCarloPage />;
  if (route.startsWith("portfolio") || route === "trading/portfolio") return <PortfolioPage />;
  if (route.startsWith("paper") || route === "trading/paper") return <PaperTradingPage />;
  if (route.startsWith("brokers") || route === "trading/brokers") return <BrokerConnectionsPage />;
  if (route.startsWith("market/calendar") || route.startsWith("calendar")) return <EconomicCalendarPage />;
  if (route.startsWith("market/sentiment") || route.startsWith("sentiment")) return <NewsSentimentPage />;
  if (route.startsWith("market/scanner") || route.startsWith("scanner")) return <MarketScannerPage />;
  if (route.startsWith("orders") || route === "trading/orders") return <OrdersPage />;
  if (route.startsWith("positions") || route === "trading/positions") return <PositionsPage />;
  if (route.startsWith("trade-history")) return <TradeHistoryPage />;
  if (route.startsWith("logs")) return <LogsPage />;
  if (route.startsWith("administration/notification-settings") || route.startsWith("notifications/settings")) return <NotificationSettingsPage />;
  if (route.startsWith("notifications")) return <NotificationsPage />;
  if (route.startsWith("trading")) return <TradingPage />;
  if (route.startsWith("activity")) return <ActivityPage />;
  return <DashboardPage />;
}

function getRoute() {
  return window.location.hash.replace(/^#\/?/, "") || "overview";
}
