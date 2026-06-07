import { lazy, Suspense } from "react";

import { AppLayout } from "./components/layout/AppLayout";
import { Card } from "./components/ui/Card";
import { LoadingSpinner } from "./components/ui/LoadingSpinner";

const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage }))
);

export function App() {
  return (
    <AppLayout>
      <Suspense
        fallback={
          <Card className="grid min-h-[420px] place-items-center p-6">
            <div className="text-center">
              <LoadingSpinner className="mx-auto mb-4 size-10" />
              <p className="text-sm font-bold text-slate-500 dark:text-white/50">Loading dashboard</p>
            </div>
          </Card>
        }
      >
        <DashboardPage />
      </Suspense>
    </AppLayout>
  );
}
