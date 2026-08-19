import { toast } from "sonner";
import { MessagesSquare, UploadCloud } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { Panel } from "../components/Panel";
import { UploadReportForm } from "../components/UploadReportForm";
import { ReportList } from "../components/ReportList";
import { MessagesPanel } from "../components/MessagesPanel";
import {
  useRadiologistDoctors,
  useRadiologistMessages,
  useRadiologistPatients,
  useRadiologistUpload,
  useRadiologistUploads,
  useSendRadiologistMessage,
} from "../api/hooks";
import type { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function RadiologistDashboard() {
  const { user } = useAuth();
  const patientsQuery = useRadiologistPatients();
  const doctorsQuery = useRadiologistDoctors();
  const uploadsQuery = useRadiologistUploads();
  const messagesQuery = useRadiologistMessages(null);

  const uploadMutation = useRadiologistUpload();
  const sendMessageMutation = useSendRadiologistMessage();

  async function handleUpload(formData: FormData) {
    try {
      await uploadMutation.mutateAsync(formData);
      toast.success("Uploaded — analysis in progress.");
    } catch (err) {
      toast.error((err as ApiError).message || "Upload failed");
      throw err;
    }
  }

  function handleSendMessage(payload: { recipient_user_id: number; patient_id?: number; body: string }) {
    if (payload.patient_id == null) return;
    sendMessageMutation.mutate(
      { recipient_user_id: payload.recipient_user_id, patient_id: payload.patient_id, body: payload.body },
      { onError: (err) => toast.error((err as ApiError).message || "Message failed") },
    );
  }

  return (
    <AppShell title="Radiologist / Lab Dashboard" subtitle="Upload diagnostic reports and coordinate with doctors">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[420px_1fr]">
        <div>
          <Panel title="Upload patient report" icon={<UploadCloud className="h-4 w-4 text-brand-600" />}>
            <UploadReportForm
              patients={patientsQuery.data ?? []}
              onSubmit={handleUpload}
              isPending={uploadMutation.isPending}
            />
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title="My uploads">
            <ReportList
              reports={uploadsQuery.data}
              selectedId={null}
              onSelect={() => {}}
              isLoading={uploadsQuery.isLoading}
              showPatientName
              emptyLabel="No uploads yet."
              pageSize={5}
            />
          </Panel>

          <Panel title="Message doctor" icon={<MessagesSquare className="h-4 w-4 text-brand-600" />}>
            <MessagesPanel
              messages={messagesQuery.data}
              currentUserId={user!.user_id}
              recipients={doctorsQuery.data}
              patients={patientsQuery.data}
              onSend={handleSendMessage}
              isPending={sendMessageMutation.isPending}
            />
          </Panel>
        </div>
      </div>
    </AppShell>
  );
}
