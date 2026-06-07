import type { TextareaHTMLAttributes } from "react";

import { cn } from "../../utils/cn";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  wrapperClassName?: string;
};

export function Textarea({ label, wrapperClassName, className, ...props }: TextareaProps) {
  const textarea = (
    <textarea
      className={cn(
        "min-h-24 resize-y rounded-[8px] border border-white/20 bg-white/10 px-3 py-2 text-sm text-slate-900 outline-none shadow-lg shadow-slate-950/5 backdrop-blur-lg transition-all placeholder:text-slate-400 focus:border-cyan-300/60 focus:bg-white/15 focus:ring-2 focus:ring-cyan-300/20 dark:text-white dark:placeholder:text-white/35",
        className
      )}
      {...props}
    />
  );

  if (!label) {
    return textarea;
  }

  return (
    <label className={cn("group grid gap-1.5", wrapperClassName)}>
      <span className="text-xs font-bold uppercase tracking-normal text-slate-500 group-focus-within:text-cyan-600 dark:text-white/50 dark:group-focus-within:text-cyan-200">
        {label}
      </span>
      {textarea}
    </label>
  );
}
