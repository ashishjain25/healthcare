import { useState } from "react";
import { CalendarClock, Users } from "lucide-react";
import type { Appointment, Patient } from "../api/types";
import { PatientsList } from "./PatientsList";
import { DoctorAppointmentsPanel } from "./DoctorAppointmentsPanel";

type Tab = "appointments" | "patients";

export function PatientSelector({
  patients,
  patientsLoading,
  appointments,
  appointmentsLoading,
  selectedPatientId,
  onSelectPatient,
}: {
  patients: Patient[] | undefined;
  patientsLoading: boolean;
  appointments: Appointment[] | undefined;
  appointmentsLoading: boolean;
  selectedPatientId: number | null;
  onSelectPatient: (patientId: number) => void;
}) {
  const [tab, setTab] = useState<Tab>("appointments");

  return (
    <div>
      <div className="mb-3 flex gap-1 rounded-lg bg-slate-100 p-1">
        <button
          onClick={() => setTab("appointments")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium transition ${
            tab === "appointments" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
          }`}
        >
          <CalendarClock className="h-3.5 w-3.5" />
          Appointments
        </button>
        <button
          onClick={() => setTab("patients")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium transition ${
            tab === "patients" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
          }`}
        >
          <Users className="h-3.5 w-3.5" />
          All patients
        </button>
      </div>

      {tab === "appointments" ? (
        <DoctorAppointmentsPanel
          appointments={appointments}
          isLoading={appointmentsLoading}
          onSelectPatient={onSelectPatient}
          pageSize={5}
        />
      ) : (
        <PatientsList
          patients={patients}
          selectedId={selectedPatientId}
          onSelect={onSelectPatient}
          isLoading={patientsLoading}
        />
      )}
    </div>
  );
}
