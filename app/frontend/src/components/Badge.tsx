const TONE_MAP: Record<string, string> = {
  // report / pipeline status
  pending_pipeline: "bg-slate-100 text-slate-600 ring-slate-300",
  processing: "bg-amber-50 text-amber-700 ring-amber-300",
  processed: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  error: "bg-red-50 text-red-700 ring-red-300",
  // extraction status
  normal: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  low: "bg-amber-50 text-amber-700 ring-amber-300",
  high: "bg-amber-50 text-amber-700 ring-amber-300",
  critical_low: "bg-red-50 text-red-700 ring-red-300",
  critical_high: "bg-red-50 text-red-700 ring-red-300",
  unknown: "bg-slate-100 text-slate-500 ring-slate-300",
  // risk level
  routine: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  moderate: "bg-amber-50 text-amber-700 ring-amber-300",
  urgent: "bg-orange-50 text-orange-700 ring-orange-300",
  stat: "bg-red-50 text-red-700 ring-red-300",
  emergency: "bg-red-100 text-red-800 ring-red-400",
  // insight status
  ai_generated: "bg-brand-50 text-brand-700 ring-brand-300",
  review_required: "bg-red-50 text-red-700 ring-red-300",
  doctor_reviewed: "bg-teal-50 text-teal-700 ring-teal-300",
  finalized: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  // doctor review action
  validated: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  modified: "bg-amber-50 text-amber-700 ring-amber-300",
  rejected: "bg-red-50 text-red-700 ring-red-300",
  // alert status
  open: "bg-red-50 text-red-700 ring-red-300",
  acknowledged: "bg-slate-100 text-slate-600 ring-slate-300",
  resolved: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  // appointment status
  suggested: "bg-brand-50 text-brand-700 ring-brand-300",
  confirmed: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  cancelled: "bg-slate-100 text-slate-500 ring-slate-300",
  // allergy severity
  mild: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  severe: "bg-orange-50 text-orange-700 ring-orange-300",
  critical: "bg-red-50 text-red-700 ring-red-300",
  flagged: "bg-red-50 text-red-700 ring-red-300",
};

export function Badge({ value, label }: { value: string | null | undefined; label?: string }) {
  if (!value) return null;
  const key = String(value).toLowerCase();
  const tone = TONE_MAP[key] ?? "bg-slate-100 text-slate-600 ring-slate-300";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${tone}`}
    >
      {(label ?? value).replace(/_/g, " ")}
    </span>
  );
}
