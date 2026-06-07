import { lazy, Suspense, useEffect, useState } from "react";

import { AppLayout } from "./components/layout/AppLayout";
import { Card } from "./components/ui/Card";
import { LoadingSpinner } from "./components/ui/LoadingSpinner";

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

  useEffect(() => {
    const handleHashChange = () => setRoute(getRoute());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  return (
    <AppLayout>
      <Suspense
        fallback={
          <Card className="grid min-h-[420px] place-items-center p-6">
            <div className="text-center">
              <LoadingSpinner className="mx-auto mb-4 size-10" />
              <p className="text-sm font-bold text-slate-500 dark:text-white/50">Loading workspace</p>
            </div>
          </Card>
        }
      >
        {route.startsWith("trading") ? <TradingPage /> : route.startsWith("activity") ? <ActivityPage /> : <DashboardPage />}
      </Suspense>
    </AppLayout>
  );
}

function getRoute() {
  return window.location.hash.replace(/^#\/?/, "") || "overview";
}
