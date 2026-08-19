import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPatchJson, apiPostForm, apiPostJson } from "./client";
import type {
  Alert,
  Allergy,
  Appointment,
  ChatMessage,
  CompareResult,
  DirectoryUser,
  DoctorReportDetail,
  MedicalHistoryEntry,
  Message,
  Patient,
  PatientReportDetail,
  Report,
  SessionUser,
} from "./types";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiGet<SessionUser>("/api/auth/me"),
    retry: false,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email: string; password: string }) =>
      apiPostJson<SessionUser>("/api/auth/login", payload),
    onSuccess: (user) => qc.setQueryData(["me"], user),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPostJson("/api/auth/logout", {}),
    onSuccess: () => qc.clear(),
  });
}

// ---------------------------------------------------------------------------
// Patient
// ---------------------------------------------------------------------------

export function usePatientReports() {
  return useQuery({ queryKey: ["patient", "reports"], queryFn: () => apiGet<Report[]>("/api/patient/reports") });
}

export function usePatientReport(reportId: number | null) {
  return useQuery({
    queryKey: ["patient", "report", reportId],
    queryFn: () => apiGet<PatientReportDetail>(`/api/patient/reports/${reportId}`),
    enabled: reportId != null,
  });
}

export function useUploadPatientReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) =>
      apiPostForm<{ report_id: number; status: string }>("/api/patient/reports/upload", formData),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["patient", "reports"] }),
  });
}

export function usePatientCompare(a: number | null, b: number | null) {
  return useQuery({
    queryKey: ["patient", "compare", a, b],
    queryFn: () => apiGet<CompareResult>(`/api/patient/reports/compare?a=${a}&b=${b}`),
    enabled: a != null && b != null && a !== b,
  });
}

export function usePatientHistory() {
  return useQuery({
    queryKey: ["patient", "history"],
    queryFn: () => apiGet<{ allergies: Allergy[]; medical_history: MedicalHistoryEntry[] }>("/api/patient/history"),
  });
}

export function useAddAllergy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { allergen: string; category: string; severity?: string; reaction_notes?: string }) =>
      apiPostJson("/api/patient/history/allergy", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["patient", "history"] }),
  });
}

export function useAddHistoryEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { entry_type: string; description: string; entry_date?: string }) =>
      apiPostJson("/api/patient/history/entry", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["patient", "history"] }),
  });
}

export function usePatientAppointments() {
  return useQuery({
    queryKey: ["patient", "appointments"],
    queryFn: () => apiGet<Appointment[]>("/api/patient/appointments"),
  });
}

export function usePatientDoctors() {
  return useQuery({
    queryKey: ["patient", "doctors"],
    queryFn: () => apiGet<DirectoryUser[]>("/api/patient/doctors"),
  });
}

export function useAppointmentAvailability(doctorUserId: number | null, date: string | null) {
  return useQuery({
    queryKey: ["patient", "appointments", "availability", doctorUserId, date],
    queryFn: () =>
      apiGet<{ available_times: string[] }>(
        `/api/patient/appointments/availability?doctor_user_id=${doctorUserId}&date=${date}`,
      ),
    enabled: doctorUserId != null && !!date,
  });
}

export function useBookAppointment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { doctor_user_id: number; date: string; time: string; reason?: string }) =>
      apiPostJson<{ id: number }>("/api/patient/appointments/book", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["patient", "appointments"] }),
  });
}

export function useCancelAppointment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (appointmentId: number) =>
      apiPatchJson(`/api/patient/appointments/${appointmentId}/cancel`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["patient", "appointments"] }),
  });
}

export function usePatientAlerts() {
  return useQuery({ queryKey: ["patient", "alerts"], queryFn: () => apiGet<Alert[]>("/api/patient/alerts") });
}

export function usePatientChatHistory() {
  return useQuery({
    queryKey: ["patient", "chat", "history"],
    queryFn: () => apiGet<ChatMessage[]>("/api/patient/chat/history"),
  });
}

export function usePatientChat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (question: string) => apiPostJson<{ answer: string }>("/api/patient/chat", { question }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["patient", "chat", "history"] }),
  });
}

// ---------------------------------------------------------------------------
// Doctor
// ---------------------------------------------------------------------------

export function useDoctorPatients() {
  return useQuery({ queryKey: ["doctor", "patients"], queryFn: () => apiGet<Patient[]>("/api/doctor/patients") });
}

export function useDoctorAppointments() {
  return useQuery({
    queryKey: ["doctor", "appointments"],
    queryFn: () => apiGet<Appointment[]>("/api/doctor/appointments"),
  });
}

export function useDoctorPatientReports(patientId: number | null) {
  return useQuery({
    queryKey: ["doctor", "patient", patientId, "reports"],
    queryFn: () => apiGet<Report[]>(`/api/doctor/patients/${patientId}/reports`),
    enabled: patientId != null,
  });
}

export function useDoctorReport(reportId: number | null) {
  return useQuery({
    queryKey: ["doctor", "report", reportId],
    queryFn: () => apiGet<DoctorReportDetail>(`/api/doctor/reports/${reportId}`),
    enabled: reportId != null,
  });
}

export function useDoctorCompare(a: number | null, b: number | null) {
  return useQuery({
    queryKey: ["doctor", "compare", a, b],
    queryFn: () => apiGet<CompareResult>(`/api/doctor/reports/compare?a=${a}&b=${b}`),
    enabled: a != null && b != null && a !== b,
  });
}

export function useReviewInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      insightId,
      reportId,
      ...payload
    }: {
      insightId: number;
      reportId: number;
      action: "validated" | "modified" | "rejected" | "finalized";
      comments?: string;
      modified_findings?: string[];
    }) => apiPostJson(`/api/doctor/insights/${insightId}/review`, payload),
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ["doctor", "report", vars.reportId] }),
  });
}

export function useDoctorAlerts() {
  return useQuery({ queryKey: ["doctor", "alerts"], queryFn: () => apiGet<Alert[]>("/api/doctor/alerts") });
}

export function useAcknowledgeAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertId: number) => apiPostJson(`/api/doctor/alerts/${alertId}/acknowledge`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["doctor", "alerts"] }),
  });
}

export function useDoctorRadiologists() {
  return useQuery({
    queryKey: ["doctor", "radiologists"],
    queryFn: () => apiGet<DirectoryUser[]>("/api/doctor/radiologists"),
  });
}

export function useDoctorMessages(patientId: number | null) {
  return useQuery({
    queryKey: ["doctor", "messages", patientId],
    queryFn: () => apiGet<Message[]>(`/api/doctor/messages?patient_id=${patientId}`),
    enabled: patientId != null,
  });
}

export function useSendDoctorMessage(patientId: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { recipient_user_id: number; body: string; report_id?: number }) =>
      apiPostJson("/api/doctor/messages", { ...payload, patient_id: patientId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["doctor", "messages", patientId] }),
  });
}

export function useDoctorChat() {
  return useMutation({
    mutationFn: (payload: { patient_id: number; question: string }) =>
      apiPostJson<{ answer: string }>("/api/doctor/chat", payload),
  });
}

// ---------------------------------------------------------------------------
// Radiologist
// ---------------------------------------------------------------------------

export function useRadiologistDoctors() {
  return useQuery({
    queryKey: ["radiologist", "doctors"],
    queryFn: () => apiGet<DirectoryUser[]>("/api/radiologist/doctors"),
  });
}

export function useRadiologistUploads() {
  return useQuery({
    queryKey: ["radiologist", "reports"],
    queryFn: () => apiGet<Report[]>("/api/radiologist/reports"),
  });
}

export function useRadiologistPatients() {
  return useQuery({
    queryKey: ["radiologist", "patients"],
    queryFn: () => apiGet<Patient[]>("/api/radiologist/patients"),
  });
}

export function useRadiologistUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) =>
      apiPostForm<{ report_id: number; status: string }>("/api/radiologist/reports/upload", formData),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["radiologist", "reports"] }),
  });
}

export function useCorrectReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      reportId,
      ...payload
    }: {
      reportId: number;
      raw_text?: string;
      table_text?: string;
      uploader_notes?: string;
    }) => apiPatchJson(`/api/radiologist/reports/${reportId}`, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["radiologist", "reports"] }),
  });
}

export function useRadiologistMessages(patientId: number | null) {
  return useQuery({
    queryKey: ["radiologist", "messages", patientId],
    queryFn: () =>
      apiGet<Message[]>(patientId != null ? `/api/radiologist/messages?patient_id=${patientId}` : "/api/radiologist/messages"),
  });
}

export function useSendRadiologistMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { recipient_user_id: number; patient_id: number; body: string }) =>
      apiPostJson("/api/radiologist/messages", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["radiologist", "messages"] }),
  });
}
