import type { SelectHTMLAttributes } from "react";

import { cn } from "../../utils/cn";

type SelectOption = {
  label: string;
  value: string;
};

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  options: Array<string | SelectOption>;
  wrapperClassName?: string;
};

export function Select({ label, options, wrapperClassName, className, ...props }: SelectProps) {
  const select = (
    <select
      className={cn(
        "min-h-11 rounded-[8px] border border-white/20 bg-white/10 px-3 text-sm text-slate-900 outline-none shadow-lg shadow-slate-950/5 backdrop-blur-lg transition-all focus:border-cyan-300/60 focus:ring-2 focus:ring-cyan-300/20 dark:text-white",
        className
      )}
      {...props}
    >
      {options.map((option) => {
        const item = typeof option === "string" ? { label: option, value: option } : option;
        return (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        );
      })}
    </select>
  );

  if (!label) {
    return select;
  }

  return (
    <label className={cn("group grid gap-1.5", wrapperClassName)}>
      <span className="text-xs font-bold uppercase tracking-normal text-slate-500 group-focus-within:text-cyan-600 dark:text-white/50">
        {label}
      </span>
      {select}
    </label>
  );
}
