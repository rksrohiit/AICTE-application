import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, RefreshCw, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
import { cn, getDocTypeLabel, getDocTypeDescription, isDocTypeMandatory, formatFileSize } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import type { DocType, Document, OCRStatus } from '@/lib/types';

interface DocumentUploadCardProps {
  docType: DocType;
  document?: Document | null;
  onUpload?: (docType: DocType, file: File) => Promise<void>;
  readOnly?: boolean;
  uploading?: boolean;
}

function OCRStatusBadge({ status }: { status: OCRStatus }) {
  const config: Record<OCRStatus, { label: string; icon: React.ReactNode; className: string }> = {
    PENDING: {
      label: 'Pending OCR',
      icon: <Clock className="h-3 w-3" />,
      className: 'text-gray-600 bg-gray-100',
    },
    PROCESSING: {
      label: 'Processing...',
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
      className: 'text-blue-700 bg-blue-100',
    },
    COMPLETE: {
      label: 'OCR Complete',
      icon: <CheckCircle className="h-3 w-3" />,
      className: 'text-success-700 bg-success-100',
    },
    FAILED: {
      label: 'OCR Failed',
      icon: <XCircle className="h-3 w-3" />,
      className: 'text-danger-700 bg-danger-100',
    },
  };

  const c = config[status];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
        c.className
      )}
    >
      {c.icon}
      {c.label}
    </span>
  );
}

export function DocumentUploadCard({
  docType,
  document,
  onUpload,
  readOnly = false,
  uploading = false,
}: DocumentUploadCardProps) {
  const [isDragging, setIsDragging] = useState(false);
  const label = getDocTypeLabel(docType);
  const description = getDocTypeDescription(docType);
  const mandatory = isDocTypeMandatory(docType);
  const hasDocument = !!document;

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0 && onUpload) {
        await onUpload(docType, acceptedFiles[0]);
      }
    },
    [docType, onUpload]
  );

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    onDragEnter: () => setIsDragging(true),
    onDragLeave: () => setIsDragging(false),
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
    maxFiles: 1,
    disabled: readOnly || uploading,
  });

  const validationStatus = document?.validation_status;
  const canReupload =
    !readOnly && hasDocument && (validationStatus === 'FAIL' || document?.ocr_status === 'FAILED');

  return (
    <div
      className={cn(
        'rounded-xl border-2 transition-colors',
        hasDocument
          ? validationStatus === 'PASS'
            ? 'border-success-200 bg-success-50'
            : validationStatus === 'FAIL'
            ? 'border-danger-200 bg-danger-50'
            : validationStatus === 'WARN'
            ? 'border-warning-200 bg-warning-50'
            : 'border-gray-200 bg-white'
          : isDragging
          ? 'border-primary-400 bg-primary-50'
          : 'border-dashed border-gray-300 bg-gray-50'
      )}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-gray-900">{label}</span>
              {mandatory ? (
                <Badge variant="danger" size="sm">Required</Badge>
              ) : (
                <Badge variant="neutral" size="sm">Optional</Badge>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-0.5 leading-tight">{description}</p>
          </div>

          {/* Validation status icon */}
          {hasDocument && validationStatus && (
            <div className="flex-shrink-0">
              {validationStatus === 'PASS' && <CheckCircle className="h-5 w-5 text-success-600" />}
              {validationStatus === 'FAIL' && <XCircle className="h-5 w-5 text-danger-600" />}
              {validationStatus === 'WARN' && (
                <span className="text-warning-500 text-lg leading-none">⚠️</span>
              )}
            </div>
          )}
        </div>

        {/* Uploaded file info */}
        {hasDocument ? (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white border border-gray-200">
              <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-700 truncate">
                  {document.file_name}
                </p>
                <p className="text-xs text-gray-400">{formatFileSize(document.file_size)}</p>
              </div>
              <OCRStatusBadge status={document.ocr_status} />
            </div>

            {/* Re-upload button */}
            {canReupload && (
              <div {...getRootProps()}>
                <input {...getInputProps()} />
                <Button
                  variant="secondary"
                  size="sm"
                  loading={uploading}
                  leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
                  className="w-full"
                >
                  Re-upload Document
                </Button>
              </div>
            )}
          </div>
        ) : readOnly ? (
          <div className="mt-3 flex items-center gap-2 px-3 py-3 rounded-lg bg-gray-100 text-gray-400">
            <FileText className="h-4 w-4" />
            <span className="text-xs">Not uploaded</span>
          </div>
        ) : (
          /* Drop zone */
          <div
            {...getRootProps()}
            className={cn(
              'mt-3 flex flex-col items-center gap-2 px-3 py-5 rounded-lg cursor-pointer transition-colors',
              'border border-dashed',
              isDragging
                ? 'border-primary-400 bg-primary-50'
                : 'border-gray-300 hover:border-primary-300 hover:bg-primary-50/30'
            )}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <Loader2 className="h-6 w-6 text-primary-500 animate-spin" />
            ) : (
              <Upload className="h-6 w-6 text-gray-400" />
            )}
            <div className="text-center">
              <p className="text-xs font-medium text-gray-600">
                {uploading ? 'Uploading...' : 'Drop file here or click to browse'}
              </p>
              <p className="text-xs text-gray-400">PDF, JPG, PNG up to 10MB</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
