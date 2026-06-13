import type { LucideIcon } from "lucide-react";

import { Badge } from "../ui/Badge";
import { cn } from "../../utils/cn";

type NotificationToggleProps = {
  label: string;
  detail: string;
  checked: boolean;
  icon: LucideIcon;
  placeholder?: boolean;
  configured?: boolean;
  onChange: (checked: boolean) => void;
};

export function NotificationToggle({
  label,
  detail,
  checked,
  icon: Icon,
  placeholder = false,
  configured = true,
  onChange
}: NotificationToggleProps) {
  return (
    <label
      className={cn(
        "flex min-h-[104px] cursor-pointer items-center gap-4 rounded-[8px] border p-4 backdrop-blur-lg transition-colors",
        checked
          ? "border-cyan-300/40 bg-cyan-400/10"
          : "border-white/15 bg-white/5 hover:border-white/30 hover:bg-white/10"
      )}
    >
      <span
        className={cn(
          "grid size-11 shrink-0 place-items-center rounded-[8px]",
          checked ? "bg-cyan-400/20 text-cyan-700 dark:text-cyan-100" : "bg-white/10 text-slate-500 dark:text-white/50"
        )}
      >
        <Icon size={19} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-black text-slate-950 dark:text-white">{label}</span>
          {placeholder ? <Badge tone="warning">Placeholder</Badge> : null}
          {!configured ? <Badge tone="warning">Not configured</Badge> : null}
        </span>
        <span className="mt-1 block text-xs font-semibold leading-5 text-slate-500 dark:text-white/45">{detail}</span>
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="size-5 rounded border-white/30 bg-white/10 accent-cyan-500"
        aria-label={label}
      />
    </label>
  );
}
