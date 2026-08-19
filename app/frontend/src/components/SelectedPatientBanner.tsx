import { UserRound } from "lucide-react";
import type { Patient } from "../api/types";

export function SelectedPatientBanner({ patient }: { patient: Patient | undefined | null }) {
  if (!patient) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-400">
        <UserRound className="h-5 w-5 shrink-0" />
        No patient selected — choose one from Appointments or All patients on the left.
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 rounded-xl border border-brand-200 bg-brand-50 px-4 py-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white">
        <UserRound className="h-4 w-4" />
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-900">{patient.full_name}</p>
        <p className="text-xs text-slate-500">
          MRN {patient.mrn}
          {patient.sex ? ` · ${patient.sex}` : ""}
          {patient.dob ? ` · DOB ${patient.dob}` : ""}
        </p>
      </div>
    </div>
  );
}
