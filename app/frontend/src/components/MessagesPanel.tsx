import { useState, type FormEvent } from "react";
import { MessageSquare, Send } from "lucide-react";
import type { Message } from "../api/types";
import { EmptyState } from "./EmptyState";
import { formatDate } from "../lib/format";

interface Recipient {
  id: number;
  full_name: string;
}

interface PatientOption {
  id: number;
  full_name: string;
  mrn?: string;
}

export function MessagesPanel({
  messages,
  currentUserId,
  recipients,
  patients,
  onSend,
  isPending,
  emptyLabel = "No messages yet.",
}: {
  messages: Message[] | undefined;
  /** The logged-in user's id — their own messages are labeled "You" and right-aligned. */
  currentUserId: number;
  /** Directory of people this user can message, shown as a name dropdown. */
  recipients: Recipient[] | undefined;
  /** When provided, shows a patient-name dropdown instead of a raw patient ID input. */
  patients?: PatientOption[];
  onSend: (payload: { recipient_user_id: number; patient_id?: number; body: string }) => void;
  isPending: boolean;
  emptyLabel?: string;
}) {
  const [recipientId, setRecipientId] = useState("");
  const [patientId, setPatientId] = useState("");
  const [body, setBody] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!recipientId || !body.trim()) return;
    if (patients && !patientId) return;
    onSend({
      recipient_user_id: Number(recipientId),
      patient_id: patients ? Number(patientId) : undefined,
      body: body.trim(),
    });
    setBody("");
  }

  return (
    <div className="space-y-3">
      <div className="max-h-56 space-y-2 overflow-y-auto">
        {!messages || messages.length === 0 ? (
          <EmptyState icon={<MessageSquare className="h-5 w-5 text-slate-300" />}>{emptyLabel}</EmptyState>
        ) : (
          messages.map((m) => {
            const isOwn = m.sender_user_id === currentUserId;
            return (
              <div key={m.id} className={`flex ${isOwn ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 ${
                    isOwn ? "bg-brand-600 text-white" : "border border-slate-100 bg-slate-50 text-slate-700"
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className={`text-xs font-semibold ${isOwn ? "text-brand-100" : "text-slate-700"}`}>
                      {isOwn ? "You" : m.sender_name}
                    </span>
                    <span className={`text-[11px] ${isOwn ? "text-brand-100/80" : "text-slate-400"}`}>
                      {formatDate(m.created_at)}
                    </span>
                  </div>
                  <p className={`mt-0.5 text-sm ${isOwn ? "text-white" : "text-slate-600"}`}>{m.body}</p>
                </div>
              </div>
            );
          })
        )}
      </div>
      <form onSubmit={handleSubmit} className="space-y-2 border-t border-slate-100 pt-3">
        <div className={`grid gap-2 ${patients ? "grid-cols-2" : "grid-cols-1"}`}>
          <select
            required
            value={recipientId}
            onChange={(e) => setRecipientId(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          >
            <option value="" disabled>
              {recipients === undefined ? "Loading…" : recipients.length ? "Recipient…" : "No recipients found"}
            </option>
            {recipients?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.full_name}
              </option>
            ))}
          </select>
          {patients && (
            <select
              required
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="" disabled>
                Patient…
              </option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.full_name}
                  {p.mrn ? ` (${p.mrn})` : ""}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="flex gap-2">
          <textarea
            rows={2}
            required
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Message…"
            className="flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <button
            type="submit"
            disabled={isPending}
            className="flex items-center justify-center rounded-lg bg-brand-600 px-3 text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
