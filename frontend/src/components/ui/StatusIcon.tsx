import { CheckCircle, XCircle, AlertTriangle, Clock, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FindingStatus } from '@/lib/types';

interface StatusIconProps {
  status: FindingStatus | 'PENDING' | 'PROCESSING' | 'COMPLETE' | 'FAILED';
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const sizeMap = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-6 w-6',
};

export function StatusIcon({ status, className, size = 'md' }: StatusIconProps) {
  const iconSize = sizeMap[size];

  switch (status) {
    case 'PASS':
    case 'COMPLETE':
      return <CheckCircle className={cn(iconSize, 'text-success-600', className)} />;
    case 'FAIL':
    case 'FAILED':
      return <XCircle className={cn(iconSize, 'text-danger-600', className)} />;
    case 'WARN':
      return <AlertTriangle className={cn(iconSize, 'text-warning-500', className)} />;
    case 'SKIPPED':
      return <Minus className={cn(iconSize, 'text-gray-400', className)} />;
    case 'PENDING':
    case 'PROCESSING':
      return <Clock className={cn(iconSize, 'text-blue-500', className)} />;
    default:
      return <Clock className={cn(iconSize, 'text-gray-400', className)} />;
  }
}
