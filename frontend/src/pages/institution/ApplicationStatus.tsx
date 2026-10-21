import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  RefreshCw,
  Download,
  AlertTriangle,
  X,
  CheckCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { DOC_TYPES_ALL } from '@/lib/constants';
import { PageSpinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { ValidationScoreRing } from '@/components/shared/ValidationScoreRing';
import { DocumentUploadCard } from '@/components/shared/DocumentUploadCard';
import { SeverityBadge } from '@/components/shared/SeverityBadge';
import type { DocType, ApplicationAlert, Document } from '@/lib/types';

function AlertBanner({
  alert,
  onDismiss,
}: {
  alert: ApplicationAlert;
  onDismiss: () => void;
}) {
  const colorMap = {
    HIGH: 'bg-danger-50 border-danger-200 text-danger-800',
    MEDIUM: 'bg-warning-50 border-warning-200 text-warning-800',
    LOW: 'bg-blue-50 border-blue-200 text-blue-800',
  };
  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 rounded-xl border ${colorMap[alert.severity]}`}
    >
      <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
      <div className="flex-1 text-sm">
        <span className="font-semibold">{alert.alert_type.replace(/_/g, ' ')}: </span>
        {alert.message}
      </div>
      <button onClick={onDismiss} className="flex-shrink-0 opacity-60 hover:opacity-100">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export default function ApplicationStatus() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());
  const [uploadingDoc, setUploadingDoc] = useState<DocType | null>(null);

  const { data: report, isLoading } = useQuery({
    queryKey: ['application-report', id],
    queryFn: () => api.applications.getValidationReport(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.application?.status;
      return status === 'UNDER_VALIDATION' ? 5000 : false;
    },
  });

  const validateMutation = useMutation({
    mutationFn: () => api.applications.validate(id!),
    onSuccess: () => {
      toast.success('Re-validation started');
      queryClient.invalidateQueries({ queryKey: ['application-report', id] });
    },
    onError: () => toast.error('Failed to trigger re-validation'),
  });

  const handleUpload = async (docType: DocType, file: File) => {
    if (!id) return;
    setUploadingDoc(docType);
    try {
      await api.documents.upload(id, docType, file);
      toast.success('Document uploaded');
      queryClient.invalidateQueries({ queryKey: ['application-report', id] });
    } catch {
      toast.error('Upload failed');
    } finally {
      setUploadingDoc(null);
    }
  };

  const handleDownloadReport = async () => {
    if (!id) return;
    try {
      const blob = await api.applications.generateReport(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `application-${id}-report.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Failed to download report');
    }
  };

  if (isLoading || !report) return <PageSpinner />;

  const { application, findings, documents, alerts } = report;
  const activeAlerts = (alerts ?? []).filter(
    (a) => !a.dismissed && !dismissedAlerts.has(a.id)
  );
  const failFindings = (findings ?? []).filter((f) => f.status === 'FAIL');
  const docMap: Partial<Record<DocType, Document>> = {};
  (documents ?? []).forEach((d) => {
    docMap[d.doc_type] = d;
  });

  const statusColorMap: Record<string, string> = {
    DRAFT: 'neutral',
    SUBMITTED: 'info',
    UNDER_VALIDATION: 'info',
    VALIDATION_COMPLETE: 'info',
    UNDER_REVIEW: 'primary',
    SENT_FOR_RECTIFICATION: 'warning',
    APPROVED_FOR_PROCESSING: 'success',
    ESCALATED: 'warning',
    REJECTED: 'danger',
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <button
            onClick={() => navigate('/institution')}
            className="mt-1 p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-gray-900">
                Application #{application.id.slice(0, 8)}
              </h1>
              <Badge
                variant={(statusColorMap[application.status] as 'neutral') ?? 'neutral'}
              >
                {application.status.replace(/_/g, ' ')}
              </Badge>
            </div>
            <p className="text-sm text-gray-500 mt-0.5">
              {application.institution_name} · Submitted{' '}
              {formatDate(application.submitted_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw className="h-4 w-4" />}
            onClick={() => validateMutation.mutate()}
            loading={validateMutation.isPending}
          >
            Re-validate
          </Button>
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Download className="h-4 w-4" />}
            onClick={handleDownloadReport}
          >
            Download Report
          </Button>
        </div>
      </div>

      {/* Score (centered) */}
      <Card>
        <div className="flex flex-col items-center py-4">
          <ValidationScoreRing score={application.validation_score} size="lg" />
          {application.status === 'UNDER_VALIDATION' && (
            <div className="mt-3 flex items-center gap-2 text-sm text-blue-600">
              <RefreshCw className="h-4 w-4 animate-spin" />
              AI validation in progress...
            </div>
          )}
        </div>
      </Card>

      {/* Alerts */}
      {activeAlerts.length > 0 && (
        <div className="space-y-2">
          {activeAlerts.map((alert) => (
            <AlertBanner
              key={alert.id}
              alert={alert}
              onDismiss={() =>
                setDismissedAlerts((prev) => new Set([...prev, alert.id]))
              }
            />
          ))}
        </div>
      )}

      {/* Document checklist */}
      <Card>
        <CardHeader>
          <CardTitle>Document Checklist</CardTitle>
          <span className="text-sm text-gray-500">
            {application.documents_complete}/{application.total_documents} complete
          </span>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {DOC_TYPES_ALL.map((docType) => (
              <DocumentUploadCard
                key={docType}
                docType={docType}
                document={docMap[docType] ?? null}
                onUpload={handleUpload}
                uploading={uploadingDoc === docType}
                readOnly={
                  application.status !== 'DRAFT' &&
                  application.status !== 'SENT_FOR_RECTIFICATION'
                }
              />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Deficiency list */}
      {failFindings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Deficiencies Identified</CardTitle>
            <Badge variant="danger">{failFindings.length} issues</Badge>
          </CardHeader>
          <CardContent>
            <ol className="space-y-3">
              {failFindings.map((finding, idx) => (
                <li key={finding.id} className="flex gap-3">
                  <span className="flex-shrink-0 h-6 w-6 rounded-full bg-danger-100 text-danger-700 text-xs font-bold flex items-center justify-center mt-0.5">
                    {idx + 1}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <SeverityBadge severity={finding.severity} />
                      <span className="text-xs text-gray-400 font-mono">{finding.rule_id}</span>
                    </div>
                    <p className="text-sm text-gray-800">{finding.message}</p>
                    {finding.guidance && (
                      <p className="text-xs text-blue-600 mt-1 flex items-start gap-1">
                        <span>💡</span>
                        <span>{finding.guidance}</span>
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      {failFindings.length === 0 && application.validation_score !== null && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-success-50 border border-success-200 text-success-700">
          <CheckCircle className="h-5 w-5" />
          <p className="text-sm font-medium">No deficiencies found! Your application looks good.</p>
        </div>
      )}
    </div>
  );
}
