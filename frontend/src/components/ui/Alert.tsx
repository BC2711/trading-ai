import { AlertTriangle, Check } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../utils/cn";

export function Alert({
  tone = "info",
  children
}: {
  tone?: "info" | "success" | "warning" | "error";
  children: ReactNode;
}) {
  const Icon = tone === "success" ? Check : AlertTriangle;

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-[8px] border p-3 text-sm font-semibold backdrop-blur-lg",
        tone === "info" && "border-cyan-300/30 bg-cyan-400/10 text-cyan-800 dark:text-cyan-100",
        tone === "success" && "border-emerald-300/30 bg-emerald-400/10 text-emerald-800 dark:text-emerald-100",
        tone === "warning" && "border-amber-300/30 bg-amber-400/10 text-amber-800 dark:text-amber-100",
        tone === "error" && "border-rose-300/30 bg-rose-400/10 text-rose-800 dark:text-rose-100"
      )}
    >
      <Icon size={16} aria-hidden />
      {children}
    </div>
  );
}
