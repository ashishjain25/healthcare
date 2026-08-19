import { useRef, useState, type FormEvent } from "react";
import { FileUp, Loader2, UploadCloud } from "lucide-react";
import type { Patient } from "../api/types";
import { OTHER_CATEGORY, REPORT_CATEGORY_GROUPS } from "../lib/reportCategories";

const REPORT_TYPES: { value: string; label: string }[] = [
  { value: "lab", label: "Lab" },
  { value: "radiology", label: "Radiology" },
  { value: "physician_note", label: "Physician note" },
  { value: "discharge_summary", label: "Discharge summary" },
];

export function UploadReportForm({
  patients,
  onSubmit,
  isPending,
}: {
  /** When provided, shows a patient selector (radiologist flow). Omit for the patient's own upload. */
  patients?: Patient[];
  onSubmit: (formData: FormData) => Promise<unknown>;
  isPending: boolean;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [reportType, setReportType] = useState(patients ? "radiology" : "lab");
  const [category, setCategory] = useState("");
  const [customCategory, setCustomCategory] = useState("");
  const [rawText, setRawText] = useState("");
  const [notes, setNotes] = useState("");
  const [patientId, setPatientId] = useState<string>(patients?.[0]?.id ? String(patients[0].id) : "");
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const resolvedCategory = category === OTHER_CATEGORY ? customCategory.trim() : category;
    if (!resolvedCategory) return;

    const formData = new FormData();
    if (patients) formData.append("patient_id", patientId);
    formData.append("report_type", reportType);
    formData.append("category", resolvedCategory);
    if (rawText) formData.append("raw_text", rawText);
    if (notes) formData.append("uploader_notes", notes);
    if (fileRef.current?.files?.length) formData.append("file", fileRef.current.files[0]);

    await onSubmit(formData);
    setCategory("");
    setCustomCategory("");
    setRawText("");
    setNotes("");
    setFileName(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  function handleFiles(files: FileList | null) {
    if (files?.length) setFileName(files[0].name);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3.5">
      {patients && (
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Patient</label>
          <select
            required
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          >
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name} ({p.mrn})
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Report type</label>
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          >
            {REPORT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Category</label>
          <select
            required
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          >
            <option value="" disabled>
              Select…
            </option>
            {REPORT_CATEGORY_GROUPS.map((g) => (
              <optgroup key={g.group} label={g.group}>
                {g.options.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </optgroup>
            ))}
            <option value={OTHER_CATEGORY}>Other…</option>
          </select>
        </div>
      </div>

      {category === OTHER_CATEGORY && (
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Specify category</label>
          <input
            required
            value={customCategory}
            onChange={(e) => setCustomCategory(e.target.value)}
            placeholder="e.g. lipid_panel"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>
      )}

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Paste report text (or attach a file below)</label>
        <textarea
          rows={3}
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          className="w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (fileRef.current) fileRef.current.files = e.dataTransfer.files;
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => fileRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed px-3 py-4 text-center text-xs transition ${
          dragOver ? "border-brand-400 bg-brand-50" : "border-slate-200 bg-slate-50 hover:border-slate-300"
        }`}
      >
        {fileName ? (
          <>
            <FileUp className="h-5 w-5 text-brand-600" />
            <span className="font-medium text-slate-700">{fileName}</span>
          </>
        ) : (
          <>
            <UploadCloud className="h-5 w-5 text-slate-400" />
            <span className="text-slate-500">Drop a .docx / .pdf file here, or click to browse</span>
          </>
        )}
        <input
          ref={fileRef}
          type="file"
          accept=".docx,.pdf"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {patients && (
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Notes</label>
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>
      )}

      <button
        type="submit"
        disabled={isPending}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
        {isPending ? "Uploading…" : "Upload report"}
      </button>
    </form>
  );
}
