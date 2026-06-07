import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { cn } from "../../utils/cn";

export type StatCardTone = "cyan" | "emerald" | "violet" | "amber" | "rose";
export type StatTrendDirection = "up" | "down" | "flat";

export type StatCardProps = {
  label: string;
  value: string;
  trend: string;
  tone?: StatCardTone;
  trendDirection?: StatTrendDirection;
  icon?: LucideIcon;
  sparkline?: number[];
};

const toneClasses = {
  cyan: "from-cyan-400/80 to-blue-500/80 shadow-cyan-500/20",
  emerald: "from-emerald-400/80 to-teal-500/80 shadow-emerald-500/20",
  violet: "from-violet-400/80 to-fuchsia-500/80 shadow-violet-500/20",
  amber: "from-amber-300/90 to-orange-500/80 shadow-amber-500/20",
  rose: "from-rose-400/80 to-pink-500/80 shadow-rose-500/20"
};

const trendTone = {
  up: "text-emerald-700 bg-emerald-400/15 dark:text-emerald-100",
  down: "text-rose-700 bg-rose-400/15 dark:text-rose-100",
  flat: "text-cyan-700 bg-cyan-400/15 dark:text-cyan-100"
};

export function StatCard({
  label,
  value,
  trend,
  tone = "cyan",
  trendDirection = "flat",
  icon: Icon,
  sparkline = [16, 24, 19, 34, 31, 44, 38]
}: StatCardProps) {
  const TrendIcon = trendDirection === "up" ? ArrowUpRight : trendDirection === "down" ? ArrowDownRight : Minus;
  const max = Math.max(...sparkline);

  return (
    <motion.article
      className="group relative min-h-[168px] overflow-hidden rounded-[8px] border border-white/20 bg-white/10 p-5 shadow-2xl shadow-slate-950/10 backdrop-blur-xl transition-colors duration-300 hover:bg-white/15 dark:border-white/10 dark:bg-white/5 dark:shadow-black/30"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/25 via-white/5 to-transparent opacity-70 dark:from-white/10" />
      <div className="relative z-10 flex h-full flex-col justify-between gap-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold text-slate-500 dark:text-white/55">{label}</p>
            <motion.strong
              className="mt-3 block text-3xl font-black tracking-normal text-slate-950 dark:text-white"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              {value}
            </motion.strong>
          </div>
          {Icon ? (
            <div className={cn("grid size-12 shrink-0 place-items-center rounded-[8px] bg-gradient-to-br text-white shadow-xl", toneClasses[tone])}>
              <Icon size={22} aria-hidden />
            </div>
          ) : null}
        </div>

        <div className="flex items-end justify-between gap-3">
          <span className={cn("inline-flex items-center gap-1 rounded-[8px] px-2.5 py-1.5 text-xs font-bold backdrop-blur-md", trendTone[trendDirection])}>
            <TrendIcon size={14} aria-hidden />
            {trend}
          </span>
          <div className="flex h-10 w-24 items-end gap-1" aria-hidden>
            {sparkline.map((point, index) => (
              <span
                key={`${point}-${index}`}
                className={cn(
                  "w-full rounded-t bg-gradient-to-t opacity-80 transition-all duration-300 group-hover:opacity-100",
                  tone === "cyan" && "from-cyan-500/40 to-cyan-300/90",
                  tone === "emerald" && "from-emerald-500/40 to-emerald-300/90",
                  tone === "violet" && "from-violet-500/40 to-violet-300/90",
                  tone === "amber" && "from-amber-500/40 to-amber-300/90",
                  tone === "rose" && "from-rose-500/40 to-rose-300/90"
                )}
                style={{ height: `${Math.max(18, (point / max) * 100)}%` }}
              />
            ))}
          </div>
        </div>
      </div>
    </motion.article>
  );
}
