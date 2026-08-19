import { AlertTriangle, ClipboardList, FileText, Loader2 } from "lucide-react";
import type { PatientReportDetail as PatientReportDetailType } from "../api/types";
import { Badge } from "./Badge";
import { formatDate } from "../lib/format";
import { EmptyState } from "./EmptyState";
import { ReviewHistory } from "./ReviewHistory";

export function PatientReportDetail({
  detail,
  isLoading,
}: {
  detail: PatientReportDetailType | undefined;
  isLoading: boolean;
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
      <EmptyState icon={<FileText className="h-5 w-5 text-slate-300" />}>
        Select a report to view AI insights.
      </EmptyState>
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

      {!detail.insight ? (
        <EmptyState icon={<ClipboardList className="h-5 w-5 text-slate-300" />}>
          AI analysis is still processing. Check back shortly.
        </EmptyState>
      ) : (
        <>
          <div className="flex gap-2">
            <Badge value={detail.insight.risk_level ?? "routine"} />
            <Badge value={detail.insight.status} />
          </div>

          <div>
            <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Key findings</h4>
            {detail.insight.key_findings?.length ? (
              <ul className="space-y-1">
                {detail.insight.key_findings.map((f, i) => (
                  <li key={i} className="rounded-md bg-slate-50 px-3 py-1.5 text-sm text-slate-700">
                    {f}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-400">None</p>
            )}
          </div>

          {detail.patient_summary ? (
            <div className="space-y-3 rounded-lg border border-teal-100 bg-teal-50/50 p-3">
              <div>
                <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-700">What this means</h4>
                <p className="text-sm text-slate-700">{detail.patient_summary.plain_language_summary}</p>
                {detail.patient_summary.what_this_means?.map((f, i) => (
                  <p key={i} className="mt-1 text-sm text-slate-600">
                    {f}
                  </p>
                ))}
              </div>
              <div>
                <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-700">What you should do</h4>
                <ul className="space-y-1">
                  {detail.patient_summary.what_you_should_do?.map((f, i) => (
                    <li key={i} className="text-sm text-slate-700">
                      • {f}
                    </li>
                  ))}
                </ul>
              </div>
              <p className="border-t border-teal-100 pt-2 text-xs italic text-slate-500">
                {detail.patient_summary.disclaimer}
              </p>
            </div>
          ) : detail.patient_summary_pending_review ? (
            <div className="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>Your doctor is reviewing this result. The plain-language explanation will appear here once reviewed.</span>
            </div>
          ) : null}

          <ReviewHistory reviews={detail.doctor_reviews} />
        </>
      )}
    </div>
  );
}
