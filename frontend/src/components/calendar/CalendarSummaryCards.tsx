import { CalendarClock, Globe2, ShieldAlert, TimerOff } from "lucide-react";

import type { EconomicCalendarEvent } from "../../api/calendarApi";
import { cn } from "../../utils/cn";
import { Card } from "../ui/Card";

type CalendarSummaryCardsProps = {
  events: EconomicCalendarEvent[];
};

export function CalendarSummaryCards({ events }: CalendarSummaryCardsProps) {
  const highImpact = events.filter((event) => event.high_impact).length;
  const blackoutWarnings = events.filter((event) => event.trading_blackout_warning.toLowerCase().includes("blackout")).length;
  const countries = new Set(events.map((event) => event.country)).size;

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <SummaryCard label="Upcoming Events" value={String(events.length)} detail="Filtered calendar releases" icon={CalendarClock} tone="cyan" />
      <SummaryCard label="High Impact" value={String(highImpact)} detail="Major volatility windows" icon={ShieldAlert} tone={highImpact ? "rose" : "emerald"} />
      <SummaryCard label="Blackouts" value={String(blackoutWarnings)} detail="Trade caution warnings" icon={TimerOff} tone={blackoutWarnings ? "amber" : "emerald"} />
      <SummaryCard label="Countries" value={String(countries)} detail="Regions represented" icon={Globe2} tone="violet" />
    </section>
  );
}

function SummaryCard({
  label,
  value,
  detail,
  icon: Icon,
  tone
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof CalendarClock;
  tone: "cyan" | "emerald" | "amber" | "rose" | "violet";
}) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-bold text-slate-500 dark:text-white/50">{label}</p>
          <p className="mt-3 truncate text-2xl font-black text-slate-950 dark:text-white">{value}</p>
          <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-white/40">{detail}</p>
        </div>
        <span
          className={cn(
            "grid size-11 shrink-0 place-items-center rounded-[8px]",
            tone === "cyan" && "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100",
            tone === "emerald" && "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100",
            tone === "amber" && "bg-amber-400/15 text-amber-700 dark:text-amber-100",
            tone === "rose" && "bg-rose-400/15 text-rose-700 dark:text-rose-100",
            tone === "violet" && "bg-violet-400/15 text-violet-700 dark:text-violet-100"
          )}
        >
          <Icon size={20} aria-hidden />
        </span>
      </div>
    </Card>
  );
}
