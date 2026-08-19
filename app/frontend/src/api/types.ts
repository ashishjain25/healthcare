export type Role = "patient" | "doctor" | "radiologist";

export interface SessionUser {
  user_id: number;
  role: Role;
  full_name: string;
  patient_id?: number | null;
}

export interface DirectoryUser {
  id: number;
  full_name: string;
  email: string;
}

export interface Patient {
  id: number;
  user_id: number;
  mrn: string;
  dob: string | null;
  sex: string | null;
  blood_group: string | null;
  known_conditions: string | null;
  primary_doctor_id: number | null;
  created_at: string;
  full_name: string;
  email: string;
}

export type AllergyCategory = "Food" | "Medication" | "Environmental" | "Skin";
export type AllergySeverity = "MILD" | "MODERATE" | "SEVERE" | "CRITICAL";

export interface Allergy {
  id: number;
  patient_id: number;
  allergen: string;
  category: AllergyCategory;
  severity: AllergySeverity | null;
  reaction_notes: string | null;
  source: "self_reported" | "ai_derived";
  created_at: string;
}

export type MedicalHistoryEntryType = "past_treatment" | "condition" | "medication" | "symptom";

export interface MedicalHistoryEntry {
  id: number;
  patient_id: number;
  entry_type: MedicalHistoryEntryType;
  description: string;
  entry_date: string | null;
  created_at: string;
}

export type ReportType = "lab" | "radiology" | "physician_note" | "discharge_summary";
export type ReportStatus = "pending_pipeline" | "processing" | "processed" | "error";

export interface Report {
  id: number;
  patient_id: number;
  uploaded_by_user_id: number;
  report_type: ReportType;
  category: string;
  original_filename: string | null;
  file_path: string | null;
  file_format: "docx" | "pdf" | "txt" | null;
  raw_text: string;
  table_text: string;
  status: ReportStatus;
  uploader_notes: string | null;
  uploaded_at: string;
  updated_at: string;
  // present on list endpoints joined with patient/user
  mrn?: string;
  patient_name?: string;
}

export type ExtractionStatus = "NORMAL" | "LOW" | "HIGH" | "CRITICAL_LOW" | "CRITICAL_HIGH" | "UNKNOWN";

export interface Extraction {
  id: number;
  report_id: number;
  parameter_name: string;
  value: string;
  unit: string | null;
  reference_range: string | null;
  status: ExtractionStatus;
  confidence: number;
  created_at: string;
}

export type AgentName =
  | "data_extraction"
  | "clinical_analysis"
  | "risk_detection"
  | "insight_generation"
  | "patient_communication";

export interface AgentOutput {
  id: number;
  pipeline_run_id: number;
  agent_name: AgentName;
  output_json: unknown;
  confidence: number | null;
  flagged: boolean | number;
  flag_reason: string | null;
  created_at: string;
}

export interface PipelineRun {
  id: number;
  report_id: number;
  patient_id: number;
  started_at: string;
  completed_at: string | null;
  status: "running" | "completed" | "failed";
  overall_confidence: number | null;
  escalation_flag: boolean | number;
  escalation_reason: string | null;
}

export type RiskLevel = "routine" | "urgent" | "stat" | "emergency" | "low" | "moderate" | "high" | "critical";
export type InsightStatus = "ai_generated" | "review_required" | "doctor_reviewed" | "finalized";

export interface Insight {
  id: number;
  risk_level: RiskLevel | null;
  status: InsightStatus;
  requires_review?: boolean;
  clinical_inconsistency?: boolean;
  key_findings: string[];
  risk_indicators: string[];
  recommendations: string[];
}

export interface PatientSummaryView {
  plain_language_summary: string;
  what_this_means: string[];
  what_you_should_do: string[];
  disclaimer: string;
}

export interface DoctorReview {
  id: number;
  insight_id?: number;
  doctor_user_id?: number;
  action: "validated" | "modified" | "rejected" | "finalized";
  modified_findings_json?: string | null;
  comments: string | null;
  doctor_name?: string;
  created_at: string;
}

export interface PatientReportDetail extends Report {
  extractions: Extraction[];
  insight: Insight | null;
  patient_summary: PatientSummaryView | null;
  patient_summary_pending_review?: boolean;
  doctor_reviews?: DoctorReview[];
}

export interface DoctorReportDetail extends Report {
  extractions: Extraction[];
  pipeline_run: PipelineRun | null;
  agent_outputs: AgentOutput[];
  insight: Insight | null;
  patient_summary: Record<string, unknown> | null;
  doctor_reviews: DoctorReview[];
}

export interface CompareRow {
  parameter: string;
  earlier: { value: string; unit: string | null; status: ExtractionStatus } | null;
  later: { value: string; unit: string | null; status: ExtractionStatus } | null;
  changed: boolean;
}

export interface CompareResult {
  earlier_report: Report;
  later_report: Report;
  rows: CompareRow[];
}

export type AlertSeverity = "urgent" | "stat" | "emergency";
export type AlertStatus = "open" | "acknowledged" | "resolved";

export interface Alert {
  id: number;
  patient_id: number;
  report_id: number | null;
  pipeline_run_id: number | null;
  alert_type: "critical_lab" | "critical_radiology" | "allergy_risk" | "clinical_inconsistency";
  severity: AlertSeverity;
  message: string;
  status: AlertStatus;
  created_at: string;
  acknowledged_by_user_id: number | null;
  acknowledged_at: string | null;
  mrn?: string;
  patient_name?: string;
}

export interface Appointment {
  id: number;
  patient_id: number;
  doctor_user_id: number | null;
  alert_id: number | null;
  suggested_reason: string;
  proposed_datetime: string;
  status: "suggested" | "confirmed" | "cancelled";
  created_at: string;
  doctor_name?: string | null;
  patient_name?: string;
  mrn?: string;
}

export interface Message {
  id: number;
  thread_id: string;
  sender_user_id: number;
  recipient_user_id: number;
  patient_id: number;
  report_id: number | null;
  body: string;
  created_at: string;
  read_at: string | null;
  sender_name?: string;
  recipient_name?: string;
  mrn?: string;
  patient_name?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
