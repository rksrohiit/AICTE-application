import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { DocType } from './types';

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));
const labels: Record<DocType, string> = {
  AFFIDAVIT: 'Affidavit',
  STATE_NOC: 'State Government NOC',
  NAAC_CERT: 'NAAC Accreditation Certificate',
  FIRE_SAFETY_CERT: 'Fire Safety Certificate',
  TER_RECEIPT: 'TER Payment Receipt',
  LAND_BUILDING_DOC: 'Land & Building Documents',
  FACULTY_DATA: 'Faculty Data',
  EOA_FORM: 'EOA Application Form',
};
export const getDocTypeLabel = (type: DocType) => labels[type] ?? type.replace(/_/g, ' ');
export const getDocTypeDescription = (type: DocType) =>
  ({ AFFIDAVIT: 'Signed institutional affidavit', STATE_NOC: 'State government no-objection certificate', NAAC_CERT: 'Current NAAC accreditation evidence', FIRE_SAFETY_CERT: 'Current fire and life-safety certificate', TER_RECEIPT: 'Treasury or TER payment receipt', LAND_BUILDING_DOC: 'Land ownership and building evidence', FACULTY_DATA: 'Faculty roster and qualification evidence', EOA_FORM: 'Completed EoA application form' } as Record<DocType, string>)[type];
export const isDocTypeMandatory = (_type: DocType) => true;
export const formatFileSize = (bytes: number) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
export const formatDate = (value: string | null | undefined) => value ? new Date(value).toLocaleDateString() : '—';
export const formatDateTime = (value: string | null | undefined) => value ? new Date(value).toLocaleString() : '—';
export const getScoreColor = (score: number | null | undefined) => (score == null ? '#94a3b8' : score >= 80 ? '#059669' : score >= 60 ? '#d97706' : '#dc2626');
