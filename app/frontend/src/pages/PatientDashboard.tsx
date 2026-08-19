import { useState } from "react";
import { toast } from "sonner";
import { CalendarPlus, MessageCircle, ShieldAlert, UploadCloud } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { Panel } from "../components/Panel";
import { ReportList } from "../components/ReportList";
import { UploadReportForm } from "../components/UploadReportForm";
import { PatientReportDetail } from "../components/PatientReportDetail";
import { CompareReportsPanel } from "../components/CompareReportsPanel";
import { ChatPanel } from "../components/ChatPanel";
import { HistoryPanel } from "../components/HistoryPanel";
import { BookAppointmentPanel } from "../components/BookAppointmentPanel";
import {
  useAddAllergy,
  usePatientAlerts,
  usePatientChat,
  usePatientChatHistory,
  usePatientCompare,
  usePatientHistory,
  usePatientReport,
  usePatientReports,
  useUploadPatientReport,
} from "../api/hooks";
import type { ApiError } from "../api/client";

export function PatientDashboard() {
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [compareA, setCompareA] = useState<number | null>(null);
  const [compareB, setCompareB] = useState<number | null>(null);

  const reportsQuery = usePatientReports();
  const reportDetailQuery = usePatientReport(selectedReportId);
  const historyQuery = usePatientHistory();
  const chatHistoryQuery = usePatientChatHistory();
  usePatientAlerts();

  const uploadMutation = useUploadPatientReport();
  const addAllergyMutation = useAddAllergy();
  const chatMutation = usePatientChat();
  const compareQuery = usePatientCompare(compareA, compareB);

  async function handleUpload(formData: FormData) {
    try {
      await uploadMutation.mutateAsync(formData);
      toast.success("Uploaded — analysis in progress.");
    } catch (err) {
      toast.error((err as ApiError).message || "Upload failed");
      throw err;
    }
  }

  function handleSendChat(question: string) {
    chatMutation.mutate(question, {
      onError: (err) => toast.error((err as ApiError).message || "Message failed"),
    });
  }

  return (
    <AppShell title="Patient Dashboard" subtitle="Your reports, insights, and care team">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
        <div className="space-y-6">
          <Panel title="Upload report" icon={<UploadCloud className="h-4 w-4 text-brand-600" />}>
            <UploadReportForm onSubmit={handleUpload} isPending={uploadMutation.isPending} />
          </Panel>

          <Panel title="My reports">
            <ReportList
              reports={reportsQuery.data}
              selectedId={selectedReportId}
              onSelect={setSelectedReportId}
              isLoading={reportsQuery.isLoading}
            />
          </Panel>

          <Panel title="Medical history" icon={<ShieldAlert className="h-4 w-4 text-brand-600" />}>
            <HistoryPanel
              allergies={historyQuery.data?.allergies}
              medicalHistory={historyQuery.data?.medical_history}
              onAddAllergy={(payload) =>
                addAllergyMutation.mutate(payload, {
                  onError: (err) => toast.error((err as ApiError).message || "Could not add allergy"),
                })
              }
              isAddingAllergy={addAllergyMutation.isPending}
            />
          </Panel>
        </div>

        <div className="space-y-6">
          <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[1fr_380px]">
            <div className="space-y-6">
              <Panel title="Report detail">
                <PatientReportDetail detail={reportDetailQuery.data} isLoading={reportDetailQuery.isFetching} />
              </Panel>

              <Panel title="Compare reports">
                <CompareReportsPanel
                  reports={reportsQuery.data}
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
              <Panel title="Book appointment" icon={<CalendarPlus className="h-4 w-4 text-brand-600" />}>
                <BookAppointmentPanel />
              </Panel>

              <Panel title="AI Health Assistant" icon={<MessageCircle className="h-4 w-4 text-brand-600" />}>
                <ChatPanel
                  messages={[
                    ...(chatHistoryQuery.data ?? []),
                    ...(chatMutation.isPending && chatMutation.variables
                      ? [{ role: "user" as const, content: chatMutation.variables }]
                      : []),
                  ]}
                  onSend={handleSendChat}
                  isPending={chatMutation.isPending}
                  placeholder="Ask about your results…"
                />
              </Panel>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
