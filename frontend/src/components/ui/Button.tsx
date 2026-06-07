import { motion } from "framer-motion";
import type { HTMLMotionProps } from "framer-motion";
import { Loader2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../utils/cn";

const buttonStyles = {
  primary:
    "border-white/20 bg-gradient-to-r from-cyan-400/80 via-blue-500/80 to-violet-500/80 text-white shadow-xl shadow-blue-500/20 hover:shadow-blue-500/30",
  secondary:
    "border-white/20 bg-white/15 text-slate-900 shadow-xl shadow-slate-950/5 hover:bg-white/25 dark:text-white dark:shadow-black/20",
  outline: "border-white/30 bg-white/5 text-slate-800 hover:bg-white/15 dark:text-white",
  ghost:
    "border-transparent bg-transparent text-slate-600 hover:border-white/20 hover:bg-white/10 dark:text-white/70 dark:hover:text-white",
  danger: "border-rose-300/30 bg-rose-500/15 text-rose-800 hover:bg-rose-500/25 dark:text-rose-100",
  success:
    "border-emerald-300/30 bg-emerald-500/15 text-emerald-800 hover:bg-emerald-500/25 dark:text-emerald-100"
};

export type ButtonVariant = keyof typeof buttonStyles;

type ButtonProps = Omit<HTMLMotionProps<"button">, "children"> & {
  children: ReactNode;
  variant?: ButtonVariant;
  icon?: LucideIcon;
  loading?: boolean;
};

export function Button({
  children,
  variant = "primary",
  icon: Icon,
  loading = false,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <motion.button
      type="button"
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      whileHover={disabled ? undefined : { y: -1 }}
      className={cn(
        "group relative inline-flex min-h-10 items-center justify-center gap-2 overflow-hidden rounded-[8px] border px-4 py-2 text-sm font-semibold outline-none backdrop-blur-lg transition-all duration-300 focus-visible:ring-2 focus-visible:ring-cyan-300/70 disabled:pointer-events-none disabled:opacity-50",
        buttonStyles[variant],
        className
      )}
      disabled={disabled}
      {...props}
    >
      <span className="absolute inset-0 translate-x-[-110%] bg-white/20 transition-transform duration-700 group-hover:translate-x-[110%]" />
      {loading ? <Loader2 size={16} className="relative animate-spin" aria-hidden /> : null}
      {!loading && Icon ? <Icon size={16} className="relative" aria-hidden /> : null}
      <span className="relative">{children}</span>
    </motion.button>
  );
}

type IconButtonProps = HTMLMotionProps<"button"> & {
  label: string;
  icon: LucideIcon;
  active?: boolean;
};

export function IconButton({ label, icon: Icon, active = false, className, ...props }: IconButtonProps) {
  return (
    <motion.button
      type="button"
      title={label}
      aria-label={label}
      whileTap={{ scale: 0.95 }}
      whileHover={{ y: -1 }}
      className={cn(
        "grid size-10 place-items-center rounded-[8px] border border-white/20 bg-white/10 text-slate-700 shadow-lg shadow-slate-950/5 backdrop-blur-lg transition-all duration-300 hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/70 dark:text-white/80 dark:shadow-black/20",
        active && "border-cyan-300/50 bg-cyan-400/20 text-cyan-700 dark:text-cyan-100",
        className
      )}
      {...props}
    >
      <Icon size={18} aria-hidden />
    </motion.button>
  );
}
