import axios from 'axios';
import mockApplications from './mockApplications.json';
import mockDocuments from './mockDocuments.json';
import mockValidationRuns from './mockValidationRuns.json';
import mockValidationFindings from './mockValidationFindings.json';
import mockAuditLogs from './mockAuditLogs.json';
import mockAlerts from './mockAlerts.json';
import mockVerifications from './mockVerifications.json';
import mockAnomalies from './mockAnomalies.json';
import type {
  LoginResponse,
  User,
  Application,
  ValidationReport,
  ApplicationAlert,
  AuditLog,
  Document,
  MetricsSummary,
  CreateApplicationPayload,
  OfficerAction,
  CampusCoordinates,
  InfrastructureScrutinyResponse,
  PublicVerificationData,
  CampusPlotSummary,
  CampusPlotVerificationResult,
  AuditChainReport,
  CrossDocumentReport,
} from './types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor — attach Bearer token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — handle 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const api = {
  auth: {
    login: async (email: string, password: string): Promise<LoginResponse> => {
      const response = await apiClient.post<LoginResponse>('/auth/login', {
        email,
        password,
      });
      return response.data;
    },

    me: async (): Promise<User> => {
      const response = await apiClient.get<User>('/auth/me');
      return response.data;
    },
  },

  applications: {
    list: async (): Promise<Application[]> => {
      try {
        const response = await apiClient.get<any>('/applications');
        let items: Application[] = [];
        if (Array.isArray(response.data)) {
          items = response.data;
        } else if (response.data?.items) {
          items = response.data.items;
        }
        if (items.length > 0) {
          return items;
        }
      } catch (err) {
        console.warn('API /applications failed, using demo data:', err);
      }
      return mockApplications as unknown as Application[];
    },

    get: async (id: string): Promise<Application> => {
      try {
        const response = await apiClient.get<Application>(`/applications/${id}`);
        if (response.data) return response.data;
      } catch (err) {
        console.warn(`API /applications/${id} failed, checking demo data:`, err);
      }
      const cleanId = id.replace(/-/g, '').toLowerCase();
      const fallback = (mockApplications as any[]).find(
        (a) => a.id === id || a.id.replace(/-/g, '').toLowerCase() === cleanId
      );
      if (fallback) return fallback as Application;
      throw new Error('Application not found');
    },

    create: async (data: CreateApplicationPayload): Promise<Application> => {
      const response = await apiClient.post<Application>('/applications', data);
      return response.data;
    },

    validate: async (id: string): Promise<void> => {
      await apiClient.post(`/applications/${id}/validate`);
    },

    getValidationReport: async (id: string): Promise<ValidationReport> => {
      try {
        const response = await apiClient.get<ValidationReport>(`/applications/${id}/report`);
        if (response.data) return response.data;
      } catch (err) {
        console.warn(`API /applications/${id}/report failed, using demo report:`, err);
      }
      const cleanId = id.replace(/-/g, '').toLowerCase();
      const app = (mockApplications as any[]).find(
        (a) => a.id === id || a.id.replace(/-/g, '').toLowerCase() === cleanId
      );
      const run = (mockValidationRuns as any[]).find(
        (r) => r.application_id === id || r.application_id?.replace(/-/g, '').toLowerCase() === cleanId
      );
      const findings = (mockValidationFindings as any[]).filter(
        (f) =>
          !run ||
          f.validation_run_id === run.id ||
          f.validation_run_id?.replace(/-/g, '').toLowerCase() === run?.id?.replace(/-/g, '').toLowerCase()
      );
      const anomalies = (mockAnomalies as any[]).filter(
        (a) => a.application_id === id || a.application_id?.replace(/-/g, '').toLowerCase() === cleanId
      );
      const verifications = (mockVerifications as any[]).filter(
        (v) => v.application_id === id || v.application_id?.replace(/-/g, '').toLowerCase() === cleanId
      );
      return {
        application: app as Application,
        validation_run: run || null,
        findings: findings || [],
        anomalies: anomalies || [],
        verifications: verifications || [],
      } as unknown as ValidationReport;
    },

    getAlerts: async (id: string): Promise<ApplicationAlert[]> => {
      try {
        const response = await apiClient.get<ApplicationAlert[]>(`/applications/${id}/alerts`);
        if (Array.isArray(response.data) && response.data.length > 0) return response.data;
      } catch (err) {
        console.warn(`API /applications/${id}/alerts failed, using demo alerts:`, err);
      }
      const cleanId = id.replace(/-/g, '').toLowerCase();
      return (mockAlerts as any[]).filter(
        (a) => a.application_id === id || a.application_id?.replace(/-/g, '').toLowerCase() === cleanId
      );
    },

    getAudit: async (id: string): Promise<AuditLog[]> => {
      try {
        const response = await apiClient.get<AuditLog[]>(`/applications/${id}/audit`);
        if (Array.isArray(response.data) && response.data.length > 0) return response.data;
      } catch (err) {
        console.warn(`API /applications/${id}/audit failed, using demo audit logs:`, err);
      }
      const cleanId = id.replace(/-/g, '').toLowerCase();
      return (mockAuditLogs as any[]).filter(
        (a) => a.application_id === id || a.application_id?.replace(/-/g, '').toLowerCase() === cleanId
      );
    },

    takeAction: async (id: string, action: OfficerAction, notes: string): Promise<void> => {
      await apiClient.post(`/applications/${id}/action`, { action, notes });
    },

    generateReport: async (id: string): Promise<Blob> => {
      const response = await apiClient.get(`/applications/${id}/generate-report`, {
        responseType: 'blob',
      });
      return response.data;
    },
  },

  documents: {
    upload: async (applicationId: string, docType: string, file: File): Promise<Document> => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('doc_type', docType);
      const response = await apiClient.post<Document>(
        `/applications/${applicationId}/documents`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      return response.data;
    },

    list: async (applicationId: string): Promise<Document[]> => {
      try {
        const response = await apiClient.get<Document[]>(`/applications/${applicationId}/documents`);
        if (Array.isArray(response.data) && response.data.length > 0) return response.data;
      } catch (err) {
        console.warn(`API /documents failed for ${applicationId}, using demo documents:`, err);
      }
      const cleanId = applicationId.replace(/-/g, '').toLowerCase();
      return (mockDocuments as any[]).filter(
        (d) => d.application_id === applicationId || d.application_id?.replace(/-/g, '').toLowerCase() === cleanId
      );
    },

    retry: async (documentId: string): Promise<Document> => {
      const response = await apiClient.post<Document>(`/documents/${documentId}/retry`);
      return response.data;
    },

    getCrossDocumentConsistency: async (applicationId: string): Promise<CrossDocumentReport> => {
      const response = await apiClient.get<CrossDocumentReport>(
        `/applications/${applicationId}/cross-document-consistency`
      );
      return response.data;
    },
  },

  metrics: {
    summary: async (): Promise<MetricsSummary> => {
      const response = await apiClient.get<MetricsSummary>('/metrics/summary');
      return response.data;
    },
  },

  infrastructure: {
    getCampusCoordinates: async (applicationId: string): Promise<CampusCoordinates> => {
      const response = await apiClient.get<CampusCoordinates>(
        `/applications/${applicationId}/infrastructure/campus-coordinates`
      );
      return response.data;
    },

    analyze: async (
      applicationId: string,
      formData: FormData
    ): Promise<InfrastructureScrutinyResponse> => {
      const response = await apiClient.post<InfrastructureScrutinyResponse>(
        `/applications/${applicationId}/infrastructure/analyze`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
        }
      );
      return response.data;
    },
  },

  publicVerify: {
    get: async (applicationId: string): Promise<PublicVerificationData> => {
      const response = await apiClient.get<PublicVerificationData>(`/public/verify/${applicationId}`);
      return response.data;
    },
  },

  campusGeo: {
    getPlotSummary: async (applicationId: string): Promise<CampusPlotSummary> => {
      const response = await apiClient.get<CampusPlotSummary>(`/applications/${applicationId}/geo/plot-summary`);
      return response.data;
    },

    verifyPlot: async (
      applicationId: string,
      data: {
        polygon_coordinates: number[][];
        claimed_acres?: number;
        location_category?: string;
      }
    ): Promise<CampusPlotVerificationResult> => {
      const response = await apiClient.post<CampusPlotVerificationResult>(
        `/applications/${applicationId}/geo/verify-plot`,
        data
      );
      return response.data;
    },
  },

  audit: {
    verifyChain: async (applicationId: string): Promise<AuditChainReport> => {
      const response = await apiClient.get<AuditChainReport>(`/applications/${applicationId}/audit/verify-chain`);
      return response.data;
    },
  },
};

export default apiClient;
