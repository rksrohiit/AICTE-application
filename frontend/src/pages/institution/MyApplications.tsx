import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { FilePlus, ChevronRight, FileText, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { PageSpinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ValidationScoreRing } from '@/components/shared/ValidationScoreRing';
import type { Application, ApplicationStatus } from '@/lib/types';

function statusToBadgeVariant(status: ApplicationStatus) {
  switch (status) {
    case 'APPROVED_FOR_PROCESSING': return 'success';
    case 'REJECTED': return 'danger';
    case 'SENT_FOR_RECTIFICATION':
    case 'ESCALATED': return 'warning';
    case 'SUBMITTED':
    case 'UNDER_VALIDATION':
    case 'VALIDATION_COMPLETE':
    case 'UNDER_REVIEW': return 'info';
    default: return 'neutral';
  }
}

function formatStatus(status: ApplicationStatus): string {
  return status.replace(/_/g, ' ');
}

export default function MyApplications() {
  const { data: rawApps, isLoading, isError } = useQuery({
    queryKey: ['applications'],
    queryFn: api.applications.list,
  });

  const applications: Application[] = Array.isArray(rawApps)
    ? rawApps
    : (rawApps as unknown as { items?: Application[] })?.items || [];

  if (isLoading) return <PageSpinner />;

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-400">
        <AlertCircle className="h-10 w-10 mb-3 text-danger-400" />
        <p className="font-medium">Failed to load applications</p>
        <p className="text-sm mt-1">Please try refreshing the page</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Applications</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {applications?.length ?? 0} application{applications?.length !== 1 ? 's' : ''} found
          </p>
        </div>
        <Link to="/institution/new">
          <Button leftIcon={<FilePlus className="h-4 w-4" />}>New Application</Button>
        </Link>
      </div>

      {/* Applications list */}
      {!applications || applications.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-gray-400 bg-white rounded-2xl border border-dashed border-gray-300">
          <FileText className="h-12 w-12 mb-3 text-gray-300" />
          <p className="text-lg font-medium text-gray-500">No applications yet</p>
          <p className="text-sm mt-1 mb-6 text-gray-400">
            Start your EOA renewal process by creating a new application
          </p>
          <Link to="/institution/new">
            <Button leftIcon={<FilePlus className="h-4 w-4" />}>Create Application</Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {applications.map((app) => (
            <Card key={app.id} className="hover:shadow-md transition-shadow">
              {/* App ID + Status */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">
                    Application ID
                  </p>
                  <p className="text-sm font-mono font-bold text-gray-800 mt-0.5">
                    #{app.id.slice(0, 8)}
                  </p>
                </div>
                <Badge variant={statusToBadgeVariant(app.status)}>
                  {formatStatus(app.status)}
                </Badge>
              </div>

              {/* Institution */}
              <p className="text-sm font-semibold text-gray-900 mb-1 truncate">
                {app.institution_name}
              </p>
              <p className="text-xs text-gray-500 mb-4">
                {app.application_type.replace(/_/g, ' ')} · AY {app.academic_year}
              </p>

              {/* Score + Docs */}
              <div className="flex items-center gap-4 mb-4">
                <ValidationScoreRing score={app.validation_score} size="sm" showLabel={false} />
                <div className="flex-1 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Documents</span>
                    <span className="font-medium text-gray-700">
                      {app.documents_complete}/{app.total_documents}
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-600 rounded-full"
                      style={{
                        width: `${(app.documents_complete / Math.max(app.total_documents, 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <p className="text-xs text-gray-400">Submitted {formatDate(app.submitted_at)}</p>
                </div>
              </div>

              {/* View button */}
              <Link to={`/institution/applications/${app.id}`}>
                <button className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-primary-700 hover:border-primary-200 transition-colors">
                  View Details
                  <ChevronRight className="h-4 w-4" />
                </button>
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
