import { useEffect, useMemo, useState } from "react";
import { GitCompare } from "lucide-react";
import type { CompareResult, Report } from "../api/types";
import { EmptyState } from "./EmptyState";
import { Skeleton } from "./Skeleton";
import { formatCategory, formatDate } from "../lib/format";

export function CompareReportsPanel({
  reports,
  a,
  b,
  onChangeA,
  onChangeB,
  result,
  isFetching,
}: {
  reports: Report[] | undefined;
  a: number | null;
  b: number | null;
  onChangeA: (id: number | null) => void;
  onChangeB: (id: number | null) => void;
  result: CompareResult | undefined;
  isFetching: boolean;
}) {
  const options = reports ?? [];

  // Comparing two different investigation types (e.g. a prostate ultrasound
  // against an MRI spine) produces a meaningless parameter diff — reports
  // must first be scoped to a single category before either report select
  // is populated.
  const categories = useMemo(() => {
    const seen = new Set<string>();
    for (const r of options) seen.add(r.category);
    return Array.from(seen).sort();
  }, [options]);

  const [category, setCategory] = useState<string>("");

  useEffect(() => {
    if (category && !categories.includes(category)) {
      setCategory("");
      onChangeA(null);
      onChangeB(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categories]);

  const needsCategoryPicker = categories.length > 1;
  const effectiveCategory = needsCategoryPicker ? category : (categories[0] ?? "");
  const filteredOptions = options.filter((r) => r.category === effectiveCategory);

  function handleCategoryChange(value: string) {
    setCategory(value);
    onChangeA(null);
    onChangeB(null);
  }

  return (
    <div className="space-y-3">
      {needsCategoryPicker && (
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Investigation type</label>
          <select
            value={category}
            onChange={(e) => handleCategoryChange(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          >
            <option value="">Select…</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {formatCategory(c)}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="mb-1 block text-xs font-medium text-slate-600">Earlier</label>
          <select
            value={a ?? ""}
            disabled={!effectiveCategory}
            onChange={(e) => onChangeA(e.target.value ? Number(e.target.value) : null)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400"
          >
            <option value="">Select…</option>
            {filteredOptions.map((r) => (
              <option key={r.id} value={r.id}>
                {formatDate(r.uploaded_at)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="mb-1 block text-xs font-medium text-slate-600">Later</label>
          <select
            value={b ?? ""}
            disabled={!effectiveCategory}
            onChange={(e) => onChangeB(e.target.value ? Number(e.target.value) : null)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400"
          >
            <option value="">Select…</option>
            {filteredOptions.map((r) => (
              <option key={r.id} value={r.id}>
                {formatDate(r.uploaded_at)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {needsCategoryPicker && !effectiveCategory && (
        <p className="text-xs text-slate-400">Pick an investigation type to see its reports.</p>
      )}

      {a && b && a === b && (
        <p className="text-xs text-amber-600">Choose two different reports to compare.</p>
      )}

      {isFetching && <Skeleton className="h-32 w-full" />}

      {!isFetching && result && (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-3 py-2 font-medium">Parameter</th>
                <th className="px-3 py-2 font-medium">Earlier</th>
                <th className="px-3 py-2 font-medium">Later</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {result.rows.map((row) => (
                <tr key={row.parameter} className={row.changed ? "bg-amber-50/60" : ""}>
                  <td className="px-3 py-2 font-medium text-slate-700">{row.parameter}</td>
                  <td className="px-3 py-2 text-slate-600">
                    {row.earlier ? `${row.earlier.value} ${row.earlier.unit ?? ""}` : "—"}
                  </td>
                  <td className="px-3 py-2 text-slate-600">
                    {row.later ? `${row.later.value} ${row.later.unit ?? ""}` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!isFetching && !result && (!a || !b) && effectiveCategory && (
        <EmptyState icon={<GitCompare className="h-5 w-5 text-slate-300" />}>
          Pick two reports to see what changed.
        </EmptyState>
      )}
    </div>
  );
}
