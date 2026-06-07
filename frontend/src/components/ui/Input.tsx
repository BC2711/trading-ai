import { Upload } from "lucide-react";
import type { InputHTMLAttributes } from "react";

import { cn } from "../../utils/cn";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
  wrapperClassName?: string;
};

export function Input({ label, error, wrapperClassName, className, ...props }: InputProps) {
  const input = (
    <input
      className={cn(
        "min-h-11 rounded-[8px] border border-white/20 bg-white/10 px-3 text-sm text-slate-900 outline-none shadow-lg shadow-slate-950/5 backdrop-blur-lg transition-all placeholder:text-slate-400 focus:border-cyan-300/60 focus:bg-white/15 focus:ring-2 focus:ring-cyan-300/20 dark:text-white dark:placeholder:text-white/35",
        error && "border-rose-300/60 focus:ring-rose-300/20",
        className
      )}
      {...props}
    />
  );

  if (!label) {
    return input;
  }

  return (
    <label className={cn("group grid gap-1.5", wrapperClassName)}>
      <span className="text-xs font-bold uppercase tracking-normal text-slate-500 transition-colors group-focus-within:text-cyan-600 dark:text-white/50 dark:group-focus-within:text-cyan-200">
        {label}
      </span>
      {input}
      {error ? <span className="text-xs font-semibold text-rose-600 dark:text-rose-200">{error}</span> : null}
    </label>
  );
}

export function ToggleSwitch({ label, checked }: { label: string; checked?: boolean }) {
  return (
    <label className="flex items-center justify-between gap-4 rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/5">
      <span className="text-sm font-semibold text-slate-700 dark:text-white/75">{label}</span>
      <input type="checkbox" defaultChecked={checked} className="peer sr-only" />
      <span className="relative h-6 w-11 rounded-full bg-slate-400/35 transition after:absolute after:left-1 after:top-1 after:size-4 after:rounded-full after:bg-white after:shadow after:transition-transform peer-checked:bg-cyan-500/80 peer-checked:after:translate-x-5" />
    </label>
  );
}

export function FileUpload({ label = "Upload strategy file" }: { label?: string }) {
  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-[8px] border border-dashed border-white/30 bg-white/10 p-4 text-sm font-semibold text-slate-600 backdrop-blur-lg transition hover:bg-white/15 dark:text-white/65">
      <Upload size={18} aria-hidden />
      <span>{label}</span>
      <input type="file" className="sr-only" />
    </label>
  );
}
