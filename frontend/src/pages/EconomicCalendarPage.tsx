import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays } from "lucide-react";
import { useState } from "react";

import type { CalendarFilters as CalendarFilterState, EconomicCalendarEventCreate } from "../api/calendarApi";
import { createCalendarEvent, fetchCalendarEvents } from "../api/calendarApi";
import { CalendarEventForm } from "../components/calendar/CalendarEventForm";
import { CalendarEventsTable } from "../components/calendar/CalendarEventsTable";
import { CalendarFilters } from "../components/calendar/CalendarFilters";
import { CalendarSummaryCards } from "../components/calendar/CalendarSummaryCards";
import { Alert } from "../components/ui/Alert";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";

const defaultFilters: CalendarFilterState = {
  country: "",
  impact_level: "",
  asset: "",
  start: "",
  end: ""
};

export function EconomicCalendarPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<CalendarFilterState>(defaultFilters);
  const eventsQuery = useQuery({
    queryKey: ["calendar", "events", filters],
    queryFn: () => fetchCalendarEvents(normalizeFilters(filters)),
    refetchInterval: 60_000
  });
  const createMutation = useMutation({
    mutationFn: (event: EconomicCalendarEventCreate) => createCalendarEvent(event),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["calendar", "events"] })
  });

  const events = eventsQuery.data ?? [];
  const isLoading = eventsQuery.isLoading || createMutation.isPending;

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <CalendarDays size={14} aria-hidden />
              Macro event risk
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Economic Calendar</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Track upcoming macro events, impact levels, affected assets, release values, and trading blackout warnings.
            </p>
          </div>
          <div className="grid min-w-[220px] gap-1 rounded-[8px] border border-white/10 bg-white/10 p-3 text-right backdrop-blur-md dark:bg-white/5">
            <span className="text-xs font-bold uppercase text-slate-500 dark:text-white/40">High-impact events</span>
            <span className="text-2xl font-black text-slate-950 dark:text-white">{events.filter((event) => event.high_impact).length}</span>
          </div>
        </div>
      </Card>

      {eventsQuery.isError ? <Alert tone="error">Unable to load economic calendar events.</Alert> : null}
      {createMutation.isError ? <Alert tone="error">Unable to create calendar event.</Alert> : null}
      {createMutation.isSuccess ? <Alert tone="success">Economic calendar event added.</Alert> : null}

      {eventsQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
      ) : (
        <CalendarSummaryCards events={events} />
      )}

      <CalendarFilters filters={filters} onChange={setFilters} onReset={() => setFilters(defaultFilters)} />
      <CalendarEventForm loading={createMutation.isPending} onSubmit={(event) => createMutation.mutate(event)} />
      <CalendarEventsTable events={events} loading={isLoading} />
    </div>
  );
}

function normalizeFilters(filters: CalendarFilterState): CalendarFilterState {
  return {
    country: filters.country?.trim() || undefined,
    impact_level: filters.impact_level || undefined,
    asset: filters.asset?.trim() || undefined,
    start: filters.start ? new Date(filters.start).toISOString() : undefined,
    end: filters.end ? new Date(filters.end).toISOString() : undefined
  };
}
