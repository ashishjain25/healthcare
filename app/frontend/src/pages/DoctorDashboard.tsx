import { useMemo, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, MessageCircle, MessagesSquare, Users } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { Panel } from "../components/Panel";
import { AlertsPanel } from "../components/AlertsPanel";
import { PatientSelector } from "../components/PatientSelector";
import { SelectedPatientBanner } from "../components/SelectedPatientBanner";
import { ReportList } from "../components/ReportList";
import { DoctorReportDetail } from "../components/DoctorReportDetail";
import { CompareReportsPanel } from "../components/CompareReportsPanel";
import { MessagesPanel } from "../components/MessagesPanel";
import { ChatPanel } from "../components/ChatPanel";
import {
  useAcknowledgeAlert,
  useDoctorAlerts,
  useDoctorAppointments,
  useDoctorChat,
  useDoctorCompare,
  useDoctorMessages,
  useDoctorPatientReports,
  useDoctorPatients,
  useDoctorRadiologists,
  useDoctorReport,
  useReviewInsight,
  useSendDoctorMessage,
} from "../api/hooks";
import type { ApiError } from "../api/client";
import type { ChatMessage } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export function DoctorDashboard() {
  const { user } = useAuth();
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [compareA, setCompareA] = useState<number | null>(null);
  const [compareB, setCompareB] = useState<number | null>(null);
  const [ackingId, setAckingId] = useState<number | null>(null);
  const [chatLog, setChatLog] = useState<ChatMessage[]>([]);

  const alertsQuery = useDoctorAlerts();
  const patientsQuery = useDoctorPatients();
  const appointmentsQuery = useDoctorAppointments();
  const radiologistsQuery = useDoctorRadiologists();
  const patientReportsQuery = useDoctorPatientReports(selectedPatientId);
  const reportDetailQuery = useDoctorReport(selectedReportId);
  const compareQuery = useDoctorCompare(compareA, compareB);
  const messagesQuery = useDoctorMessages(selectedPatientId);

  const ackMutation = useAcknowledgeAlert();
  const reviewMutation = useReviewInsight();
  const sendMessageMutation = useSendDoctorMessage(selectedPatientId);
  const chatMutation = useDoctorChat();

  const selectedPatient = useMemo(
    () => patientsQuery.data?.find((p) => p.id === selectedPatientId),
    [patientsQuery.data, selectedPatientId],
  );

  function selectPatient(id: number) {
    setSelectedPatientId(id);
    setSelectedReportId(null);
    setCompareA(null);
    setCompareB(null);
    setChatLog([]);
  }

  function handleAcknowledge(id: number) {
    setAckingId(id);
    ackMutation.mutate(id, {
      onSettled: () => setAckingId(null),
      onError: (err) => toast.error((err as ApiError).message || "Could not acknowledge alert"),
    });
  }

  function handleReview(payload: { action: "validated" | "modified" | "finalized"; comments: string }) {
    if (!reportDetailQuery.data?.insight || selectedReportId == null) return;
    reviewMutation.mutate(
      { insightId: reportDetailQuery.data.insight.id, reportId: selectedReportId, ...payload },
      {
        onSuccess: () => toast.success(`Insight marked ${payload.action}.`),
        onError: (err) => toast.error((err as ApiError).message || "Review failed"),
      },
    );
  }

  function handleSendMessage(payload: { recipient_user_id: number; body: string }) {
    sendMessageMutation.mutate(payload, {
      onError: (err) => toast.error((err as ApiError).message || "Message failed"),
    });
  }

  function handleSendChat(question: string) {
    if (!selectedPatientId) return;
    setChatLog((log) => [...log, { role: "user", content: question }]);
    chatMutation.mutate(
      { patient_id: selectedPatientId, question },
      {
        onSuccess: (res) => setChatLog((log) => [...log, { role: "assistant", content: res.answer }]),
        onError: (err) => toast.error((err as ApiError).message || "Chat failed"),
      },
    );
  }

  return (
    <AppShell title="Doctor Dashboard" subtitle="Patient reports, AI insights, and clinical review">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
        <div className="space-y-6">
          <Panel title="Alerts" icon={<AlertTriangle className="h-4 w-4 text-red-500" />}>
            <AlertsPanel
              alerts={alertsQuery.data}
              isLoading={alertsQuery.isLoading}
              onAcknowledge={handleAcknowledge}
              acknowledgingId={ackingId}
              onSelectPatient={selectPatient}
              selectedPatientId={selectedPatientId}
            />
          </Panel>

          <Panel title="Select patient" icon={<Users className="h-4 w-4 text-brand-600" />}>
            <PatientSelector
              patients={patientsQuery.data}
              patientsLoading={patientsQuery.isLoading}
              appointments={appointmentsQuery.data}
              appointmentsLoading={appointmentsQuery.isLoading}
              selectedPatientId={selectedPatientId}
              onSelectPatient={selectPatient}
            />
          </Panel>

          <Panel
            title="Reports for selected patient"
            action={
              selectedPatient ? (
                <span className="text-xs font-medium text-slate-400">{selectedPatient.full_name}</span>
              ) : undefined
            }
          >
            {selectedPatientId == null ? (
              <p className="py-4 text-center text-sm text-slate-400">Select a patient.</p>
            ) : (
              <ReportList
                reports={patientReportsQuery.data}
                selectedId={selectedReportId}
                onSelect={setSelectedReportId}
                isLoading={patientReportsQuery.isLoading}
                emptyLabel="No reports for this patient."
                pageSize={5}
              />
            )}
          </Panel>
        </div>

        <div className="space-y-6">
          <SelectedPatientBanner patient={selectedPatient} />

          <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[1fr_380px]">
            <div className="space-y-6">
              <Panel title="Report detail & AI audit trail">
                <DoctorReportDetail
                  detail={reportDetailQuery.data}
                  isLoading={reportDetailQuery.isFetching}
                  onReview={handleReview}
                  isReviewPending={reviewMutation.isPending}
                />
              </Panel>

              <Panel title="Compare reports">
                <CompareReportsPanel
                  reports={patientReportsQuery.data}
                  a={compareA}
                  b={compareB}
                  onChangeA={setCompareA}
                  onChangeB={setCompareB}
                  result={compareQuery.data}
                  isFetching={compareQuery.isFetching}
                />
              </Panel>
            </div>

            <div className="space-y-6">
              <Panel title="AI Clinical Assistant" icon={<MessageCircle className="h-4 w-4 text-brand-600" />}>
                <ChatPanel
                  messages={chatLog}
                  onSend={handleSendChat}
                  isPending={chatMutation.isPending}
                  placeholder="Ask about the selected patient…"
                  disabled={selectedPatientId == null}
                  disabledHint="Select a patient to ask about their reports."
                />
              </Panel>

              <Panel title="Message radiologist" icon={<MessagesSquare className="h-4 w-4 text-brand-600" />}>
                {selectedPatientId == null ? (
                  <p className="py-4 text-center text-sm text-slate-400">Select a patient to view messages.</p>
                ) : (
                  <MessagesPanel
                    messages={messagesQuery.data}
                    currentUserId={user!.user_id}
                    recipients={radiologistsQuery.data}
                    onSend={(p) => handleSendMessage({ recipient_user_id: p.recipient_user_id, body: p.body })}
                    isPending={sendMessageMutation.isPending}
                  />
                )}
              </Panel>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
