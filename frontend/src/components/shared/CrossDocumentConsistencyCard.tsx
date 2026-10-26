import { useState, useEffect } from 'react';
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  GitCompare,
  Info,
  ShieldAlert,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/lib/api';
import type { CrossDocumentReport } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

interface Props {
  applicationId: string;
}

export function CrossDocumentConsistencyCard({ applicationId }: Props) {
  const [report, setReport] = useState<CrossDocumentReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const loadData = async (isManual = false) => {
    if (!applicationId) return;
    if (isManual) setRefreshing(true);
    else setLoading(true);

    try {
      const data = await api.documents.getCrossDocumentConsistency(applicationId);
      setReport(data);
      if (isManual) toast.success('Cross-document consistency re-evaluated!');
    } catch {
      if (isManual) toast.error('Failed to run consistency engine.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [applicationId]);

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 text-center space-y-2">
          <RefreshCw className="h-6 w-6 animate-spin text-primary-600 mx-auto" />
          <p className="text-xs text-gray-500">
            Running cross-document consistency scrutiny across extracted pages...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!report || report.findings.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <GitCompare className="h-4 w-4 text-primary-600" />
            Cross-Document Consistency Engine
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-gray-400 space-y-2">
            <Info className="h-8 w-8 mx-auto text-gray-300" />
            <p className="text-xs">
              Upload at least two documents (e.g. EOA Form + Affidavit or State NOC) to run automated cross-document claim comparison.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const isAllConsistent = report.overall_consistency_status === 'VERIFIED_CONSISTENT';
  const hasConflicts = report.overall_consistency_status === 'CONFLICTS_DETECTED';

  return (
    <Card className="border border-slate-200 shadow-sm overflow-hidden">
      {/* Header with High-Tech Gov Banner */}
      <div className="bg-slate-900 text-white p-5 border-b border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1 bg-indigo-500/20 text-indigo-400 rounded-md">
                <GitCompare className="h-4 w-4" />
              </span>
              <span className="text-xs uppercase font-bold tracking-wider text-slate-300">
                AICTE Cross-Document Consistency Engine · Evidence-Backed
              </span>
            </div>
            <h3 className="text-base font-bold text-white">
              Inter-Document Claims &amp; Identity Scrutiny
            </h3>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Compares legal claims (institution name, address, academic year, ID, intake) across all uploaded documents without relying on external APIs. Uses semantic abbreviation normalization to prevent false fraud alarms.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => loadData(true)}
              loading={refreshing}
              className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs"
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Re-Scrutinize
            </Button>
          </div>
        </div>

        {/* Status Pill */}
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Consistency Verdict:</span>
            <Badge
              variant={
                isAllConsistent ? 'success' : hasConflicts ? 'danger' : 'warning'
              }
              className="text-xs"
            >
              {report.overall_consistency_status.replace(/_/g, ' ')}
            </Badge>
          </div>

          <div className="flex items-center gap-4 text-slate-400 text-[11px]">
            <span>Analyzed: <b>{report.total_documents_analyzed} documents</b></span>
            <span>Conflicts: <b className="text-red-400">{report.total_conflicts}</b></span>
            <span>Warnings: <b className="text-amber-400">{report.total_warnings}</b></span>
          </div>
        </div>
      </div>

      <CardContent className="p-5 space-y-5">
        {/* Statutory Honest Methodology Disclosure */}
        <div className="p-3 bg-blue-50/70 border border-blue-100 rounded-xl text-blue-900 text-xs flex items-start gap-2.5">
          <Info className="h-4 w-4 flex-shrink-0 text-blue-600 mt-0.5" />
          <p className="leading-relaxed">
            <b>Evidentiary Standard:</b> Discrepancies below 90% token similarity are flagged for human officer review (<code>NEEDS_REVIEW</code>), not declared fraud. Historical addresses, permissible legal abbreviations (e.g. <i>Inst. of Tech.</i> vs <i>Institute of Technology</i>), and municipal updates are preserved for manual evaluation.
          </p>
        </div>

        {/* Findings List */}
        <div className="space-y-4">
          {report.findings.map((f, idx) => {
            const isMatch = f.status === 'CONSISTENT';
            const isConflict = f.status === 'CONFLICT';

            return (
              <div
                key={idx}
                className={`rounded-2xl border transition-all ${
                  isMatch
                    ? 'border-gray-200 bg-white'
                    : isConflict
                    ? 'border-red-200 bg-red-50/20'
                    : 'border-amber-200 bg-amber-50/20'
                } p-4 space-y-3 shadow-sm`}
              >
                {/* Title line */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {isMatch ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    ) : isConflict ? (
                      <ShieldAlert className="h-4 w-4 text-red-600" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                    )}
                    <h4 className="text-sm font-bold text-gray-900 capitalize">
                      {f.field.replace(/_/g, ' ')}
                    </h4>
                    {f.authoritative_doc_type && (
                      <span className="text-[10px] font-semibold bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                        Authoritative: {f.authoritative_doc_type}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono text-gray-500">
                      Token Similarity: <b>{Math.round(f.similarity_score * 100)}%</b>
                    </span>
                    <Badge
                      variant={isMatch ? 'success' : isConflict ? 'danger' : 'warning'}
                      className="text-[10px]"
                    >
                      {f.status.replace(/_/g, ' ')}
                    </Badge>
                  </div>
                </div>

                <p className="text-xs text-gray-700 leading-relaxed">{f.explanation}</p>

                {/* Resolution Guidance */}
                {f.resolution_guidance && (
                  <div className="p-2.5 bg-gray-50 rounded-xl text-xs text-gray-600 border border-gray-100">
                    <span className="font-semibold text-gray-800">Reviewer Guidance: </span>
                    {f.resolution_guidance}
                  </div>
                )}

                {/* Page-by-Page Side-by-Side Evidence Comparison */}
                <div className="pt-2">
                  <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider block mb-2">
                    Cross-Document Source Provenance ({f.evidence.length} Evidence Records)
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    {f.evidence.map((ev, eIdx) => (
                      <div
                        key={eIdx}
                        className="p-3 bg-white rounded-xl border border-gray-200 space-y-1.5 shadow-2xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-gray-800 flex items-center gap-1.5">
                            <FileText className="h-3.5 w-3.5 text-primary-600" />
                            {ev.doc_type}
                          </span>
                          <span className="font-semibold text-primary-700 bg-primary-50 px-2 py-0.5 rounded text-[10px]">
                            Page {ev.page}
                          </span>
                        </div>

                        <div className="bg-gray-50 p-2 rounded-lg border border-gray-100 font-mono text-[11px] text-gray-900 break-words font-semibold">
                          "{ev.extracted_value}"
                        </div>

                        <div className="flex items-center justify-between text-[10px] text-gray-400 pt-0.5">
                          <span className="truncate max-w-[180px]">{ev.file_name}</span>
                          <span>Confidence: {Math.round(ev.confidence * 100)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default CrossDocumentConsistencyCard;
