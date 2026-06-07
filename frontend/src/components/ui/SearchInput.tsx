import { Search } from "lucide-react";
import type { InputHTMLAttributes } from "react";

import { cn } from "../../utils/cn";

type SearchInputProps = InputHTMLAttributes<HTMLInputElement> & {
  wrapperClassName?: string;
  shortcut?: string;
};

export function SearchInput({ wrapperClassName, className, shortcut = "/", ...props }: SearchInputProps) {
  return (
    <label
      className={cn(
        "group flex min-h-11 items-center gap-3 rounded-[8px] border border-white/20 bg-white/10 px-3 text-sm text-slate-500 shadow-xl shadow-slate-950/5 backdrop-blur-lg transition-all duration-300 focus-within:border-cyan-300/60 focus-within:bg-white/15 focus-within:ring-2 focus-within:ring-cyan-300/20 dark:text-white/50 dark:shadow-black/20",
        wrapperClassName
      )}
    >
      <Search size={17} className="text-slate-400 dark:text-white/40" aria-hidden />
      <input
        className={cn("w-full bg-transparent text-slate-900 outline-none placeholder:text-slate-400 dark:text-white dark:placeholder:text-white/40", className)}
        aria-label="Search"
        {...props}
      />
      {shortcut ? (
        <span className="hidden rounded border border-white/20 bg-white/10 px-1.5 py-0.5 text-[11px] font-semibold text-slate-400 sm:inline dark:text-white/40">
          {shortcut}
        </span>
      ) : null}
    </label>
  );
}
