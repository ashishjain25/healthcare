import { useEffect, useRef, useState, type FormEvent } from "react";
import { Bot, Loader2, Send, User } from "lucide-react";
import type { ChatMessage } from "../api/types";
import { EmptyState } from "./EmptyState";

export function ChatPanel({
  messages,
  onSend,
  isPending,
  placeholder,
  disabled,
  disabledHint,
}: {
  messages: ChatMessage[];
  onSend: (question: string) => void;
  isPending: boolean;
  placeholder: string;
  disabled?: boolean;
  disabledHint?: string;
}) {
  const [input, setInput] = useState("");
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages, isPending]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q || disabled) return;
    setInput("");
    onSend(q);
  }

  return (
    <div className="flex flex-col gap-3">
      <div ref={logRef} className="flex h-44 flex-col gap-2 overflow-y-auto rounded-lg bg-slate-50 p-3">
        {messages.length === 0 && !isPending ? (
          <EmptyState icon={<Bot className="h-5 w-5 text-slate-300" />}>
            {disabled ? disabledHint : "Ask a question to get started."}
          </EmptyState>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`flex items-start gap-2 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
              <div
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                  m.role === "user" ? "bg-brand-600 text-white" : "bg-teal-100 text-teal-700"
                }`}
              >
                {m.role === "user" ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
              </div>
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  m.role === "user" ? "bg-brand-600 text-white" : "border border-slate-200 bg-white text-slate-700"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))
        )}
        {isPending && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Thinking…
          </div>
        )}
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50"
        />
        <button
          type="submit"
          disabled={disabled || isPending || !input.trim()}
          className="flex items-center justify-center rounded-lg bg-brand-600 px-3 py-2 text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
