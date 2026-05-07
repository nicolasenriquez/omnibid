import { ApiClientError } from "@/src/lib/api/http";
import {
  formatCount,
  formatMoney,
  formatStage,
  formatUnavailable,
} from "@/src/lib/formatters/opportunities";
import {
  PROCUREMENT_TYPE_LABELS,
  WORKSPACE_TAB_LABELS,
} from "@/src/features/opportunity-workspace/display-contract";
import type {
  ManualUploadDatasetType,
} from "@/src/types/manual-uploads";
import type {
  OpportunityListItem,
  OpportunitySortDirection,
  OpportunitySortField,
  OpportunityStage,
  OpportunitySummaryMetric,
  OpportunityWorkspaceQueryState,
  WorkspaceTab,
} from "@/src/types/opportunities";
import { OPPORTUNITY_STAGES } from "@/src/types/opportunities";
import type { UploadConsoleEntry } from "@/src/features/opportunity-workspace/upload-workflow-state";

export const UPLOAD_CONSOLE_SEED: UploadConsoleEntry = {
  level: "info",
  text: "Flujo listo. Selecciona conjunto y CSV.",
};

export const STAGE_COLUMNS: OpportunityStage[] = [
  "open",
  "closing_soon",
  "closed",
  "awarded",
  "revoked_or_suspended",
  "unknown",
];

export const TAB_OPTIONS: Array<{ id: WorkspaceTab; label: string }> = [
  { id: "explorer", label: WORKSPACE_TAB_LABELS.explorer },
  { id: "radar", label: WORKSPACE_TAB_LABELS.radar },
];

export const MANUAL_UPLOAD_DATASET_OPTIONS: Array<{
  value: ManualUploadDatasetType;
  label: string;
  helper: string;
}> = [
  {
    value: "licitacion",
    label: "Licitaciones",
    helper: "Usa este flujo para avisos y sus líneas.",
  },
  {
    value: "orden_compra",
    label: "Órdenes de compra",
    helper: "Usa este flujo para OC y sus ítems asociados.",
  },
];

export const PRIMARY_METRIC_KEYS = new Set([
  "total_opportunities",
  "open",
  "closing_soon",
  "closed",
  "awarded",
  "revoked_or_suspended",
]);

export const HEADER_METRIC_FALLBACKS: OpportunitySummaryMetric[] = [
  { key: "open", label: "Abiertas", value: null },
  { key: "closing_soon", label: "Cierran pronto", value: null },
  { key: "awarded", label: "Adjudicadas", value: null },
  { key: "total_estimated_amount", label: "Monto total", value: null },
];

export const WATCHLIST_STORAGE_KEY = "opportunity-workspace.watchlist.v1";

export function toReadableError(error: unknown): { message: string; statusCode: number | null } {
  if (error instanceof ApiClientError) {
    if (error.status === 404) {
      return {
        message: "No se encontraron oportunidades. Intenta con otros filtros o más tarde.",
        statusCode: 404,
      };
    }
    if (error.status && error.status >= 500) {
      return {
        message: "Hubo un problema al cargar las oportunidades. Intenta de nuevo en unos momentos.",
        statusCode: error.status,
      };
    }
    return {
      message: "La consulta no pudo completarse. Revisa los filtros aplicados.",
      statusCode: error.status,
    };
  }
  if (error instanceof Error) {
    if (error.message.toLowerCase().includes("failed to fetch")) {
      return {
        message: "No se pudo conectar con el servidor. Verifica tu conexión.",
        statusCode: null,
      };
    }
    return { message: error.message, statusCode: null };
  }
  return { message: "Error inesperado al consultar oportunidades.", statusCode: null };
}

export function readApiErrorDetail(error: ApiClientError): string | null {
  if (!error.body) {
    return null;
  }

  try {
    const parsed = JSON.parse(error.body) as { detail?: unknown };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) {
      return parsed.detail.trim();
    }
  } catch {
    if (error.body.trim()) {
      return error.body.trim();
    }
  }

  return null;
}

export function toManualUploadError(error: unknown): { message: string; statusCode: number | null } {
  if (error instanceof ApiClientError) {
    return {
      message:
        readApiErrorDetail(error) ??
        "La validación del CSV no pudo completarse. Revisa el archivo, columnas o límite de carga.",
      statusCode: error.status,
    };
  }

  if (error instanceof Error) {
    if (error.name === "AbortError") {
      return {
        message: "Carga cancelada en cliente. Si backend ya comenzó, revisa estado antes de reintentar.",
        statusCode: null,
      };
    }
    return { message: error.message, statusCode: null };
  }

  return { message: "Error inesperado en ingesta manual de CSV.", statusCode: null };
}

export function formatDatasetTypeLabel(datasetType: ManualUploadDatasetType): string {
  return datasetType === "licitacion" ? "Licitaciones" : "Órdenes de compra";
}

export function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toLocaleString("es-CL", {
      maximumFractionDigits: 1,
    })} MiB`;
  }
  if (bytes >= 1024) {
    return `${(bytes / 1024).toLocaleString("es-CL", {
      maximumFractionDigits: 1,
    })} KiB`;
  }
  return `${bytes.toLocaleString("es-CL")} B`;
}

export function metricClassName(key: string): string {
  switch (key) {
    case "open":
      return "pulse-chip pulse-chip--open";
    case "closing_soon":
      return "pulse-chip pulse-chip--closing-soon";
    case "awarded":
      return "pulse-chip pulse-chip--awarded";
    case "revoked_or_suspended":
      return "pulse-chip pulse-chip--risk";
    case "closed":
      return "pulse-chip pulse-chip--closed";
    default:
      return "pulse-chip";
  }
}

export function metricKeyToStage(key: string): OpportunityStage | "" {
  return OPPORTUNITY_STAGES.includes(key as OpportunityStage) ? (key as OpportunityStage) : "";
}

export function uniqueByNoticeId(items: OpportunityListItem[]): OpportunityListItem[] {
  const byNoticeId = new Map<string, OpportunityListItem>();
  for (const item of items) {
    if (!byNoticeId.has(item.noticeId)) {
      byNoticeId.set(item.noticeId, item);
    }
  }
  return Array.from(byNoticeId.values());
}

export function formatMetricValue(metric: OpportunitySummaryMetric): string {
  if (metric.key.includes("amount")) {
    return formatMoney(metric.value, "CLP");
  }
  return formatCount(metric.value);
}

export function formatCompactMetricValue(metric: OpportunitySummaryMetric): string {
  if (!metric.key.includes("amount")) {
    return formatMetricValue(metric);
  }
  if (metric.value === null) {
    return formatUnavailable(null);
  }
  return formatMoney(metric.value, "CLP");
}

export function getSortLabel(sortBy: OpportunitySortField, sortOrder: OpportunitySortDirection): string {
  if (sortBy === "estimated_amount") {
    return sortOrder === "desc" ? "Monto mayor" : "Monto menor";
  }
  if (sortBy === "publication_date") {
    return sortOrder === "desc" ? "Publicación reciente" : "Publicación antigua";
  }
  if (sortBy === "days_remaining") {
    return sortOrder === "desc" ? "Días restantes (más)" : "Días restantes (menos)";
  }
  return sortOrder === "desc" ? "Cierre más lejano" : "Cierre más cercano";
}

export function formatToday(): string {
  return new Intl.DateTimeFormat("es-CL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date());
}

export function getActiveFilterLabels(state: OpportunityWorkspaceQueryState): string[] {
  const labels: string[] = [];
  if (state.q.trim()) labels.push(`Búsqueda: ${state.q.trim()}`);
  if (state.procurementType) {
    labels.push(PROCUREMENT_TYPE_LABELS[state.procurementType]);
  }
  if (state.officialStatus) labels.push(`Estado: ${state.officialStatus}`);
  if (state.stage) labels.push(`Etapa: ${formatStage(state.stage)}`);
  if (state.closeFrom || state.closeTo) labels.push("Rango de cierre");
  if (state.publicationFrom || state.publicationTo) labels.push("Rango de publicación");
  if (state.lessThan100Utm) labels.push("Menor a 100 UTM");
  if (state.maxAmount) labels.push(`Máximo ${state.maxAmount}`);
  return labels;
}

export function parseAmountInput(value: string): string {
  const compact = value.replace(/\s+/g, "");
  const hasCommaDecimal = compact.includes(",");
  const normalized = hasCommaDecimal
    ? compact.replace(/\./g, "").replace(",", ".")
    : compact;
  const sanitized = normalized.replace(/[^\d.]/g, "");
  const [whole, ...rest] = sanitized.split(".");
  return rest.length > 0 ? `${whole}.${rest.join("")}` : whole;
}
