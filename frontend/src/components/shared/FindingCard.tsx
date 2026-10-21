import { SeverityBadge } from './SeverityBadge';
import { StatusIcon } from '@/components/ui/StatusIcon';
import { getDocTypeLabel } from '@/lib/utils';
import type { ValidationFinding } from '@/lib/types';

interface FindingCardProps {
  finding: ValidationFinding;
}

export function FindingCard({ finding }: FindingCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-mono text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded border border-gray-200">
          {finding.rule_id}
        </span>
        <SeverityBadge severity={finding.severity} />
        <StatusIcon status={finding.status} size="sm" />
        <span className="text-xs text-gray-500">{finding.status}</span>
        {finding.doc_type && (
          <span className="ml-auto text-xs text-gray-400">
            {getDocTypeLabel(finding.doc_type)}
          </span>
        )}
      </div>

      {/* Message */}
      <p className="text-sm text-gray-800 font-medium">{finding.message}</p>

      {/* Evidence */}
      {finding.evidence && (
        <div className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2">
          <p className="text-xs text-gray-500 font-medium mb-1">Evidence</p>
          <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap break-all">
            {finding.evidence}
          </pre>
        </div>
      )}

      {/* Guidance */}
      {finding.guidance && (
        <div className="rounded-lg bg-blue-50 border border-blue-200 px-3 py-2">
          <p className="text-xs text-blue-600 font-medium mb-0.5">💡 Guidance</p>
          <p className="text-xs text-blue-700">{finding.guidance}</p>
        </div>
      )}
    </div>
  );
}
