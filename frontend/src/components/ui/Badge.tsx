import { cn } from '@/lib/utils';

type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'primary' | 'purple';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md';
}

const variantClasses: Record<BadgeVariant, string> = {
  success: 'bg-success-100 text-success-700 border border-success-200',
  warning: 'bg-warning-100 text-warning-700 border border-warning-200',
  danger: 'bg-danger-100 text-danger-700 border border-danger-200',
  info: 'bg-blue-100 text-blue-700 border border-blue-200',
  neutral: 'bg-gray-100 text-gray-600 border border-gray-200',
  primary: 'bg-primary-100 text-primary-800 border border-primary-200',
  purple: 'bg-purple-100 text-purple-700 border border-purple-200',
};

export function Badge({ variant = 'neutral', children, className, size = 'sm' }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-full',
        size === 'sm' ? 'px-2.5 py-0.5 text-xs' : 'px-3 py-1 text-sm',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
