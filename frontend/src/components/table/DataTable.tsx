import { motion } from "framer-motion";
import { ChevronDown, Filter, SlidersHorizontal } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../utils/cn";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Skeleton } from "../ui/LoadingSpinner";
import { EmptyState } from "./EmptyState";
import { Pagination } from "./Pagination";

export type DataColumn<T> = {
  key: keyof T;
  label: string;
  align?: "left" | "right" | "center";
  render?: (row: T) => ReactNode;
};

type DataTableProps<T extends { id: string }> = {
  title?: string;
  description?: string;
  columns: Array<DataColumn<T>>;
  rows: T[];
  loading?: boolean;
  emptyTitle?: string;
  emptyMessage?: string;
};

export function DataTable<T extends { id: string }>({
  title = "Signal Book",
  description = "Sortable execution intelligence",
  columns,
  rows,
  loading = false,
  emptyTitle = "No rows found",
  emptyMessage = "Try adjusting filters or connect a signal source."
}: DataTableProps<T>) {
  return (
    <Card className="p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-4">
        <div>
          <h3 className="text-base font-bold text-slate-950 dark:text-white">{title}</h3>
          <p className="text-xs font-medium text-slate-500 dark:text-white/50">{description}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" icon={Filter} className="min-h-9 px-3">
            Filters
          </Button>
          <Button variant="secondary" icon={SlidersHorizontal} className="min-h-9 px-3">
            Bulk actions
          </Button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 z-10 bg-white/30 backdrop-blur-xl dark:bg-slate-950/40">
            <tr>
              <th className="w-12 border-b border-white/10 px-4 py-3 text-left">
                <input type="checkbox" aria-label="Select all rows" className="size-4 rounded border-white/30 bg-white/10 accent-cyan-500" />
              </th>
              {columns.map((column) => (
                <th
                  key={String(column.key)}
                  className={cn(
                    "border-b border-white/10 px-4 py-3 text-xs font-bold uppercase tracking-normal text-slate-500 dark:text-white/50",
                    column.align === "right" ? "text-right" : column.align === "center" ? "text-center" : "text-left"
                  )}
                >
                  <button type="button" className="inline-flex items-center gap-1">
                    {column.label}
                    <ChevronDown size={14} aria-hidden />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 4 }).map((_, index) => (
                  <tr key={index}>
                    <td colSpan={columns.length + 1} className="px-4 py-3">
                      <Skeleton className="h-11 w-full" />
                    </td>
                  </tr>
                ))
              : rows.map((row) => (
                  <motion.tr
                    key={row.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="group transition-colors hover:bg-white/10 dark:hover:bg-white/5"
                  >
                    <td className="border-b border-white/10 px-4 py-4">
                      <input type="checkbox" aria-label={`Select ${row.id}`} className="size-4 rounded border-white/30 bg-white/10 accent-cyan-500" />
                    </td>
                    {columns.map((column) => (
                      <td
                        key={String(column.key)}
                        className={cn(
                          "border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/75",
                          column.align === "right" ? "text-right" : column.align === "center" ? "text-center" : "text-left"
                        )}
                      >
                        {column.render ? column.render(row) : String(row[column.key])}
                      </td>
                    ))}
                  </motion.tr>
                ))}
          </tbody>
        </table>
      </div>
      {!loading && rows.length === 0 ? <EmptyState title={emptyTitle} message={emptyMessage} /> : null}
      <Pagination totalItems={rows.length} />
    </Card>
  );
}
