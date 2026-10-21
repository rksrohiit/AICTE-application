import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Search, Filter, ChevronLeft, ChevronRight, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { PageSpinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ScorePill } from '@/components/shared/ValidationScoreRing';
import type { Application, ApplicationStatus } from '@/lib/types';

type ScoreFilter = 'all' | 'high' | 'medium' | 'low';

const PAGE_SIZE = 10;

const STATUS_OPTIONS: ApplicationStatus[] = [
  'SUBMITTED',
  'UNDER_VALIDATION',
  'VALIDATION_COMPLETE',
  'UNDER_REVIEW',
  'SENT_FOR_RECTIFICATION',
  'APPROVED_FOR_PROCESSING',
  'ESCALATED',
  'REJECTED',
];

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-2xl font-bold" style={{ color }}>
        {value}
      </p>
      <p className="text-sm text-gray-500 mt-0.5">{label}</p>
    </div>
  );
}

function getRowBg(score: number | null): string {
  if (score === null) return '';
  if (score < 40) return 'bg-red-50';
  if (score < 70) return 'bg-amber-50';
  return '';
}

function badgeVariantForStatus(status: ApplicationStatus) {
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

export default function ApplicationQueue() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>('all');
  const [anomalyFilter, setAnomalyFilter] = useState(false);
  const [page, setPage] = useState(1);

  const { data: applications, isLoading, isError } = useQuery({
    queryKey: ['applications'],
    queryFn: api.applications.list,
  });

  const { data: metrics } = useQuery({
    queryKey: ['metrics'],
    queryFn: api.metrics.summary,
  });

  const filtered = useMemo(() => {
    const list: Application[] = Array.isArray(applications)
      ? applications
      : (applications as unknown as { items?: Application[] })?.items || [];
    return list.filter((app: Application) => {
      if (searchQuery && !app.institution_name.toLowerCase().includes(searchQuery.toLowerCase()))
        return false;
      if (statusFilter && app.status !== statusFilter) return false;
      if (scoreFilter !== 'all') {
        const s = app.validation_score ?? 0;
        if (scoreFilter === 'high' && s <= 70) return false;
        if (scoreFilter === 'medium' && (s < 40 || s > 70)) return false;
        if (scoreFilter === 'low' && s >= 40) return false;
      }
      if (anomalyFilter && !app.has_anomalies) return false;
      return true;
    });
  }, [applications, searchQuery, statusFilter, scoreFilter, anomalyFilter]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  if (isLoading) return <PageSpinner />;

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-400">
        <AlertCircle className="h-10 w-10 mb-3 text-danger-400" />
        <p className="font-medium">Failed to load application queue</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Application Queue</h1>
        <p className="text-sm text-gray-500 mt-0.5">Review and process institution applications</p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          label="Total Applications"
          value={metrics?.total_applications ?? applications?.length ?? 0}
          color="#1E3A8A"
        />
        <StatCard
          label="Pending Review"
          value={metrics?.pending_review ?? 0}
          color="#D97706"
        />
        <StatCard
          label="Anomalies Flagged"
          value={metrics?.anomalies_flagged ?? 0}
          color="#DC2626"
        />
        <StatCard
          label="Verified Today"
          value={metrics?.verified_today ?? 0}
          color="#16A34A"
        />
      </div>

      {/* Filter bar */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div className="flex flex-wrap gap-3">
          {/* Search */}
          <div className="flex-1 min-w-48 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by institution name..."
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
            ))}
          </select>

          {/* Score filter */}
          <select
            value={scoreFilter}
            onChange={(e) => { setScoreFilter(e.target.value as ScoreFilter); setPage(1); }}
            className="px-3 py-2 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Scores</option>
            <option value="high">&gt;70 (Good)</option>
            <option value="medium">40–70 (Average)</option>
            <option value="low">&lt;40 (Poor)</option>
          </select>

          {/* Anomaly filter */}
          <label className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 cursor-pointer text-sm text-gray-600 hover:bg-gray-50">
            <input
              type="checkbox"
              checked={anomalyFilter}
              onChange={(e) => { setAnomalyFilter(e.target.checked); setPage(1); }}
              className="rounded text-primary-600"
            />
            <Filter className="h-3.5 w-3.5" />
            Has Anomalies
          </label>
        </div>

        <p className="text-xs text-gray-400">
          Showing {paginated.length} of {filtered.length} results
        </p>
      </div>

      {/* Data table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  App ID
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Institution
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Score
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Status
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Anomalies
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Submitted
                </th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {paginated.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-gray-400">
                    No applications match your filters
                  </td>
                </tr>
              ) : (
                paginated.map((app) => (
                  <tr
                    key={app.id}
                    className={`hover:bg-gray-50/80 transition-colors ${getRowBg(app.validation_score)}`}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">
                      #{app.id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900 truncate max-w-[180px]">
                        {app.institution_name}
                      </p>
                      <p className="text-xs text-gray-400">{app.academic_year}</p>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <ScorePill score={app.validation_score} />
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={badgeVariantForStatus(app.status)} size="sm">
                        {app.status.replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {app.has_anomalies ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-danger-700 bg-danger-50 px-2 py-0.5 rounded-full">
                          ⚠️ {app.anomaly_count}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {formatDate(app.submitted_at)}
                    </td>
                    <td className="px-4 py-3">
                      <Link to={`/officer/applications/${app.id}`}>
                        <Button size="sm" variant="primary">Review</Button>
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <p className="text-xs text-gray-500">
              Page {page} of {totalPages} · {filtered.length} total
            </p>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`h-8 w-8 rounded-lg text-sm font-medium transition-colors ${
                    p === page
                      ? 'bg-primary-900 text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {p}
                </button>
              ))}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
