import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  Printer,
  Building2,
  RefreshCw,
} from 'lucide-react';
import { api } from '@/lib/api';
import type { PublicVerificationData } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export default function PublicVerification() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<PublicVerificationData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showFullHashes, setShowFullHashes] = useState<boolean>(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.publicVerify
      .get(id)
      .then((res) => {
        setData(res);
        setError(null);
      })
      .catch((err) => {
        setError(err.response?.data?.detail || 'Application record could not be found or verified.');
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="text-center space-y-3">
          <RefreshCw className="h-8 w-8 animate-spin text-primary-600 mx-auto" />
          <p className="text-sm font-semibold text-gray-700">
            Verifying cryptographic hash-chain authenticity...
          </p>
          <p className="text-xs text-gray-400">Querying immutable decision ledger</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl border border-red-200 p-6 text-center space-y-4 shadow-sm">
          <ShieldAlert className="h-12 w-12 text-red-500 mx-auto" />
          <h2 className="text-lg font-bold text-gray-900">Verification Failed</h2>
          <p className="text-xs text-gray-600">{error}</p>
          <div className="pt-2">
            <Link to="/login">
              <Button variant="secondary" size="sm">
                Return to AICTE Platform
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const isValid = data.chain_integrity.is_valid;

  return (
    <div className="min-h-screen bg-slate-100 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* National Emblem & AICTE Official Header */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm text-center space-y-3 print:border-none print:shadow-none">
          <div className="inline-flex items-center justify-center p-2 bg-blue-50 rounded-2xl text-blue-900 mb-1">
            <Building2 className="h-8 w-8" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-gray-900 sm:text-2xl">
              All India Council for Technical Education
            </h1>
            <p className="text-xs font-semibold text-primary-700 uppercase tracking-widest mt-0.5">
              Statutory Body of the Government of India · Public Verification Portal
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Extension of Approval (EoA) &amp; Application Integrity Ledger
            </p>
          </div>

          {/* Cryptographic Seal Banner */}
          <div
            className={`p-4 rounded-xl border flex flex-col sm:flex-row items-center justify-between gap-3 text-left ${
              isValid
                ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                : 'bg-red-50 border-red-200 text-red-950'
            }`}
          >
            <div className="flex items-center gap-3">
              {isValid ? (
                <ShieldCheck className="h-8 w-8 text-emerald-600 flex-shrink-0" />
              ) : (
                <ShieldAlert className="h-8 w-8 text-red-600 flex-shrink-0" />
              )}
              <div>
                <span className="font-bold text-sm block">
                  {isValid ? 'Cryptographically Verified Authentic Record' : 'Security Alert: Chain Discontinuity Detected'}
                </span>
                <span className="text-xs opacity-85 block">
                  {data.chain_integrity.verification_message}
                </span>
              </div>
            </div>

            <Badge variant={isValid ? 'success' : 'danger'} className="text-xs whitespace-nowrap">
              {isValid ? 'TAMPER-PROOF VALID' : 'TAMPERING DETECTED'}
            </Badge>
          </div>
        </div>

        {/* Certificate Card with QR & Particulars */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-6 print:border-none">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6 pb-6 border-b border-gray-100">
            {/* Institution particulars */}
            <div className="space-y-3 flex-1 text-center sm:text-left">
              <div>
                <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                  Institution Name
                </span>
                <h2 className="text-lg font-bold text-gray-900">
                  {data.institution_name}
                </h2>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-gray-400 block">Academic Year</span>
                  <span className="font-semibold text-gray-800">{data.academic_year}</span>
                </div>
                <div>
                  <span className="text-gray-400 block">Application Type</span>
                  <span className="font-semibold text-gray-800">{data.application_type}</span>
                </div>
                <div>
                  <span className="text-gray-400 block">Official Status</span>
                  <span className="font-semibold text-primary-700">{data.current_status}</span>
                </div>
                <div>
                  <span className="text-gray-400 block">Approval Date</span>
                  <span className="font-semibold text-gray-800">
                    {data.approval_date
                      ? new Date(data.approval_date).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })
                      : 'Pending Final Review'}
                  </span>
                </div>
              </div>

              <div>
                <span className="text-[10px] text-gray-400 block">Application Unique ID</span>
                <span className="font-mono text-xs text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                  {data.application_id}
                </span>
              </div>
            </div>

            {/* Official Scannable Public QR Code */}
            <div className="p-4 bg-white rounded-2xl border border-gray-200 shadow-sm text-center space-y-2 flex-shrink-0">
              <img
                src={data.qr_code_data_uri}
                alt="AICTE Public Verification QR Code"
                className="w-36 h-36 mx-auto object-contain"
              />
              <span className="text-[10px] font-mono text-gray-400 block">
                Scan to Verify Online
              </span>
            </div>
          </div>

          {/* Cryptographic Hash-Chain Ledger Summary */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-gray-900 flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5 text-indigo-600" />
                Immutable Decision Chain ({data.chain_integrity.total_audit_events} Sequentially Linked Records)
              </span>
              <button
                onClick={() => setShowFullHashes(!showFullHashes)}
                className="text-[11px] text-primary-600 hover:underline"
              >
                {showFullHashes ? 'Hide Technical Hashes' : 'Inspect Technical Hashes'}
              </button>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1 text-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px]">
                <span className="text-slate-500 font-semibold">Current Chain Head Hash:</span>
                <span className="font-mono text-slate-800 break-all select-all font-semibold">
                  {data.chain_integrity.chain_head_hash}
                </span>
              </div>
            </div>

            {/* Timeline of chained decision events */}
            <div className="border border-gray-200 rounded-xl overflow-hidden text-xs">
              <div className="bg-gray-50 px-4 py-2.5 border-b border-gray-200 font-semibold text-gray-700 flex justify-between">
                <span>Decision &amp; Regulatory Audit Trail</span>
                <span>SHA-256 Hash Digest</span>
              </div>
              <div className="divide-y divide-gray-100 max-h-60 overflow-y-auto">
                {data.decision_timeline.map((entry, idx) => (
                  <div key={entry.id} className="p-3 flex items-start justify-between gap-3 hover:bg-gray-50/50">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-gray-900">
                          #{idx + 1} {entry.action.replace(/_/g, ' ')}
                        </span>
                        {entry.result && (
                          <Badge variant="neutral" className="text-[10px]">
                            {entry.result}
                          </Badge>
                        )}
                      </div>
                      <p className="text-[11px] text-gray-500">
                        Actor: {entry.actor} · {new Date(entry.timestamp).toLocaleString('en-IN')}
                      </p>
                      {entry.notes && (
                        <p className="text-[11px] text-gray-600 italic">{entry.notes}</p>
                      )}
                    </div>
                    <span className="font-mono text-[10px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded flex-shrink-0">
                      {entry.entry_hash_short}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Legal / Statutory Disclaimer */}
          <div className="p-3 bg-gray-50 rounded-xl text-[11px] text-gray-500 leading-relaxed">
            <b>Statutory Note:</b> {data.disclaimer}
          </div>

          {/* Actions: Print / Return */}
          <div className="flex items-center justify-between pt-2 print:hidden">
            <Link to="/login">
              <Button variant="secondary" size="sm">
                AICTE Official Login
              </Button>
            </Link>

            <Button
              variant="primary"
              size="sm"
              onClick={() => window.print()}
              className="bg-primary-700 hover:bg-primary-800"
            >
              <Printer className="h-4 w-4 mr-1.5" />
              Print Verification Record
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
