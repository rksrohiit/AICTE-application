import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { Check, ChevronRight, ChevronLeft, Send } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { DOC_TYPES_ALL } from '@/lib/constants';
import { getDocTypeLabel } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { DocumentUploadCard } from '@/components/shared/DocumentUploadCard';
import type { DocType, Document } from '@/lib/types';

const step1Schema = z.object({
  institution_name: z.string().min(3, 'Institution name must be at least 3 characters'),
  academic_year: z.string().min(1, 'Please select an academic year'),
  application_type: z.string().min(1, 'Please select an application type'),
});

type Step1Data = z.infer<typeof step1Schema>;

const ACADEMIC_YEARS = ['2024-25', '2025-26', '2026-27'];
const APPLICATION_TYPES = [{ value: 'EOA_RENEWAL', label: 'Extension of Approval (EOA) Renewal' }];

const STEPS = ['Application Info', 'Upload Documents', 'Review & Submit'];

interface StepperProps {
  current: number;
  steps: string[];
}

function Stepper({ current, steps }: StepperProps) {
  return (
    <div className="flex items-center gap-0 mb-8">
      {steps.map((step, index) => (
        <div key={step} className="flex items-center flex-1 last:flex-none">
          <div className="flex items-center gap-2">
            <div
              className={`h-8 w-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
                index < current
                  ? 'bg-success-600 text-white'
                  : index === current
                  ? 'bg-primary-900 text-white ring-4 ring-primary-100'
                  : 'bg-gray-200 text-gray-500'
              }`}
            >
              {index < current ? <Check className="h-4 w-4" /> : index + 1}
            </div>
            <span
              className={`text-sm font-medium hidden sm:block ${
                index === current ? 'text-primary-900' : index < current ? 'text-success-700' : 'text-gray-400'
              }`}
            >
              {step}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div
              className={`flex-1 h-0.5 mx-3 ${index < current ? 'bg-success-400' : 'bg-gray-200'}`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

export default function NewApplication() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Partial<Record<DocType, Document>>>({});
  const [uploadingDoc, setUploadingDoc] = useState<DocType | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<Step1Data>({
    resolver: zodResolver(step1Schema),
    defaultValues: {
      institution_name: user?.full_name ?? '',
      application_type: 'EOA_RENEWAL',
    },
  });

  const handleStep1Submit = async (data: Step1Data) => {
    try {
      setIsSubmitting(true);
      const app = await api.applications.create(data);
      setApplicationId(app.id);
      setCurrentStep(1);
      toast.success('Application created! Please upload your documents.');
    } catch {
      toast.error('Failed to create application. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpload = async (docType: DocType, file: File) => {
    if (!applicationId) return;
    setUploadingDoc(docType);
    try {
      const doc = await api.documents.upload(applicationId, docType, file);
      setDocuments((prev) => ({ ...prev, [docType]: doc }));
      toast.success(`${getDocTypeLabel(docType)} uploaded successfully`);
    } catch {
      toast.error(`Failed to upload ${getDocTypeLabel(docType)}`);
    } finally {
      setUploadingDoc(null);
    }
  };

  const handleSubmitApplication = async () => {
    if (!applicationId) return;
    setIsSubmitting(true);
    try {
      await api.applications.validate(applicationId);
      toast.success('Application submitted! AI validation is in progress.');
      navigate(`/institution/applications/${applicationId}`);
    } catch {
      toast.error('Failed to submit application. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const uploadedCount = Object.keys(documents).length;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">New Application</h1>
        <p className="text-sm text-gray-500 mt-0.5">Extension of Approval (EOA) Renewal</p>
      </div>

      {/* Stepper */}
      <Stepper current={currentStep} steps={STEPS} />

      {/* Step 1: Application Info */}
      {currentStep === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Application Information</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(handleStep1Submit)} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Institution Name
                </label>
                <input
                  {...register('institution_name')}
                  type="text"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Enter institution name"
                />
                {errors.institution_name && (
                  <p className="mt-1 text-xs text-danger-600">{errors.institution_name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Academic Year
                </label>
                <select
                  {...register('academic_year')}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
                >
                  <option value="">Select academic year</option>
                  {ACADEMIC_YEARS.map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
                </select>
                {errors.academic_year && (
                  <p className="mt-1 text-xs text-danger-600">{errors.academic_year.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Application Type
                </label>
                <select
                  {...register('application_type')}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
                >
                  {APPLICATION_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
                {errors.application_type && (
                  <p className="mt-1 text-xs text-danger-600">{errors.application_type.message}</p>
                )}
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  type="submit"
                  loading={isSubmitting}
                  rightIcon={<ChevronRight className="h-4 w-4" />}
                >
                  Continue to Documents
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Document Upload */}
      {currentStep === 1 && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Upload Documents</CardTitle>
              <span className="text-sm text-gray-500">
                {uploadedCount} of {DOC_TYPES_ALL.length} uploaded
              </span>
            </CardHeader>
            <CardContent>
              <div className="w-full bg-gray-200 rounded-full h-1.5 mb-4">
                <div
                  className="bg-primary-700 h-1.5 rounded-full transition-all"
                  style={{ width: `${(uploadedCount / DOC_TYPES_ALL.length) * 100}%` }}
                />
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-3 sm:grid-cols-2">
            {DOC_TYPES_ALL.map((docType) => (
              <DocumentUploadCard
                key={docType}
                docType={docType}
                document={documents[docType] ?? null}
                onUpload={handleUpload}
                uploading={uploadingDoc === docType}
              />
            ))}
          </div>

          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setCurrentStep(0)} leftIcon={<ChevronLeft className="h-4 w-4" />}>
              Back
            </Button>
            <Button onClick={() => setCurrentStep(2)} rightIcon={<ChevronRight className="h-4 w-4" />}>
              Review Application
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Review & Submit */}
      {currentStep === 2 && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Review & Submit</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Application info summary */}
                <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                  <p className="text-sm font-semibold text-gray-700 mb-3">Application Details</p>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-gray-500">Institution</p>
                      <p className="font-medium text-gray-900">{getValues('institution_name')}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Academic Year</p>
                      <p className="font-medium text-gray-900">{getValues('academic_year')}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Application Type</p>
                      <p className="font-medium text-gray-900">EOA Renewal</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Documents Uploaded</p>
                      <p className="font-medium text-gray-900">
                        {uploadedCount}/{DOC_TYPES_ALL.length}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Document checklist */}
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-3">Document Checklist</p>
                  <div className="space-y-2">
                    {DOC_TYPES_ALL.map((docType) => {
                      const doc = documents[docType];
                      return (
                        <div
                          key={docType}
                          className="flex items-center gap-3 py-2 px-3 rounded-lg bg-gray-50 border border-gray-100"
                        >
                          <div
                            className={`h-5 w-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                              doc ? 'bg-success-500' : 'bg-gray-200'
                            }`}
                          >
                            {doc && <Check className="h-3 w-3 text-white" />}
                          </div>
                          <span className="text-sm text-gray-700 flex-1">
                            {getDocTypeLabel(docType)}
                          </span>
                          {doc ? (
                            <span className="text-xs text-gray-400 truncate max-w-[120px]">
                              {doc.file_name}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">Not uploaded</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button variant="secondary" onClick={() => setCurrentStep(1)} leftIcon={<ChevronLeft className="h-4 w-4" />}>
              Back to Documents
            </Button>
            <Button
              loading={isSubmitting}
              leftIcon={<Send className="h-4 w-4" />}
              onClick={handleSubmitApplication}
            >
              Submit Application
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
