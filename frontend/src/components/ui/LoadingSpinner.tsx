import { Loader2 } from "lucide-react";

import { cn } from "../../utils/cn";

export function LoadingSpinner({ className = "" }: { className?: string }) {
  return <Loader2 className={cn("animate-spin text-cyan-500", className)} aria-hidden />;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-[8px] border border-white/10 bg-gradient-to-r from-white/5 via-white/20 to-white/5 backdrop-blur-md",
        className
      )}
    />
  );
}
