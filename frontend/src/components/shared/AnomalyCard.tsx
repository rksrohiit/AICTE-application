import { formatDateTime } from '@/lib/utils';
import { AlertTriangle, Info } from 'lucide-react';
import type { AnomalyFlag } from '@/lib/types';

interface AnomalyCardProps {
  anomaly: AnomalyFlag;
}

function ConfidenceMeter({ value }: { value: number }) {
  const percentage = Math.round(value * 100);
  const color =
    percentage >= 80
      ? 'bg-danger-500'
      : percentage >= 50
      ? 'bg-warning-500'
      : 'bg-blue-500';

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">Confidence</span>
        <span className="text-xs font-bold text-gray-700">{percentage}%</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export function AnomalyCard({ anomaly }: AnomalyCardProps) {
  const highConfidence = anomaly.confidence >= 0.8;

  return (
    <div
      className={`rounded-xl border p-4 space-y-3 ${
        highConfidence
          ? 'border-danger-200 bg-danger-50'
          : 'border-warning-200 bg-warning-50'
      }`}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className={`flex-shrink-0 p-1.5 rounded-lg ${
            highConfidence ? 'bg-danger-100 text-danger-600' : 'bg-warning-100 text-warning-600'
          }`}
        >
          <AlertTriangle className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900">
            {anomaly.anomaly_type.replace(/_/g, ' ')}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">{formatDateTime(anomaly.flagged_at)}</p>
        </div>
        {anomaly.reviewed && (
          <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            Reviewed
          </span>
        )}
      </div>

      {/* Confidence meter */}
      <ConfidenceMeter value={anomaly.confidence} />

      {/* Evidence */}
      {anomaly.evidence && (
        <div className="rounded-lg bg-white border border-gray-200 px-3 py-2">
          <p className="text-xs font-medium text-gray-500 mb-1">Evidence</p>
          <p className="text-xs text-gray-700 whitespace-pre-wrap">{anomaly.evidence}</p>
        </div>
      )}

      {/* Advisory disclaimer */}
      <div className="flex items-start gap-1.5 pt-1">
        <Info className="h-3.5 w-3.5 text-gray-400 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-gray-400 italic">
          AI-generated anomaly detection is advisory only. Human review required before any action.
        </p>
      </div>
    </div>
  );
}
