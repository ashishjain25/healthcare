import { useEffect, useMemo, useState } from "react";
import { CalendarClock } from "lucide-react";
import type { Appointment } from "../api/types";
import { Badge } from "./Badge";
import { EmptyState } from "./EmptyState";
import { SkeletonList } from "./Skeleton";
import { Pagination } from "./Pagination";
import { formatDate } from "../lib/format";

export function DoctorAppointmentsPanel({
  appointments,
  isLoading,
  onSelectPatient,
  pageSize,
}: {
  appointments: Appointment[] | undefined;
  isLoading: boolean;
  onSelectPatient: (patientId: number) => void;
  /** When set, paginates the list client-side at this many appointments per page. */
  pageSize?: number;
}) {
  // Deliberately separate from the dashboard's selectedPatientId: a patient
  // can have several appointments, and highlighting by patient would light
  // up every row of theirs when only one was actually clicked.
  const [selectedAppointmentId, setSelectedAppointmentId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const upcoming = useMemo(() => {
    const now = Date.now();
    return (appointments ?? []).filter(
      (a) => new Date(a.proposed_datetime.replace(" ", "T")).getTime() >= now,
    );
  }, [appointments]);

  useEffect(() => {
    setPage(1);
  }, [upcoming.length, pageSize]);

  if (isLoading) return <SkeletonList rows={2} />;
  if (!upcoming.length) {
    return (
      <EmptyState icon={<CalendarClock className="h-5 w-5 text-slate-300" />}>
        No upcoming appointments.
      </EmptyState>
    );
  }

  const totalPages = pageSize ? Math.max(1, Math.ceil(upcoming.length / pageSize)) : 1;
  const currentPage = Math.min(page, totalPages);
  const pageAppointments = pageSize
    ? upcoming.slice((currentPage - 1) * pageSize, currentPage * pageSize)
    : upcoming;

  return (
    <div className="space-y-2">
      {pageAppointments.map((a) => (
        <button
          key={a.id}
          onClick={() => {
            setSelectedAppointmentId(a.id);
            onSelectPatient(a.patient_id);
          }}
          className={`w-full rounded-lg border px-3 py-2.5 text-left transition ${
            selectedAppointmentId === a.id
              ? "border-brand-400 bg-brand-50 ring-1 ring-brand-200"
              : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-slate-800">
              {a.patient_name} {a.mrn ? <span className="font-normal text-slate-400">({a.mrn})</span> : null}
            </span>
            <Badge value={a.status} />
          </div>
          <div className="mt-0.5 flex items-center justify-between gap-2">
            <span className="truncate text-xs text-slate-500">{a.suggested_reason}</span>
            <span className="shrink-0 text-xs text-slate-400">{formatDate(a.proposed_datetime)}</span>
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
