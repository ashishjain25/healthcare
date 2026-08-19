import type { ReactElement, ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import type { AgentName } from "../api/types";
import { Badge } from "./Badge";

// The 5 pipeline agents each persist a different Pydantic schema as
// output_json (see backend/agents/schemas.py) — every field read below is
// optional-chained since the raw JSON is untyped on the wire.
type AnyOutput = Record<string, any>;

function ConfidenceMeter({ value, label }: { value: number | null | undefined; label: string }) {
  if (value == null) return null;
  const pct = Math.round(value * 100);
  const tone = pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-medium text-slate-500">{label}</span>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] font-semibold text-slate-600">{pct}%</span>
    </div>
  );
}

function Bullets({ items }: { items?: string[] | null }) {
  if (!items?.length) return null;
  return (
    <ul className="space-y-1">
      {items.map((s, i) => (
        <li key={i} className="rounded-md bg-slate-50 px-2.5 py-1.5 text-sm text-slate-700">
          {s}
        </li>
      ))}
    </ul>
  );
}

function InlineList({ items }: { items?: string[] | null }) {
  if (!items?.length) return null;
  return <span>{items.join(", ")}</span>;
}

function FlagBanner({
  active,
  tone = "amber",
  children,
}: {
  active: boolean | undefined;
  tone?: "amber" | "red";
  children: ReactNode;
}) {
  if (!active) return null;
  const cls = tone === "red" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700";
  return (
    <div className={`flex items-start gap-2 rounded-lg px-3 py-2 text-sm ${cls}`}>
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  if (children == null || children === false) return null;
  return (
    <div>
      <h5 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{title}</h5>
      {children}
    </div>
  );
}

function DataExtractionView({ o }: { o: AnyOutput }) {
  return (
    <div className="space-y-3">
      <ConfidenceMeter value={o.extraction_confidence} label="Extraction confidence" />
      <FlagBanner active={o.needs_review}>
        Flagged for review{o.review_reason ? `: ${o.review_reason}` : "."}
      </FlagBanner>
      <Section title="Extracted parameters">
        {o.parameters?.length ? (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-3 py-1.5 font-medium">Parameter</th>
                  <th className="px-3 py-1.5 font-medium">Value</th>
                  <th className="px-3 py-1.5 font-medium">Reference range</th>
                  <th className="px-3 py-1.5 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {o.parameters.map((p: AnyOutput, i: number) => (
                  <tr key={i}>
                    <td className="px-3 py-1.5 font-medium text-slate-700">{p.name}</td>
                    <td className="px-3 py-1.5 text-slate-600">
                      {p.value} {p.unit ?? ""}
                    </td>
                    <td className="px-3 py-1.5 text-slate-500">{p.reference_range ?? "—"}</td>
                    <td className="px-3 py-1.5">
                      <Badge value={p.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-400">None extracted.</p>
        )}
      </Section>
      <Section title="Narrative observations">
        <Bullets items={o.narrative_observations} />
      </Section>
      <Section title="Missing or ambiguous">
        <Bullets items={o.missing_or_ambiguous} />
      </Section>
    </div>
  );
}

function ClinicalAnalysisView({ o }: { o: AnyOutput }) {
  const rad = o.radiology_detail;
  return (
    <div className="space-y-3">
      <ConfidenceMeter value={o.analysis_confidence} label="Analysis confidence" />
      <FlagBanner active={o.clinical_inconsistency} tone="red">
        Clinical inconsistency{o.inconsistency_reason ? `: ${o.inconsistency_reason}` : "."}
      </FlagBanner>
      <Section title="Overall impression">
        <p className="text-sm text-slate-700">{o.overall_impression}</p>
      </Section>
      {rad && (
        <Section title={`Radiology — ${rad.study_type} (${rad.body_region})`}>
          <div className="space-y-2 rounded-lg border border-slate-200 p-2.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm text-slate-700">
                <span className="font-medium">Impression:</span> {rad.impression}
              </span>
              <Badge value={rad.urgency} />
            </div>
            <Bullets items={rad.findings} />
            {rad.differential_diagnoses?.length ? (
              <p className="text-xs text-slate-500">
                <span className="font-medium">Differential diagnoses:</span>{" "}
                <InlineList items={rad.differential_diagnoses} />
              </p>
            ) : null}
            {rad.recommendations?.length ? (
              <p className="text-xs text-slate-500">
                <span className="font-medium">Recommendations:</span> <InlineList items={rad.recommendations} />
              </p>
            ) : null}
          </div>
        </Section>
      )}
      <Section title="Findings">
        <div className="space-y-2">
          {o.findings?.map((f: AnyOutput, i: number) => (
            <div key={i} className="rounded-lg border border-slate-200 p-2.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-700">{f.parameter_name}</span>
                <div className="flex gap-1">
                  <Badge value={f.status} />
                  <Badge value={f.urgency} />
                </div>
              </div>
              <p className="mt-1 text-sm text-slate-600">{f.interpretation}</p>
              {f.potential_causes?.length ? (
                <p className="mt-1 text-xs text-slate-400">
                  Potential causes: <InlineList items={f.potential_causes} />
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </Section>
      <Section title="Conflicting indicators">
        <Bullets items={o.conflicting_indicators} />
      </Section>
    </div>
  );
}

function RiskDetectionView({ o }: { o: AnyOutput }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge value={o.overall_risk_level} />
        <ConfidenceMeter value={o.risk_confidence} label="Risk confidence" />
      </div>
      <FlagBanner active={o.requires_immediate_escalation} tone="red">
        Requires immediate escalation.
      </FlagBanner>
      <FlagBanner active={o.escalate_for_clinician_validation}>
        Escalated for clinician validation{o.escalation_reason ? `: ${o.escalation_reason}` : "."}
      </FlagBanner>
      <FlagBanner active={o.ambiguous_multiple_conditions}>Ambiguous — multiple possible conditions.</FlagBanner>
      <FlagBanner active={o.possible_false_positive}>Possible false positive.</FlagBanner>
      <Section title="Risk flags">
        <div className="space-y-2">
          {o.risk_flags?.map((r: AnyOutput, i: number) => (
            <div key={i} className="rounded-lg border border-slate-200 p-2.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-700">{r.source_parameter}</span>
                <Badge value={r.risk_level} />
              </div>
              <p className="mt-1 text-sm text-slate-600">{r.rationale}</p>
              {r.kg_supporting_diagnoses?.length ? (
                <p className="mt-1 text-xs text-slate-400">
                  Supporting diagnoses: <InlineList items={r.kg_supporting_diagnoses} />
                </p>
              ) : null}
              {r.cross_reactive_allergens?.length ? (
                <p className="mt-1 text-xs text-slate-400">
                  Cross-reactive allergens: <InlineList items={r.cross_reactive_allergens} />
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

function InsightGenerationView({ o }: { o: AnyOutput }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Badge value={o.status} />
        <ConfidenceMeter value={o.overall_confidence} label="Overall confidence" />
      </div>
      <FlagBanner active={o.contradictory_outputs_detected} tone="red">
        Contradictory outputs detected across agents.
      </FlagBanner>
      <FlagBanner active={o.status === "review_required" && Boolean(o.review_required_reason)}>
        {o.review_required_reason}
      </FlagBanner>
      <Section title="Key findings">
        <Bullets items={o.key_findings} />
      </Section>
      <Section title="Risk indicators">
        <Bullets items={o.risk_indicators} />
      </Section>
      <Section title="Recommendations">
        <Bullets items={o.recommendations} />
      </Section>
      <Section title="Historical comparison">
        <Bullets items={o.historical_comparison_notes} />
      </Section>
    </div>
  );
}

function PatientCommunicationView({ o }: { o: AnyOutput }) {
  return (
    <div className="space-y-3">
      <FlagBanner active={o.diagnostic_language_flag}>
        Diagnostic language flagged — review before releasing to patient.
      </FlagBanner>
      <Section title="Plain-language summary">
        <p className="text-sm text-slate-700">{o.plain_language_summary}</p>
      </Section>
      <Section title="What this means">
        <Bullets items={o.what_this_means} />
      </Section>
      <Section title="What you should do">
        <Bullets items={o.what_you_should_do} />
      </Section>
      {o.disclaimer && <p className="border-t border-slate-100 pt-2 text-xs italic text-slate-400">{o.disclaimer}</p>}
    </div>
  );
}

const VIEWS: Partial<Record<AgentName, (props: { o: AnyOutput }) => ReactElement>> = {
  data_extraction: DataExtractionView,
  clinical_analysis: ClinicalAnalysisView,
  risk_detection: RiskDetectionView,
  insight_generation: InsightGenerationView,
  patient_communication: PatientCommunicationView,
};

export function AgentOutputView({ agentName, output }: { agentName: AgentName; output: unknown }) {
  const View = VIEWS[agentName];
  if (!View || typeof output !== "object" || output === null) {
    return (
      <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words text-[11px] text-slate-600">
        {JSON.stringify(output, null, 2)}
      </pre>
    );
  }
  return <View o={output as AnyOutput} />;
}
