import { motion } from "framer-motion";

import type { EconomicCalendarEvent } from "../../api/calendarApi";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { Skeleton } from "../ui/LoadingSpinner";
import { EmptyState } from "../table/EmptyState";
import { ImpactBadge } from "./CalendarBadges";

type CalendarEventsTableProps = {
  events: EconomicCalendarEvent[];
  loading?: boolean;
};

export function CalendarEventsTable({ events, loading = false }: CalendarEventsTableProps) {
  return (
    <Card className="p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-4">
        <div>
          <h3 className="text-base font-bold text-slate-950 dark:text-white">Calendar Events</h3>
          <p className="text-xs font-medium text-slate-500 dark:text-white/50">
            Economic releases, affected assets, value expectations, and trading warnings
          </p>
        </div>
        <span className="rounded-[8px] border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold text-slate-600 dark:text-white/60">
          {events.length} events
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1120px] border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 z-10 bg-white/30 backdrop-blur-xl dark:bg-slate-950/40">
            <tr>
              {["Event", "Country", "Impact", "Date/Time", "Affected Assets", "Trading Warning", "Previous", "Forecast", "Actual"].map((label) => (
                <th
                  key={label}
                  className="border-b border-white/10 px-4 py-3 text-left text-xs font-bold uppercase tracking-normal text-slate-500 dark:text-white/50"
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 5 }).map((_, index) => (
                  <tr key={index}>
                    <td colSpan={9} className="px-4 py-3">
                      <Skeleton className="h-11 w-full" />
                    </td>
                  </tr>
                ))
              : events.map((event) => (
                  <motion.tr
                    key={event.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="group transition-colors hover:bg-white/10 dark:hover:bg-white/5"
                  >
                    <td className="max-w-[240px] border-b border-white/10 px-4 py-4">
                      <p className="font-black text-slate-950 dark:text-white">{event.event_name}</p>
                      {event.high_impact ? <p className="mt-1 text-xs font-bold text-rose-600 dark:text-rose-200">High-impact event</p> : null}
                    </td>
                    <td className="border-b border-white/10 px-4 py-4 font-semibold text-slate-700 dark:text-white/75">{event.country}</td>
                    <td className="border-b border-white/10 px-4 py-4">
                      <ImpactBadge impact={event.impact_level} />
                    </td>
                    <td className="border-b border-white/10 px-4 py-4 text-xs font-semibold text-slate-500 dark:text-white/45">
                      {formatDate(event.event_datetime)}
                    </td>
                    <td className="border-b border-white/10 px-4 py-4">
                      <div className="flex max-w-[220px] flex-wrap gap-1.5">
                        {event.affected_assets.map((asset) => (
                          <Badge key={asset} tone="neutral">{asset}</Badge>
                        ))}
                      </div>
                    </td>
                    <td className="max-w-[260px] border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/75">
                      <span className="line-clamp-2 font-semibold">{event.trading_blackout_warning}</span>
                    </td>
                    <td className="border-b border-white/10 px-4 py-4 font-semibold text-slate-700 dark:text-white/75">{event.previous_value ?? "-"}</td>
                    <td className="border-b border-white/10 px-4 py-4 font-semibold text-slate-700 dark:text-white/75">{event.forecast_value ?? "-"}</td>
                    <td className="border-b border-white/10 px-4 py-4 font-semibold text-slate-700 dark:text-white/75">{event.actual_value ?? "Pending"}</td>
                  </motion.tr>
                ))}
          </tbody>
        </table>
      </div>

      {!loading && events.length === 0 ? (
        <EmptyState title="No calendar events" message="Adjust filters or add an economic event." />
      ) : null}
    </Card>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short"
  }).format(new Date(value));
}
