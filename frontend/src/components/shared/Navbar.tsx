import { useAuthStore } from '@/store/authStore';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Bell, LogOut, Shield } from 'lucide-react';

const roleLabelMap = {
  INSTITUTION: { label: 'Institution', variant: 'info' as const },
  OFFICER: { label: 'Officer', variant: 'primary' as const },
  SENIOR_OFFICER: { label: 'Senior Officer', variant: 'purple' as const },
};

export function Navbar() {
  const { user, logout } = useAuthStore();
  const roleInfo = user ? roleLabelMap[user.role] : null;

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-shrink-0 z-10">
      {/* Left: Breadcrumb / Page Title area */}
      <div className="flex items-center gap-2">
        <Shield className="h-5 w-5 text-primary-900" />
        <span className="text-sm font-medium text-gray-500">AICTE Validation Platform</span>
      </div>

      {/* Right: User info */}
      <div className="flex items-center gap-4">
        <button className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors relative">
          <Bell className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 pl-3 border-l border-gray-200">
          <div className="text-right">
            <p className="text-sm font-semibold text-gray-900">{user?.full_name}</p>
            {roleInfo && (
              <Badge variant={roleInfo.variant} size="sm">
                {roleInfo.label}
              </Badge>
            )}
          </div>

          <div className="h-9 w-9 bg-primary-900 rounded-full flex items-center justify-center text-white text-sm font-bold">
            {user?.full_name?.charAt(0).toUpperCase() ?? 'U'}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            className="text-gray-500 hover:text-danger-600"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
