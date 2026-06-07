import { motion } from "framer-motion";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import { cn } from "../../utils/cn";

type CardProps = ComponentPropsWithoutRef<typeof motion.section> & {
  children: ReactNode;
  interactive?: boolean;
};

export function Card({ children, className, interactive = false, ...props }: CardProps) {
  return (
    <motion.section
      className={cn(
        "relative overflow-hidden rounded-[8px] border border-white/20 bg-white/10 shadow-2xl shadow-slate-950/10 backdrop-blur-xl backdrop-saturate-150 dark:border-white/10 dark:bg-white/5 dark:shadow-black/30",
        interactive && "transition-colors duration-300 hover:border-white/30 hover:bg-white/15 dark:hover:bg-white/10",
        className
      )}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.42, ease: "easeOut" }}
      {...props}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_10%,rgba(255,255,255,0.34),transparent_28%),linear-gradient(135deg,rgba(255,255,255,0.18),transparent_38%)] dark:bg-[radial-gradient(circle_at_12%_10%,rgba(255,255,255,0.12),transparent_30%),linear-gradient(135deg,rgba(255,255,255,0.08),transparent_42%)]" />
      <div className="relative z-10">{children}</div>
    </motion.section>
  );
}
