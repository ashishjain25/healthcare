import { useState, type FormEvent } from "react";
import { CheckCircle2, Loader2, PenLine, Stamp } from "lucide-react";

export function ReviewForm({
  onSubmit,
  isPending,
}: {
  onSubmit: (payload: { action: "validated" | "modified" | "finalized"; comments: string }) => void;
  isPending: boolean;
}) {
  const [comments, setComments] = useState("");

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const action = (e.nativeEvent as SubmitEvent).submitter?.getAttribute("data-action") as
      | "validated"
      | "modified"
      | "finalized"
      | null;
    onSubmit({ action: action ?? "validated", comments });
  }

  return (
    <form onSubmit={submit} className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <label className="block text-xs font-medium text-slate-600">Doctor review</label>
      <textarea
        rows={2}
        value={comments}
        onChange={(e) => setComments(e.target.value)}
        placeholder="Comments…"
        className="w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          data-action="validated"
          disabled={isPending}
          className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          {isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
          Validate
        </button>
        <button
          type="submit"
          data-action="modified"
          disabled={isPending}
          className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 disabled:opacity-50"
        >
          <PenLine className="h-3.5 w-3.5" />
          Mark modified
        </button>
        <button
          type="submit"
          data-action="finalized"
          disabled={isPending}
          className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 disabled:opacity-50"
        >
          <Stamp className="h-3.5 w-3.5" />
          Finalize diagnosis
        </button>
      </div>
    </form>
  );
}
