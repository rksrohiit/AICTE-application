import { useState } from 'react';
import { formatDateTime } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { CheckCircle, XCircle, Info, ShieldCheck, ShieldAlert, Lock, RefreshCw, QrCode } from 'lucide-react';
import type { AuditLog, AuditChainReport } from '@/lib/types';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

interface AuditTimelineProps {
  logs: AuditLog[];
  applicationId?: string;
  onShowQr?: () => void;
}

function getActionIcon(result: string) {
  if (result === 'SUCCESS' || result === 'success' || result === 'PASS') {
    return <CheckCircle className="h-4 w-4 text-success-600" />;
  }
  if (result === 'FAILURE' || result === 'ERROR' || result === 'error' || result === 'REJECTED') {
    return <XCircle className="h-4 w-4 text-danger-600" />;
  }
  return <Info className="h-4 w-4 text-blue-500" />;
}

function getActionColor(action: string): string {
  const upper = action.toUpperCase();
  if (upper.includes('APPROVE')) return 'text-success-700';
  if (upper.includes('REJECT')) return 'text-danger-700';
  if (upper.includes('ESCALAT')) return 'text-purple-700';
  if (upper.includes('RECTIF')) return 'text-warning-700';
  if (upper.includes('SUBMIT')) return 'text-blue-700';
  if (upper.includes('VALIDATE') || upper.includes('VALIDATION')) return 'text-indigo-700';
  return 'text-gray-700';
}

const roleLabelMap: Record<string, string> = {
  INSTITUTION: 'Institution',
  OFFICER: 'Officer',
  SENIOR_OFFICER: 'Senior Officer',
  SYSTEM: 'System',
};

export function AuditTimeline({ logs, applicationId, onShowQr }: AuditTimelineProps) {
  const [verifying, setVerifying] = useState<boolean>(false);
  const [chainReport, setChainReport] = useState<AuditChainReport | null>(null);

  const handleVerifyChain = async () => {
    if (!applicationId) return;
    setVerifying(true);
    try {
      const report = await api.audit.verifyChain(applicationId);
      setChainReport(report);
      if (report.is_valid) {
        toast.success(`Cryptographic integrity verified! All ${report.total_records} records intact.`);
      } else {
        toast.error('Warning: Hash chain discontinuity detected in audit ledger!');
      }
    } catch {
      toast.error('Failed to verify audit chain.');
    } finally {
      setVerifying(false);
    }
  };

  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center py-12 text-gray-400">
        <Info className="h-8 w-8 mb-2" />
        <p className="text-sm">No audit entries yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Cryptographic Hash Chain Verification Controls */}
      {applicationId && (
        <div className="p-4 bg-slate-900 text-white rounded-2xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-emerald-400" />
              <span className="text-xs uppercase font-bold tracking-wider text-slate-300">
                Cryptographic SHA-256 Hash-Chained Audit Ledger
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Each decision record encapsulates the previous record's hash digest. Zero retroactive alteration possible.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {onShowQr && (
              <button
                onClick={onShowQr}
                className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-lg text-xs font-medium border border-white/15 flex items-center gap-1.5 transition-colors"
              >
                <QrCode className="h-3.5 w-3.5 text-blue-300" />
                Public QR
              </button>
            )}

            <button
              onClick={handleVerifyChain}
              disabled={verifying}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${verifying ? 'animate-spin' : ''}`} />
              Verify Chain Integrity
            </button>
          </div>
        </div>
      )}

      {/* Verification Result Banner */}
      {chainReport && (
        <div
          className={`p-3 rounded-xl border flex items-center justify-between text-xs ${
            chainReport.is_valid
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-red-50 border-red-200 text-red-900'
          }`}
        >
          <div className="flex items-center gap-2">
            {chainReport.is_valid ? (
              <ShieldCheck className="h-5 w-5 text-emerald-600 flex-shrink-0" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-red-600 flex-shrink-0" />
            )}
            <div>
              <span className="font-bold block">
                {chainReport.is_valid
                  ? `Chain Verified: ${chainReport.total_records} events cryptographically linked`
                  : 'Chain Compromised: Discontinuity detected'}
              </span>
              <span className="text-[10px] font-mono opacity-80 block truncate max-w-md">
                Head Hash: {chainReport.head_hash}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Timeline List */}
      <div className="relative space-y-0 pt-2">
        {/* Vertical line */}
        <div className="absolute left-5 top-0 bottom-0 w-px bg-gray-200" />

        {logs.map((log, index) => (
          <div key={log.id} className="relative flex gap-4 pb-6">
            {/* Timeline dot */}
            <div
              className={cn(
                'flex-shrink-0 h-10 w-10 rounded-full border-2 border-white bg-gray-50 flex items-center justify-center z-10 shadow-sm',
                index === 0 && 'bg-primary-50 border-primary-100'
              )}
            >
              {getActionIcon(log.result)}
            </div>

            {/* Content */}
            <div className="flex-1 pt-1.5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className={cn('text-sm font-semibold', getActionColor(log.action))}>
                    {log.action.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-gray-400 ml-2">
                    by {(log as any).actor_name || (log as any).actor || 'Officer'} ({roleLabelMap[log.actor_role] ?? log.actor_role ?? 'Officer'})
                  </span>
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0">
                  {formatDateTime(log.created_at || (log as any).timestamp)}
                </span>
              </div>

              {log.notes && (
                <p className="mt-1 text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                  {log.notes}
                </p>
              )}

              <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                <span
                  className={cn(
                    'text-[10px] font-medium px-1.5 py-0.5 rounded',
                    log.result === 'SUCCESS' || log.result === 'success' || log.result === 'PASS'
                      ? 'text-success-700 bg-success-50'
                      : log.result === 'FAILURE' || log.result === 'error' || log.result === 'REJECTED'
                      ? 'text-danger-700 bg-danger-50'
                      : 'text-blue-700 bg-blue-50'
                  )}
                >
                  {log.result}
                </span>

                {log.entry_hash && (
                  <span
                    className="font-mono text-[10px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200"
                    title={`Full SHA-256 Hash: ${log.entry_hash}`}
                  >
                    SHA256: {log.entry_hash.slice(0, 12)}...
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
