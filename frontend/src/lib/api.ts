import axios from 'axios';
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
      const response = await apiClient.get<any>('/applications');
      if (Array.isArray(response.data)) {
        return response.data;
      }
      return response.data?.items || [];
    },

    get: async (id: string): Promise<Application> => {
      const response = await apiClient.get<Application>(`/applications/${id}`);
      return response.data;
    },

    create: async (data: CreateApplicationPayload): Promise<Application> => {
      const response = await apiClient.post<Application>('/applications', data);
      return response.data;
    },

    validate: async (id: string): Promise<void> => {
      await apiClient.post(`/applications/${id}/validate`);
    },

    getValidationReport: async (id: string): Promise<ValidationReport> => {
      const response = await apiClient.get<ValidationReport>(`/applications/${id}/report`);
      return response.data;
    },

    getAlerts: async (id: string): Promise<ApplicationAlert[]> => {
      const response = await apiClient.get<ApplicationAlert[]>(`/applications/${id}/alerts`);
      return response.data;
    },

    getAudit: async (id: string): Promise<AuditLog[]> => {
      const response = await apiClient.get<AuditLog[]>(`/applications/${id}/audit`);
      return response.data;
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
      const response = await apiClient.get<Document[]>(`/applications/${applicationId}/documents`);
      return response.data;
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
