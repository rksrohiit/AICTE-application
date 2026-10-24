import axios from 'axios';
import type { Application, ApplicationListResponse, ApplicationAlert, AuditLog, AuditChainReport, CampusPlotSummary, CampusPlotVerificationResult, CampusCoordinates, Document, InfrastructureScrutinyResponse, PublicVerificationData, ValidationReport, User, DocType } from './types';

const client = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1' });
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const api = {
  auth: {
    login: async (email: string, password: string) => (await client.post<{ access_token: string; user: User }>('/auth/login', { email, password })).data,
    me: async () => (await client.get<User>('/auth/me')).data,
    register: async (payload: { email: string; password: string; full_name: string; institution_id?: string }) => (await client.post<User>('/auth/register', payload)).data,
  },
  applications: {
    list: async () => (await client.get<ApplicationListResponse>('/applications')).data,
    get: async (id: string) => (await client.get<Application>(`/applications/${id}`)).data,
    create: async (payload: { institution_name: string; application_type: string; academic_year: string; programmes?: unknown[] }) => (await client.post<Application>('/applications', { ...payload, programmes: payload.programmes ?? [] })).data,
    validate: async (id: string) => (await client.post(`/applications/${id}/validate`)).data,
    getValidationReport: async (id: string) => (await client.get<ValidationReport>(`/applications/${id}/validation-report`)).data,
    getAlerts: async (id: string) => (await client.get<ApplicationAlert[]>(`/applications/${id}/alerts`)).data,
    getAudit: async (id: string) => (await client.get<AuditLog[]>(`/applications/${id}/audit`)).data,
    verifyAuditChain: async (id: string) => (await client.get<AuditChainReport>(`/applications/${id}/audit/verify-chain`)).data,
    takeAction: async (id: string, action: string, notes: string) => (await client.post(`/applications/${id}/actions`, { action, notes })).data,
    generateReport: async (id: string) => (await client.get<Blob>(`/applications/${id}/generate-report`, { responseType: 'blob' })).data,
  },
  documents: {
    list: async (id: string) => (await client.get<Document[]>(`/applications/${id}/documents`)).data,
    upload: async (id: string, docType: DocType, file: File) => { const form = new FormData(); form.append('doc_type', docType); form.append('file', file); return (await client.post(`/applications/${id}/documents`, form)).data; },
  },
  metrics: { summary: async () => (await client.get('/metrics/summary')).data },
  publicVerify: { get: async (id: string) => (await client.get<PublicVerificationData>(`/public/verify/${id}`)).data },
  campusGeo: {
    getPlotSummary: async (id: string) => (await client.get<CampusPlotSummary>(`/applications/${id}/geo/plot-summary`)).data,
    verifyPlot: async (id: string, payload: { polygon_coordinates: number[][]; claimed_acres: number; location_category: string }) => (await client.post<CampusPlotVerificationResult>(`/applications/${id}/geo/verify-plot`, payload)).data,
  },
  infrastructure: {
    getCampusCoordinates: async (id: string) => (await client.get<CampusCoordinates>(`/applications/${id}/infrastructure/campus-coordinates`)).data,
    analyze: async (id: string, form: FormData) => (await client.post<InfrastructureScrutinyResponse>(`/applications/${id}/infrastructure/analyze`, form)).data,
  },
  audit: { verifyChain: async (id: string) => (await client.get<AuditChainReport>(`/applications/${id}/audit/verify-chain`)).data },
};
