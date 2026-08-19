import { useState } from "react";
import { ChevronDown, ChevronRight, Cpu } from "lucide-react";
import type { AgentOutput } from "../api/types";
import { Badge } from "./Badge";
import { EmptyState } from "./EmptyState";
import { AgentOutputView } from "./AgentOutputView";

const AGENT_LABELS: Record<string, string> = {
  data_extraction: "Data Extraction",
  clinical_analysis: "Clinical Analysis",
  risk_detection: "Risk Detection",
  insight_generation: "Insight Generation",
  patient_communication: "Patient Communication",
};

function AgentRow({ output }: { output: AgentOutput }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-lg border border-slate-200">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left"
      >
        <span className="flex items-center gap-1.5 text-sm font-medium text-slate-700">
          {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          {AGENT_LABELS[output.agent_name] ?? output.agent_name}
        </span>
        {Boolean(output.flagged) && <Badge value="flagged" label="review required" />}
      </button>
      {open && (
        <div className="space-y-3 border-t border-slate-100 px-3 py-3">
          {output.flag_reason && (
            <p className="rounded-md bg-red-50 px-2.5 py-1.5 text-xs text-red-700">{output.flag_reason}</p>
          )}
          <AgentOutputView agentName={output.agent_name} output={output.output_json} />
        </div>
      )}
    </div>
  );
}

export function AgentAuditTrail({ outputs }: { outputs: AgentOutput[] }) {
  if (!outputs.length) {
    return <EmptyState icon={<Cpu className="h-5 w-5 text-slate-300" />}>Pipeline not yet run.</EmptyState>;
  }
  return (
    <div className="space-y-1.5">
      {outputs.map((o) => (
        <AgentRow key={o.id} output={o} />
      ))}
    </div>
  );
}
