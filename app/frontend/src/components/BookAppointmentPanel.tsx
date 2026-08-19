import { useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { CalendarPlus, ChevronDown, Loader2 } from "lucide-react";
import {
  useAppointmentAvailability,
  useBookAppointment,
  useCancelAppointment,
  usePatientAppointments,
  usePatientDoctors,
} from "../api/hooks";
import type { ApiError } from "../api/client";
import { AppointmentsList } from "./AppointmentsList";
import { formatTime12h, todayIsoDate } from "../lib/format";

export function BookAppointmentPanel() {
  const doctorsQuery = usePatientDoctors();
  const appointmentsQuery = usePatientAppointments();
  const bookMutation = useBookAppointment();
  const cancelMutation = useCancelAppointment();

  const [showHistory, setShowHistory] = useState(false);
  const [doctorId, setDoctorId] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [reason, setReason] = useState("");
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  const availabilityQuery = useAppointmentAvailability(doctorId ? Number(doctorId) : null, date || null);

  const { upcoming, past } = useMemo(() => {
    const all = appointmentsQuery.data ?? [];
    const now = Date.now();
    const upcoming = all.filter((a) => new Date(a.proposed_datetime.replace(" ", "T")).getTime() >= now);
    const past = all.filter((a) => new Date(a.proposed_datetime.replace(" ", "T")).getTime() < now);
    return { upcoming, past };
  }, [appointmentsQuery.data]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!doctorId || !date || !time) return;
    bookMutation.mutate(
      { doctor_user_id: Number(doctorId), date, time, reason: reason.trim() || undefined },
      {
        onSuccess: () => {
          toast.success("Appointment booked.");
          setTime("");
          setReason("");
        },
        onError: (err) => toast.error((err as ApiError).message || "Could not book appointment"),
      },
    );
  }

  function handleCancel(appointmentId: number) {
    setCancellingId(appointmentId);
    cancelMutation.mutate(appointmentId, {
      onSuccess: () => toast.success("Appointment cancelled."),
      onError: (err) => toast.error((err as ApiError).message || "Could not cancel appointment"),
      onSettled: () => setCancellingId(null),
    });
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Doctor</label>
          <select
            required
            value={doctorId}
            onChange={(e) => {
              setDoctorId(e.target.value);
              setTime("");
            }}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          >
            <option value="" disabled>
              {doctorsQuery.data === undefined ? "Loading…" : "Select…"}
            </option>
            {doctorsQuery.data?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.full_name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Date</label>
          <input
            required
            type="date"
            min={todayIsoDate()}
            value={date}
            onChange={(e) => {
              setDate(e.target.value);
              setTime("");
            }}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Time slot <span className="font-normal text-slate-400">(15 min · 10 AM–1 PM &amp; 4–7 PM)</span>
          </label>
          <select
            required
            disabled={!doctorId || !date}
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400"
          >
            <option value="" disabled>
              {!doctorId || !date
                ? "Choose a doctor and date first"
                : availabilityQuery.isFetching
                  ? "Loading…"
                  : availabilityQuery.data?.available_times.length
                    ? "Select…"
                    : "No slots available"}
            </option>
            {availabilityQuery.data?.available_times.map((t) => (
              <option key={t} value={t}>
                {formatTime12h(t)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Reason (optional)</label>
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Follow-up on recent report"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>

        <button
          type="submit"
          disabled={bookMutation.isPending || !doctorId || !date || !time}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {bookMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarPlus className="h-4 w-4" />}
          {bookMutation.isPending ? "Booking…" : "Book appointment"}
        </button>
      </form>

      <div>
        <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Upcoming</h4>
        <AppointmentsList
          appointments={upcoming}
          isLoading={appointmentsQuery.isLoading}
          emptyLabel="No upcoming appointments."
          onCancel={handleCancel}
          cancellingId={cancellingId}
        />
      </div>

      <div>
        <button
          onClick={() => setShowHistory((s) => !s)}
          className="flex w-full items-center justify-between text-xs font-semibold uppercase tracking-wide text-slate-500"
        >
          Past appointments
          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${showHistory ? "rotate-180" : ""}`} />
        </button>
        {showHistory && (
          <div className="mt-1.5">
            <AppointmentsList
              appointments={past}
              isLoading={appointmentsQuery.isLoading}
              emptyLabel="No past appointments."
            />
          </div>
        )}
      </div>
    </div>
  );
}
