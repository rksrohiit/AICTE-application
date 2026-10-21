import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FilePlus,
  ClipboardList,
  LogOut,
  ChevronRight,
} from 'lucide-react';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const { user, logout } = useAuthStore();
  const location = useLocation();

  const institutionNav: NavItem[] = [
    {
      label: 'My Applications',
      href: '/institution',
      icon: <LayoutDashboard className="h-5 w-5" />,
    },
    {
      label: 'New Application',
      href: '/institution/new',
      icon: <FilePlus className="h-5 w-5" />,
    },
  ];

  const officerNav: NavItem[] = [
    {
      label: 'Application Queue',
      href: '/officer',
      icon: <ClipboardList className="h-5 w-5" />,
    },
  ];

  const navItems =
    user?.role === 'INSTITUTION' ? institutionNav : officerNav;

  const isActive = (href: string) => {
    if (href === '/institution' || href === '/officer') {
      return location.pathname === href;
    }
    return location.pathname.startsWith(href);
  };

  return (
    <aside
      className={cn(
        'flex flex-col w-64 min-h-screen bg-primary-900 text-white',
        className
      )}
    >
      {/* Logo section */}
      <div className="px-6 py-5 border-b border-primary-800">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 bg-accent-500 rounded-lg flex items-center justify-center font-bold text-white text-sm">
            AI
          </div>
          <div>
            <p className="text-xs font-medium text-primary-300 uppercase tracking-wider">AICTE</p>
            <p className="text-sm font-semibold leading-tight">Validation Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            to={item.href}
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              isActive(item.href)
                ? 'bg-white/10 text-white'
                : 'text-primary-200 hover:bg-white/5 hover:text-white'
            )}
          >
            {item.icon}
            <span className="flex-1">{item.label}</span>
            {isActive(item.href) && (
              <ChevronRight className="h-4 w-4 text-primary-300" />
            )}
          </Link>
        ))}
      </nav>

      {/* User info + Logout */}
      <div className="px-3 py-4 border-t border-primary-800 space-y-2">
        <div className="px-3 py-2">
          <p className="text-sm font-medium text-white truncate">{user?.full_name}</p>
          <p className="text-xs text-primary-300 truncate">{user?.email}</p>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-primary-200 hover:bg-white/5 hover:text-white transition-colors"
        >
          <LogOut className="h-5 w-5" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
