// TypeScript types matching backend Pydantic schemas

export type UserRole = 'INSTITUTION' | 'OFFICER' | 'SENIOR_OFFICER';

export type ApplicationStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'UNDER_VALIDATION'
  | 'VALIDATION_COMPLETE'
  | 'UNDER_REVIEW'
  | 'SENT_FOR_RECTIFICATION'
  | 'APPROVED_FOR_PROCESSING'
  | 'ESCALATED'
  | 'REJECTED';

export type DocType =
  | 'AFFIDAVIT'
  | 'STATE_NOC'
  | 'NAAC_CERT'
  | 'FIRE_SAFETY_CERT'
  | 'TER_RECEIPT'
  | 'LAND_BUILDING_DOC'
  | 'FACULTY_DATA'
  | 'EOA_FORM';

export type OCRStatus = 'PENDING' | 'PROCESSING' | 'COMPLETE' | 'FAILED';

export type ProcessingStatus =
  | 'UPLOADED'
  | 'PROCESSING'
  | 'EXTRACTED'
  | 'VALIDATED'
  | 'FAILED';

export interface ExtractedClaimItem {
  field_name: string;
  value: any;
  page_number: number;
  confidence: number;
  source_type: string;
  raw_snippet?: string | null;
  status: 'VERIFIED' | 'UNCERTAIN' | 'NOT_FOUND';
}

export interface CrossDocumentEvidenceItem {
  document_id: string;
  doc_type: DocType;
  file_name: string;
  page: number;
  extracted_value: any;
  confidence: number;
  raw_snippet?: string | null;
}

export interface CrossDocumentFindingItem {
  finding_type: string;
  field: string;
  status: 'CONSISTENT' | 'NEEDS_REVIEW' | 'CONFLICT';
  severity: FindingSeverity;
  similarity_score: number;
  authoritative_doc_type?: string | null;
  resolution_guidance: string;
  evidence: CrossDocumentEvidenceItem[];
  explanation: string;
}

export interface CrossDocumentReport {
  application_id: string;
  total_documents_analyzed: number;
  overall_consistency_status: 'VERIFIED_CONSISTENT' | 'NEEDS_HUMAN_REVIEW' | 'CONFLICTS_DETECTED';
  total_conflicts: number;
  total_warnings: number;
  findings: CrossDocumentFindingItem[];
  analyzed_at: string;
}

export type FindingSeverity = 'HIGH' | 'MEDIUM' | 'LOW';

export type FindingStatus = 'PASS' | 'FAIL' | 'WARN' | 'SKIPPED';

export type VerificationStatus =
  | 'VERIFIED'
  | 'MISMATCH_DETECTED'
  | 'EXPIRED'
  | 'VERIFICATION_PENDING'
  | 'SOURCE_UNAVAILABLE'
  | 'MANUAL_REVIEW_REQUIRED';

export type OfficerAction =
  | 'APPROVE_FOR_PROCESSING'
  | 'SEND_FOR_RECTIFICATION'
  | 'ESCALATE'
  | 'REJECT';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  institution_id?: string;
}

export interface Application {
  id: string;
  institution_id: string;
  institution_name: string;
  academic_year: string;
  application_type: string;
  status: ApplicationStatus;
  validation_score: number | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
  has_anomalies: boolean;
  anomaly_count: number;
  documents_complete: number;
  total_documents: number;
}

export interface Document {
  id: string;
  application_id: string;
  doc_type: DocType;
  file_name: string;
  file_size: number;
  file_hash: string;
  ocr_status: OCRStatus;
  processing_status?: ProcessingStatus;
  error_message?: string | null;
  retry_count?: number;
  ocr_data: Record<string, unknown> | null;
  extracted_claims?: ExtractedClaimItem[] | null;
  uploaded_at: string;
  validation_status: FindingStatus | null;
}

export interface ValidationRun {
  id: string;
  application_id: string;
  started_at: string;
  completed_at: string | null;
  overall_score: number | null;
  findings_count: number;
  high_severity_count: number;
  medium_severity_count: number;
  low_severity_count: number;
  status: 'RUNNING' | 'COMPLETE' | 'FAILED';
}

export interface ValidationFinding {
  id: string;
  validation_run_id: string;
  rule_id: string;
  severity: FindingSeverity;
  status: FindingStatus;
  message: string;
  evidence: string | null;
  doc_type: DocType | null;
  guidance: string | null;
}

export interface AnomalyFlag {
  id: string;
  application_id: string;
  anomaly_type: string;
  confidence: number;
  evidence: string;
  flagged_at: string;
  reviewed: boolean;
}

export interface VerificationResult {
  id: string;
  document_id: string;
  doc_type: DocType;
  source: string;
  status: VerificationStatus;
  reference_number: string | null;
  verified_at: string | null;
  source_response: Record<string, unknown> | null;
}

export interface AuditLog {
  id: string;
  application_id: string;
  actor_id: string;
  actor_name: string;
  actor_role: UserRole;
  action: string;
  result: string;
  notes: string | null;
  created_at: string;
  prev_hash?: string | null;
  entry_hash?: string | null;
}

export interface ApplicationAlert {
  id: string;
  application_id: string;
  alert_type: string;
  message: string;
  severity: FindingSeverity;
  created_at: string;
  dismissed: boolean;
}

export interface ValidationReport {
  application: Application;
  validation_run: ValidationRun | null;
  findings: ValidationFinding[];
  anomalies: AnomalyFlag[];
  verifications: VerificationResult[];
  documents: Document[];
  audit_logs: AuditLog[];
  alerts: ApplicationAlert[];
}

export interface MetricsSummary {
  total_applications: number;
  pending_review: number;
  anomalies_flagged: number;
  verified_today: number;
  avg_validation_score: number;
  status_breakdown: Record<ApplicationStatus, number>;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface CreateApplicationPayload {
  institution_name: string;
  academic_year: string;
  application_type: string;
}

export interface CampusCoordinates {
  application_id: string;
  institution_name: string;
  registered_campus_coordinates: {
    latitude: number;
    longitude: number;
    address: string;
  };
}

export interface GeoLocationAnalysis {
  exif_metadata?: {
    has_gps: boolean;
    latitude: number | null;
    longitude: number | null;
    altitude: number | null;
    device_make: string | null;
    device_model: string | null;
    timestamp: string | null;
  };
  campus_coordinates?: {
    latitude: number;
    longitude: number;
  };
  live_submission_coordinates?: {
    latitude: number;
    longitude: number;
  };
  photo_to_campus_distance_meters: number | null;
  live_to_campus_distance_meters: number | null;
  photo_to_live_distance_meters: number | null;
  status: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  summary: string;
  anomaly_flags: Array<{ code: string; severity: string; message: string }>;
}

export interface ForensicsAnalysis {
  tamper_score: number;
  is_tampered: boolean;
  is_cloned: boolean;
  cloned_feature_pairs: number;
  ela_heatmap_base64: string | null;
  clone_preview_base64: string | null;
  stats: {
    mean_difference: number;
    std_deviation: number;
    high_contrast_ratio_pct: number;
  };
}

export interface EquipmentScrutiny {
  facility_type: string;
  facility_label: string;
  detected_counts: Record<string, number>;
  total_objects_identified: number;
  bounding_boxes: Array<{
    label: string;
    confidence: number;
    bbox: number[];
    is_safety_critical?: boolean;
  }>;
  annotated_image_base64: string | null;
  compliance_status: 'COMPLIANT' | 'DEFICIENT';
  regulatory_findings: string[];
  aph_norm_applied: Record<string, any>;
}

export interface InfrastructureScrutinyResponse {
  application_id: string;
  facility_type: string;
  overall_verdict: string;
  has_critical_anomalies: boolean;
  location_analysis: GeoLocationAnalysis;
  forensics_analysis: ForensicsAnalysis;
  equipment_scrutiny: EquipmentScrutiny;
  analyzed_at: string;
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
  chain_integrity: {
    is_valid: boolean;
    total_audit_events: number;
    chain_head_hash: string;
    genesis_hash: string;
    verification_message: string;
  };
  qr_code_data_uri: string;
  public_verification_url: string;
  decision_timeline: Array<{
    id: string;
    timestamp: string;
    actor: string;
    action: string;
    result: string | null;
    notes: string | null;
    entry_hash_short: string;
  }>;
  verified_at: string;
  disclaimer: string;
}

export interface CampusPlotSummary {
  application_id: string;
  institution_name: string;
  registered_campus_center: {
    latitude: number;
    longitude: number;
  };
  claimed_land_acres: number;
  location_category: string;
  sample_initial_polygon: number[][];
}

export interface CampusPlotVerificationResult {
  application_id: string;
  area_metrics: {
    vertices_count: number;
    centroid: { latitude: number; longitude: number };
    area_sq_meters: number;
    area_acres: number;
    area_hectares: number;
    perimeter_meters: number;
  };
  land_claim_evaluation: {
    claimed_acres: number;
    measured_acres: number;
    difference_acres: number;
    variance_percent: number;
    location_category: string;
    aicte_min_norm_acres: number;
    meets_aicte_norm: boolean;
    claim_status: string;
    discrepancy_level: string;
    explanation: string;
  };
  osm_spatial_context: {
    source: string;
    status: string;
    connected_road_ways: string[];
    has_road_connectivity: boolean;
    nearby_waterbodies: string[];
    nearby_civic_facilities: string[];
    query_radius_meters: number;
  };
  sentinel2_satellite_context: {
    satellite_constellation: string;
    spatial_resolution: string;
    spectral_bands_used: string[];
    indices: {
      ndwi_water_index: number;
      ndvi_vegetation_index: number;
    };
    terrain_classification: string;
    water_body_conflict: string;
    reserve_forest_conflict: string;
    is_terrain_viable: boolean;
    honest_resolution_disclosure: string;
  };
  has_deficit_anomaly: boolean;
  verified_at: string;
}

export interface AuditChainReport {
  application_id: string;
  is_valid: boolean;
  total_records: number;
  genesis_hash: string;
  head_hash: string;
  verified_at: string;
  records: Array<{
    step: number;
    id: string;
    timestamp: string;
    actor: string;
    action: string;
    result: string | null;
    prev_hash_short: string;
    entry_hash_short: string;
    entry_hash_full: string;
  }>;
  message: string;
}
