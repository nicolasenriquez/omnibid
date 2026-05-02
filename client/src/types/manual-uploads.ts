export type ManualUploadDatasetType = "licitacion" | "orden_compra";

export type ManualUploadLimit = {
  max_size_bytes: number;
  max_size_label: string;
};

export type ManualUploadDatasetSummary = Record<string, number>;

export type ManualUploadSourceFile = {
  id: string;
  dataset_type: ManualUploadDatasetType;
  file_name: string;
  file_path: string;
  file_hash_sha256: string;
  status: string;
  registered_at: string | null;
  source_meta: Record<string, unknown> | null;
};

export type ManualUploadPreflightResponse = {
  file_token: string;
  status: "staged" | "consumed";
  dataset_type: ManualUploadDatasetType;
  original_filename: string;
  canonical_filename: string;
  file_size_bytes: number;
  file_hash_sha256: string;
  row_count: number;
  missing_required_columns: string[];
  content_type: string | null;
  staged_file_path: string;
  metadata_path: string;
  staged_at: string;
  consumed_at: string | null;
  consumed_job_id: string | null;
  duplicate_source_file: ManualUploadSourceFile | null;
  dataset_summary: ManualUploadDatasetSummary;
  upload_limits: ManualUploadLimit;
};

export type ManualUploadStep = {
  name: string;
  status: string;
  rows_in: number | null;
  rows_out: number | null;
  rows_rejected: number | null;
  error_details: Record<string, unknown> | null;
};

export type ManualUploadTelemetry = {
  processed_rows: number;
  accepted_rows: number;
  inserted_delta_rows: number;
  duplicate_existing_rows: number;
  rejected_rows: number;
  normalized_rows: number;
  silver_rows: number;
  normalized_inserted_delta_rows: number;
  silver_inserted_delta_rows: number;
  raw_ingest: Record<string, number>;
  entity_metrics: Record<string, Record<string, number>>;
};

export type ManualUploadProgress = {
  phase: "preparing" | "raw_ingest" | "normalized" | "finalizing" | "completed" | "failed";
  label: string;
  detail: string;
  percent: number;
  raw_processed_rows: number;
  raw_total_rows: number;
  normalized_processed_rows: number;
  normalized_total_rows: number;
  updated_at: string;
};

export type ManualUploadJobResponse = {
  job_id: string;
  status: string;
  terminal_state: boolean;
  progress: ManualUploadProgress;
  step: ManualUploadStep;
  telemetry: ManualUploadTelemetry;
  source_file: ManualUploadSourceFile | null;
  file_token: string;
  dataset_type: ManualUploadDatasetType;
  original_filename: string;
  canonical_filename: string;
  file_hash_sha256: string;
  row_count: number;
};
