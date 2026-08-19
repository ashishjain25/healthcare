import { ChevronLeft, ChevronRight } from "lucide-react";

export function Pagination({
  page,
  totalPages,
  onPrev,
  onNext,
}: {
  page: number;
  totalPages: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between pt-1">
      <button
        onClick={onPrev}
        disabled={page === 1}
        className="flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <ChevronLeft className="h-3.5 w-3.5" />
        Prev
      </button>
      <span className="text-xs text-slate-400">
        Page {page} of {totalPages}
      </span>
      <button
        onClick={onNext}
        disabled={page === totalPages}
        className="flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Next
        <ChevronRight className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
