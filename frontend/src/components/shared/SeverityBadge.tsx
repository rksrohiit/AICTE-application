import { Badge } from '@/components/ui/Badge';
import type { FindingSeverity } from '@/lib/types';

interface SeverityBadgeProps {
  severity: FindingSeverity;
  size?: 'sm' | 'md';
}

const severityConfig: Record<
  FindingSeverity,
  { variant: 'danger' | 'warning' | 'info'; label: string }
> = {
  HIGH: { variant: 'danger', label: 'HIGH' },
  MEDIUM: { variant: 'warning', label: 'MEDIUM' },
  LOW: { variant: 'info', label: 'LOW' },
};

export function SeverityBadge({ severity, size = 'sm' }: SeverityBadgeProps) {
  const config = severityConfig[severity];
  return (
    <Badge variant={config.variant} size={size}>
      {config.label}
    </Badge>
  );
}
