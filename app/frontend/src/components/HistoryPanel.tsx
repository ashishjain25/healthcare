import { useState, type FormEvent } from "react";
import { Loader2, Plus, ShieldAlert } from "lucide-react";
import type { Allergy, MedicalHistoryEntry } from "../api/types";
import { Badge } from "./Badge";
import { EmptyState } from "./EmptyState";

const CATEGORIES = ["Food", "Medication", "Environmental", "Skin"];

export function HistoryPanel({
  allergies,
  medicalHistory,
  onAddAllergy,
  isAddingAllergy,
}: {
  allergies: Allergy[] | undefined;
  medicalHistory: MedicalHistoryEntry[] | undefined;
  onAddAllergy: (payload: { allergen: string; category: string }) => void;
  isAddingAllergy: boolean;
}) {
  const [allergen, setAllergen] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const value = allergen.trim();
    if (!value) return;
    onAddAllergy({ allergen: value, category });
    setAllergen("");
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Allergies</h4>
        {!allergies || allergies.length === 0 ? (
          <EmptyState icon={<ShieldAlert className="h-5 w-5 text-slate-300" />}>No allergies on file.</EmptyState>
        ) : (
          <div className="space-y-1.5">
            {allergies.map((a) => (
              <div
                key={a.id}
                className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-1.5 text-sm"
              >
                <span className="text-slate-700">
                  {a.allergen} <span className="text-slate-400">({a.category})</span>
                </span>
                {a.severity && <Badge value={a.severity} />}
              </div>
            ))}
          </div>
        )}
      </div>

      {medicalHistory && medicalHistory.length > 0 && (
        <div>
          <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Medical history</h4>
          <div className="space-y-1.5">
            {medicalHistory.map((h) => (
              <div key={h.id} className="rounded-md bg-slate-50 px-3 py-1.5 text-sm text-slate-700">
                <span className="text-slate-400">[{h.entry_type.replace(/_/g, " ")}]</span> {h.description}
              </div>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-slate-100 pt-3">
        <div className="flex-1">
          <label className="mb-1 block text-xs font-medium text-slate-600">Add allergy</label>
          <input
            value={allergen}
            onChange={(e) => setAllergen(e.target.value)}
            placeholder="e.g. Peanut"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-lg border border-slate-300 px-2 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        >
          {CATEGORIES.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        <button
          type="submit"
          disabled={isAddingAllergy}
          className="flex items-center justify-center rounded-lg bg-slate-800 px-3 py-2 text-white transition hover:bg-slate-700 disabled:opacity-50"
        >
          {isAddingAllergy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
        </button>
      </form>
    </div>
  );
}
