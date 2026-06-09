import { ChevronLeft, ChevronRight } from "lucide-react";

import { IconButton } from "../ui/Button";

type PaginationProps = {
  page?: number;
  totalPages?: number;
  totalItems?: number;
  startItem?: number;
  endItem?: number;
  onPrevious?: () => void;
  onNext?: () => void;
};

export function Pagination({
  page = 1,
  totalPages = 1,
  totalItems = 0,
  startItem = totalItems > 0 ? 1 : 0,
  endItem = totalItems,
  onPrevious,
  onNext
}: PaginationProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm text-slate-500 dark:text-white/50">
      <span>
        Showing {startItem}-{endItem} of {totalItems} rows
      </span>
      <div className="flex items-center gap-2">
        <IconButton label="Previous page" icon={ChevronLeft} onClick={onPrevious} disabled={page <= 1} />
        <span className="rounded-[8px] border border-white/20 bg-white/10 px-3 py-2 font-bold text-slate-700 backdrop-blur-md dark:text-white">
          {page} / {totalPages}
        </span>
        <IconButton label="Next page" icon={ChevronRight} onClick={onNext} disabled={page >= totalPages} />
      </div>
    </div>
  );
}
