import { AlertOctagon, AlertTriangle, FileText, Loader2, Sparkles } from "lucide-react";
import type { DoctorReportDetail as DoctorReportDetailType } from "../api/types";
import { Badge } from "./Badge";
import { EmptyState } from "./EmptyState";
import { AgentAuditTrail } from "./AgentAuditTrail";
import { ReviewForm } from "./ReviewForm";
import { ReviewHistory } from "./ReviewHistory";
import { formatDate } from "../lib/format";

export function DoctorReportDetail({
  detail,
  isLoading,
  onReview,
  isReviewPending,
}: {
  detail: DoctorReportDetailType | undefined;
  isLoading: boolean;
  onReview: (payload: { action: "validated" | "modified" | "finalized"; comments: string }) => void;
  isReviewPending: boolean;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-10 text-slate-300">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }
  if (!detail) {
    return (
      <EmptyState icon={<FileText className="h-5 w-5 text-slate-300" />}>Select a report to review.</EmptyState>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold text-slate-800">{detail.category}</h3>
          <Badge value={detail.status} />
        </div>
        <p className="text-xs text-slate-400">Uploaded {formatDate(detail.uploaded_at)}</p>
      </div>

      <div>
        <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Extracted parameters</h4>
        {detail.extractions.length ? (
          <ul className="space-y-1">
            {detail.extractions.map((e) => (
              <li key={e.id} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-1.5 text-sm">
                <span className="text-slate-700">
                  {e.parameter_name}: {e.value} {e.unit}
                </span>
                <Badge value={e.status} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-400">None extracted</p>
        )}
      </div>

      <div>
        <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">AI audit trail</h4>
        <AgentAuditTrail outputs={detail.agent_outputs} />
      </div>

      {!detail.insight ? (
        <EmptyState icon={<FileText className="h-5 w-5 text-slate-300" />}>No AI insight yet.</EmptyState>
      ) : (
        <>
          {detail.insight.clinical_inconsistency && (
            <div className="flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0" />
              <span>Clinical Inconsistency flagged — findings conflict with reported symptoms.</span>
            </div>
          )}
          {detail.insight.requires_review && (
            <div className="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>Review Required before this insight can reach the patient.</span>
            </div>
          )}

          <div className="space-y-3 rounded-xl border-2 border-indigo-200 bg-indigo-50/50 p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <h4 className="text-sm font-semibold text-indigo-900">AI Insight</h4>
              <Badge value={detail.insight.risk_level ?? "routine"} />
              <Badge value={detail.insight.status} />
            </div>

            <div>
              <h5 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-500">Key findings</h5>
              <ul className="space-y-1">
                {(detail.insight.key_findings ?? []).map((f, i) => (
                  <li
                    key={i}
                    className="rounded-md border border-indigo-100 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm"
                  >
                    {f}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h5 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-500">
                Recommendations
              </h5>
              <ul className="space-y-1">
                {(detail.insight.recommendations ?? []).map((f, i) => (
                  <li
                    key={i}
                    className="rounded-md border border-indigo-100 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm"
                  >
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <ReviewHistory reviews={detail.doctor_reviews} title="Review history" />

          <ReviewForm onSubmit={onReview} isPending={isReviewPending} />
        </>
      )}
    </div>
  );
}
