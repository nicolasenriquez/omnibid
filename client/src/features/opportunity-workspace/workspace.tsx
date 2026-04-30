"use client";

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CircleDollarSign,
  Copy,
  ExternalLink,
  FileSpreadsheet,
  FilterX,
  Eye,
  RefreshCw,
  Search,
  ServerCrash,
  ShieldCheck,
  SlidersHorizontal,
  Upload,
  X,
} from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ApiClientError } from "@/src/lib/api/http";
import {
  preflightManualCsvUpload,
  processManualCsvUpload,
} from "@/src/lib/api/manual-uploads";
import {
  fetchOpportunityDetail,
  fetchOpportunities,
  fetchOpportunitySummary,
} from "@/src/lib/api/opportunities";
import {
  formatCount,
  formatDate,
  formatMoney,
  formatRelationshipCertainty,
  formatStage,
  formatUnavailable,
} from "@/src/lib/formatters/opportunities";
import {
  PROCUREMENT_TYPE_LABELS,
  WORKSPACE_TAB_LABELS,
} from "@/src/features/opportunity-workspace/display-contract";
import {
  WORKSPACE_DEFAULTS,
  parseWorkspaceQueryState,
  patchWorkspaceQuery,
  toFilters,
} from "@/src/lib/url-state/workspace";
import type {
  ManualUploadDatasetType,
  ManualUploadJobResponse,
  ManualUploadPreflightResponse,
} from "@/src/types/manual-uploads";
import type {
  OpportunityDetail,
  OpportunityListItem,
  OpportunityListResponse,
  OpportunityStage,
  OpportunitySummaryMetric,
  OpportunitySummaryResponse,
  WorkspaceTab,
} from "@/src/types/opportunities";
import { OPPORTUNITY_STAGES } from "@/src/types/opportunities";
import {
  Badge,
  Button,
  Chip,
  DetailSection,
  IconButton,
  Input,
  Panel,
  Select,
  Skeleton,
  Table,
  TableWrap,
  Tabs,
} from "@/src/components/ui";

type RemoteState<T> =
  | { status: "idle" | "loading" }
  | { status: "success"; data: T }
  | { status: "error"; message: string; statusCode: number | null };

const STAGE_COLUMNS: OpportunityStage[] = [
  "open",
  "closing_soon",
  "closed",
  "awarded",
  "revoked_or_suspended",
  "unknown",
];

const TAB_OPTIONS: Array<{ id: WorkspaceTab; label: string }> = [
  { id: "explorer", label: WORKSPACE_TAB_LABELS.explorer },
  { id: "radar", label: WORKSPACE_TAB_LABELS.radar },
];

const MANUAL_UPLOAD_DATASET_OPTIONS: Array<{
  value: ManualUploadDatasetType;
  label: string;
  helper: string;
}> = [
  {
    value: "licitacion",
    label: "Licitaciones",
    helper: "Usa este flujo para avisos y sus lineas.",
  },
  {
    value: "orden_compra",
    label: "Ordenes de compra",
    helper: "Usa este flujo para OC y sus items asociados.",
  },
];

const PRIMARY_METRIC_KEYS = new Set([
  "total_opportunities",
  "open",
  "closing_soon",
  "closed",
  "awarded",
  "revoked_or_suspended",
]);

const HEADER_METRIC_FALLBACKS: OpportunitySummaryMetric[] = [
  { key: "open", label: "Abiertas", value: null },
  { key: "closing_soon", label: "Cierran pronto", value: null },
  { key: "awarded", label: "Adjudicadas", value: null },
  { key: "total_estimated_amount", label: "Monto total", value: null },
];

const CHILECOMPRA_NOTICE_URL = "https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx";

function toReadableError(error: unknown): { message: string; statusCode: number | null } {
  if (error instanceof ApiClientError) {
    if (error.status === 404) {
      return {
        message:
          "Los endpoints de oportunidades aun no estan disponibles en backend (404).",
        statusCode: 404,
      };
    }
    if (error.status && error.status >= 500) {
      return {
        message:
          "La API esta en linea, pero el endpoint de oportunidades respondio con un error interno.",
        statusCode: error.status,
      };
    }
    return {
      message:
        "La API rechazo la consulta de oportunidades. Revisa filtros, contrato de datos o permisos CORS.",
      statusCode: error.status,
    };
  }
  if (error instanceof Error) {
    if (error.message.toLowerCase().includes("failed to fetch")) {
      return {
        message:
          "No fue posible contactar la API de oportunidades. Verifica backend en http://localhost:8000 y CORS.",
        statusCode: null,
      };
    }
    return { message: error.message, statusCode: null };
  }
  return { message: "Error inesperado al consultar oportunidades.", statusCode: null };
}

function hasActiveFilters(state: ReturnType<typeof parseWorkspaceQueryState>): boolean {
  return Boolean(
    state.q.trim() ||
      state.officialStatus ||
      state.stage ||
      state.buyerRegion ||
      state.primaryCategory ||
      state.publicationFrom ||
      state.publicationTo ||
      state.closeFrom ||
      state.closeTo ||
      state.minAmount ||
      state.maxAmount ||
      state.procurementType ||
      state.lessThan100Utm ||
      state.page !== WORKSPACE_DEFAULTS.page ||
      state.pageSize !== WORKSPACE_DEFAULTS.pageSize ||
      state.sortBy !== WORKSPACE_DEFAULTS.sortBy ||
      state.sortOrder !== WORKSPACE_DEFAULTS.sortOrder,
  );
}

function stageClassName(stage: OpportunityStage): string {
  switch (stage) {
    case "open":
      return "status-chip status-chip--open";
    case "closing_soon":
      return "status-chip status-chip--closing-soon";
    case "closed":
      return "status-chip status-chip--closed";
    case "awarded":
      return "status-chip status-chip--awarded";
    case "revoked_or_suspended":
      return "status-chip status-chip--revoked-or-suspended";
    default:
      return "status-chip status-chip--unknown";
  }
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

function toManualUploadError(error: unknown): { message: string; statusCode: number | null } {
  if (error instanceof ApiClientError) {
    return {
      message:
        readApiErrorDetail(error) ??
        "La validacion del CSV no pudo completarse. Revisa dataset, columnas o limite de carga.",
      statusCode: error.status,
    };
  }

  if (error instanceof Error) {
    if (error.name === "AbortError") {
      return {
        message: "Carga cancelada en cliente. Si backend ya comenzo, revisa estado antes de reintentar.",
        statusCode: null,
      };
    }
    return { message: error.message, statusCode: null };
  }

  return { message: "Error inesperado en carga manual de CSV.", statusCode: null };
}

function formatDatasetTypeLabel(datasetType: ManualUploadDatasetType): string {
  return datasetType === "licitacion" ? "Licitaciones" : "Ordenes de compra";
}

function formatFileSize(bytes: number): string {
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

function opportunityCardClassName(item: OpportunityListItem, selectedNoticeId: string | null): string {
  const classes = ["opportunity-card", `opportunity-card--${item.derivedStage}`];
  if (item.noticeId === selectedNoticeId) {
    classes.push("opportunity-card--selected");
  }
  return classes.join(" ");
}

function metricClassName(key: string): string {
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

function metricKeyToStage(key: string): OpportunityStage | "" {
  return OPPORTUNITY_STAGES.includes(key as OpportunityStage) ? (key as OpportunityStage) : "";
}

function uniqueByNoticeId(items: OpportunityListItem[]): OpportunityListItem[] {
  const byNoticeId = new Map<string, OpportunityListItem>();
  for (const item of items) {
    if (!byNoticeId.has(item.noticeId)) {
      byNoticeId.set(item.noticeId, item);
    }
  }
  return Array.from(byNoticeId.values());
}

function formatMetricValue(metric: OpportunitySummaryMetric): string {
  if (metric.key.includes("amount")) {
    return formatMoney(metric.value, "CLP");
  }
  return formatCount(metric.value);
}

function formatCompactMetricValue(metric: OpportunitySummaryMetric): string {
  if (!metric.key.includes("amount")) {
    return formatMetricValue(metric);
  }
  if (metric.value === null) {
    return formatUnavailable(null);
  }
  const absValue = Math.abs(metric.value);
  if (absValue >= 1_000_000_000_000) {
    return `CLP ${(metric.value / 1_000_000_000_000).toLocaleString("es-CL", {
      maximumFractionDigits: 1,
    })}T`;
  }
  if (absValue >= 1_000_000_000) {
    return `CLP ${(metric.value / 1_000_000_000).toLocaleString("es-CL", {
      maximumFractionDigits: 1,
    })}B`;
  }
  return formatMoney(metric.value, "CLP");
}

function buildChileCompraNoticeUrl(externalNoticeCode: string | null): string | null {
  if (!externalNoticeCode) {
    return null;
  }
  const code = externalNoticeCode.trim();
  if (!code) {
    return null;
  }
  return `${CHILECOMPRA_NOTICE_URL}?idlicitacion=${encodeURIComponent(code)}`;
}

function getSortLabel(sortBy: string, sortOrder: string): string {
  if (sortBy === "estimated_amount") {
    return sortOrder === "desc" ? "Monto mayor" : "Monto menor";
  }
  if (sortBy === "publication_date") {
    return sortOrder === "desc" ? "Publicacion reciente" : "Publicacion antigua";
  }
  return sortOrder === "desc" ? "Cierre lejano" : "Cierre cercano";
}

function formatToday(): string {
  return new Intl.DateTimeFormat("es-CL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date());
}

function getActiveFilterLabels(
  state: ReturnType<typeof parseWorkspaceQueryState>,
): string[] {
  const labels: string[] = [];
  if (state.q.trim()) labels.push(`Busqueda: ${state.q.trim()}`);
  if (state.procurementType) {
    labels.push(PROCUREMENT_TYPE_LABELS[state.procurementType]);
  }
  if (state.officialStatus) labels.push(`Estado: ${state.officialStatus}`);
  if (state.stage) labels.push(`Etapa: ${formatStage(state.stage)}`);
  if (state.closeFrom || state.closeTo) labels.push("Rango de cierre");
  if (state.publicationFrom || state.publicationTo) labels.push("Rango de publicacion");
  if (state.lessThan100Utm) labels.push("Menor a 100 UTM");
  if (state.maxAmount) labels.push(`Maximo ${state.maxAmount}`);
  return labels;
}

function SortHeader({
  label,
  active = false,
}: {
  label: string;
  active?: boolean;
}) {
  return (
    <span className={active ? "table-sort table-sort--active" : "table-sort"}>
      <span>{label}</span>
      <ChevronDown size={13} aria-hidden="true" />
    </span>
  );
}

function NoDataState({
  title,
  description,
  isError = false,
  statusCode,
  action,
}: {
  title: string;
  description: string;
  isError?: boolean;
  statusCode?: number | null;
  action?: React.ReactNode;
}) {
  return (
    <div
      className={isError ? "state-block state-block--error" : "state-block"}
      role={isError ? "alert" : "status"}
    >
      <div className="state-block__header">
        {isError ? <ServerCrash size={18} aria-hidden="true" /> : null}
        <strong>{title}</strong>
        {statusCode ? <span className="state-block__code">{`HTTP ${statusCode}`}</span> : null}
      </div>
      <p className="state-block__description">{description}</p>
      {action ? <div className="state-actions">{action}</div> : null}
    </div>
  );
}

function parseAmountInput(value: string): string {
  const sanitized = value.replace(/[^\d.]/g, "");
  const [whole, ...rest] = sanitized.split(".");
  return rest.length > 0 ? `${whole}.${rest.join("")}` : whole;
}

function LoadingShell() {
  return (
    <Panel>
      <div className="loading-stack" aria-busy="true" aria-label="Cargando oportunidades">
        <Skeleton height="1rem" className="loading-stack__title" />
        <Skeleton height="2.3rem" />
        <Skeleton height="2.3rem" />
        <Skeleton height="2.3rem" />
      </div>
    </Panel>
  );
}

export function OpportunityWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryState = useMemo(
    () => parseWorkspaceQueryState(searchParams),
    [searchParams],
  );
  const filters = useMemo(() => toFilters(queryState), [queryState]);
  const activeFilters = hasActiveFilters(queryState);

  const [listState, setListState] = useState<RemoteState<OpportunityListResponse>>({
    status: "loading",
  });
  const [summaryState, setSummaryState] = useState<RemoteState<OpportunitySummaryResponse>>({
    status: "loading",
  });
  const [detailState, setDetailState] = useState<RemoteState<OpportunityDetail>>(() =>
    queryState.selectedNoticeId ? { status: "loading" } : { status: "idle" },
  );
  const [expandedNoticeId, setExpandedNoticeId] = useState<string | null>(null);
  const [reloadNonce, setReloadNonce] = useState(0);
  const [isUploadSheetOpen, setIsUploadSheetOpen] = useState(false);
  const [uploadDatasetType, setUploadDatasetType] = useState<ManualUploadDatasetType | "">("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploadDragActive, setIsUploadDragActive] = useState(false);
  const [uploadPreflightState, setUploadPreflightState] =
    useState<RemoteState<ManualUploadPreflightResponse>>({ status: "idle" });
  const [uploadJobState, setUploadJobState] = useState<RemoteState<ManualUploadJobResponse>>({
    status: "idle",
  });
  const uploadAbortRef = useRef<AbortController | null>(null);

  const replaceQuery = useCallback(
    (patch: Partial<typeof queryState>) => {
      router.replace(patchWorkspaceQuery(pathname, searchParams, patch), { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const refreshList = useCallback(
    (patch: Partial<typeof queryState>) => {
      setListState({ status: "loading" });
      setSummaryState({ status: "loading" });
      replaceQuery(patch);
    },
    [replaceQuery],
  );

  const openDetail = useCallback(
    (tab: WorkspaceTab, noticeId: string) => {
      setDetailState({ status: "loading" });
      replaceQuery({ tab, selectedNoticeId: noticeId });
    },
    [replaceQuery],
  );

  useEffect(() => {
    const controller = new AbortController();

    fetchOpportunities(filters, controller.signal)
      .then((data) => setListState({ status: "success", data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const normalized = toReadableError(error);
        setListState({
          status: "error",
          message: normalized.message,
          statusCode: normalized.statusCode,
        });
      });

    fetchOpportunitySummary(filters, controller.signal)
      .then((data) => setSummaryState({ status: "success", data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const normalized = toReadableError(error);
        setSummaryState({
          status: "error",
          message: normalized.message,
          statusCode: normalized.statusCode,
        });
      });

    return () => controller.abort();
  }, [filters, reloadNonce]);

  useEffect(() => {
    const noticeId = queryState.selectedNoticeId;
    if (!noticeId) {
      return;
    }

    const controller = new AbortController();

    fetchOpportunityDetail(noticeId, controller.signal)
      .then((data) => setDetailState({ status: "success", data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const normalized = toReadableError(error);
        setDetailState({
          status: "error",
          message: normalized.message,
          statusCode: normalized.statusCode,
        });
      });

    return () => controller.abort();
  }, [queryState.selectedNoticeId]);

  useEffect(() => {
    return () => uploadAbortRef.current?.abort();
  }, []);

  const listItems = useMemo(
    () => (listState.status === "success" ? uniqueByNoticeId(listState.data.items) : []),
    [listState],
  );
  const metrics = useMemo(
    () => (summaryState.status === "success" ? summaryState.data.metrics : []),
    [summaryState],
  );
  const pulseMetrics = metrics.filter((metric) => PRIMARY_METRIC_KEYS.has(metric.key));
  const economyMetrics = metrics.filter((metric) => !PRIMARY_METRIC_KEYS.has(metric.key));
  const activeFilterLabels = getActiveFilterLabels(queryState);
  const headerMetrics = useMemo(() => {
    const byKey = new Map(metrics.map((metric) => [metric.key, metric]));
    return HEADER_METRIC_FALLBACKS.map((fallback) => byKey.get(fallback.key) ?? fallback);
  }, [metrics]);

  const radarColumns = useMemo(() => {
    return STAGE_COLUMNS.map((stage) => ({
      stage,
      label: formatStage(stage),
      items: listItems.filter((item) => item.derivedStage === stage),
    }));
  }, [listItems]);

  const noResults = listState.status === "success" && listItems.length === 0 && activeFilters;
  const emptyState = listState.status === "success" && listItems.length === 0 && !activeFilters;
  const uploadCanValidate = Boolean(uploadDatasetType && uploadFile);
  const uploadCanProcess =
    uploadPreflightState.status === "success" &&
    uploadJobState.status !== "loading" &&
    uploadJobState.status !== "success";
  const apiStatusLabel =
    listState.status === "loading" || summaryState.status === "loading"
      ? "Consultando API"
      : listState.status === "error"
        ? listState.statusCode
          ? `API ${listState.statusCode}`
          : "API sin respuesta"
        : "API conectada";
  const resultStatusLabel =
    listState.status === "success"
      ? `${formatCount(listState.data.total)} licitaciones`
      : "Resultados pendientes";

  const handleTabChange = (tab: WorkspaceTab) => {
    refreshList({ tab, page: 1 });
  };

  const handleStagePulse = (stage: OpportunityStage | "") => {
    refreshList({ stage, page: 1, selectedNoticeId: null });
  };

  const handleToggleExpanded = (noticeId: string) => {
    setExpandedNoticeId((current) => (current === noticeId ? null : noticeId));
  };

  const handleRefreshCurrentFilters = () => {
    setListState({ status: "loading" });
    setSummaryState({ status: "loading" });
    setReloadNonce((current) => current + 1);
  };

  const handleResetFilters = () => {
    refreshList({
      q: "",
      officialStatus: "",
      stage: "",
      buyerRegion: "",
      primaryCategory: "",
      publicationFrom: "",
      publicationTo: "",
      closeFrom: "",
      closeTo: "",
      minAmount: "",
      maxAmount: "",
      procurementType: "",
      lessThan100Utm: false,
      page: 1,
      selectedNoticeId: null,
      sortBy: WORKSPACE_DEFAULTS.sortBy,
      sortOrder: WORKSPACE_DEFAULTS.sortOrder,
      pageSize: WORKSPACE_DEFAULTS.pageSize,
    });
  };

  const handleCopyNoticeCode = async (externalNoticeCode: string | null) => {
    if (!externalNoticeCode || !navigator.clipboard) {
      return;
    }
    await navigator.clipboard.writeText(externalNoticeCode);
  };

  const abortActiveUpload = useCallback(() => {
    uploadAbortRef.current?.abort();
    uploadAbortRef.current = null;
  }, []);

  const resetUploadProgress = useCallback(() => {
    setUploadPreflightState({ status: "idle" });
    setUploadJobState({ status: "idle" });
  }, []);

  const closeUploadSheet = useCallback(() => {
    abortActiveUpload();
    setIsUploadSheetOpen(false);
    setUploadDatasetType("");
    setUploadFile(null);
    setIsUploadDragActive(false);
    resetUploadProgress();
  }, [abortActiveUpload, resetUploadProgress]);

  const handleUploadFileSelected = useCallback(
    (nextFile: File | null) => {
      setUploadFile(nextFile);
      resetUploadProgress();
    },
    [resetUploadProgress],
  );

  const handleStartPreflight = useCallback(async () => {
    if (!uploadDatasetType || !uploadFile) {
      return;
    }

    abortActiveUpload();
    const controller = new AbortController();
    uploadAbortRef.current = controller;
    setUploadPreflightState({ status: "loading" });
    setUploadJobState({ status: "idle" });

    try {
      const data = await preflightManualCsvUpload(uploadFile, uploadDatasetType, controller.signal);
      setUploadPreflightState({ status: "success", data });
    } catch (error) {
      if (controller.signal.aborted) {
        setUploadPreflightState({ status: "idle" });
        return;
      }
      const normalized = toManualUploadError(error);
      setUploadPreflightState({
        status: "error",
        message: normalized.message,
        statusCode: normalized.statusCode,
      });
    } finally {
      if (uploadAbortRef.current === controller) {
        uploadAbortRef.current = null;
      }
    }
  }, [abortActiveUpload, uploadDatasetType, uploadFile]);

  const handleStartProcessing = useCallback(async () => {
    if (uploadPreflightState.status !== "success") {
      return;
    }

    abortActiveUpload();
    const controller = new AbortController();
    uploadAbortRef.current = controller;
    setUploadJobState({ status: "loading" });

    try {
      const data = await processManualCsvUpload(
        uploadPreflightState.data.file_token,
        controller.signal,
      );
      setUploadJobState({ status: "success", data });
      setListState({ status: "loading" });
      setSummaryState({ status: "loading" });
      setReloadNonce((current) => current + 1);
    } catch (error) {
      if (controller.signal.aborted) {
        setUploadJobState({ status: "idle" });
        return;
      }
      const normalized = toManualUploadError(error);
      setUploadJobState({
        status: "error",
        message: normalized.message,
        statusCode: normalized.statusCode,
      });
    } finally {
      if (uploadAbortRef.current === controller) {
        uploadAbortRef.current = null;
      }
    }
  }, [abortActiveUpload, uploadPreflightState]);

  return (
    <main className="workspace-page">
      <div className="workspace-layout">
        <section className="workspace-main" aria-label="Vista principal de oportunidades">
          <header className="workspace-header">
            <div className="workspace-header__content">
              <div className="workspace-header__eyebrow-row">
                <span className="workspace-kicker">Control operativo</span>
                <Badge>Explorer y Radar en solo lectura</Badge>
              </div>
              <h1 className="workspace-title">Espacio de oportunidades</h1>
              <p className="workspace-subtitle">
                Prioriza licitaciones por etapa, cierre, monto y evidencia. Carga manual queda
                aislada en flujo aparte, sin mutar acciones de exploracion.
              </p>
              <div className="workspace-header__meta" aria-label="Estado del espacio">
                <Badge>{queryState.tab === "radar" ? "Radar activo" : "Explorador activo"}</Badge>
                <span>{activeFilters ? "Filtros aplicados" : "Vista base"}</span>
                <span>{apiStatusLabel}</span>
                <span>{`Hoy ${formatToday()}`}</span>
              </div>
            </div>
            <div className="workspace-header__aside">
              <section className="workspace-operator-card" aria-label="Carga manual de CSV">
                <div className="workspace-operator-card__topline">
                  <span className="workspace-mode__label">Carga manual</span>
                  <Badge>{uploadJobState.status === "success" ? "Ultima carga lista" : "Flujo separado"}</Badge>
                </div>
                <div className="workspace-operator-card__body">
                  <div>
                    <strong>Cargar CSV</strong>
                    <p>
                      Valida columnas, hash y dataset antes de tocar Raw, Normalized o Silver.
                    </p>
                  </div>
                  <Button
                    variant="primary"
                    className="workspace-upload-button"
                    leadingIcon={<Upload size={15} aria-hidden="true" />}
                    onClick={() => setIsUploadSheetOpen(true)}
                  >
                    Cargar CSV
                  </Button>
                </div>
                <div className="workspace-operator-card__facts">
                  <span>
                    <ShieldCheck size={14} aria-hidden="true" />
                    Dataset explicito
                  </span>
                  <span>
                    <FileSpreadsheet size={14} aria-hidden="true" />
                    CSV con validacion previa
                  </span>
                </div>
              </section>

              <section className="workspace-mode" aria-label="Snapshot operativo">
                <div className="workspace-mode__topline">
                  <span className="workspace-mode__label">Snapshot operativo</span>
                  <span>{`${activeFilters ? activeFilterLabels.length : 0} filtros`}</span>
                </div>
                <div className="workspace-mode__hero" aria-label="Resumen operativo">
                  <div>
                    <small>{queryState.tab === "radar" ? "Radar activo" : "Explorador activo"}</small>
                    <strong>{resultStatusLabel}</strong>
                  </div>
                  <Badge>{apiStatusLabel}</Badge>
                </div>
                <div className="workspace-header-kpis" aria-label="KPIs del proceso">
                  {headerMetrics.map((metric) => (
                    <span
                      key={metric.key}
                      className={
                        metric.key.includes("amount") ? "workspace-header-kpi--money" : undefined
                      }
                      title={metric.key.includes("amount") ? formatMetricValue(metric) : undefined}
                    >
                      <small>{metric.label}</small>
                      <strong>{formatCompactMetricValue(metric)}</strong>
                    </span>
                  ))}
                </div>
              </section>
            </div>
          </header>

          <Panel dense className="workspace-toolbar">
            <div className="workspace-toolbar__main">
              <Tabs
                label="Vista"
                value={queryState.tab}
                options={TAB_OPTIONS}
                onChange={handleTabChange}
              />
              <div className="workspace-toolbar__summary">
                <strong>{queryState.tab === "explorer" ? "Explorador" : "Radar"}</strong>
                <span>{resultStatusLabel}</span>
                <Chip>{getSortLabel(queryState.sortBy, queryState.sortOrder)}</Chip>
              </div>
              <div className="workspace-pagination">
                <Badge>{`Pagina ${queryState.page}`}</Badge>
                <IconButton
                  icon={<ArrowLeft size={15} aria-hidden="true" />}
                  label="Pagina anterior"
                  onClick={() =>
                    refreshList({ page: Math.max(1, queryState.page - 1) })
                  }
                  disabled={queryState.page <= 1}
                />
                <IconButton
                  icon={<ArrowRight size={15} aria-hidden="true" />}
                  label="Pagina siguiente"
                  onClick={() => refreshList({ page: queryState.page + 1 })}
                />
              </div>
            </div>
          </Panel>

          <section className="pulse-strip" aria-label="Pulso de oportunidades">
            <div className="pulse-strip__copy">
              <span className="workspace-kicker">Pulso de oportunidades</span>
              <p>
                {summaryState.status === "success"
                  ? "Lectura viva por etapa, monto y evidencia disponible."
                  : "Resumen disponible cuando responde la API de oportunidades."}
              </p>
            </div>
            {summaryState.status === "loading" ? (
              <div className="pulse-strip__chips" aria-busy="true">
                <Skeleton height="2rem" className="pulse-skeleton" />
                <Skeleton height="2rem" className="pulse-skeleton" />
                <Skeleton height="2rem" className="pulse-skeleton" />
              </div>
            ) : null}
            {summaryState.status === "error" ? (
              <div className="pulse-strip__unavailable" role="status">
                Pulso no disponible. La tabla mantiene los resultados de la consulta principal si la API los entrega.
              </div>
            ) : null}
            {summaryState.status === "success" && pulseMetrics.length === 0 ? (
              <div className="pulse-strip__unavailable" role="status">
                La API no entrego metricas de pulso para los filtros actuales.
              </div>
            ) : null}
            {summaryState.status === "success" && pulseMetrics.length > 0 ? (
              <div className="pulse-strip__chips">
                {pulseMetrics.map((metric) => {
                  const stageKey =
                    metric.key === "total_opportunities" ? "" : metricKeyToStage(metric.key);
                  return (
                    <button
                      key={metric.key}
                      type="button"
                      className={
                        queryState.stage === stageKey
                          ? `${metricClassName(metric.key)} pulse-chip--selected`
                          : metricClassName(metric.key)
                      }
                      onClick={() => handleStagePulse(stageKey)}
                    >
                      <span>{metric.label}</span>
                      <strong>{formatMetricValue(metric)}</strong>
                    </button>
                  );
                })}
              </div>
            ) : null}
            {economyMetrics.length > 0 ? (
              <div className="pulse-strip__economy" aria-label="Resumen economico">
                {economyMetrics.slice(0, 2).map((metric) => (
                  <span key={metric.key}>
                    <span>{metric.label}</span>
                    <strong>{formatMetricValue(metric)}</strong>
                  </span>
                ))}
              </div>
            ) : null}
          </section>

          <Panel aria-label="Filtros" className="filter-panel">
            <div className="filter-panel__header">
              <div>
                <span className="workspace-kicker">Filtros</span>
                <h2 className="section-title">Enfoca el analisis sin ruido</h2>
                <p className="section-subtitle">
                  Busqueda, etapas y rangos clave al frente. El resto queda como contexto.
                </p>
              </div>
              <div className="filter-panel__tools">
                <Chip>{`${activeFilterLabels.length} activos`}</Chip>
                <Button
                  variant="ghost"
                  leadingIcon={<SlidersHorizontal size={14} aria-hidden="true" />}
                  onClick={handleRefreshCurrentFilters}
                >
                  Aplicar
                </Button>
              </div>
            </div>
            <div className="filter-grid">
              <div className="filter-field filter-field--wide">
                <label className="ui-label" htmlFor="workspace-search">
                  Buscar
                </label>
                <div className="input-with-icon">
                  <Search size={15} aria-hidden="true" />
                  <Input
                    id="workspace-search"
                    value={queryState.q}
                    placeholder="Codigo, nombre, comprador o categoria"
                    onChange={(event) =>
                      refreshList({
                        q: event.target.value,
                        page: 1,
                        selectedNoticeId: null,
                      })
                    }
                  />
                </div>
              </div>

              <div className="filter-field">
                <label className="ui-label" htmlFor="workspace-procurement-type">
                  Tipo
                </label>
                <Select
                  id="workspace-procurement-type"
                  value={queryState.procurementType}
                  onChange={(event) =>
                    refreshList({
                      procurementType: event.target.value as typeof queryState.procurementType,
                      page: 1,
                      selectedNoticeId: null,
                    })
                  }
                >
                  <option value="">Todos</option>
                  <option value="public">Publica</option>
                  <option value="private">Privada</option>
                  <option value="service">Servicios</option>
                </Select>
              </div>

              <div className="filter-field">
                <label className="ui-label" htmlFor="workspace-status">
                  Estado oficial
                </label>
                <Select
                  id="workspace-status"
                  value={queryState.officialStatus}
                  onChange={(event) =>
                    refreshList({
                      officialStatus: event.target.value,
                      page: 1,
                      selectedNoticeId: null,
                    })
                  }
                >
                  <option value="">Todos</option>
                  <option value="abierta">Abierta</option>
                  <option value="cerrada">Cerrada</option>
                  <option value="adjudicada">Adjudicada</option>
                </Select>
              </div>

              <div className="filter-field">
                <label className="ui-label" htmlFor="workspace-stage">
                  Etapa derivada
                </label>
                <Select
                  id="workspace-stage"
                  value={queryState.stage}
                  onChange={(event) =>
                    refreshList({
                      stage: event.target.value as typeof queryState.stage,
                      page: 1,
                      selectedNoticeId: null,
                    })
                  }
                >
                  <option value="">Todas</option>
                  <option value="open">Abierta</option>
                  <option value="closing_soon">Cierra pronto</option>
                  <option value="closed">Cerrada</option>
                  <option value="awarded">Adjudicada</option>
                  <option value="revoked_or_suspended">Revocada o suspendida</option>
                </Select>
              </div>

              <div className="filter-field filter-field--compact">
                <label className="ui-label" htmlFor="workspace-sort">
                  Orden
                </label>
                <Select
                  id="workspace-sort"
                  value={`${queryState.sortBy}:${queryState.sortOrder}`}
                  onChange={(event) => {
                    const [sortBy, sortOrder] = event.target.value.split(":");
                    refreshList({
                      sortBy: sortBy as typeof queryState.sortBy,
                      sortOrder: sortOrder as typeof queryState.sortOrder,
                      page: 1,
                    });
                  }}
                >
                  <option value="close_date:asc">Cierre mas cercano</option>
                  <option value="close_date:desc">Cierre mas lejano</option>
                  <option value="publication_date:desc">Publicacion reciente</option>
                  <option value="estimated_amount:desc">Monto mayor</option>
                </Select>
              </div>
            </div>

            <details className="advanced-filters">
              <summary>
                <span>Filtros avanzados</span>
                <Chip>{activeFilterLabels.length > 0 ? "Revisar estado" : "Opcional"}</Chip>
              </summary>
              <div className="filter-grid filter-grid--advanced">
                <div className="filter-field">
                  <label className="ui-label" htmlFor="workspace-page-size">
                    Tamano pagina
                  </label>
                  <Select
                    id="workspace-page-size"
                    value={String(queryState.pageSize)}
                    onChange={(event) =>
                      refreshList({
                        pageSize: Number.parseInt(event.target.value, 10),
                        page: 1,
                      })
                    }
                  >
                    <option value="10">10</option>
                    <option value="20">20</option>
                    <option value="50">50</option>
                  </Select>
                </div>

                <div className="filter-field">
                  <label className="ui-label" htmlFor="workspace-publication-from">
                    Publicacion desde
                  </label>
                  <div className="input-with-icon">
                    <CalendarDays size={15} aria-hidden="true" />
                    <Input
                      id="workspace-publication-from"
                      type="date"
                      value={queryState.publicationFrom}
                      onChange={(event) =>
                        refreshList({
                          publicationFrom: event.target.value,
                          page: 1,
                          selectedNoticeId: null,
                        })
                      }
                    />
                  </div>
                </div>

                <div className="filter-field">
                  <label className="ui-label" htmlFor="workspace-publication-to">
                    Publicacion hasta
                  </label>
                  <Input
                    id="workspace-publication-to"
                    type="date"
                    value={queryState.publicationTo}
                    onChange={(event) =>
                      refreshList({
                        publicationTo: event.target.value,
                        page: 1,
                        selectedNoticeId: null,
                      })
                    }
                  />
                </div>

                <div className="filter-field">
                  <label className="ui-label" htmlFor="workspace-close-from">
                    Cierre desde
                  </label>
                  <Input
                    id="workspace-close-from"
                    type="date"
                    value={queryState.closeFrom}
                    onChange={(event) =>
                      refreshList({
                        closeFrom: event.target.value,
                        page: 1,
                        selectedNoticeId: null,
                      })
                    }
                  />
                </div>

                <div className="filter-field">
                  <label className="ui-label" htmlFor="workspace-close-to">
                    Cierre hasta
                  </label>
                  <Input
                    id="workspace-close-to"
                    type="date"
                    value={queryState.closeTo}
                    onChange={(event) =>
                      refreshList({
                        closeTo: event.target.value,
                        page: 1,
                        selectedNoticeId: null,
                      })
                    }
                  />
                </div>

                <div className="filter-field">
                  <label className="ui-label" htmlFor="workspace-max-amount">
                    Monto maximo
                  </label>
                  <div className="input-with-icon">
                    <CircleDollarSign size={15} aria-hidden="true" />
                    <Input
                      id="workspace-max-amount"
                      inputMode="decimal"
                      value={queryState.maxAmount}
                      placeholder="100"
                      onChange={(event) =>
                        refreshList({
                          maxAmount: parseAmountInput(event.target.value),
                          page: 1,
                          selectedNoticeId: null,
                        })
                      }
                    />
                  </div>
                </div>

                <label
                  className={
                    queryState.lessThan100Utm
                      ? "filter-check filter-check--selected"
                      : "filter-check"
                  }
                  htmlFor="workspace-less-than-100-utm"
                >
                  <input
                    id="workspace-less-than-100-utm"
                    type="checkbox"
                    checked={queryState.lessThan100Utm}
                    onChange={(event) =>
                      refreshList({
                        lessThan100Utm: event.target.checked,
                        page: 1,
                        selectedNoticeId: null,
                      })
                    }
                  />
                  <span>Menor a 100 UTM</span>
                </label>
              </div>
            </details>

            <div className="active-filter-row" aria-label="Filtros activos">
              {activeFilterLabels.length === 0 ? (
                <span>Sin filtros activos. Parte por busqueda, etapa o menor a 100 UTM.</span>
              ) : (
                activeFilterLabels.map((label) => <Chip key={label}>{label}</Chip>)
              )}
            </div>

            <div className="filter-actions">
              <Button variant="primary" onClick={handleRefreshCurrentFilters}>
                Actualizar vista
              </Button>
              <Button
                variant="ghost"
                leadingIcon={<FilterX size={14} aria-hidden="true" />}
                onClick={handleResetFilters}
              >
                Limpiar filtros
              </Button>
            </div>
          </Panel>

          {listState.status === "loading" ? <LoadingShell /> : null}

          {listState.status === "error" ? (
            <NoDataState
              title={
                listState.statusCode && listState.statusCode >= 500
                  ? "Error del servidor de oportunidades"
                  : "Backend no disponible"
              }
              description={listState.message}
              isError
              statusCode={listState.statusCode}
              action={
                <Button
                  leadingIcon={<RefreshCw size={15} aria-hidden="true" />}
                  onClick={handleRefreshCurrentFilters}
                >
                  Reintentar
                </Button>
              }
            />
          ) : null}

          {noResults ? (
            <NoDataState
              title="Sin resultados"
              description="Los filtros actuales no devolvieron oportunidades. Ajusta filtros o limpia la busqueda."
              action={<Button onClick={handleResetFilters}>Limpiar filtros</Button>}
            />
          ) : null}

          {emptyState ? (
            <NoDataState
              title="Sin oportunidades disponibles"
              description="Aun no existen oportunidades para mostrar en este entorno."
            />
          ) : null}

          {listState.status === "success" && queryState.tab === "radar" && listItems.length > 0 ? (
            <section className="radar-board" aria-label="Radar de oportunidades">
              {radarColumns.map((column) => (
                <article key={column.stage} className="radar-column">
                  <header className="radar-column__header">
                    <div>
                      <strong>{column.label}</strong>
                      <span>Etapa derivada</span>
                    </div>
                    <Chip>{formatCount(column.items.length)}</Chip>
                  </header>
                  <div className="radar-column__list">
                    {column.items.length === 0 ? (
                      <NoDataState
                        title="Sin tarjetas"
                        description="No hay oportunidades para esta etapa."
                      />
                    ) : null}
                    {column.items.map((item) => (
                      <button
                        key={item.noticeId}
                        type="button"
                        className={opportunityCardClassName(item, queryState.selectedNoticeId)}
                        onClick={() => openDetail("radar", item.noticeId)}
                      >
                        <h3 className="opportunity-card__title">
                          <span>{formatUnavailable(item.externalNoticeCode)}</span>
                          {item.title}
                        </h3>
                        <div className="opportunity-card__meta">
                          <span className={stageClassName(item.derivedStage)}>
                            {formatStage(item.derivedStage)}
                          </span>
                          <span>{formatUnavailable(item.buyerName)}</span>
                          <span>{formatDate(item.closeDate)}</span>
                          <span>{formatMoney(item.estimatedAmount, item.currencyCode)}</span>
                        </div>
                        <div className="opportunity-card__evidence">
                          <span>{`${formatCount(item.lineCount)} lineas`}</span>
                          <span>{`${formatCount(item.bidCount)} ofertas`}</span>
                          <span>{`${formatCount(item.purchaseOrderCount)} OC`}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </section>
          ) : null}

          {listState.status === "success" &&
          queryState.tab === "explorer" &&
          listItems.length > 0 ? (
            <TableWrap>
              <Table aria-label="Explorador de oportunidades">
                <thead>
                  <tr>
                    <th><span className="sr-only">Expandir</span></th>
                    <th><SortHeader label="Codigo" /></th>
                    <th><SortHeader label="Licitacion" /></th>
                    <th><SortHeader label="Comprador" /></th>
                    <th><SortHeader label="Region" /></th>
                    <th><SortHeader label="Estado" /></th>
                    <th><SortHeader label="Etapa" active={queryState.sortBy === "days_remaining"} /></th>
                    <th><SortHeader label="Monto" active={queryState.sortBy === "estimated_amount"} /></th>
                    <th><SortHeader label="Cierre" active={queryState.sortBy === "close_date"} /></th>
                    <th><SortHeader label="Lineas" /></th>
                    <th><SortHeader label="Ofertas" /></th>
                    <th><SortHeader label="OC" /></th>
                  </tr>
                </thead>
                <tbody>
                  {listItems.map((item) => {
                    const isExpanded = expandedNoticeId === item.noticeId;
                    return (
                      <Fragment key={item.noticeId}>
                        <tr
                          key={item.noticeId}
                          className={
                            item.noticeId === queryState.selectedNoticeId
                              ? "ui-table-row-active"
                              : undefined
                          }
                        >
                          <td className="ui-table-cell-control">
                            <IconButton
                              icon={
                                isExpanded ? (
                                  <ChevronDown size={14} aria-hidden="true" />
                                ) : (
                                  <ChevronRight size={14} aria-hidden="true" />
                                )
                              }
                              label={isExpanded ? "Contraer licitacion" : "Expandir licitacion"}
                              aria-expanded={isExpanded}
                              onClick={() => handleToggleExpanded(item.noticeId)}
                            />
                          </td>
                          <td>
                            <button
                              type="button"
                              className="ui-table-row-button"
                              onClick={() => openDetail("explorer", item.noticeId)}
                            >
                              {formatUnavailable(item.externalNoticeCode)}
                            </button>
                          </td>
                          <td className="ui-table-title-cell">
                            <button
                              type="button"
                              className="ui-table-row-button"
                              title={item.title}
                              onClick={() => openDetail("explorer", item.noticeId)}
                            >
                              {item.title}
                            </button>
                          </td>
                          <td>{formatUnavailable(item.buyerName)}</td>
                          <td>{formatUnavailable(item.buyerRegion)}</td>
                          <td>{formatUnavailable(item.officialStatus)}</td>
                          <td>
                            <span className={stageClassName(item.derivedStage)}>
                              {formatStage(item.derivedStage)}
                            </span>
                          </td>
                          <td className="ui-table-number">{formatMoney(item.estimatedAmount, item.currencyCode)}</td>
                          <td>{formatDate(item.closeDate)}</td>
                          <td className="ui-table-number">{formatCount(item.lineCount)}</td>
                          <td className="ui-table-number">{formatCount(item.bidCount)}</td>
                          <td className="ui-table-number">
                            <div className="table-action-cell">
                              <span>{formatCount(item.purchaseOrderCount)}</span>
                              <IconButton
                                icon={<Eye size={14} aria-hidden="true" />}
                                label="Ver detalle"
                                onClick={() => openDetail("explorer", item.noticeId)}
                              />
                            </div>
                          </td>
                        </tr>
                        {isExpanded ? (
                          <tr key={`${item.noticeId}-expanded`} className="ui-table-expanded-row">
                            <td colSpan={12}>
                              <div className="table-evidence-panel">
                                <div className="table-evidence-panel__hero">
                                  <div className="table-evidence-panel__hero-copy">
                                    <span className="evidence-label">Ficha resumida</span>
                                    <strong>{item.title}</strong>
                                    <p>
                                      {formatUnavailable(item.buyerName)} ·{" "}
                                      {formatUnavailable(item.externalNoticeCode)}
                                    </p>
                                  </div>
                                  <div className="table-evidence-panel__hero-badges">
                                    <span className={stageClassName(item.derivedStage)}>
                                      {formatStage(item.derivedStage)}
                                    </span>
                                    <span className="ui-chip">
                                      {item.daysRemaining === null
                                        ? "Cerrada o sin fecha"
                                        : `${formatCount(item.daysRemaining)} dias`}
                                    </span>
                                  </div>
                                </div>
                                <div className="table-evidence-panel__summary">
                                  <div className="table-evidence-panel__fact">
                                    <span className="evidence-label">Categoria</span>
                                    <strong>{formatUnavailable(item.primaryCategory)}</strong>
                                  </div>
                                  <div className="table-evidence-panel__fact">
                                    <span className="evidence-label">Publicacion</span>
                                    <strong>{formatDate(item.publicationDate)}</strong>
                                  </div>
                                  <div className="table-evidence-panel__fact">
                                    <span className="evidence-label">Cierre</span>
                                    <strong>{formatDate(item.closeDate)}</strong>
                                  </div>
                                  <div className="table-evidence-panel__fact">
                                    <span className="evidence-label">Dias restantes</span>
                                    <strong>
                                      {item.daysRemaining === null
                                        ? "Cerrada o sin fecha"
                                        : formatCount(item.daysRemaining)}
                                    </strong>
                                  </div>
                                  <div className="table-evidence-panel__fact">
                                    <span className="evidence-label">Certeza relacion</span>
                                    <strong>{formatRelationshipCertainty("unconfirmed")}</strong>
                                  </div>
                                  <div className="table-evidence-panel__fact">
                                    <span className="evidence-label">Monto estimado</span>
                                    <strong>{formatMoney(item.estimatedAmount, item.currencyCode)}</strong>
                                  </div>
                                </div>
                                <div className="evidence-groups" aria-label="Evidencia hija disponible">
                                  <article className="evidence-group">
                                    <span className="evidence-label">Lineas o items</span>
                                    <strong>{formatCount(item.lineCount)}</strong>
                                    <small>Detalle disponible si la API entrega lineas.</small>
                                  </article>
                                  <article className="evidence-group">
                                    <span className="evidence-label">Ofertas</span>
                                    <strong>{formatCount(item.bidCount)}</strong>
                                    <small>{`${formatCount(item.supplierCount)} proveedores asociados.`}</small>
                                  </article>
                                  <article className="evidence-group">
                                    <span className="evidence-label">Ordenes de compra</span>
                                    <strong>{formatCount(item.purchaseOrderCount)}</strong>
                                    <small>Relaciones tratadas como evidencia, no como hecho confirmado.</small>
                                  </article>
                                </div>
                                <div className="table-evidence-panel__actions">
                                  <Button
                                    variant="primary"
                                    onClick={() => openDetail("explorer", item.noticeId)}
                                  >
                                    Abrir detalle
                                  </Button>
                                </div>
                              </div>
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })}
                </tbody>
              </Table>
            </TableWrap>
          ) : null}
        </section>

        {isUploadSheetOpen ? (
          <div className="upload-sheet-shell" role="dialog" aria-modal="true" aria-labelledby="upload-sheet-title">
            <button
              type="button"
              className="upload-sheet-shell__backdrop"
              aria-label="Cerrar carga manual"
              onClick={closeUploadSheet}
            />
            <section className="upload-sheet">
              <header className="upload-sheet__header">
                <div>
                  <span className="workspace-kicker">Carga manual</span>
                  <h2 id="upload-sheet-title" className="section-title">
                    Cargar CSV al pipeline correcto
                  </h2>
                  <p className="section-subtitle">
                    Selecciona dataset, valida columnas y confirma procesamiento acotado.
                  </p>
                </div>
                <IconButton
                  icon={<X size={15} aria-hidden="true" />}
                  label="Cerrar carga manual"
                  onClick={closeUploadSheet}
                />
              </header>

              <div className="upload-sheet__body">
                <div className="upload-sheet__grid">
                  <div className="upload-sheet__field">
                    <label className="ui-label" htmlFor="manual-upload-dataset">
                      Dataset destino
                    </label>
                    <Select
                      id="manual-upload-dataset"
                      value={uploadDatasetType}
                      onChange={(event) => {
                        setUploadDatasetType(event.target.value as ManualUploadDatasetType | "");
                        resetUploadProgress();
                      }}
                      disabled={uploadPreflightState.status === "loading" || uploadJobState.status === "loading"}
                    >
                      <option value="">Selecciona dataset</option>
                      {MANUAL_UPLOAD_DATASET_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                    <p className="upload-sheet__hint">
                      {uploadDatasetType
                        ? MANUAL_UPLOAD_DATASET_OPTIONS.find((option) => option.value === uploadDatasetType)?.helper
                        : "Nombre de archivo no define dataset. Seleccion obligatoria."}
                    </p>
                  </div>

                  <div className="upload-sheet__field upload-sheet__field--meta">
                    <span className="workspace-mode__label">Guardrails</span>
                    <ul className="upload-sheet__guardrails">
                      <li>1 archivo CSV por corrida.</li>
                      <li>Validacion previa antes de escribir.</li>
                      <li>Procesamiento acotado al source file cargado.</li>
                    </ul>
                  </div>
                </div>

                <label
                  className={
                    isUploadDragActive ? "upload-dropzone upload-dropzone--active" : "upload-dropzone"
                  }
                  onDragEnter={(event) => {
                    event.preventDefault();
                    setIsUploadDragActive(true);
                  }}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setIsUploadDragActive(true);
                  }}
                  onDragLeave={(event) => {
                    event.preventDefault();
                    if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
                      return;
                    }
                    setIsUploadDragActive(false);
                  }}
                  onDrop={(event) => {
                    event.preventDefault();
                    setIsUploadDragActive(false);
                    handleUploadFileSelected(event.dataTransfer.files[0] ?? null);
                  }}
                >
                  <input
                    className="sr-only"
                    type="file"
                    accept=".csv,text/csv"
                    onChange={(event) => handleUploadFileSelected(event.target.files?.[0] ?? null)}
                  />
                  <FileSpreadsheet size={20} aria-hidden="true" />
                  <strong>{uploadFile ? uploadFile.name : "Arrastra CSV o haz click para elegir"}</strong>
                  <span>
                    CSV delimitado por <code>;</code>. El backend revisa columnas requeridas, hash y tamaño permitido.
                  </span>
                  {uploadFile ? (
                    <small>{`${formatFileSize(uploadFile.size)} · ultimo cambio ${new Date(uploadFile.lastModified).toLocaleDateString("es-CL")}`}</small>
                  ) : null}
                </label>

                {uploadPreflightState.status === "loading" ? (
                  <div className="upload-progress" role="status">
                    <RefreshCw size={16} aria-hidden="true" className="upload-progress__spinner" />
                    <div>
                      <strong>Validando archivo</strong>
                      <span>Revisando delimitador, columnas requeridas, hash y resumen previo.</span>
                    </div>
                  </div>
                ) : null}

                {uploadPreflightState.status === "error" ? (
                  <NoDataState
                    title="Preflight rechazado"
                    description={uploadPreflightState.message}
                    isError
                    statusCode={uploadPreflightState.statusCode}
                    action={
                      <Button
                        leadingIcon={<RefreshCw size={15} aria-hidden="true" />}
                        onClick={handleStartPreflight}
                        disabled={!uploadCanValidate}
                      >
                        Reintentar validacion
                      </Button>
                    }
                  />
                ) : null}

                {uploadPreflightState.status === "success" ? (
                  <section className="upload-preview" aria-label="Resumen de preflight">
                    <div className="upload-preview__header">
                      <div>
                        <span className="workspace-mode__label">Preflight listo</span>
                        <strong>{uploadPreflightState.data.original_filename}</strong>
                        <p>
                          {formatDatasetTypeLabel(uploadPreflightState.data.dataset_type)} ·{" "}
                          {formatCount(uploadPreflightState.data.row_count)} filas detectadas
                        </p>
                      </div>
                      <Badge>{uploadPreflightState.data.upload_limits.max_size_label}</Badge>
                    </div>

                    {uploadPreflightState.data.duplicate_source_file ? (
                      <div className="upload-banner upload-banner--warning" role="status">
                        <CircleAlert size={15} aria-hidden="true" />
                        <div>
                          <strong>Hash ya visto en pipeline</strong>
                          <span>
                            Source file previo: {uploadPreflightState.data.duplicate_source_file.file_name}. Si confirmas, UI debe leer conteos canonicos y duplicados por separado.
                          </span>
                        </div>
                      </div>
                    ) : null}

                    <dl className="upload-preview__facts">
                      <div>
                        <dt>Nombre canonico</dt>
                        <dd>{uploadPreflightState.data.canonical_filename}</dd>
                      </div>
                      <div>
                        <dt>Hash SHA-256</dt>
                        <dd>{uploadPreflightState.data.file_hash_sha256.slice(0, 16)}...</dd>
                      </div>
                      <div>
                        <dt>Tamano</dt>
                        <dd>{formatFileSize(uploadPreflightState.data.file_size_bytes)}</dd>
                      </div>
                      <div>
                        <dt>Staging</dt>
                        <dd>{uploadPreflightState.data.status === "staged" ? "Listo para procesar" : "Ya consumido"}</dd>
                      </div>
                    </dl>
                  </section>
                ) : null}

                {uploadJobState.status === "loading" ? (
                  <div className="upload-progress upload-progress--processing" role="status">
                    <RefreshCw size={16} aria-hidden="true" className="upload-progress__spinner" />
                    <div>
                      <strong>Procesando CSV</strong>
                      <span>Backend registra Raw y construye deltas Normalized y Silver para dataset elegido.</span>
                    </div>
                    <Button variant="ghost" onClick={abortActiveUpload}>
                      Cancelar espera
                    </Button>
                  </div>
                ) : null}

                {uploadJobState.status === "error" ? (
                  <NoDataState
                    title="Procesamiento fallido"
                    description={uploadJobState.message}
                    isError
                    statusCode={uploadJobState.statusCode}
                    action={
                      <Button
                        leadingIcon={<RefreshCw size={15} aria-hidden="true" />}
                        onClick={handleStartProcessing}
                        disabled={uploadPreflightState.status !== "success"}
                      >
                        Reintentar proceso
                      </Button>
                    }
                  />
                ) : null}

                {uploadJobState.status === "success" ? (
                  <section className="upload-result" aria-label="Resultado de carga manual">
                    <div className="upload-result__header">
                      <div>
                        <span className="workspace-mode__label">Resultado final</span>
                        <strong>Pipeline acotado completado</strong>
                        <p>{uploadJobState.data.original_filename}</p>
                      </div>
                      <Badge>Job {uploadJobState.data.job_id.slice(0, 8)}</Badge>
                    </div>
                    <div className="upload-banner upload-banner--success" role="status">
                      <CheckCircle2 size={16} aria-hidden="true" />
                      <div>
                        <strong>{uploadJobState.data.step.status === "completed" ? "Carga completada" : uploadJobState.data.step.status}</strong>
                        <span>{uploadJobState.data.step.name}</span>
                      </div>
                    </div>
                    <div className="upload-result__grid">
                      <article>
                        <span>Procesadas</span>
                        <strong>{formatCount(uploadJobState.data.telemetry.processed_rows)}</strong>
                      </article>
                      <article>
                        <span>Aceptadas Raw</span>
                        <strong>{formatCount(uploadJobState.data.telemetry.accepted_rows)}</strong>
                      </article>
                      <article>
                        <span>Delta canonico</span>
                        <strong>{formatCount(uploadJobState.data.telemetry.inserted_delta_rows)}</strong>
                      </article>
                      <article>
                        <span>Duplicadas o existentes</span>
                        <strong>{formatCount(uploadJobState.data.telemetry.duplicate_existing_rows)}</strong>
                      </article>
                      <article>
                        <span>Normalized</span>
                        <strong>{formatCount(uploadJobState.data.telemetry.normalized_rows)}</strong>
                      </article>
                      <article>
                        <span>Silver</span>
                        <strong>{formatCount(uploadJobState.data.telemetry.silver_rows)}</strong>
                      </article>
                    </div>
                  </section>
                ) : null}
              </div>

              <footer className="upload-sheet__actions">
                <Button
                  variant="ghost"
                  leadingIcon={<FilterX size={14} aria-hidden="true" />}
                  onClick={() => {
                    setUploadDatasetType("");
                    setUploadFile(null);
                    setIsUploadDragActive(false);
                    resetUploadProgress();
                  }}
                  disabled={uploadPreflightState.status === "loading" || uploadJobState.status === "loading"}
                >
                  Limpiar
                </Button>
                <Button variant="ghost" onClick={closeUploadSheet}>
                  Cerrar
                </Button>
                <Button
                  leadingIcon={<ShieldCheck size={15} aria-hidden="true" />}
                  onClick={handleStartPreflight}
                  disabled={!uploadCanValidate || uploadPreflightState.status === "loading" || uploadJobState.status === "loading"}
                  loading={uploadPreflightState.status === "loading"}
                >
                  Validar archivo
                </Button>
                <Button
                  variant="primary"
                  leadingIcon={<Upload size={15} aria-hidden="true" />}
                  onClick={handleStartProcessing}
                  disabled={!uploadCanProcess}
                  loading={uploadJobState.status === "loading"}
                >
                  Confirmar y procesar
                </Button>
              </footer>
            </section>
          </div>
        ) : null}

        {queryState.selectedNoticeId ? (
        <aside className="workspace-detail" aria-label="Detalle de licitación">
          <header className="workspace-detail__header">
            <div>
              <strong>Detalle de licitación</strong>
              <span>{queryState.tab === "radar" ? "Origen: Radar" : "Origen: Explorador"}</span>
            </div>
            <IconButton
              icon={<X size={15} aria-hidden="true" />}
              label="Cerrar detalle"
              onClick={() => {
                setDetailState({ status: "idle" });
                replaceQuery({ selectedNoticeId: null });
              }}
              disabled={!queryState.selectedNoticeId}
            />
          </header>

          {queryState.selectedNoticeId && detailState.status === "loading" ? (
            <div className="workspace-detail__loading">
              <Skeleton height="1rem" />
              <Skeleton height="1rem" />
              <Skeleton height="8rem" />
              <Skeleton height="8rem" />
            </div>
          ) : null}

          {queryState.selectedNoticeId && detailState.status === "error" ? (
            <div className="workspace-detail__body">
              <NoDataState
                title={
                  detailState.statusCode === 404
                    ? "Detalle no disponible"
                    : "Error de detalle"
                }
                description={detailState.message}
                isError
                action={
                  <Button
                    leadingIcon={<AlertTriangle size={15} aria-hidden="true" />}
                    onClick={() => {
                      setDetailState({ status: "loading" });
                      replaceQuery({ selectedNoticeId: queryState.selectedNoticeId });
                    }}
                  >
                    Reintentar
                  </Button>
                }
              />
            </div>
          ) : null}

          {detailState.status === "success" ? (
            <>
              <div className="workspace-detail__actions" aria-label="Acciones de solo lectura">
                <Button
                  leadingIcon={<Copy size={15} aria-hidden="true" />}
                  onClick={() => handleCopyNoticeCode(detailState.data.externalNoticeCode)}
                  disabled={!detailState.data.externalNoticeCode}
                >
                  Copiar codigo
                </Button>
                {buildChileCompraNoticeUrl(detailState.data.externalNoticeCode) ? (
                  <Button
                    leadingIcon={<ExternalLink size={15} aria-hidden="true" />}
                    onClick={() => {
                      const url = buildChileCompraNoticeUrl(detailState.data.externalNoticeCode);
                      if (url) {
                        window.open(url, "_blank", "noopener,noreferrer");
                      }
                    }}
                  >
                    Abrir licitacion
                  </Button>
                ) : null}
              </div>

              <DetailSection title="Resumen">
                <strong>{formatUnavailable(detailState.data.externalNoticeCode)}</strong>
                <span>{detailState.data.title}</span>
                <span>{`Estado oficial: ${formatUnavailable(detailState.data.officialStatus)}`}</span>
                <span>{`Etapa: ${formatStage(detailState.data.derivedStage)}`}</span>
                <span>
                  {`Monto estimado: ${formatMoney(
                    detailState.data.estimatedAmount,
                    detailState.data.currencyCode,
                  )}`}
                </span>
                <span>{`Comprador: ${formatUnavailable(detailState.data.buyer.buyerName)}`}</span>
              </DetailSection>

              <DetailSection title="Linea de tiempo">
                {detailState.data.timeline.length === 0 ? (
                  <span>No disponible</span>
                ) : (
                  detailState.data.timeline.map((event) => (
                    <span key={event.key}>{`${event.label}: ${formatDate(event.date)}`}</span>
                  ))
                )}
              </DetailSection>

              <DetailSection title="Productos o servicios">
                {detailState.data.lines.length === 0 ? (
                  <span>Sin informacion disponible.</span>
                ) : (
                  detailState.data.lines.slice(0, 5).map((line) => (
                    <article key={line.itemCode} className="detail-line-card">
                      <strong>{`Item ${line.itemCode}`}</strong>
                      <div>{formatUnavailable(line.lineName)}</div>
                      <div>{`Categoria: ${formatUnavailable(line.category)}`}</div>
                      <div>{`Ofertas: ${formatCount(line.offerCount)}`}</div>
                      <div>{`Certeza: ${formatRelationshipCertainty(line.relationshipCertainty)}`}</div>
                    </article>
                  ))
                )}
              </DetailSection>

              <DetailSection title="Comprador">
                <span>{`Nombre: ${formatUnavailable(detailState.data.buyer.buyerName)}`}</span>
                <span>{`Region: ${formatUnavailable(detailState.data.buyer.buyerRegion)}`}</span>
                <span>
                  {`Unidad: ${formatUnavailable(detailState.data.buyer.contractingUnitName)}`}
                </span>
              </DetailSection>

              <DetailSection title="Economico y evidencia">
                <span>{`Ofertas: ${formatCount(detailState.data.offers.length)}`}</span>
                <span>{`Ordenes de compra: ${formatCount(detailState.data.purchaseOrders.length)}`}</span>
                <span>
                  {`Certeza relacion: ${formatRelationshipCertainty(
                    detailState.data.relationshipSummary,
                  )}`}
                </span>
              </DetailSection>

              <DetailSection title="Ofertas">
                {detailState.data.offers.length === 0 ? (
                  <span>Sin ofertas disponibles en la API.</span>
                ) : (
                  detailState.data.offers.slice(0, 5).map((offer, index) => (
                    <article
                      key={`${offer.supplierCode ?? "proveedor"}-${index}`}
                      className={
                        offer.isSelected
                          ? "detail-offer-card detail-offer-card--selected"
                          : "detail-offer-card"
                      }
                    >
                      <header>
                        <strong>{formatUnavailable(offer.supplierName)}</strong>
                        <span>{offer.isSelected ? "Seleccionada" : "Oferta"}</span>
                      </header>
                      <div>{formatUnavailable(offer.offerName)}</div>
                      <dl>
                        <div>
                          <dt>Monto</dt>
                          <dd>{formatMoney(offer.offeredAmount, offer.currencyCode)}</dd>
                        </div>
                        <div>
                          <dt>Unitario</dt>
                          <dd>{formatMoney(offer.unitPrice, offer.currencyCode)}</dd>
                        </div>
                        <div>
                          <dt>Cantidad</dt>
                          <dd>{formatCount(offer.offeredQuantity)}</dd>
                        </div>
                        <div>
                          <dt>Estado</dt>
                          <dd>{formatUnavailable(offer.offerStatus)}</dd>
                        </div>
                        <div>
                          <dt>Item</dt>
                          <dd>{formatUnavailable(offer.itemCode)}</dd>
                        </div>
                        <div>
                          <dt>Envio</dt>
                          <dd>{formatDate(offer.submittedAt)}</dd>
                        </div>
                      </dl>
                    </article>
                  ))
                )}
              </DetailSection>

              <DetailSection title="Ordenes de compra">
                {detailState.data.purchaseOrders.length === 0 ? (
                  <span>Sin ordenes de compra disponibles en la API.</span>
                ) : (
                  detailState.data.purchaseOrders.slice(0, 5).map((order) => (
                    <article key={order.purchaseOrderCode} className="detail-line-card">
                      <strong>{order.purchaseOrderCode}</strong>
                      <div>{`Estado: ${formatUnavailable(order.purchaseOrderStatus)}`}</div>
                      <div>
                        {`Monto: ${formatMoney(
                          order.purchaseOrderAmount,
                          order.currencyCode,
                        )}`}
                      </div>
                      <div>{`Certeza: ${formatRelationshipCertainty(order.relationshipCertainty)}`}</div>
                    </article>
                  ))
                )}
              </DetailSection>

              <DetailSection title="Metadatos">
                <span>{`Identificador interno: ${detailState.data.noticeId}`}</span>
                <span>{`Codigo externo: ${formatUnavailable(detailState.data.externalNoticeCode)}`}</span>
                <span>Fuente: API de oportunidades en modo lectura.</span>
              </DetailSection>
            </>
          ) : null}
        </aside>
        ) : null}
      </div>
    </main>
  );
}
