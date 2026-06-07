import { Bell } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({
  title,
  message,
  action
}: {
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="grid place-items-center gap-3 px-6 py-10 text-center">
      <div className="grid size-14 place-items-center rounded-[8px] border border-white/20 bg-gradient-to-br from-cyan-400/20 to-violet-400/20 text-cyan-700 shadow-xl shadow-cyan-500/10 backdrop-blur-lg dark:text-cyan-100">
        <Bell size={22} aria-hidden />
      </div>
      <div>
        <h3 className="text-base font-bold text-slate-900 dark:text-white">{title}</h3>
        <p className="mt-1 max-w-md text-sm text-slate-500 dark:text-white/55">{message}</p>
      </div>
      {action}
    </div>
  );
}
