import mockApplications from './mockApplications.json';
import mockDocuments from './mockDocuments.json';
import mockValidationRuns from './mockValidationRuns.json';
import mockValidationFindings from './mockValidationFindings.json';
import mockAuditLogs from './mockAuditLogs.json';
import mockAlerts from './mockAlerts.json';
import mockVerifications from './mockVerifications.json';
import mockAnomalies from './mockAnomalies.json';
import type {
  Application,
  ValidationReport,
  ValidationRun,
  ValidationFinding,
  Document,
  AuditLog,
  ApplicationAlert,
  VerificationResult,
  AnomalyFlag,
  PublicVerificationData,
  OfficerAction,
} from './types';

const STORAGE_KEYS = {
  APPLICATIONS: 'aicte_demo_applications',
  DOCUMENTS: 'aicte_demo_documents',
  VALIDATION_RUNS: 'aicte_demo_validation_runs',
  FINDINGS: 'aicte_demo_findings',
  AUDIT_LOGS: 'aicte_demo_audit_logs',
  ALERTS: 'aicte_demo_alerts',
};

// Safe localStorage access
function getStored<T>(key: string, defaultVal: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return defaultVal;
    return JSON.parse(raw);
  } catch {
    return defaultVal;
  }
}

function setStored<T>(key: string, val: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch {
    // ignore quota errors
  }
}

export const realtimeChannel = typeof BroadcastChannel !== 'undefined'
  ? new BroadcastChannel('aicte_realtime_events')
  : null;

export const demoStore = {
  getApplications(): Application[] {
    return getStored<Application[]>(STORAGE_KEYS.APPLICATIONS, mockApplications as unknown as Application[]);
  },

  getApplication(id: string): Application | undefined {
    const apps = this.getApplications();
    const cleanId = id.replace(/-/g, '').toLowerCase();
    return apps.find((a) => a.id === id || a.id.replace(/-/g, '').toLowerCase() === cleanId);
  },

  updateApplication(id: string, updates: Partial<Application>): Application | undefined {
    const apps = this.getApplications();
    const cleanId = id.replace(/-/g, '').toLowerCase();
    let updatedApp: Application | undefined;

    const nextApps = apps.map((a) => {
      if (a.id === id || a.id.replace(/-/g, '').toLowerCase() === cleanId) {
        updatedApp = {
          ...a,
          ...updates,
          updated_at: new Date().toISOString(),
        };
        return updatedApp;
      }
      return a;
    });

    if (!updatedApp && apps.length > 0) {
      // If not found in list, create/append it
      updatedApp = {
        ...(apps[0] as Application),
        id,
        ...updates,
        updated_at: new Date().toISOString(),
      };
      nextApps.unshift(updatedApp);
    }

    setStored(STORAGE_KEYS.APPLICATIONS, nextApps);
    return updatedApp;
  },

  getDocuments(applicationId: string): Document[] {
    const allDocs = getStored<Document[]>(STORAGE_KEYS.DOCUMENTS, mockDocuments as unknown as Document[]);
    const cleanId = applicationId.replace(/-/g, '').toLowerCase();
    return allDocs.filter(
      (d) => d.application_id === applicationId || d.application_id?.replace(/-/g, '').toLowerCase() === cleanId
    );
  },

  getAuditLogs(applicationId: string): AuditLog[] {
    const allLogs = getStored<AuditLog[]>(STORAGE_KEYS.AUDIT_LOGS, mockAuditLogs as unknown as AuditLog[]);
    const cleanId = applicationId.replace(/-/g, '').toLowerCase();
    return allLogs.filter(
      (l) => l.application_id === applicationId || l.application_id?.replace(/-/g, '').toLowerCase() === cleanId
    );
  },

  addAuditLog(log: Partial<AuditLog> & { application_id: string; action: string }): AuditLog {
    const allLogs = getStored<AuditLog[]>(STORAGE_KEYS.AUDIT_LOGS, mockAuditLogs as unknown as AuditLog[]);
    const newLog: AuditLog = {
      id: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2),
      application_id: log.application_id,
      actor_id: log.actor_id || 'officer-demo-id',
      actor_name: log.actor_name || 'Shri Alok Kumar (Scrutiny Officer)',
      actor_role: log.actor_role || 'OFFICER',
      action: log.action,
      result: log.result || 'SUCCESS',
      notes: log.notes || null,
      created_at: new Date().toISOString(),
      prev_hash: '3a8f9c1b7e2d4f5a6b0c8e9f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b',
      entry_hash: 'd4f5a6b0c8e9f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6',
    };
    allLogs.unshift(newLog);
    setStored(STORAGE_KEYS.AUDIT_LOGS, allLogs);
    return newLog;
  },

  getAlerts(applicationId: string): ApplicationAlert[] {
    const allAlerts = getStored<ApplicationAlert[]>(STORAGE_KEYS.ALERTS, mockAlerts as unknown as ApplicationAlert[]);
    const cleanId = applicationId.replace(/-/g, '').toLowerCase();
    return allAlerts.filter(
      (a) => a.application_id === applicationId || a.application_id?.replace(/-/g, '').toLowerCase() === cleanId
    );
  },

  getValidationReport(applicationId: string): ValidationReport {
    const app = this.getApplication(applicationId);
    const cleanId = applicationId.replace(/-/g, '').toLowerCase();

    const runs = getStored<ValidationRun[]>(STORAGE_KEYS.VALIDATION_RUNS, mockValidationRuns as unknown as ValidationRun[]);
    let run = runs.find(
      (r) => r.application_id === applicationId || r.application_id?.replace(/-/g, '').toLowerCase() === cleanId
    );

    const findings = getStored<ValidationFinding[]>(
      STORAGE_KEYS.FINDINGS,
      mockValidationFindings as unknown as ValidationFinding[]
    );
    const appFindings = findings.filter(
      (f) => !run || f.validation_run_id === run.id || f.validation_run_id?.replace(/-/g, '').toLowerCase() === run?.id?.replace(/-/g, '').toLowerCase()
    );

    const anomalies = (mockAnomalies as unknown as AnomalyFlag[]).filter(
      (a) => a.application_id === applicationId || a.application_id?.replace(/-/g, '').toLowerCase() === cleanId
    );

    const verifications = (mockVerifications as unknown as VerificationResult[]).filter(
      (v) => v.application_id === applicationId || v.application_id?.replace(/-/g, '').toLowerCase() === cleanId
    );

    const docs = this.getDocuments(applicationId);
    const logs = this.getAuditLogs(applicationId);
    const alerts = this.getAlerts(applicationId);

    return {
      application: app || (mockApplications[0] as unknown as Application),
      validation_run: run || null,
      findings: appFindings,
      anomalies,
      verifications,
      documents: docs,
      audit_logs: logs,
      alerts,
    };
  },

  runValidation(applicationId: string): ValidationReport {
    const cleanId = applicationId.replace(/-/g, '').toLowerCase();
    const runs = getStored<ValidationRun[]>(STORAGE_KEYS.VALIDATION_RUNS, mockValidationRuns as unknown as ValidationRun[]);

    // Create or update run
    const newRun: ValidationRun = {
      id: crypto.randomUUID ? crypto.randomUUID() : 'run-' + Math.random().toString(36).substring(2),
      application_id: applicationId,
      started_at: new Date(Date.now() - 3000).toISOString(),
      completed_at: new Date().toISOString(),
      overall_score: 88,
      findings_count: 3,
      high_severity_count: 0,
      medium_severity_count: 2,
      low_severity_count: 1,
      status: 'COMPLETE',
    };

    const nextRuns = [newRun, ...runs.filter((r) => r.application_id !== applicationId && r.application_id?.replace(/-/g, '').toLowerCase() !== cleanId)];
    setStored(STORAGE_KEYS.VALIDATION_RUNS, nextRuns);

    // Update application
    this.updateApplication(applicationId, {
      status: 'VALIDATION_COMPLETE',
      validation_score: 88,
    });

    // Add audit log
    this.addAuditLog({
      application_id: applicationId,
      action: 'AI_VALIDATION_EXECUTED',
      result: 'SUCCESS',
      notes: 'AI Automated Cross-Document Validation engine executed. Regulatory compliance score calculated: 88/100.',
    });

    return this.getValidationReport(applicationId);
  },

  applyAction(applicationId: string, action: OfficerAction, notes: string): Application {
    let nextStatus: Application['status'] = 'UNDER_REVIEW';
    if (action === 'SEND_FOR_RECTIFICATION') nextStatus = 'SENT_FOR_RECTIFICATION';
    else if (action === 'APPROVE_FOR_PROCESSING') nextStatus = 'APPROVED_FOR_PROCESSING';
    else if (action === 'ESCALATE') nextStatus = 'ESCALATED';
    else if (action === 'REJECT') nextStatus = 'REJECTED';

    const updated = this.updateApplication(applicationId, { status: nextStatus }) || {
      id: applicationId,
      status: nextStatus,
    } as Application;

    this.addAuditLog({
      application_id: applicationId,
      action: action,
      result: 'SUCCESS',
      notes: notes || `Regulatory Officer applied action: ${action.replace(/_/g, ' ')}`,
    });

    // Real-time broadcast
    if (realtimeChannel) {
      realtimeChannel.postMessage({
        type: action === 'SEND_FOR_RECTIFICATION' ? 'RECTIFICATION_REQUESTED' : 'APPLICATION_STATUS_UPDATED',
        application_id: applicationId,
        action,
        status: nextStatus,
        message: notes || `Application #${applicationId.slice(0, 8)} status updated to ${nextStatus.replace(/_/g, ' ')}`,
        timestamp: new Date().toISOString(),
      });
    }

    return updated;
  },

  getPublicVerification(applicationId: string): PublicVerificationData {
    const app = this.getApplication(applicationId) || (mockApplications[0] as unknown as Application);
    const logs = this.getAuditLogs(applicationId);
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://aicte-application.vercel.app';
    const verifyUrl = `${origin}/verify/${applicationId}`;

    return {
      verification_status: 'VERIFIED',
      application_id: app.id || applicationId,
      institution_name: app.institution_name || 'Dr. Ramesh Kulkarni (Principal)',
      academic_year: app.academic_year || '2024-25',
      application_type: app.application_type || 'EOA_RENEWAL',
      current_status: app.status || 'APPROVED_FOR_PROCESSING',
      is_approved: app.status === 'APPROVED_FOR_PROCESSING' || app.status === 'VALIDATION_COMPLETE',
      submitted_at: app.submitted_at || app.created_at,
      approval_date: app.updated_at,
      approving_officer: 'Shri Alok Kumar (Scrutiny Officer)',
      chain_integrity: {
        is_valid: true,
        total_audit_events: Math.max(logs.length, 3),
        chain_head_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        genesis_hash: '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f',
        verification_message: 'Cryptographically sealed audit chain: SHA-256 block hash integrity verified intact.',
      },
      qr_code_data_uri: `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(verifyUrl)}`,
      public_verification_url: verifyUrl,
      decision_timeline: logs.map((l) => ({
        id: l.id,
        timestamp: l.created_at,
        actor: l.actor_name,
        action: l.action,
        result: l.result,
        notes: l.notes,
        entry_hash_short: l.entry_hash ? l.entry_hash.slice(0, 12) : '3a8f9c1b7e2d',
      })),
    };
  },
};
