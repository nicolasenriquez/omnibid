import { useMemo } from "react";

import { formatCount } from "@/src/lib/formatters/opportunities";
import type {
  ManualUploadDatasetType,
  ManualUploadJobResponse,
  ManualUploadPreflightResponse,
} from "@/src/types/manual-uploads";

export type UploadConsoleEntry = {
  level: "info" | "done" | "error" | "muted" | "running";
  text: string;
};

export type UploadWorkflowStepState = "idle" | "active" | "done" | "error";

export type UploadWorkflowStep = {
  key: "prepare" | "validate" | "process";
  label: string;
  summary: string;
  state: UploadWorkflowStepState;
};

export type UploadJobState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "running"; data: ManualUploadJobResponse }
  | { status: "success"; data: ManualUploadJobResponse }
  | { status: "error"; message: string; statusCode: number | null };

export type UploadPreflightState =
  | { status: "idle" | "loading" }
  | { status: "success"; data: ManualUploadPreflightResponse }
  | { status: "error"; message: string; statusCode: number | null };

type UploadFlowStage =
  | "idle"
  | "ready"
  | "validating"
  | "validated"
  | "processing"
  | "success"
  | "error";

type UploadConsoleStatusTone = "success" | "running" | "danger" | "neutral";

function formatDatasetTypeLabel(datasetType: ManualUploadDatasetType): string {
  return datasetType === "licitacion" ? "Licitaciones" : "Órdenes de compra";
}

type UploadWorkflowState = {
  uploadCanValidate: boolean;
  uploadJobData: ManualUploadJobResponse | null;
  uploadJobProgress: ManualUploadJobResponse["progress"] | null;
  uploadJobIsActive: boolean;
  uploadCanProcess: boolean;
  uploadConsoleStatus: { label: string; tone: UploadConsoleStatusTone };
  uploadFlowStage: UploadFlowStage;
  uploadFlowBusy: boolean;
  uploadFlowTone: UploadConsoleStatusTone;
  uploadTriggerLabel: string;
  uploadFlowHeadline: string;
  uploadWorkflowSteps: UploadWorkflowStep[];
};

type UploadWorkflowStateInput = {
  uploadDatasetType: ManualUploadDatasetType | "";
  uploadFile: File | null;
  uploadPreflightState: UploadPreflightState;
  uploadJobState: UploadJobState;
};

function deriveUploadWorkflowState(input: UploadWorkflowStateInput): UploadWorkflowState {
  const {
    uploadDatasetType,
    uploadFile,
    uploadPreflightState,
    uploadJobState,
  } = input;
  const uploadCanValidate = Boolean(uploadDatasetType && uploadFile);
  const uploadJobData =
    uploadJobState.status === "running" || uploadJobState.status === "success"
      ? uploadJobState.data
      : null;
  const uploadJobProgress = uploadJobData?.progress ?? null;
  const uploadJobIsActive = uploadJobState.status === "loading" || uploadJobState.status === "running";
  const uploadCanProcess =
    uploadPreflightState.status === "success" &&
    !uploadJobIsActive &&
    uploadJobState.status !== "success";

  const uploadConsoleStatus =
    uploadJobState.status === "success"
      ? { label: "Completado", tone: "success" as const }
      : uploadJobState.status === "loading" || uploadJobState.status === "running"
        ? { label: "Procesando", tone: "running" as const }
        : uploadPreflightState.status === "loading"
          ? { label: "Validando", tone: "running" as const }
          : uploadPreflightState.status === "error" || uploadJobState.status === "error"
            ? { label: "Revisar", tone: "danger" as const }
            : { label: "Preparado", tone: "neutral" as const };
  const uploadFlowStage: UploadFlowStage =
    uploadJobState.status === "loading" || uploadJobState.status === "running"
      ? "processing"
      : uploadJobState.status === "success"
        ? "success"
        : uploadJobState.status === "error"
          ? "error"
          : uploadPreflightState.status === "loading"
            ? "validating"
            : uploadPreflightState.status === "success"
              ? "validated"
              : uploadPreflightState.status === "error"
                ? "error"
                : uploadCanValidate
                  ? "ready"
                  : "idle";
  const uploadFlowBusy = uploadFlowStage === "validating" || uploadFlowStage === "processing";
  const uploadFlowTone =
    uploadFlowStage === "processing" || uploadFlowStage === "validating"
      ? "running"
      : uploadFlowStage === "success"
        ? "success"
        : uploadFlowStage === "error"
          ? "danger"
          : "neutral";
  const uploadTriggerLabel =
    uploadFlowStage === "processing"
      ? "Ingesta en curso"
      : uploadFlowStage === "validating"
        ? "Validando ingesta"
        : "Centro de Ingesta";
  const uploadFlowHeadline =
    uploadFlowStage === "processing"
      ? uploadJobProgress
        ? `${uploadJobProgress.label} · ${uploadJobProgress.percent}%`
        : "Las capas Raw, Normalized y Silver siguen en ejecución"
      : uploadFlowStage === "validating"
        ? "Validando archivo antes de abrir el Centro de Ingesta"
      : uploadFlowStage === "validated"
          ? "Archivo validado. Listo para cargar."
          : uploadFlowStage === "success"
            ? "Ingesta cerrada con resultado."
            : uploadFlowStage === "error"
              ? "Flujo con error. Revisa consola."
              : uploadCanValidate
                ? "Paso siguiente: valida el CSV."
                : "Prepara conjunto y CSV para arrancar.";

  const prepareSummary = uploadDatasetType
    ? `${formatDatasetTypeLabel(uploadDatasetType)} · ${uploadFile ? uploadFile.name : "CSV pendiente"}`
    : uploadFile
      ? `${uploadFile.name} · conjunto pendiente`
      : "Selecciona conjunto y CSV";
  const validateSummary =
    uploadPreflightState.status === "loading"
      ? "Chequeando columnas, hash y tamaño."
      : uploadPreflightState.status === "success"
        ? `${formatCount(uploadPreflightState.data.row_count)} filas validadas.`
        : uploadPreflightState.status === "error"
          ? uploadPreflightState.message
          : "Corre validación antes de cargar.";
  const processSummary =
    uploadJobState.status === "loading"
      ? "Arrancando proceso en backend."
      : uploadJobState.status === "running" && uploadJobProgress
        ? `${uploadJobProgress.percent}% · ${uploadJobProgress.label}`
        : uploadJobState.status === "success"
          ? `Proceso ${uploadJobState.data.job_id.slice(0, 8)} completo.`
          : uploadJobState.status === "error"
            ? uploadJobState.message
            : "Se activa después de la validación previa aprobada.";

  const uploadWorkflowSteps: UploadWorkflowStep[] = [
    {
      key: "prepare",
      label: "Preparar",
      summary: prepareSummary,
      state:
        uploadPreflightState.status === "loading" ||
        uploadPreflightState.status === "success" ||
        uploadPreflightState.status === "error" ||
        uploadJobState.status === "loading" ||
        uploadJobState.status === "success"
          ? "done"
          : uploadDatasetType || uploadFile
            ? "active"
            : "idle",
    },
    {
      key: "validate",
      label: "Validar",
      summary: validateSummary,
      state:
        uploadPreflightState.status === "loading"
          ? "active"
          : uploadPreflightState.status === "success"
            ? "done"
            : uploadPreflightState.status === "error"
              ? "error"
              : uploadCanValidate
                ? "active"
                : "idle",
    },
    {
      key: "process",
      label: "Cargar",
      summary: processSummary,
      state:
        uploadJobState.status === "loading"
          ? "active"
          : uploadJobState.status === "running"
            ? "active"
            : uploadJobState.status === "success"
              ? "done"
              : uploadJobState.status === "error"
                ? "error"
                : uploadPreflightState.status === "success"
                  ? "active"
                  : "idle",
    },
  ];

  return {
    uploadCanValidate,
    uploadJobData,
    uploadJobProgress,
    uploadJobIsActive,
    uploadCanProcess,
    uploadConsoleStatus,
    uploadFlowStage,
    uploadFlowBusy,
    uploadFlowTone,
    uploadTriggerLabel,
    uploadFlowHeadline,
    uploadWorkflowSteps,
  };
}

export function useUploadWorkflowState(input: UploadWorkflowStateInput): UploadWorkflowState {
  const {
    uploadDatasetType,
    uploadFile,
    uploadPreflightState,
    uploadJobState,
  } = input;

  return useMemo(
    () => deriveUploadWorkflowState({
      uploadDatasetType,
      uploadFile,
      uploadPreflightState,
      uploadJobState,
    }),
    [uploadDatasetType, uploadFile, uploadPreflightState, uploadJobState],
  );
}
