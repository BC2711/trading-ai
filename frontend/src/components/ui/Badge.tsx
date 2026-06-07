import type { ComponentPropsWithoutRef, ReactNode } from "react";

import { cn } from "../../utils/cn";

const badgeStyles = {
  info: "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100",
  success: "bg-emerald-400/15 text-emerald-700 dark:text-emerald-100",
  warning: "bg-amber-400/15 text-amber-700 dark:text-amber-100",
  error: "bg-rose-400/15 text-rose-700 dark:text-rose-100",
  violet: "bg-violet-400/15 text-violet-700 dark:text-violet-100",
  neutral: "bg-white/10 text-slate-600 dark:text-white/70"
};

export type BadgeTone = keyof typeof badgeStyles;

type BadgeProps = ComponentPropsWithoutRef<"span"> & {
  children: ReactNode;
  tone?: BadgeTone;
};

export function Badge({ children, tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-[8px] px-2.5 py-1 text-xs font-bold", badgeStyles[tone], className)} {...props}>
      {children}
    </span>
  );
}
