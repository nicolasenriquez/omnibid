"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  CircleDollarSign,
  FilterX,
  RefreshCw,
  Search,
  ServerCrash,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ApiClientError } from "@/src/lib/api/http";
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
  WORKSPACE_DEFAULTS,
  parseWorkspaceQueryState,
  patchWorkspaceQuery,
  toFilters,
} from "@/src/lib/url-state/workspace";
import type {
  OpportunityDetail,
  OpportunityListItem,
  OpportunityListResponse,
  OpportunityStage,
  OpportunitySummaryMetric,
  OpportunitySummaryResponse,
  WorkspaceTab,
} from "@/src/types/opportunities";
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
  { id: "explorer", label: "Explorador" },
  { id: "radar", label: "Radar" },
];

const PRIMARY_METRIC_KEYS = new Set([
  "total_opportunities",
  "open",
  "closing_soon",
  "closed",
  "awarded",
  "revoked_or_suspended",
]);

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

function buildFallbackMetrics(items: OpportunityListItem[]): OpportunitySummaryMetric[] {
  return [
    { key: "total", label: "Total oportunidades", value: items.length },
    {
      key: "abiertas",
      label: "Abiertas",
      value: items.filter((item) => item.derivedStage === "open").length,
    },
    {
      key: "cierra_pronto",
      label: "Cierra pronto",
      value: items.filter((item) => item.derivedStage === "closing_soon").length,
    },
    {
      key: "adjudicadas",
      label: "Adjudicadas",
      value: items.filter((item) => item.derivedStage === "awarded").length,
    },
  ];
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

function formatMetricValue(metric: OpportunitySummaryMetric): string {
  if (metric.key.includes("amount")) {
    return formatMoney(metric.value, "CLP");
  }
  return formatCount(metric.value);
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

function getActiveFilterLabels(
  state: ReturnType<typeof parseWorkspaceQueryState>,
): string[] {
  const labels: string[] = [];
  if (state.q.trim()) labels.push(`Busqueda: ${state.q.trim()}`);
  if (state.procurementType) {
    labels.push(
      state.procurementType === "public"
        ? "Publica"
        : state.procurementType === "private"
          ? "Privada"
          : "Servicios",
    );
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
    <div className={isError ? "state-block state-block--error" : "state-block"}>
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
      <div className="loading-stack">
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
  }, [filters]);

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

  const listItems = useMemo(
    () => (listState.status === "success" ? listState.data.items : []),
    [listState],
  );
  const metrics =
    summaryState.status === "success"
      ? summaryState.data.metrics
      : buildFallbackMetrics(listItems);
  const pulseMetrics = metrics.filter((metric) => PRIMARY_METRIC_KEYS.has(metric.key));
  const economyMetrics = metrics.filter((metric) => !PRIMARY_METRIC_KEYS.has(metric.key));
  const activeFilterLabels = getActiveFilterLabels(queryState);

  const radarColumns = useMemo(() => {
    return STAGE_COLUMNS.map((stage) => ({
      stage,
      label: formatStage(stage),
      items: listItems.filter((item) => item.derivedStage === stage),
    }));
  }, [listItems]);

  const noResults = listState.status === "success" && listItems.length === 0 && activeFilters;
  const emptyState = listState.status === "success" && listItems.length === 0 && !activeFilters;
  const apiStatusLabel =
    listState.status === "loading" || summaryState.status === "loading"
      ? "Consultando API"
      : listState.status === "error"
        ? listState.statusCode
          ? `API ${listState.statusCode}`
          : "API sin respuesta"
        : "API conectada";

  const handleTabChange = (tab: WorkspaceTab) => {
    refreshList({ tab, page: 1, selectedNoticeId: null });
  };

  const handleStagePulse = (stage: OpportunityStage | "") => {
    refreshList({ stage, page: 1, selectedNoticeId: null });
  };

  const handleToggleExpanded = (noticeId: string) => {
    setExpandedNoticeId((current) => (current === noticeId ? null : noticeId));
  };

  const handleRefreshCurrentFilters = () => {
    refreshList({ page: queryState.page });
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

  return (
    <main className="workspace-page">
      <div className="workspace-layout">
        <section className="workspace-main" aria-label="Vista principal de oportunidades">
          <header className="workspace-header">
            <div className="workspace-header__content">
              <span className="workspace-kicker">Workspace de licitaciones</span>
              <h1 className="workspace-title">Espacio de oportunidades</h1>
              <p className="workspace-subtitle">
                Radar y explorador de licitaciones en modo lectura, con filtros trazables
                sobre datos Silver.
              </p>
              <div className="workspace-header__meta" aria-label="Estado del espacio">
                <Badge>{queryState.tab === "radar" ? "Radar activo" : "Explorador activo"}</Badge>
                <span>{activeFilters ? "Filtros aplicados" : "Vista base"}</span>
                <span>{apiStatusLabel}</span>
              </div>
            </div>
            <div className="workspace-mode" aria-label="Modo del espacio">
              <Badge>Solo lectura</Badge>
              <span>Acciones operativas fuera de alcance en esta vista</span>
            </div>
          </header>

          <section className="pulse-strip" aria-label="Pulso de oportunidades">
            <div className="pulse-strip__copy">
              <span className="workspace-kicker">Pulso de oportunidades</span>
              <p>Lectura viva por etapa, monto y evidencia disponible.</p>
            </div>
            <div className="pulse-strip__chips">
              {pulseMetrics.map((metric) => {
                const stageKey =
                  metric.key === "total_opportunities" ? "" : (metric.key as OpportunityStage);
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

              <div className="filter-field">
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

          <Panel dense className="workspace-toolbar">
            <div className="workspace-toolbar__main">
              <Tabs
                label="Vista"
                value={queryState.tab}
                options={TAB_OPTIONS}
                onChange={handleTabChange}
              />
              <div className="workspace-toolbar__summary">
                <strong>{queryState.tab === "explorer" ? "Tabla de licitaciones" : "Radar por etapa"}</strong>
                <span>{listState.status === "success" ? `${formatCount(listState.data.total)} resultados` : "Resultados pendientes"}</span>
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
                    <strong>{column.label}</strong>
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
                        className={
                          item.noticeId === queryState.selectedNoticeId
                            ? "opportunity-card opportunity-card--selected"
                            : "opportunity-card"
                        }
                        onClick={() => openDetail("radar", item.noticeId)}
                      >
                        <h3 className="opportunity-card__title">
                          {formatUnavailable(item.externalNoticeCode)} - {item.title}
                        </h3>
                        <div className="opportunity-card__meta">
                          <span className={stageClassName(item.derivedStage)}>
                            {formatStage(item.derivedStage)}
                          </span>
                          <span>{`Comprador: ${formatUnavailable(item.buyerName)}`}</span>
                          <span>{`Cierre: ${formatDate(item.closeDate)}`}</span>
                          <span>{`Monto: ${formatMoney(item.estimatedAmount, item.currencyCode)}`}</span>
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
                          <td className="ui-table-number">{formatCount(item.purchaseOrderCount)}</td>
                        </tr>
                        {isExpanded ? (
                          <tr key={`${item.noticeId}-expanded`} className="ui-table-expanded-row">
                            <td colSpan={12}>
                              <div className="table-evidence-panel">
                                <div>
                                  <span className="evidence-label">Categoria</span>
                                  <strong>{formatUnavailable(item.primaryCategory)}</strong>
                                </div>
                                <div>
                                  <span className="evidence-label">Publicacion</span>
                                  <strong>{formatDate(item.publicationDate)}</strong>
                                </div>
                                <div>
                                  <span className="evidence-label">Dias restantes</span>
                                  <strong>{item.daysRemaining === null ? "Cerrada o sin fecha" : formatCount(item.daysRemaining)}</strong>
                                </div>
                                <div>
                                  <span className="evidence-label">Evidencia</span>
                                  <strong>{`${formatCount(item.bidCount)} ofertas · ${formatCount(item.supplierCount)} proveedores · ${formatCount(item.purchaseOrderCount)} OC`}</strong>
                                </div>
                                <Button onClick={() => openDetail("explorer", item.noticeId)}>
                                  Abrir detalle
                                </Button>
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

        {queryState.selectedNoticeId ? (
        <aside className="workspace-detail" aria-label="Detalle de oportunidad">
          <header className="workspace-detail__header">
            <strong>Detalle</strong>
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
              <DetailSection title="Cabecera de decision">
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
            </>
          ) : null}
        </aside>
        ) : null}
      </div>
    </main>
  );
}
