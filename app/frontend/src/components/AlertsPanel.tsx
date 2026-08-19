import { AlertTriangle, Check, Loader2 } from "lucide-react";
import type { Alert } from "../api/types";
import { Badge } from "./Badge";
import { EmptyState } from "./EmptyState";
import { SkeletonList } from "./Skeleton";

export function AlertsPanel({
  alerts,
  isLoading,
  onAcknowledge,
  acknowledgingId,
  onSelectPatient,
  selectedPatientId,
}: {
  alerts: Alert[] | undefined;
  isLoading: boolean;
  onAcknowledge: (id: number) => void;
  acknowledgingId: number | null;
  onSelectPatient?: (patientId: number) => void;
  selectedPatientId?: number | null;
}) {
  if (isLoading) return <SkeletonList rows={2} />;
  if (!alerts || alerts.length === 0) {
    return <EmptyState icon={<AlertTriangle className="h-5 w-5 text-slate-300" />}>No open alerts.</EmptyState>;
  }

  return (
    <div className="space-y-2">
      {alerts.map((a) => (
        <div
          key={a.id}
          onClick={() => onSelectPatient?.(a.patient_id)}
          className={`rounded-lg border px-3 py-2.5 transition ${
            onSelectPatient ? "cursor-pointer hover:border-red-200" : ""
          } ${
            selectedPatientId === a.patient_id
              ? "border-red-300 bg-red-50 ring-1 ring-red-200"
              : "border-red-100 bg-red-50/60"
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-slate-800">{a.patient_name}</span>
            <Badge value={a.severity} />
          </div>
          <p className="mt-0.5 text-xs text-slate-600">{a.message}</p>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAcknowledge(a.id);
            }}
            disabled={acknowledgingId === a.id}
            className="mt-2 flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
          >
            {acknowledgingId === a.id ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Check className="h-3 w-3" />
            )}
            Acknowledge
          </button>
        </div>
      ))}
    </div>
  );
}
