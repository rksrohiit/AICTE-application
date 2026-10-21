import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertOctagon,
  HelpCircle,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { VerificationStatus } from '@/lib/types';

interface VerificationStatusChipProps {
  status: VerificationStatus;
  className?: string;
}

const statusConfig: Record<
  VerificationStatus,
  { icon: React.ReactNode; label: string; className: string }
> = {
  VERIFIED: {
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    label: 'Verified',
    className: 'text-success-700 bg-success-50 border-success-200',
  },
  MISMATCH_DETECTED: {
    icon: <XCircle className="h-3.5 w-3.5" />,
    label: 'Mismatch',
    className: 'text-danger-700 bg-danger-50 border-danger-200',
  },
  EXPIRED: {
    icon: <AlertOctagon className="h-3.5 w-3.5" />,
    label: 'Expired',
    className: 'text-warning-700 bg-warning-50 border-warning-200',
  },
  VERIFICATION_PENDING: {
    icon: <Clock className="h-3.5 w-3.5" />,
    label: 'Pending',
    className: 'text-blue-700 bg-blue-50 border-blue-200',
  },
  SOURCE_UNAVAILABLE: {
    icon: <HelpCircle className="h-3.5 w-3.5" />,
    label: 'Source Unavailable',
    className: 'text-gray-600 bg-gray-50 border-gray-200',
  },
  MANUAL_REVIEW_REQUIRED: {
    icon: <Eye className="h-3.5 w-3.5" />,
    label: 'Manual Review',
    className: 'text-purple-700 bg-purple-50 border-purple-200',
  },
};

export function VerificationStatusChip({ status, className }: VerificationStatusChipProps) {
  const config = statusConfig[status];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border',
        config.className,
        className
      )}
    >
      {config.icon}
      {config.label}
    </span>
  );
}
