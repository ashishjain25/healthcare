import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import type { Report } from "../api/types";
import { Badge } from "./Badge";
import { EmptyState } from "./EmptyState";
import { SkeletonList } from "./Skeleton";
import { Pagination } from "./Pagination";
import { formatDate } from "../lib/format";

export function ReportList({
  reports,
  selectedId,
  onSelect,
  isLoading,
  showPatientName,
  emptyLabel = "No reports yet.",
  pageSize,
}: {
  reports: Report[] | undefined;
  selectedId: number | null;
  onSelect: (id: number) => void;
  isLoading?: boolean;
  showPatientName?: boolean;
  emptyLabel?: string;
  /** When set, paginates the list client-side at this many reports per page. */
  pageSize?: number;
}) {
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [reports, pageSize]);

  if (isLoading) return <SkeletonList rows={3} />;
  if (!reports || reports.length === 0) {
    return (
      <EmptyState icon={<FileText className="h-5 w-5 text-slate-300" />}>{emptyLabel}</EmptyState>
    );
  }

  const totalPages = pageSize ? Math.max(1, Math.ceil(reports.length / pageSize)) : 1;
  const currentPage = Math.min(page, totalPages);
  const pageReports = pageSize
    ? reports.slice((currentPage - 1) * pageSize, currentPage * pageSize)
    : reports;

  return (
    <div className="space-y-2">
      {pageReports.map((r) => (
        <button
          key={r.id}
          onClick={() => onSelect(r.id)}
          className={`w-full rounded-lg border px-3 py-2.5 text-left transition ${
            selectedId === r.id
              ? "border-brand-400 bg-brand-50 ring-1 ring-brand-200"
              : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-slate-800">
              {showPatientName && r.patient_name ? `${r.patient_name} — ` : ""}
              {r.category} <span className="font-normal text-slate-400">({r.report_type.replace(/_/g, " ")})</span>
            </span>
          </div>
          <div className="mt-1 flex items-center justify-between">
            <span className="text-xs text-slate-400">{formatDate(r.uploaded_at)}</span>
            <Badge value={r.status} />
          </div>
        </button>
      ))}

      {pageSize && (
        <Pagination
          page={currentPage}
          totalPages={totalPages}
          onPrev={() => setPage((p) => Math.max(1, p - 1))}
          onNext={() => setPage((p) => Math.min(totalPages, p + 1))}
        />
      )}
    </div>
  );
}
