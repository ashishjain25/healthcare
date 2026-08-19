import { UserCheck } from "lucide-react";
import type { DoctorReview } from "../api/types";
import { Badge } from "./Badge";
import { formatDate } from "../lib/format";

export function ReviewHistory({ reviews, title = "Doctor review" }: { reviews: DoctorReview[] | undefined; title?: string }) {
  if (!reviews?.length) return null;

  return (
    <div>
      <h5 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{title}</h5>
      <div className="space-y-2">
        {reviews.map((r) => (
          <div key={r.id} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 text-xs font-medium text-slate-700">
                <UserCheck className="h-3.5 w-3.5 text-teal-600" />
                {r.doctor_name ?? "Doctor"}
              </span>
              <div className="flex items-center gap-2">
                <Badge value={r.action} />
                <span className="text-[11px] text-slate-400">{formatDate(r.created_at)}</span>
              </div>
            </div>
            {r.comments && <p className="mt-1 text-sm text-slate-600">{r.comments}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
