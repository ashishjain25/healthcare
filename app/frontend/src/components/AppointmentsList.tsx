import { CalendarClock, Loader2, X } from "lucide-react";
import type { Appointment } from "../api/types";
import { Badge } from "./Badge";
import { EmptyState } from "./EmptyState";
import { SkeletonList } from "./Skeleton";
import { formatDate } from "../lib/format";

export function AppointmentsList({
  appointments,
  isLoading,
  emptyLabel = "No appointments suggested.",
  onCancel,
  cancellingId,
}: {
  appointments: Appointment[] | undefined;
  isLoading: boolean;
  emptyLabel?: string;
  /** When provided, shows a Cancel button on appointments that aren't already cancelled. */
  onCancel?: (id: number) => void;
  cancellingId?: number | null;
}) {
  if (isLoading) return <SkeletonList rows={2} />;
  if (!appointments || appointments.length === 0) {
    return <EmptyState icon={<CalendarClock className="h-5 w-5 text-slate-300" />}>{emptyLabel}</EmptyState>;
  }

  return (
    <div className="space-y-2">
      {appointments.map((a) => (
        <div key={a.id} className="rounded-lg border border-slate-200 px-3 py-2.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-slate-800">{a.suggested_reason}</span>
            <Badge value={a.status} />
          </div>
          <div className="mt-0.5 flex items-center justify-between gap-2">
            <p className="text-xs text-slate-400">
              {formatDate(a.proposed_datetime)}
              {a.doctor_name ? ` — ${a.doctor_name}` : ""}
            </p>
            {onCancel && a.status !== "cancelled" && (
              <button
                onClick={() => onCancel(a.id)}
                disabled={cancellingId === a.id}
                className="flex shrink-0 items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
              >
                {cancellingId === a.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <X className="h-3 w-3" />}
                Cancel
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
