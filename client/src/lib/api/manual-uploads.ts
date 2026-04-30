import { requestJson } from "@/src/lib/api/http";
import type {
  ManualUploadDatasetType,
  ManualUploadJobResponse,
  ManualUploadPreflightResponse,
} from "@/src/types/manual-uploads";

export async function preflightManualCsvUpload(
  file: File,
  datasetType: ManualUploadDatasetType,
  signal?: AbortSignal,
): Promise<ManualUploadPreflightResponse> {
  const formData = new FormData();
  formData.append("dataset_type", datasetType);
  formData.append("file", file, file.name);

  return requestJson<ManualUploadPreflightResponse>("/uploads/procurement-csv/preflight", {
    method: "POST",
    body: formData,
    signal,
  });
}

export async function processManualCsvUpload(
  fileToken: string,
  signal?: AbortSignal,
): Promise<ManualUploadJobResponse> {
  return requestJson<ManualUploadJobResponse>(
    `/uploads/procurement-csv/${encodeURIComponent(fileToken)}/process`,
    {
      method: "POST",
      signal,
    },
  );
}

export async function fetchManualCsvUploadJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<ManualUploadJobResponse> {
  return requestJson<ManualUploadJobResponse>(
    `/uploads/procurement-csv/jobs/${encodeURIComponent(jobId)}`,
    { signal },
  );
}
