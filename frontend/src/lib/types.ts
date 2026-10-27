export type UserRole = 'INSTITUTION' | 'OFFICER' | 'SENIOR_OFFICER';
export type ApplicationStatus =
  | 'DRAFT' | 'SUBMITTED' | 'UNDER_VALIDATION' | 'VALIDATION_COMPLETE'
  | 'UNDER_REVIEW' | 'SENT_FOR_RECTIFICATION' | 'APPROVED_FOR_PROCESSING'
  | 'ESCALATED' | 'REJECTED';
export type ApplicationType = 'EOA_RENEWAL' | 'EOA_NEW_PROGRAMME';
export type DocType =
  | 'AFFIDAVIT' | 'STATE_NOC' | 'NAAC_CERT' | 'FIRE_SAFETY_CERT'
  | 'TER_RECEIPT' | 'LAND_BUILDING_DOC' | 'FACULTY_DATA' | 'EOA_FORM';
export type OCRStatus = 'PENDING' | 'PROCESSING' | 'COMPLETE' | 'FAILED';
export type FindingSeverity = 'HIGH' | 'MEDIUM' | 'LOW';
export type FindingStatus = 'PASS' | 'FAIL' | 'WARN' | 'SKIPPED';
export type VerificationStatus = 'VERIFIED' | 'MISMATCH' | 'PENDING' | 'FAILED' | string;
export type OfficerAction = 'APPROVE' | 'APPROVE_FOR_PROCESSING' | 'REJECT' | 'ESCALATE' | 'SEND_FOR_RECTIFICATION' | 'START_REVIEW';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  institution_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Application {
  id: string;
  institution_id: string;
  institution_name: string;
  application_type: ApplicationType;
  status: ApplicationStatus;
  submitted_at: string | null;
  academic_year: string;
  programmes: unknown[];
  created_at: string;
  updated_at: string;
  validation_score: number | null;
  documents_complete: number;
  total_documents: number;
  has_anomalies?: boolean;
  anomaly_count?: number;
}
export interface ApplicationListResponse { total: number; items: Application[]; length?: number; }
export interface Document {
  id: string;
  application_id: string;
  doc_type: DocType;
  file_name: string;
  file_size: number;
  mime_type: string;
  ocr_status: OCRStatus;
  extracted_data?: Record<string, unknown> | null;
  ocr_data?: Record<string, unknown> | null;
  validation_status?: string;
  file_hash?: string | null;
  uploaded_at: string;
  updated_at: string;
}
export interface ValidationFinding {
  id: string;
  validation_run_id: string;
  rule_id: string;
  rule_name: string;
  severity: FindingSeverity;
  status: FindingStatus;
  document_id: string | null;
  doc_type?: DocType;
  evidence: string | null;
  message: string;
  category: string;
  guidance?: string | null;
}
export interface ValidationRun {
  id: string;
  application_id: string;
  started_at: string;
  completed_at: string | null;
  overall_score: number;
  status: string;
  rules_version: string;
  findings_count_high: number;
  findings_count_medium: number;
  findings_count_low: number;
  high_severity_count?: number;
  medium_severity_count?: number;
  low_severity_count?: number;
}
export interface ValidationReport {
  application: Application;
  documents: Document[];
  alerts: ApplicationAlert[];
  run?: ValidationRun;
  validation_run?: ValidationRun;
  findings: ValidationFinding[];
  anomalies?: AnomalyFlag[];
  verifications?: VerificationResult[];
  summary?: Record<string, unknown>;
}
export interface ChecklistItem {
  rule_id: string;
  rule_name: string;
  category: string;
  severity: string;
  description?: string | null;
  status: FindingStatus;
  message: string;
  evidence?: string | null;
  document_id?: string | null;
}
export interface ChecklistResponse {
  application_id: string;
  application_type: string;
  rules_version: string;
  items: ChecklistItem[];
  counts: Record<string, number>;
  completion_percent: number;
}
export interface WorkflowStatus {
  application_id: string;
  application_status: ApplicationStatus;
  documents: { total: number; ocr: Record<string, number> };
  is_processing: boolean;
  last_updated: string;
}
export interface AnomalyFlag {
  id: string;
  check_type: string;
  severity: FindingSeverity | string;
  confidence: number;
  evidence: string;
  advisory_note?: string;
  anomaly_type: string;
  reviewed: boolean;
  flagged_at?: string;
  created_at?: string;
  is_reviewed?: boolean;
}
export interface VerificationResult {
  id: string;
  doc_type: DocType;
  source: string;
  status: VerificationStatus;
  reference_number?: string | null;
  verified_at?: string | null;
}
export interface AuditLog {
  id: string;
  event_id?: string;
  timestamp?: string;
  created_at?: string;
  actor: string;
  actor_role: string;
  action: string;
  result: string;
  notes: string | null;
  entry_hash?: string | null;
}
export interface AuditChainReport {
  is_valid: boolean;
  total_records: number;
  head_hash: string | null;
  genesis_hash: string | null;
  message: string;
  verification_message?: string;
  total_audit_events?: number;
  chain_head_hash?: string | null;
}
export interface ApplicationAlert {
  id: string;
  alert_type: string;
  severity: string;
  message: string;
  is_resolved: boolean;
  created_at: string;
  resolved_at: string | null;
  dismissed?: boolean;
}
export interface PublicVerificationData {
  verification_status: string;
  application_id: string;
  institution_name: string;
  academic_year: string;
  application_type: string;
  current_status: string;
  is_approved: boolean;
  submitted_at: string | null;
  approval_date: string | null;
  approving_officer: string | null;
  chain_integrity: AuditChainReport;
  qr_code_data_uri: string;
  public_verification_url: string;
  decision_timeline: Array<{ id: string; timestamp: string; actor: string; action: string; result: string | null; notes: string | null; entry_hash_short: string }>;
  verified_at: string;
  disclaimer: string;
}
export interface CampusCoordinates {
  application_id: string;
  institution_name: string;
  registered_campus_coordinates: { latitude: number; longitude: number; address: string };
}
export interface CampusPlotSummary {
  application_id: string;
  institution_name: string;
  registered_campus_center: { latitude: number; longitude: number };
  claimed_land_acres: number;
  location_category: string;
  sample_initial_polygon: number[][];
}
export interface CampusPlotVerificationResult {
  application_id: string;
  area_metrics: Record<string, any>;
  land_claim_evaluation: Record<string, any>;
  osm_spatial_context: Record<string, any>;
  sentinel2_satellite_context: Record<string, any>;
  has_deficit_anomaly: boolean;
  verified_at: string;
}
export interface InfrastructureScrutinyResponse {
  overall_verdict: string;
  analyzed_at: string;
  location_analysis: {
    exif_metadata?: { has_gps?: boolean; latitude?: number | null; longitude?: number | null; device_model?: string; device_make?: string };
    photo_to_campus_distance_meters?: number | null;
    risk_level: string;
    status: string;
    summary: string;
  };
  forensics_analysis: {
    is_cloned: boolean;
    cloned_feature_pairs: number;
    tamper_score: number;
    ela_heatmap_base64?: string;
    clone_preview_base64?: string;
  };
  equipment_scrutiny: {
    compliance_status: string;
    regulatory_findings: string[];
    annotated_image_base64?: string;
    aph_norm_applied?: Record<string, number>;
    detected_counts?: Record<string, number>;
    total_objects_identified: number;
    bounding_boxes?: Array<{ label: string; confidence: number; [key: string]: unknown }>;
  };
}
