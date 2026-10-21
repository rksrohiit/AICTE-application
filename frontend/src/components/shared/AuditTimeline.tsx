import { formatDateTime } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { CheckCircle, XCircle, Info } from 'lucide-react';
import type { AuditLog } from '@/lib/types';

interface AuditTimelineProps {
  logs: AuditLog[];
}

function getActionIcon(result: string) {
  if (result === 'SUCCESS' || result === 'success') {
    return <CheckCircle className="h-4 w-4 text-success-600" />;
  }
  if (result === 'FAILURE' || result === 'ERROR' || result === 'error') {
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

export function AuditTimeline({ logs }: AuditTimelineProps) {
  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center py-12 text-gray-400">
        <Info className="h-8 w-8 mb-2" />
        <p className="text-sm">No audit entries yet</p>
      </div>
    );
  }

  return (
    <div className="relative space-y-0">
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
                  by {log.actor_name} ({roleLabelMap[log.actor_role] ?? log.actor_role})
                </span>
              </div>
              <span className="text-xs text-gray-400 flex-shrink-0">
                {formatDateTime(log.created_at)}
              </span>
            </div>

            {log.notes && (
              <p className="mt-1 text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                {log.notes}
              </p>
            )}

            <div className="mt-1">
              <span
                className={cn(
                  'text-xs font-medium px-1.5 py-0.5 rounded',
                  log.result === 'SUCCESS' || log.result === 'success'
                    ? 'text-success-700 bg-success-50'
                    : log.result === 'FAILURE' || log.result === 'error'
                    ? 'text-danger-700 bg-danger-50'
                    : 'text-blue-700 bg-blue-50'
                )}
              >
                {log.result}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
