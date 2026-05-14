import { ApiClientError } from "@/src/lib/api/http";
import {
  formatCount,
  formatDate,
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
const TODAY_FORMATTER = new Intl.DateTimeFormat("es-CL", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});
const OFFICIAL_STATUS_LABELS: Record<string, string> = {
  publicada: "Publicada",
  cerrada: "Cerrada",
  desierta: "Desierta",
  adjudicada: "Adjudicada",
  revocada: "Revocada",
  suspendida: "Suspendida",
};

export const OFFICIAL_STATUS_FILTER_OPTIONS: Array<{
  value: string;
  label: string;
}> = [
  { value: "publicada", label: "Publicada" },
  { value: "cerrada", label: "Cerrada" },
  { value: "desierta", label: "Desierta" },
  { value: "adjudicada", label: "Adjudicada" },
  { value: "revocada", label: "Revocada" },
  { value: "suspendida", label: "Suspendida" },
];

export const REGION_FILTER_OPTIONS: string[] = [
  "Región Metropolitana de Santiago",
  "Región del Biobío",
  "Región de Valparaíso",
  "Región de la Araucanía",
  "Región del Maule",
  "Región de los Lagos",
  "Región del Libertador General Bernardo O´Higgins",
  "Región de Coquimbo",
  "Región del Ñuble",
  "Región de Los Ríos",
  "Región de Magallanes y de la Antártica",
  "Región de Antofagasta",
  "Región de Atacama",
  "Región de Arica y Parinacota",
  "Región de Tarapacá",
  "Región Aysén del General Carlos Ibáñez del Campo",
];

const OPPORTUNITY_EXPORT_HEADERS = [
  "Código",
  "Licitación",
  "Comprador",
  "Región",
  "Estado",
  "Etapa",
  "Monto",
  "Cierre",
  "Líneas",
  "Ofertas",
  "OC",
  "Radar",
] as const;

export type WorkspaceFilterChip = {
  key: string;
  label: string;
  patch: Partial<OpportunityWorkspaceQueryState>;
};

function createFilterChip(
  key: string,
  label: string,
  patch: Partial<OpportunityWorkspaceQueryState>,
): WorkspaceFilterChip {
  return {
    key,
    label,
    patch: {
      page: 1,
      selectedNoticeId: null,
      ...patch,
    },
  };
}

function formatAmountChipValue(value: string): string {
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return formatMoney(parsed, "CLP");
}

function formatRangeChipLabel(
  label: string,
  from: string,
  to: string,
): string {
  if (from && to) {
    return `${label}: ${formatDate(from)} - ${formatDate(to)}`;
  }
  if (from) {
    return `${label}: desde ${formatDate(from)}`;
  }
  return `${label}: hasta ${formatDate(to)}`;
}

function escapeCsvValue(value: string): string {
  const escaped = value.replace(/"/g, '""');
  return /[;"\r\n]/.test(escaped) ? `"${escaped}"` : escaped;
}

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

function readApiErrorDetail(error: ApiClientError): string | null {
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

export function formatToday(value: Date): string {
  return TODAY_FORMATTER.format(value);
}

export function getActiveFilterChips(state: OpportunityWorkspaceQueryState): WorkspaceFilterChip[] {
  const chips: WorkspaceFilterChip[] = [];

  if (state.q.trim()) {
    chips.push(createFilterChip("q", `Búsqueda: ${state.q.trim()}`, { q: "" }));
  }
  if (state.procurementType) {
    chips.push(
      createFilterChip(
        "procurementType",
        PROCUREMENT_TYPE_LABELS[state.procurementType],
        { procurementType: "" },
      ),
    );
  }
  if (state.sourceView) {
    chips.push(
      createFilterChip("sourceView", "Vista: Publicadas / Activas", {
        sourceView: "",
      }),
    );
  }
  if (state.officialStatus.trim()) {
    chips.push(
      createFilterChip(
        "officialStatus",
        `Estado oficial: ${OFFICIAL_STATUS_LABELS[state.officialStatus] ?? state.officialStatus.trim()}`,
        { officialStatus: "" },
      ),
    );
  }
  if (state.stage) {
    chips.push(createFilterChip("stage", `Etapa: ${formatStage(state.stage)}`, { stage: "" }));
  }
  if (state.buyerRegion.trim()) {
    chips.push(
      createFilterChip("buyerRegion", `Región: ${state.buyerRegion.trim()}`, {
        buyerRegion: "",
      }),
    );
  }
  if (state.primaryCategory.trim()) {
    chips.push(
      createFilterChip("primaryCategory", `Categoría: ${state.primaryCategory.trim()}`, {
        primaryCategory: "",
      }),
    );
  }
  if (state.minAmount.trim()) {
    chips.push(
      createFilterChip("minAmount", `Monto mínimo: ${formatAmountChipValue(state.minAmount)}`, {
        minAmount: "",
      }),
    );
  }
  if (state.maxAmount.trim()) {
    chips.push(
      createFilterChip("maxAmount", `Monto máximo: ${formatAmountChipValue(state.maxAmount)}`, {
        maxAmount: "",
      }),
    );
  }
  if (state.publicationFrom.trim() || state.publicationTo.trim()) {
    chips.push(
      createFilterChip(
        "publicationRange",
        formatRangeChipLabel("Publicación", state.publicationFrom.trim(), state.publicationTo.trim()),
        {
          publicationFrom: "",
          publicationTo: "",
        },
      ),
    );
  }
  if (state.closeFrom.trim() || state.closeTo.trim()) {
    chips.push(
      createFilterChip(
        "closeRange",
        formatRangeChipLabel("Cierre", state.closeFrom.trim(), state.closeTo.trim()),
        {
          closeFrom: "",
          closeTo: "",
        },
      ),
    );
  }
  if (state.lessThan100Utm) {
    chips.push(createFilterChip("lessThan100Utm", "Menor a 100 UTM", { lessThan100Utm: false }));
  }

  return chips;
}

export function getActiveFilterLabels(state: OpportunityWorkspaceQueryState): string[] {
  return getActiveFilterChips(state).map((chip) => chip.label);
}

export function buildOpportunityWorkspaceCsv(
  items: OpportunityListItem[],
  watchlistNoticeIds: string[],
): string {
  const watchlistSet = new Set(watchlistNoticeIds);
  const rows = items.map((item) => {
    const values = [
      formatUnavailable(item.externalNoticeCode),
      formatUnavailable(item.title),
      formatUnavailable(item.buyerName),
      formatUnavailable(item.buyerRegion),
      formatUnavailable(item.officialStatus),
      formatStage(item.derivedStage),
      formatMoney(item.estimatedAmount, item.currencyCode),
      formatDate(item.closeDate),
      formatCount(item.lineCount),
      formatCount(item.bidCount),
      formatCount(item.purchaseOrderCount),
      watchlistSet.has(item.noticeId) ? "Sí" : "No",
    ];

    return values.map((value) => escapeCsvValue(value)).join(";");
  });

  const headerRow = OPPORTUNITY_EXPORT_HEADERS.map((header) => escapeCsvValue(header)).join(";");
  return [headerRow, ...rows].join("\r\n");
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
