import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { UserRole } from '@/lib/types';

import LoginPage from '@/pages/LoginPage';
import InstitutionLayout from '@/pages/institution/Layout';
import MyApplications from '@/pages/institution/MyApplications';
import NewApplication from '@/pages/institution/NewApplication';
import ApplicationStatus from '@/pages/institution/ApplicationStatus';
import OfficerLayout from '@/pages/officer/Layout';
import ApplicationQueue from '@/pages/officer/ApplicationQueue';
import ApplicationDetail from '@/pages/officer/ApplicationDetail';
import PublicVerification from '@/pages/public/PublicVerification';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles: UserRole[];
}

function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    if (user.role === 'INSTITUTION') {
      return <Navigate to="/institution" replace />;
    }
    return <Navigate to="/officer" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/verify/:id" element={<PublicVerification />} />

        {/* Institution routes */}
        <Route
          path="/institution"
          element={
            <ProtectedRoute allowedRoles={['INSTITUTION']}>
              <InstitutionLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<MyApplications />} />
          <Route path="new" element={<NewApplication />} />
          <Route path="applications/:id" element={<ApplicationStatus />} />
        </Route>

        {/* Officer routes */}
        <Route
          path="/officer"
          element={
            <ProtectedRoute allowedRoles={['OFFICER', 'SENIOR_OFFICER']}>
              <OfficerLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<ApplicationQueue />} />
          <Route path="applications/:id" element={<ApplicationDetail />} />
        </Route>

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
