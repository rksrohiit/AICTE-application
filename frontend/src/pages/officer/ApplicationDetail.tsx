import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  FileText,
  AlertTriangle,
  CheckCircle,
  Clock,
  ShieldAlert,
  ArrowLeft,
  Download,
  Play,
  ListFilter,
  RefreshCw,
  QrCode,
  ExternalLink,
} from 'lucide-react';
import toast from 'react-hot-toast';

import { api } from '@/lib/api';
import { formatDateTime, formatDate, formatFileSize, getDocTypeLabel } from '@/lib/utils';
import type {
  Application,
  ValidationReport,
  ApplicationAlert,
  AuditLog,
  Document,
  OfficerAction,
  FindingSeverity,
  PublicVerificationData,
  ChecklistResponse,
  WorkflowStatus,
} from '@/lib/types';

import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Modal } from '@/components/ui/Modal';
import { Spinner } from '@/components/ui/Spinner';
import { ValidationScoreRing } from '@/components/shared/ValidationScoreRing';
import { FindingCard } from '@/components/shared/FindingCard';
import { AnomalyCard } from '@/components/shared/AnomalyCard';
import { VerificationStatusChip } from '@/components/shared/VerificationStatusChip';
import { AuditTimeline } from '@/components/shared/AuditTimeline';
import { InfrastructureScrutinyPanel } from '@/components/shared/InfrastructureScrutinyPanel';
import { CampusPlotBoundaryPanel } from '@/components/shared/CampusPlotBoundaryPanel';

type TabKey =
  | 'overview'
  | 'documents'
  | 'checklist'
  | 'infrastructure'
  | 'findings'
  | 'anomalies'
  | 'verification'
  | 'audit';

export default function ApplicationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [application, setApplication] = useState<Application | null>(null);
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [alerts, setAlerts] = useState<ApplicationAlert[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);

  // Officer action state
  const [actionNotes, setActionNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [selectedAction, setSelectedAction] = useState<OfficerAction | null>(null);

  // Finding filter
  const [severityFilter, setSeverityFilter] = useState<'ALL' | FindingSeverity>('ALL');

  // Public QR modal state
  const [qrModalOpen, setQrModalOpen] = useState(false);
  const [qrData, setQrData] = useState<PublicVerificationData | null>(null);
  const [qrLoading, setQrLoading] = useState(false);

  const handleOpenQrModal = async () => {
    if (!id) return;
    setQrModalOpen(true);
    setQrLoading(true);
    try {
      const data = await api.publicVerify.get(id);
      setQrData(data);
    } catch {
      toast.error('Failed to load public verification record');
    } finally {
      setQrLoading(false);
    }
  };

  const loadData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const appData = await api.applications.get(id);
      setApplication(appData);

      // Attempt to load documents
      try {
        const docs = await api.documents.list(id);
        setDocuments(docs);
      } catch {
        // Ignored
      }

      // Attempt to load alerts
      try {
        const alertList = await api.applications.getAlerts(id);
        setAlerts(alertList);
      } catch {
        // Ignored
      }

      // Attempt to load audit logs
      try {
        const logs = await api.applications.getAudit(id);
        setAuditLogs(logs);
      } catch {
        // Ignored
      }

      // Attempt to load validation report
      try {
        const rep = await api.applications.getValidationReport(id);
        setReport(rep);
      } catch {
        // No report yet
      }
      try {
        setChecklist(await api.applications.getChecklist(id));
      } catch {
        setChecklist(null);
      }
      try {
        setWorkflowStatus(await api.applications.getWorkflowStatus(id));
      } catch {
        setWorkflowStatus(null);
      }
    } catch {
      toast.error('Failed to load application details');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!application) return;
    const processing = workflowStatus?.is_processing ?? (
      application.status === 'UNDER_VALIDATION' ||
      documents.some((document) => document.ocr_status === 'PENDING' || document.ocr_status === 'PROCESSING')
    );
    if (!processing) return;

    const interval = window.setInterval(() => {
      void loadData();
    }, 4000);
    return () => window.clearInterval(interval);
  }, [application, documents, workflowStatus, loadData]);

  const handleResolveAlert = async (alertId: string) => {
    if (!id) return;
    try {
      await api.applications.resolveAlert(id, alertId);
      toast.success('Alert resolved and recorded in the audit trail');
      await loadData();
    } catch {
      toast.error('Failed to resolve alert');
    }
  };

  const handleReviewAnomaly = async (anomalyId: string) => {
    if (!id) return;
    try {
      await api.applications.reviewAnomaly(id, anomalyId, 'Reviewed by officer');
      toast.success('Anomaly review recorded');
      await loadData();
    } catch {
      toast.error('Failed to record anomaly review');
    }
  };

  const handleTriggerValidate = async () => {
    if (!id) return;
    setValidating(true);
    try {
      await api.applications.validate(id);
      toast.success('Validation process queued. Live status updates are enabled.');
      await loadData();
      setValidating(false);
    } catch {
      toast.error('Failed to trigger validation');
      setValidating(false);
    }
  };

  const handleDownloadReport = async () => {
    if (!id) return;
    try {
      const blob = await api.applications.generateReport(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `AICTE_Validation_Report_${id.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Report downloaded');
    } catch {
      toast.error('Could not download report');
    }
  };

  const handleInitiateAction = (action: OfficerAction) => {
    setSelectedAction(action);
    setConfirmModalOpen(true);
  };

  const handleConfirmAction = async () => {
    if (!id || !selectedAction) return;
    setActionLoading(true);
    try {
      await api.applications.takeAction(id, selectedAction, actionNotes);
      toast.success(`Action applied: ${selectedAction.replace(/_/g, ' ')}`);
      setConfirmModalOpen(false);
      setActionNotes('');
      setSelectedAction(null);
      await loadData();
    } catch {
      toast.error('Failed to apply officer action');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && !application) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Spinner size="lg" />
        <p className="mt-4 text-sm text-gray-500">Loading application details...</p>
      </div>
    );
  }

  if (!application) {
    return (
      <div className="text-center py-16">
        <h2 className="text-xl font-semibold text-gray-700">Application not found</h2>
        <Button className="mt-4" onClick={() => navigate('/officer')}>
          Back to Queue
        </Button>
      </div>
    );
  }

  const findingsList = report?.findings ?? [];
  const anomaliesList = report?.anomalies ?? [];
  const verificationsList = report?.verifications ?? [];
  const filteredFindings =
    severityFilter === 'ALL'
      ? findingsList
      : findingsList.filter((f) => f.severity === severityFilter);

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'documents', label: 'Documents', count: documents.length },
    { key: 'checklist', label: 'Checklist', count: checklist?.items.length },
    { key: 'infrastructure', label: '🏛️ Infrastructure & Lab Scrutiny' },
    { key: 'findings', label: 'Findings', count: findingsList.length },
    { key: 'anomalies', label: 'Anomalies', count: anomaliesList.length },
    { key: 'verification', label: 'Verification', count: verificationsList.length },
    { key: 'audit', label: 'Audit Trail', count: auditLogs.length },
  ];

  return (
    <div className="space-y-6 pb-24">
      {/* Top Breadcrumb & Action bar */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <button
          onClick={() => navigate('/officer')}
          className="flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Application Queue
        </button>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={loadData}
            title="Refresh application data"
          >
            <RefreshCw className="h-4 w-4 mr-1.5" />
            Refresh
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleOpenQrModal}
            title="Public Verification QR Code"
          >
            <QrCode className="h-4 w-4 mr-1.5 text-indigo-600" />
            Public QR
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleDownloadReport}
          >
            <Download className="h-4 w-4 mr-1.5" />
            Export PDF
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleTriggerValidate}
            loading={validating}
          >
            <Play className="h-4 w-4 mr-1.5" />
            Run Validation
          </Button>
        </div>
      </div>

      {/* Hero Header Card */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-mono text-sm text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                {application.id}
              </span>
              <Badge variant="neutral">{application.application_type.replace(/_/g, ' ')}</Badge>
              <Badge
                variant={
                  application.status.includes('APPROV')
                    ? 'success'
                    : application.status.includes('REJECT')
                    ? 'danger'
                    : application.status.includes('RECTIF')
                    ? 'warning'
                    : 'info'
                }
              >
                {application.status.replace(/_/g, ' ')}
              </Badge>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{application.institution_name}</h1>
            <p className="text-sm text-gray-500">
              Academic Year: <span className="font-medium text-gray-700">{application.academic_year || '2024-25'}</span> • Submitted:{' '}
              <span className="font-medium text-gray-700">
                {application.submitted_at ? formatDate(application.submitted_at) : 'Draft'}
              </span>
            </p>
          </div>

          <div className="flex items-center gap-6 self-start md:self-auto border-t md:border-t-0 md:border-l border-gray-200 pt-4 md:pt-0 md:pl-6">
            <ValidationScoreRing score={application.validation_score} size="md" />
            <div className="text-xs text-gray-500 space-y-1">
              <p>
                Docs uploaded:{' '}
                <span className="font-semibold text-gray-800">
                  {application.documents_complete || documents.length}/8
                </span>
              </p>
              <p>
                Anomalies:{' '}
                <span className={`font-semibold ${anomaliesList.length > 0 ? 'text-danger-600' : 'text-gray-800'}`}>
                  {anomaliesList.length}
                </span>
              </p>
              <p>
                Findings:{' '}
                <span className="font-semibold text-gray-800">
                  {findingsList.length}
                </span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Alerts Bar (if any) */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((al) => (
            <div
              key={al.id}
              className={`flex items-start gap-3 p-3.5 rounded-xl border text-sm ${
                al.severity === 'HIGH'
                  ? 'bg-danger-50 border-danger-200 text-danger-900'
                  : 'bg-warning-50 border-warning-200 text-warning-900'
              }`}
            >
              <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5 text-current" />
              <div className="flex-1">
                <span className="font-semibold">[{al.alert_type}]</span> {al.message}
              </div>
              {!al.is_resolved && (
                <Button variant="secondary" size="sm" onClick={() => handleResolveAlert(al.id)}>
                  Resolve
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      {activeTab === 'checklist' && (
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <div className="flex items-center justify-between gap-4 mb-4">
              <div>
                <h2 className="font-semibold text-gray-900">Configurable compliance checklist</h2>
                <p className="text-xs text-gray-500 mt-1">
                  Rules version {checklist?.rules_version ?? '—'} · Results are decision-support evidence for officer review.
                </p>
              </div>
              <span className="text-sm font-semibold text-primary-700">
                {checklist?.completion_percent ?? 0}% evaluated
              </span>
            </div>
            {!checklist ? (
              <p className="text-sm text-gray-500">Checklist is not available yet.</p>
            ) : (
              <div className="space-y-2">
                {checklist.items.map((item) => (
                  <div key={item.rule_id} className="border border-gray-100 rounded-lg p-3 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-gray-400">{item.rule_id}</span>
                        <span className="font-medium text-sm text-gray-800">{item.rule_name}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{item.message}</p>
                      {item.evidence && <p className="text-xs text-gray-400 mt-1">Evidence: {item.evidence}</p>}
                    </div>
                    <Badge variant={item.status === 'PASS' ? 'success' : item.status === 'FAIL' ? 'danger' : item.status === 'WARN' ? 'warning' : 'neutral'}>
                      {item.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-6 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 whitespace-nowrap transition-colors ${
                activeTab === tab.key
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
              {typeof tab.count === 'number' && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    activeTab === tab.key
                      ? 'bg-primary-50 text-primary-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Contents */}
      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Validation Run Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {report?.validation_run ? (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                    <div className="p-3 bg-gray-50 rounded-xl">
                      <p className="text-xs text-gray-500">Run Status</p>
                      <p className="text-base font-bold text-gray-800">
                        {report.validation_run.status}
                      </p>
                    </div>
                    <div className="p-3 bg-danger-50 rounded-xl">
                      <p className="text-xs text-danger-600">High Deficiencies</p>
                      <p className="text-base font-bold text-danger-700">
                        {report.validation_run.high_severity_count}
                      </p>
                    </div>
                    <div className="p-3 bg-warning-50 rounded-xl">
                      <p className="text-xs text-warning-600">Medium Warnings</p>
                      <p className="text-base font-bold text-warning-700">
                        {report.validation_run.medium_severity_count}
                      </p>
                    </div>
                    <div className="p-3 bg-blue-50 rounded-xl">
                      <p className="text-xs text-blue-600">Low Observations</p>
                      <p className="text-base font-bold text-blue-700">
                        {report.validation_run.low_severity_count}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-6 text-gray-500">
                    <p>No validation has been executed yet.</p>
                    <Button
                      variant="primary"
                      size="sm"
                      className="mt-3"
                      onClick={handleTriggerValidate}
                    >
                      <Play className="h-4 w-4 mr-1.5" />
                      Run Validation Now
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Key Observations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {findingsList.length === 0 ? (
                  <p className="text-sm text-gray-500">No rule findings reported.</p>
                ) : (
                  findingsList.slice(0, 3).map((f) => <FindingCard key={f.id} finding={f} />)
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Application Info</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-3">
                <div>
                  <p className="text-xs text-gray-400">Application Type</p>
                  <p className="font-medium text-gray-800">
                    {application.application_type.replace(/_/g, ' ')}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Created At</p>
                  <p className="font-medium text-gray-800">{formatDateTime(application.created_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Last Modified</p>
                  <p className="font-medium text-gray-800">{formatDateTime(application.updated_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Institution ID</p>
                  <p className="font-mono text-xs text-gray-600 break-all">
                    {application.institution_id}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* TAB 2: DOCUMENTS */}
      {activeTab === 'documents' && (
        <div className="space-y-4">
          {documents.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <FileText className="h-10 w-10 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">No documents uploaded for this application.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-xs font-semibold text-primary-700 bg-primary-50 px-2 py-0.5 rounded">
                        {getDocTypeLabel(doc.doc_type)}
                      </span>
                      <h4 className="text-sm font-semibold text-gray-900 mt-1">{doc.file_name}</h4>
                    </div>
                    <Badge
                      variant={
                        doc.ocr_status === 'COMPLETE'
                          ? 'success'
                          : doc.ocr_status === 'PROCESSING'
                          ? 'warning'
                          : 'danger'
                      }
                    >
                      OCR: {doc.ocr_status}
                    </Badge>
                  </div>

                  <div className="text-xs text-gray-500 space-y-1">
                    <p>Size: {formatFileSize(doc.file_size)}</p>
                    <p>Uploaded: {formatDateTime(doc.uploaded_at)}</p>
                    <p className="font-mono text-[10px] text-gray-400 truncate">
                      SHA256: {doc.file_hash || 'Pending computation'}
                    </p>
                  </div>

                  {doc.ocr_data && (
                    <details className="text-xs border-t border-gray-100 pt-2 text-gray-600">
                      <summary className="cursor-pointer font-medium text-primary-600 hover:text-primary-800">
                        View Extracted Fields
                      </summary>
                      <pre className="mt-2 bg-gray-50 p-2 rounded text-[11px] font-mono overflow-x-auto max-h-40">
                        {JSON.stringify(doc.ocr_data, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB: INFRASTRUCTURE & LAB SCRUTINY */}
      {activeTab === 'infrastructure' && application && (
        <div className="space-y-8">
          {/* 1. Campus Plot Boundary Geodesic & Satellite Scrutiny */}
          <CampusPlotBoundaryPanel
            applicationId={application.id}
          />

          {/* 2. Photo EXIF Geotag, ELA Tampering & Lab Equipment Detection */}
          <InfrastructureScrutinyPanel
            applicationId={application.id}
            institutionName={application.institution_name}
          />
        </div>
      )}

      {/* TAB 3: FINDINGS */}
      {activeTab === 'findings' && (
        <div className="space-y-4">
          {/* Severity filter bar */}
          <div className="flex items-center justify-between flex-wrap gap-2 bg-white p-3 rounded-xl border border-gray-200">
            <div className="flex items-center gap-2 text-xs font-medium text-gray-600">
              <ListFilter className="h-4 w-4" />
              <span>Filter by Severity:</span>
            </div>
            <div className="flex items-center gap-1.5">
              {(['ALL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors ${
                    severityFilter === sev
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {filteredFindings.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <CheckCircle className="h-10 w-10 text-success-500 mx-auto mb-2" />
              <p className="text-sm text-gray-500">
                {findingsList.length === 0
                  ? 'No validation findings have been recorded yet.'
                  : 'No findings matching this severity filter.'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredFindings.map((f) => (
                <FindingCard key={f.id} finding={f} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: ANOMALIES */}
      {activeTab === 'anomalies' && (
        <div className="space-y-4">
          <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs p-3 rounded-xl flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 flex-shrink-0 text-amber-600" />
            <span>
              <b>Statutory Note:</b> Anomaly flags indicate preliminary computer vision / metadata inconsistencies. Each item requires human officer evaluation and does not constitute final proof of misconduct.
            </span>
          </div>

          {anomaliesList.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <CheckCircle className="h-10 w-10 text-success-500 mx-auto mb-2" />
              <p className="text-sm font-medium text-gray-700">No anomalies detected</p>
              <p className="text-xs text-gray-400 mt-1">
                Document hashes, dates, and cross-metadata appear consistent.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {anomaliesList.map((anom) => (
                <div key={anom.id} className="space-y-2">
                  <AnomalyCard anomaly={anom} />
                  {!anom.is_reviewed && (
                    <Button variant="secondary" size="sm" onClick={() => handleReviewAnomaly(anom.id)}>
                      Mark reviewed
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 5: VERIFICATION */}
      {activeTab === 'verification' && (
        <div className="space-y-4">
          {verificationsList.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <Clock className="h-10 w-10 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">No external source verifications recorded yet.</p>
            </div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-gray-700">
                  <thead className="bg-gray-50 text-gray-500 border-b border-gray-200 uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="py-3 px-4">Document</th>
                      <th className="py-3 px-4">Issuing Authority / Source</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Reference</th>
                      <th className="py-3 px-4">Verified At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {verificationsList.map((vr) => (
                      <tr key={vr.id} className="hover:bg-gray-50">
                        <td className="py-3 px-4 font-medium text-gray-900">
                          {getDocTypeLabel(vr.doc_type)}
                        </td>
                        <td className="py-3 px-4">{vr.source}</td>
                        <td className="py-3 px-4">
                          <VerificationStatusChip status={vr.status} />
                        </td>
                        <td className="py-3 px-4 font-mono text-gray-500">
                          {vr.reference_number || 'N/A'}
                        </td>
                        <td className="py-3 px-4 text-gray-500">
                          {vr.verified_at ? formatDateTime(vr.verified_at) : 'Pending'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 6: AUDIT TRAIL */}
      {activeTab === 'audit' && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <AuditTimeline
            logs={auditLogs}
            applicationId={application.id}
            onShowQr={handleOpenQrModal}
          />
        </div>
      )}

      {/* Sticky Officer Action Bottom Panel */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 shadow-lg z-20">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex-1 max-w-lg">
            <input
              type="text"
              placeholder="Add review notes (optional, recorded in permanent audit trail)..."
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              className="w-full text-xs px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleInitiateAction('SEND_FOR_RECTIFICATION')}
              className="text-amber-700 hover:bg-amber-50 border-amber-300"
            >
              Send for Rectification
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleInitiateAction('ESCALATE')}
              className="text-purple-700 hover:bg-purple-50 border-purple-300"
            >
              Escalate to Senior Authority
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => handleInitiateAction('REJECT')}
            >
              Reject
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleInitiateAction('APPROVE_FOR_PROCESSING')}
              className="bg-success-600 hover:bg-success-700 text-white"
            >
              Approve for Processing
            </Button>
          </div>
        </div>
      </div>

      {/* Action Confirmation Modal */}
      <Modal
        isOpen={confirmModalOpen}
        onClose={() => setConfirmModalOpen(false)}
        title="Confirm Officer Regulatory Action"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-700">
            Are you sure you want to perform the action{' '}
            <b className="text-primary-700">{selectedAction?.replace(/_/g, ' ')}</b> on this
            application?
          </p>

          {actionNotes && (
            <div className="bg-gray-50 border border-gray-200 p-3 rounded-lg text-xs text-gray-600">
              <span className="font-semibold block mb-1">Attached Notes:</span>
              {actionNotes}
            </div>
          )}

          <p className="text-xs text-gray-400">
            This action will be permanently recorded in the immutable audit log with your officer ID
            and timestamp.
          </p>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setConfirmModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant={selectedAction === 'REJECT' ? 'danger' : 'primary'}
              onClick={handleConfirmAction}
              loading={actionLoading}
            >
              Confirm & Apply
            </Button>
          </div>
        </div>
      </Modal>

      {/* Public Verification QR Code Modal */}
      <Modal
        isOpen={qrModalOpen}
        onClose={() => setQrModalOpen(false)}
        title="Public Verification QR Code & Cryptographic Certificate"
      >
        <div className="space-y-4 text-center">
          {qrLoading ? (
            <div className="py-8">
              <Spinner size="lg" className="mx-auto" />
              <p className="text-xs text-gray-500 mt-2">Loading verifiable certificate & QR...</p>
            </div>
          ) : qrData ? (
            <div className="space-y-4">
              <div className="p-4 bg-white rounded-2xl border border-gray-200 shadow-sm inline-block">
                <img
                  src={qrData.qr_code_data_uri}
                  alt="Public Verification QR Code"
                  className="w-44 h-44 mx-auto object-contain"
                />
              </div>

              <div className="space-y-1 text-xs">
                <h4 className="font-bold text-gray-900 text-sm">{qrData.institution_name}</h4>
                <p className="text-gray-500 font-mono text-[11px]">{qrData.application_id}</p>
                <div className="pt-1">
                  <Badge variant={qrData.chain_integrity.is_valid ? 'success' : 'danger'}>
                    {qrData.chain_integrity.is_valid
                      ? '✓ SHA-256 Hash Chain: Intact'
                      : '✗ Hash Chain Compromised'}
                  </Badge>
                </div>
              </div>

              <p className="text-[11px] text-gray-500 max-w-sm mx-auto leading-relaxed">
                Scan with any smartphone camera to inspect the immutable public decision ledger and verify EoA authenticity.
              </p>

              <div className="flex items-center justify-center gap-2 pt-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => window.open(`/verify/${qrData.application_id}`, '_blank')}
                >
                  <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                  Open Public Portal
                </Button>
                <Button variant="primary" size="sm" onClick={() => setQrModalOpen(false)}>
                  Close
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-xs text-red-500">Failed to load QR code</p>
          )}
        </div>
      </Modal>
    </div>
  );
}
