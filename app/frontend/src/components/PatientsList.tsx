import { Users } from "lucide-react";
import type { Patient } from "../api/types";
import { EmptyState } from "./EmptyState";
import { SkeletonList } from "./Skeleton";

export function PatientsList({
  patients,
  selectedId,
  onSelect,
  isLoading,
}: {
  patients: Patient[] | undefined;
  selectedId: number | null;
  onSelect: (id: number) => void;
  isLoading: boolean;
}) {
  if (isLoading) return <SkeletonList rows={3} />;
  if (!patients || patients.length === 0) {
    return <EmptyState icon={<Users className="h-5 w-5 text-slate-300" />}>No patients.</EmptyState>;
  }

  return (
    <div className="space-y-2">
      {patients.map((p) => (
        <button
          key={p.id}
          onClick={() => onSelect(p.id)}
          className={`w-full rounded-lg border px-3 py-2.5 text-left transition ${
            selectedId === p.id
              ? "border-brand-400 bg-brand-50 ring-1 ring-brand-200"
              : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
          }`}
        >
          <div className="text-sm font-medium text-slate-800">{p.full_name}</div>
          <div className="text-xs text-slate-400">MRN {p.mrn}</div>
        </button>
      ))}
    </div>
  );
}
