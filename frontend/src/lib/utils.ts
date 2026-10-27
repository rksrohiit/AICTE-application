import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format } from 'date-fns';
import type { DocType, FindingSeverity, ApplicationStatus, OCRStatus } from './types';

/** Merge Tailwind classes intelligently */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format date as DD/MM/YYYY (Indian format) */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '—';
  try {
    return format(new Date(date), 'dd/MM/yyyy');
  } catch {
    return '—';
  }
}

/** Format datetime as DD/MM/YYYY HH:mm IST */
export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return '—';
  try {
    return format(new Date(date), 'dd/MM/yyyy HH:mm') + ' IST';
  } catch {
    return '—';
  }
}

/** Map severity level to Tailwind color classes */
export function getSeverityColor(severity: FindingSeverity): string {
  switch (severity) {
    case 'HIGH':
      return 'text-danger-700 bg-danger-50 border-danger-200';
    case 'MEDIUM':
      return 'text-warning-700 bg-warning-50 border-warning-200';
    case 'LOW':
      return 'text-blue-700 bg-blue-50 border-blue-200';
    default:
      return 'text-gray-700 bg-gray-50 border-gray-200';
  }
}

/** Map application status to Tailwind color classes */
export function getStatusColor(status: ApplicationStatus): string {
  switch (status) {
    case 'DRAFT':
      return 'text-gray-600 bg-gray-100';
    case 'SUBMITTED':
      return 'text-blue-700 bg-blue-100';
    case 'UNDER_VALIDATION':
      return 'text-indigo-700 bg-indigo-100';
    case 'VALIDATION_COMPLETE':
      return 'text-cyan-700 bg-cyan-100';
    case 'UNDER_REVIEW':
      return 'text-primary-700 bg-primary-100';
    case 'SENT_FOR_RECTIFICATION':
      return 'text-warning-700 bg-warning-100';
    case 'APPROVED_FOR_PROCESSING':
      return 'text-success-700 bg-success-100';
    case 'ESCALATED':
      return 'text-purple-700 bg-purple-100';
    case 'REJECTED':
      return 'text-danger-700 bg-danger-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

/** Map OCR status to Tailwind color classes */
export function getOCRStatusColor(status: OCRStatus): string {
  switch (status) {
    case 'COMPLETE':
      return 'text-success-700 bg-success-100';
    case 'PROCESSING':
      return 'text-blue-700 bg-blue-100';
    case 'PENDING':
      return 'text-gray-600 bg-gray-100';
    case 'FAILED':
      return 'text-danger-700 bg-danger-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

/** Format bytes to human-readable size */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/** Get human-readable label for document type */
export function getDocTypeLabel(docType: DocType): string {
  const labels: Record<DocType, string> = {
    AFFIDAVIT: 'Affidavit',
    STATE_NOC: 'State NOC',
    NAAC_CERT: 'NAAC Certificate',
    FIRE_SAFETY_CERT: 'Fire Safety Certificate',
    TER_RECEIPT: 'TER Receipt',
    LAND_BUILDING_DOC: 'Land & Building Document',
    FACULTY_DATA: 'Faculty Data',
    EOA_FORM: 'EOA Form',
  };
  return labels[docType] ?? docType;
}

/** Get description for a document type */
export function getDocTypeDescription(docType: DocType): string {
  const descriptions: Record<DocType, string> = {
    AFFIDAVIT: 'Notarized affidavit from institution head',
    STATE_NOC: 'No Objection Certificate from State Government',
    NAAC_CERT: 'National Assessment and Accreditation Council certificate',
    FIRE_SAFETY_CERT: 'Fire safety compliance certificate from Fire Department',
    TER_RECEIPT: 'Tuition Fee Rationalization receipt',
    LAND_BUILDING_DOC: 'Land and building ownership/lease documents',
    FACULTY_DATA: 'Faculty details with qualifications and experience',
    EOA_FORM: 'Extension of Approval application form',
  };
  return descriptions[docType] ?? '';
}

/** Check if a document type is mandatory */
export function isDocTypeMandatory(docType: DocType): boolean {
  const mandatory: DocType[] = [
    'AFFIDAVIT',
    'STATE_NOC',
    'NAAC_CERT',
    'FIRE_SAFETY_CERT',
    'TER_RECEIPT',
    'EOA_FORM',
  ];
  return mandatory.includes(docType);
}

/** Get score ring color based on score value */
export function getScoreColor(score: number | null): string {
  if (score === null) return '#9CA3AF';
  if (score >= 70) return '#16A34A';
  if (score >= 40) return '#D97706';
  return '#DC2626';
}

/** Truncate string to max length */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength) + '…';
}
