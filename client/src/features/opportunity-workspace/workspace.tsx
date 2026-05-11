"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import {
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  CircleDollarSign,
  FileSpreadsheet,
  FilterX,
  Printer,
  RefreshCw,
  Search,
  ServerCrash,
  ShieldCheck,
  SlidersHorizontal,
  Star,
  Terminal,
  Upload,
  X,
} from "lucide-react";

import {
  preflightManualCsvUpload,
  fetchManualCsvUploadJob,
  processManualCsvUpload,
} from "@/src/lib/api/manual-uploads";
import {
  fetchOpportunityDetail,
  fetchOpportunities,
  fetchOpportunitySummary,
} from "@/src/lib/api/opportunities";
import {
  formatCount,
  formatStage,
} from "@/src/lib/formatters/opportunities";
import { ThemeToggle } from "@/src/components/theme-toggle";
import { WorkspaceDetailPane } from "@/src/features/opportunity-workspace/workspace-detail-pane";
import {
  WorkspaceExplorerTable,
  WorkspaceRadarBoard,
} from "@/src/features/opportunity-workspace/workspace-list-views";
import { useOpportunityWorkspaceQueryState } from "@/src/features/opportunity-workspace/query-state";
import {
  type UploadConsoleEntry,
  type UploadJobState,
  type UploadPreflightState,
  useUploadWorkflowState,
} from "@/src/features/opportunity-workspace/upload-workflow-state";
import {
  buildOpportunityWorkspaceCsv,
  getActiveFilterChips,
  getSortLabel,
  HEADER_METRIC_FALLBACKS,
  MANUAL_UPLOAD_DATASET_OPTIONS,
  metricClassName,
  metricKeyToStage,
  parseAmountInput,
  PRIMARY_METRIC_KEYS,
  STAGE_COLUMNS,
  TAB_OPTIONS,
  toManualUploadError,
  toReadableError,
  uniqueByNoticeId,
  UPLOAD_CONSOLE_SEED,
  WATCHLIST_STORAGE_KEY,
  formatCompactMetricValue,
  formatDatasetTypeLabel,
  formatFileSize,
  formatMetricValue,
  formatToday,
} from "@/src/features/opportunity-workspace/workspace-view-model";
import {
  WORKSPACE_DEFAULTS,
} from "@/src/lib/url-state/workspace";
import type {
  ManualUploadDatasetType,
} from "@/src/types/manual-uploads";
import type {
  OpportunityDetail,
  OpportunityListItem,
  OpportunityListResponse,
  OpportunitySortDirection,
  OpportunitySortField,
  OpportunityStage,
  OpportunitySummaryResponse,
  WorkspaceTab,
} from "@/src/types/opportunities";
import {
  Badge,
  Button,
  Chip,
  IconButton,
  Input,
  Panel,
  Select,
  Skeleton,
  Tabs,
} from "@/src/components/ui";

type RemoteState<T> =
  | { status: "idle" | "loading" }
  | { status: "success"; data: T }
  | { status: "error"; message: string; statusCode: number | null };

const TODAY_LABEL_PLACEHOLDER = "Hoy --/--/----";
const SUBSCRIBE_NOOP = () => () => undefined;

function getTodayLabelSnapshot(): string {
  return `Hoy ${formatToday(new Date())}`;
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
  const { queryState, filters, activeFilters, explorerScopeKey, replaceQuery } =
    useOpportunityWorkspaceQueryState();

  const [listState, setListState] = useState<RemoteState<OpportunityListResponse>>({
    status: "loading",
  });
  const [summaryState, setSummaryState] = useState<RemoteState<OpportunitySummaryResponse>>({
    status: "loading",
  });
  const [detailState, setDetailState] = useState<RemoteState<OpportunityDetail>>(() =>
    queryState.selectedNoticeId ? { status: "loading" } : { status: "idle" },
  );
  const [detailRefreshNonce, setDetailRefreshNonce] = useState(0);
  const [expandedNoticeId, setExpandedNoticeId] = useState<string | null>(null);
  const [explorerInfiniteItems, setExplorerInfiniteItems] = useState<OpportunityListItem[]>([]);
  const [isLoadingMoreExplorer, setIsLoadingMoreExplorer] = useState(false);
  const [loadMoreErrorMessage, setLoadMoreErrorMessage] = useState<string | null>(null);
  const [watchlistNoticeIds, setWatchlistNoticeIds] = useState<string[]>(() => {
    if (typeof window === "undefined") {
      return [];
    }
    try {
      const raw = window.localStorage.getItem(WATCHLIST_STORAGE_KEY);
      if (!raw) {
        return [];
      }
      const parsed = JSON.parse(raw) as unknown;
      if (!Array.isArray(parsed)) {
        return [];
      }
      return Array.from(
        new Set(
          parsed
            .filter((value): value is string => typeof value === "string")
            .map((noticeId) => noticeId.trim())
            .filter((noticeId) => noticeId.length > 0),
        ),
      );
    } catch {
      return [];
    }
  });
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [selectedExplorerNoticeIds, setSelectedExplorerNoticeIds] = useState<string[]>([]);
  const [reloadNonce, setReloadNonce] = useState(0);
  const [isUploadSheetOpen, setIsUploadSheetOpen] = useState(false);
  const [uploadDatasetType, setUploadDatasetType] = useState<ManualUploadDatasetType | "">("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploadDragActive, setIsUploadDragActive] = useState(false);
  const [uploadPreflightState, setUploadPreflightState] =
    useState<UploadPreflightState>({ status: "idle" });
  const [uploadJobState, setUploadJobState] = useState<UploadJobState>({ status: "idle" });
  const [uploadConsoleEntries, setUploadConsoleEntries] = useState<UploadConsoleEntry[]>([
    UPLOAD_CONSOLE_SEED,
  ]);
  const todayLabel = useSyncExternalStore(
    SUBSCRIBE_NOOP,
    getTodayLabelSnapshot,
    () => TODAY_LABEL_PLACEHOLDER,
  );
  const uploadAbortRef = useRef<AbortController | null>(null);
  const previousUploadPreflightStatus = useRef(uploadPreflightState.status);
  const previousUploadJobStatus = useRef(uploadJobState.status);
  const previousUploadRunningConsoleKey = useRef<string | null>(null);
  const skipSummaryFetchRef = useRef(false);
  const appendListFetchRef = useRef(false);
  const loadMoreTriggerLockRef = useRef(false);
  const explorerLoadMoreRef = useRef<HTMLDivElement | null>(null);
  const explorerScopeKeyRef = useRef<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const uploadRunningJobId =
    uploadJobState.status === "running" ? uploadJobState.data.job_id : null;
  const uploadRunningConsoleKey =
    uploadJobState.status === "running"
      ? `${uploadJobState.data.progress.phase}:${Math.floor(uploadJobState.data.progress.percent / 5)}`
      : null;

  const refreshList = useCallback(
    (
      patch: Partial<typeof queryState>,
      options?: { preserveList?: boolean; preserveSummary?: boolean },
    ) => {
      if (!options?.preserveList) {
        setListState({ status: "loading" });
      } else {
        appendListFetchRef.current = true;
      }
      if (!options?.preserveSummary) {
        setSummaryState({ status: "loading" });
      } else {
        skipSummaryFetchRef.current = true;
      }
      setSelectedExplorerNoticeIds([]);
      replaceQuery(patch);
    },
    [replaceQuery],
  );

  const openDetail = useCallback(
    (tab: WorkspaceTab, noticeId: string) => {
      setDetailState({ status: "loading" });
      setDetailRefreshNonce((current) => current + 1);
      replaceQuery({ tab, selectedNoticeId: noticeId });
    },
    [replaceQuery],
  );

  useEffect(() => {
    const controller = new AbortController();
    const skipSummaryFetch = skipSummaryFetchRef.current;
    const appendListFetch = appendListFetchRef.current;
    skipSummaryFetchRef.current = false;
    appendListFetchRef.current = false;

    fetchOpportunities(filters, controller.signal)
      .then((data) => {
        setListState({ status: "success", data });
        setLoadMoreErrorMessage(null);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const normalized = toReadableError(error);
        if (appendListFetch) {
          setLoadMoreErrorMessage(normalized.message);
          return;
        }
        setListState({
          status: "error",
          message: normalized.message,
          statusCode: normalized.statusCode,
        });
      })
      .finally(() => {
        setIsLoadingMoreExplorer(false);
        loadMoreTriggerLockRef.current = false;
      });

    if (!skipSummaryFetch) {
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
    }

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
  }, [queryState.selectedNoticeId, detailRefreshNonce]);

  useEffect(() => {
    return () => uploadAbortRef.current?.abort();
  }, []);

  const appendUploadConsoleEntries = useCallback((entries: UploadConsoleEntry[]) => {
    if (entries.length === 0) {
      return;
    }

    setUploadConsoleEntries((current) => {
      const next = [...current];
      for (const entry of entries) {
        const last = next[next.length - 1];
        if (last && last.level === entry.level && last.text === entry.text) {
          continue;
        }
        next.push(entry);
      }
      return next.slice(-12);
    });
  }, []);

  const resetUploadConsole = useCallback(() => {
    setUploadConsoleEntries([UPLOAD_CONSOLE_SEED]);
  }, []);

  useEffect(() => {
    if (previousUploadPreflightStatus.current === uploadPreflightState.status) {
      return;
    }
    previousUploadPreflightStatus.current = uploadPreflightState.status;

    if (uploadPreflightState.status === "loading") {
      queueMicrotask(() => {
        appendUploadConsoleEntries([
          { level: "running", text: "Validando archivo: delimitador, columnas, hash y tamaño." },
        ]);
      });
      return;
    }

    if (uploadPreflightState.status === "error") {
      queueMicrotask(() => {
        appendUploadConsoleEntries([
          { level: "error", text: `Validación previa rechazada: ${uploadPreflightState.message}` },
        ]);
      });
      return;
    }

    if (uploadPreflightState.status === "success") {
      queueMicrotask(() => {
        appendUploadConsoleEntries([
          {
            level: "done",
            text: `Validación previa completada: ${formatCount(uploadPreflightState.data.row_count)} filas, hash ${uploadPreflightState.data.file_hash_sha256.slice(0, 12)}…`,
          },
          {
            level: "muted",
            text: uploadPreflightState.data.duplicate_source_file
              ? "Este archivo ya fue procesado anteriormente."
              : "Archivo listo para procesar.",
          },
        ]);
      });
    }
  }, [appendUploadConsoleEntries, uploadPreflightState.status, uploadPreflightState]);

  useEffect(() => {
    if (previousUploadJobStatus.current === uploadJobState.status) {
      return;
    }
    previousUploadJobStatus.current = uploadJobState.status;

    if (uploadJobState.status === "loading") {
      queueMicrotask(() => {
        appendUploadConsoleEntries([
          { level: "running", text: "Procesando archivo…" },
          { level: "muted", text: "Esto puede tardar varios minutos en CSV grandes." },
        ]);
      });
      return;
    }

    if (uploadJobState.status === "running") {
      queueMicrotask(() => {
        appendUploadConsoleEntries([
          {
            level: "running",
            text: `${uploadJobState.data.progress.label} · ${uploadJobState.data.progress.percent}%`,
          },
          {
            level: "muted",
            text: "Puedes cerrar esta ventana. El proceso continua en el servidor.",
          },
        ]);
      });
      previousUploadRunningConsoleKey.current = uploadRunningConsoleKey;
      return;
    }

    if (uploadJobState.status === "error") {
      queueMicrotask(() => {
        appendUploadConsoleEntries([
          { level: "error", text: `Proceso fallido: ${uploadJobState.message}` },
        ]);
      });
      return;
    }

    if (uploadJobState.status === "success") {
      queueMicrotask(() => {
        appendUploadConsoleEntries([
          {
            level: "done",
            text: `Proceso completado: ${formatCount(uploadJobState.data.telemetry.processed_rows)} registros procesados.`,
          },
          {
            level: "done",
            text: `Datos listos: ${formatCount(uploadJobState.data.telemetry.normalized_rows)} unificados, ${formatCount(uploadJobState.data.telemetry.silver_rows)} finales.`,
          },
        ]);
      });
    }
  }, [appendUploadConsoleEntries, uploadJobState.status, uploadJobState, uploadRunningConsoleKey]);

  useEffect(() => {
    if (uploadJobState.status !== "running" || uploadRunningConsoleKey === null) {
      previousUploadRunningConsoleKey.current = null;
      return;
    }

    if (previousUploadRunningConsoleKey.current === uploadRunningConsoleKey) {
      return;
    }

    previousUploadRunningConsoleKey.current = uploadRunningConsoleKey;
    queueMicrotask(() => {
      appendUploadConsoleEntries([
        {
          level: "running",
          text: `${uploadJobState.data.progress.label}: ${uploadJobState.data.progress.percent}%`,
        },
      ]);
    });
  }, [appendUploadConsoleEntries, uploadJobState, uploadRunningConsoleKey]);

  useEffect(() => {
    if (!uploadRunningJobId) {
      return;
    }

    const controller = new AbortController();
    let stopped = false;
    let timeoutId: number | undefined;

    const scheduleNextPoll = (delayMs: number) => {
      timeoutId = window.setTimeout(() => {
        void pollOnce();
      }, delayMs);
    };

    const pollOnce = async () => {
      if (stopped) {
        return;
      }

      try {
        const data = await fetchManualCsvUploadJob(uploadRunningJobId, controller.signal);
        if (stopped) {
          return;
        }

        if (data.terminal_state) {
          setUploadJobState({ status: "success", data });
          setListState({ status: "loading" });
          setSummaryState({ status: "loading" });
          setReloadNonce((current) => current + 1);
          queueMicrotask(() => {
            appendUploadConsoleEntries([
                {
                  level: "done",
                  text: `Proceso finalizado: ${data.progress.percent}% completado.`,
                },
            ]);
          });
          return;
        }

        setUploadJobState({ status: "running", data });
        scheduleNextPoll(1800);
      } catch (error) {
        if (stopped || controller.signal.aborted) {
          return;
        }
        const normalized = toManualUploadError(error);
        setUploadJobState({
          status: "error",
          message: normalized.message,
          statusCode: normalized.statusCode,
        });
      }
    };

    scheduleNextPoll(1500);

    return () => {
      stopped = true;
      controller.abort();
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
    }, [appendUploadConsoleEntries, uploadRunningJobId]);



  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(watchlistNoticeIds));
    } catch {
      // Ignore persistence errors in constrained browsers.
    }
  }, [watchlistNoticeIds]);

  useEffect(() => {
    if (queryState.tab !== "explorer") {
      return;
    }
    if (listState.status !== "success") {
      return;
    }

    const shouldReset =
      queryState.page <= 1 || explorerScopeKeyRef.current !== explorerScopeKey;
    const incoming = uniqueByNoticeId(listState.data.items);

    setExplorerInfiniteItems((current) =>
      shouldReset ? incoming : uniqueByNoticeId([...current, ...incoming]),
    );
    explorerScopeKeyRef.current = explorerScopeKey;
  }, [explorerScopeKey, listState, queryState.page, queryState.tab]);

  const baseListItems = useMemo(() => {
    if (listState.status !== "success") {
      return [];
    }
    if (queryState.tab === "explorer") {
      return uniqueByNoticeId(explorerInfiniteItems);
    }
    return uniqueByNoticeId(listState.data.items);
  }, [explorerInfiniteItems, listState, queryState.tab]);

  const listItems = useMemo(() => {
    if (!watchlistOnly) {
      return baseListItems;
    }
    const watchlistSet = new Set(watchlistNoticeIds);
    return baseListItems.filter((item) => watchlistSet.has(item.noticeId));
  }, [baseListItems, watchlistNoticeIds, watchlistOnly]);

  const metrics = useMemo(
    () => (summaryState.status === "success" ? summaryState.data.metrics : []),
    [summaryState],
  );
  const pulseMetrics = metrics.filter((metric) => PRIMARY_METRIC_KEYS.has(metric.key));
  const economyMetrics = metrics.filter((metric) => !PRIMARY_METRIC_KEYS.has(metric.key));
  const activeFilterChips = getActiveFilterChips(queryState);
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

  const noResults =
    listState.status === "success" &&
    listItems.length === 0 &&
    activeFilters &&
    !watchlistOnly;
  const emptyState =
    listState.status === "success" &&
    listItems.length === 0 &&
    !activeFilters &&
    !watchlistOnly;
  const watchlistEmptyState =
    listState.status === "success" &&
    listItems.length === 0 &&
    watchlistOnly;
  const canAutoLoadMore =
    listState.status === "success" &&
    queryState.tab === "explorer" &&
    !watchlistOnly &&
    listItems.length < listState.data.total;
  const {
    uploadCanValidate,
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
  } = useUploadWorkflowState({
    uploadDatasetType,
    uploadFile,
    uploadPreflightState,
    uploadJobState,
  });
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
      ? watchlistOnly
        ? `${formatCount(listItems.length)} en radar`
        : `${formatCount(listState.data.total)} licitaciones`
      : "Resultados pendientes";

  useEffect(() => {
    if (!canAutoLoadMore || queryState.tab !== "explorer") {
      return;
    }
    const sentinel = explorerLoadMoreRef.current;
    if (!sentinel) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (!entry?.isIntersecting) {
          return;
        }
        if (loadMoreTriggerLockRef.current) {
          return;
        }
        loadMoreTriggerLockRef.current = true;
        setLoadMoreErrorMessage(null);
        setIsLoadingMoreExplorer(true);
        refreshList(
          { page: queryState.page + 1 },
          { preserveList: true, preserveSummary: true },
        );
      },
      {
        root: null,
        rootMargin: "0px 0px 260px 0px",
        threshold: 0.1,
      },
    );
    observer.observe(sentinel);

    return () => observer.disconnect();
  }, [canAutoLoadMore, queryState.page, queryState.tab, refreshList]);

  const handleTabChange = (tab: WorkspaceTab) => {
    refreshList({ tab, page: 1 });
  };

  const handleStagePulse = (stage: OpportunityStage | "") => {
    refreshList({ stage, page: 1, selectedNoticeId: null });
  };

  const handleSort = useCallback(
    (field: OpportunitySortField) => {
      const isCurrent = queryState.sortBy === field;
      const defaultOrder: Record<OpportunitySortField, OpportunitySortDirection> = {
        close_date: "asc",
        days_remaining: "asc",
        estimated_amount: "desc",
        publication_date: "desc",
      };
      const nextOrder: OpportunitySortDirection = isCurrent
        ? queryState.sortOrder === "asc"
          ? "desc"
          : "asc"
        : defaultOrder[field];
      refreshList({ sortBy: field, sortOrder: nextOrder, page: 1 });
    },
    [queryState.sortBy, queryState.sortOrder, refreshList],
  );

  const handleToggleExpanded = (noticeId: string) => {
    setExpandedNoticeId((current) => (current === noticeId ? null : noticeId));
  };

  const handleRetryLoadMore = useCallback(() => {
    loadMoreTriggerLockRef.current = false;
    setLoadMoreErrorMessage(null);
    setIsLoadingMoreExplorer(true);
    refreshList(
      { page: queryState.page + 1 },
      { preserveList: true, preserveSummary: true },
    );
  }, [queryState.page, refreshList]);

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

  const handleCloseDetail = useCallback(() => {
    setDetailState({ status: "idle" });
    replaceQuery({ selectedNoticeId: null });
  }, [replaceQuery]);

  const handleCopyNoticeCode = useCallback(
    async (externalNoticeCode: string | null): Promise<boolean> => {
      if (!externalNoticeCode || !navigator.clipboard) {
        return false;
      }

      try {
        await navigator.clipboard.writeText(externalNoticeCode);
        return true;
      } catch {
        return false;
      }
    },
    [],
  );

  const handleToggleSelectedNotice = useCallback((noticeId: string) => {
    setSelectedExplorerNoticeIds((current) =>
      current.includes(noticeId)
        ? current.filter((id) => id !== noticeId)
        : [...current, noticeId],
    );
  }, []);

  const handleToggleAllSelectedNotices = useCallback(
    (checked: boolean) => {
      setSelectedExplorerNoticeIds(checked ? listItems.map((item) => item.noticeId) : []);
    },
    [listItems],
  );

  const handleClearSelectedNoticeIds = useCallback(() => {
    setSelectedExplorerNoticeIds([]);
  }, []);

  const handleAddSelectedToWatchlist = useCallback(() => {
    if (selectedExplorerNoticeIds.length === 0) {
      return;
    }

    setWatchlistNoticeIds((current) =>
      Array.from(new Set([...current, ...selectedExplorerNoticeIds])),
    );
  }, [selectedExplorerNoticeIds]);

  const handleRemoveSelectedFromWatchlist = useCallback(() => {
    if (selectedExplorerNoticeIds.length === 0) {
      return;
    }

    const selectedSet = new Set(selectedExplorerNoticeIds);
    setWatchlistNoticeIds((current) => current.filter((id) => !selectedSet.has(id)));
  }, [selectedExplorerNoticeIds]);

  const toggleWatchlistNotice = useCallback((noticeId: string) => {
    setWatchlistNoticeIds((current) =>
      current.includes(noticeId)
        ? current.filter((id) => id !== noticeId)
        : [...current, noticeId],
    );
  }, []);

  const handleExportVisibleItemsCsv = useCallback(() => {
    if (listState.status !== "success" || listItems.length === 0) {
      return;
    }

    const csv = buildOpportunityWorkspaceCsv(listItems, watchlistNoticeIds);
    const fileName = `oportunidades-${new Date().toISOString().slice(0, 10)}.csv`;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => {
      window.URL.revokeObjectURL(url);
    }, 0);
  }, [listItems, listState.status, watchlistNoticeIds]);

  const handlePrintVisibleSnapshot = useCallback(() => {
    if (listState.status !== "success") {
      return;
    }
    window.print();
  }, [listState.status]);

  const closeUploadSheet = useCallback(() => {
    setIsUploadSheetOpen(false);
    setIsUploadDragActive(false);
  }, []);

  const handleWorkspaceShortcutKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.isContentEditable ||
          target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT")
      ) {
        return;
      }

      const key = event.key.toLowerCase();

      if (key === "escape") {
        if (isUploadSheetOpen) {
          event.preventDefault();
          closeUploadSheet();
          return;
        }
        if (queryState.selectedNoticeId) {
          event.preventDefault();
          handleCloseDetail();
        }
        return;
      }

      const hasModifier = event.ctrlKey || event.metaKey;
      if (!hasModifier) {
        return;
      }

      if (key === "f" && !event.shiftKey) {
        event.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
        return;
      }

      if (event.shiftKey && key === "e") {
        event.preventDefault();
        handleExportVisibleItemsCsv();
        return;
      }

      if (event.shiftKey && key === "p") {
        event.preventDefault();
        handlePrintVisibleSnapshot();
      }
    },
    [
      closeUploadSheet,
      handleCloseDetail,
      handleExportVisibleItemsCsv,
      handlePrintVisibleSnapshot,
      isUploadSheetOpen,
      queryState.selectedNoticeId,
    ],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleWorkspaceShortcutKeyDown);
    return () => window.removeEventListener("keydown", handleWorkspaceShortcutKeyDown);
  }, [handleWorkspaceShortcutKeyDown]);

  const abortActiveUpload = useCallback(() => {
    uploadAbortRef.current?.abort();
    uploadAbortRef.current = null;
  }, []);

  const resetUploadProgress = useCallback(() => {
    setUploadPreflightState({ status: "idle" });
    setUploadJobState({ status: "idle" });
  }, []);

  const handleUploadFileSelected = useCallback(
    (nextFile: File | null) => {
      if (uploadJobIsActive) {
        return;
      }
      setUploadFile(nextFile);
      resetUploadProgress();
      if (nextFile) {
        appendUploadConsoleEntries([
          {
            level: "info",
            text: `Archivo montado: ${nextFile.name} (${formatFileSize(nextFile.size)}).`,
          },
        ]);
      } else {
        appendUploadConsoleEntries([{ level: "muted", text: "Archivo removido. Esperando CSV." }]);
      }
    },
    [appendUploadConsoleEntries, resetUploadProgress, uploadJobIsActive],
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
      if (data.terminal_state) {
        setUploadJobState({ status: "success", data });
        setListState({ status: "loading" });
        setSummaryState({ status: "loading" });
        setReloadNonce((current) => current + 1);
      } else {
        setUploadJobState({ status: "running", data });
      }
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
      <div
        className={
          queryState.selectedNoticeId
            ? "workspace-layout workspace-layout--with-detail"
            : "workspace-layout"
        }
      >
        <div className="sr-only" aria-live="polite" aria-atomic="true">
          {listState.status === "loading"
            ? "Cargando oportunidades"
            : listState.status === "error"
              ? "Error al cargar oportunidades"
              : listState.status === "success"
                ? `${formatCount(listState.data.total)} oportunidades encontradas`
                : ""}
        </div>
        <section
          className={
            queryState.selectedNoticeId
              ? "workspace-main workspace-main--with-detail"
              : "workspace-main"
          }
          aria-label="Vista principal de oportunidades"
        >
          <header className="workspace-header">
            <div className="workspace-header__content">
              <div className="workspace-header__eyebrow-row">
                <div className="workspace-header__eyebrow-copy">
                  <span className="workspace-kicker">Control operativo</span>
                  <Badge>Lista y Radar en solo lectura</Badge>
                </div>
              </div>
              <h1 className="workspace-title">Espacio de oportunidades</h1>
              <p className="workspace-subtitle">
                Filtra, revisa y comparte la vista sin salir de aquí. El radar funciona como una
                lista local de seguimiento y el Centro de Ingesta sigue separado.
              </p>
              <div className="workspace-header__meta" aria-label="Estado del espacio">
                <Badge>{queryState.tab === "radar" ? "Radar activo" : "Lista activa"}</Badge>
                <span>{activeFilters ? "Filtros aplicados" : "Vista base"}</span>
                <span>{apiStatusLabel}</span>
                <span>{todayLabel}</span>
              </div>
            </div>
            <div className="workspace-header__aside">
              <section className="workspace-mode" aria-label="Vista rápida">
                <div className="workspace-mode__topline">
                  <span className="workspace-mode__label">Vista rápida</span>
                  <span>{`${activeFilters ? activeFilterChips.length : 0} filtros`}</span>
                </div>
                <div className="workspace-mode__hero" aria-label="Resumen operativo">
                  <div>
                    <small>{queryState.tab === "radar" ? "Radar activo" : "Lista activa"}</small>
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
                <Button
                  variant="ghost"
                  className={`workspace-mode__upload-trigger${
                    uploadFlowBusy ? " workspace-mode__upload-trigger--busy" : ""
                  }`}
                  leadingIcon={<Upload size={14} aria-hidden="true" />}
                  trailingIcon={
                    uploadFlowBusy ? (
                      <RefreshCw size={13} aria-hidden="true" className="upload-progress__spinner" />
                    ) : undefined
                  }
                  busy={uploadFlowBusy}
                  onClick={() => setIsUploadSheetOpen(true)}
                >
                  {uploadTriggerLabel}
                </Button>
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
                <strong>{queryState.tab === "explorer" ? "Lista" : "Radar"}</strong>
                <span>{resultStatusLabel}</span>
                <Chip>{getSortLabel(queryState.sortBy, queryState.sortOrder)}</Chip>
                <Chip>{`Radar ${formatCount(watchlistNoticeIds.length)}`}</Chip>
                <Button
                  variant={watchlistOnly ? "primary" : "ghost"}
                  className="workspace-toolbar__watchlist-toggle"
                  leadingIcon={<Star size={14} aria-hidden="true" />}
                  onClick={() => setWatchlistOnly((current) => !current)}
                >
                  {watchlistOnly ? "Ver todo" : "Solo radar"}
                </Button>
              </div>
              <div className="workspace-toolbar__actions" aria-label="Exportar, imprimir y tema">
                <ThemeToggle />
                <Button
                  variant="ghost"
                  leadingIcon={<FileSpreadsheet size={14} aria-hidden="true" />}
                  onClick={handleExportVisibleItemsCsv}
                  disabled={listState.status !== "success" || listItems.length === 0}
                >
                  Exportar CSV
                </Button>
                <Button
                  variant="ghost"
                  leadingIcon={<Printer size={14} aria-hidden="true" />}
                  onClick={handlePrintVisibleSnapshot}
                  disabled={listState.status !== "success"}
                >
                  Imprimir
                </Button>
              </div>
              <div className="workspace-pagination" aria-label="Estado de paginación">
                <Badge>{`Página ${queryState.page}`}</Badge>
                {queryState.tab === "explorer" ? (
                  <span className="workspace-pagination__hint">
                    Scroll continuo: carga automática al final.
                  </span>
                ) : null}
              </div>
            </div>
          </Panel>

          <section className="pulse-strip" aria-label="Pulso de oportunidades">
            <div className="pulse-strip__copy">
              <span className="workspace-kicker">Pulso de oportunidades</span>
              <p>
                {summaryState.status === "success"
                  ? "Resumen simple por etapa, monto y señales disponibles."
                  : "El resumen aparece cuando responde la API de oportunidades."}
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
                La API no entregó métricas de pulso para los filtros actuales.
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
                <h2 className="section-title">Busca y filtra sin ruido</h2>
                <p className="section-subtitle">
                  Busca lo esencial al frente. Lo avanzado queda a un clic y el resto se
                  mantiene como contexto.
                </p>
              </div>
              <div className="filter-panel__tools">
                <Chip>{`${activeFilterChips.length} activos`}</Chip>
                <Button
                  variant="ghost"
                  leadingIcon={<SlidersHorizontal size={14} aria-hidden="true" />}
                  onClick={handleRefreshCurrentFilters}
                >
                  Aplicar
                </Button>
                <details className="workspace-help">
                  <summary>Ayuda rápida</summary>
                  <div className="workspace-help__content">
                    <div>
                      <strong>Atajos</strong>
                      <ul>
                        <li>
                          <kbd>Ctrl</kbd>/<kbd>Cmd</kbd> + <kbd>F</kbd> enfoca la búsqueda.
                        </li>
                        <li>
                          <kbd>Ctrl</kbd>/<kbd>Cmd</kbd> + <kbd>Shift</kbd> + <kbd>E</kbd> exporta CSV.
                        </li>
                        <li>
                          <kbd>Ctrl</kbd>/<kbd>Cmd</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd> abre impresión.
                        </li>
                        <li>
                          <kbd>Esc</kbd> cierra el detalle o el centro de ingesta.
                        </li>
                      </ul>
                    </div>
                    <div>
                      <strong>Glosario</strong>
                      <ul>
                        <li>
                          <strong>Radar</strong>: tu lista local de seguimiento.
                        </li>
                        <li>
                          <strong>Certeza de relación</strong>: señal de qué tan claro es el
                          vínculo entre registros.
                        </li>
                      </ul>
                    </div>
                  </div>
                </details>
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
                    ref={searchInputRef}
                    id="workspace-search"
                    value={queryState.q}
                    placeholder="Código, nombre, comprador o categoría"
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
                  <option value="public">Pública</option>
                  <option value="private">Privada</option>
                  <option value="service">Servicios</option>
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
                  Ordenar
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
                  <option value="close_date:asc">Cierre más cercano</option>
                  <option value="close_date:desc">Cierre más lejano</option>
                  <option value="days_remaining:asc">Días restantes (menos primero)</option>
                  <option value="days_remaining:desc">Días restantes (más primero)</option>
                  <option value="publication_date:desc">Publicación reciente</option>
                  <option value="estimated_amount:desc">Monto mayor</option>
                </Select>
              </div>
            </div>

            <details className="advanced-filters">
              <summary>
                <span>Filtros avanzados</span>
                <Chip>{activeFilterChips.length > 0 ? "Revisar filtros" : "Opcional"}</Chip>
              </summary>
              <div className="filter-grid filter-grid--advanced">
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
                  <label className="ui-label" htmlFor="workspace-page-size">
                    Tamaño de página
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
                    Publicación desde
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
                    Publicación hasta
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
                    Monto máximo
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
              {activeFilterChips.length === 0 ? (
                <span>Sin filtros activos. Parte por búsqueda, etapa o menor a 100 UTM.</span>
              ) : (
                activeFilterChips.map((chip) => (
                  <button
                    key={chip.key}
                    type="button"
                    className="active-filter-chip"
                    aria-label={`Quitar filtro ${chip.label}`}
                    onClick={() => refreshList(chip.patch)}
                  >
                    <span>{chip.label}</span>
                    <X size={12} aria-hidden="true" />
                  </button>
                ))
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
              description="Los filtros actuales no devolvieron oportunidades. Ajusta filtros o limpia la búsqueda."
              action={<Button onClick={handleResetFilters}>Limpiar filtros</Button>}
            />
          ) : null}

          {emptyState ? (
            <NoDataState
              title="Sin oportunidades disponibles"
              description="Aun no existen oportunidades para mostrar en este entorno."
            />
          ) : null}

          {watchlistEmptyState ? (
            <NoDataState
              title="Sin licitaciones en radar"
              description="Marca licitaciones con la estrella para agregarlas a tu radar local."
              action={
                <Button variant="ghost" onClick={() => setWatchlistOnly(false)}>
                  Volver a toda la lista
                </Button>
              }
            />
          ) : null}

          {listState.status === "success" && queryState.tab === "radar" && listItems.length > 0 ? (
            <WorkspaceRadarBoard
              radarColumns={radarColumns}
              selectedNoticeId={queryState.selectedNoticeId}
              onOpenDetail={(noticeId) => openDetail("radar", noticeId)}
            />
          ) : null}

          {listState.status === "success" &&
          queryState.tab === "explorer" &&
          listItems.length > 0 ? (
            <WorkspaceExplorerTable
              listItems={listItems}
              selectedNoticeId={queryState.selectedNoticeId}
              expandedNoticeId={expandedNoticeId}
              watchlistNoticeIds={watchlistNoticeIds}
              selectedNoticeIds={selectedExplorerNoticeIds}
              sortBy={queryState.sortBy}
              sortOrder={queryState.sortOrder}
              onSort={handleSort}
              onOpenDetail={(noticeId) => openDetail("explorer", noticeId)}
              onToggleExpanded={handleToggleExpanded}
              onToggleWatchlistNotice={toggleWatchlistNotice}
              onToggleSelectedNotice={handleToggleSelectedNotice}
              onToggleAllSelectedNotices={handleToggleAllSelectedNotices}
              onClearSelectedNoticeIds={handleClearSelectedNoticeIds}
              onAddSelectedToWatchlist={handleAddSelectedToWatchlist}
              onRemoveSelectedFromWatchlist={handleRemoveSelectedFromWatchlist}
              explorerLoadMoreRef={explorerLoadMoreRef}
              isLoadingMoreExplorer={isLoadingMoreExplorer}
              loadMoreErrorMessage={loadMoreErrorMessage}
              onRetryLoadMore={handleRetryLoadMore}
              canAutoLoadMore={canAutoLoadMore}
            />
          ) : null}
        </section>

        {isUploadSheetOpen ? (
          <div className="upload-sheet-shell" role="dialog" aria-modal="true" aria-labelledby="upload-sheet-title">
            <button
              type="button"
              className="upload-sheet-shell__backdrop"
              aria-label="Cerrar centro de ingesta"
              onClick={closeUploadSheet}
            />
            <section className="upload-sheet">
              <header className="upload-sheet__header">
                <div>
                  <span className="workspace-kicker">Centro de Ingesta</span>
                  <h2 id="upload-sheet-title" className="section-title">
                    Cargar CSV al flujo
                  </h2>
                  <p className="section-subtitle">
                    Selecciona Licitaciones u Órdenes de compra, adjunta CSV y valida antes de cargar.
                  </p>
                </div>
                <IconButton
                  icon={<X size={15} aria-hidden="true" />}
                  label="Cerrar centro de ingesta"
                  onClick={closeUploadSheet}
                />
              </header>

              <div className="upload-sheet__body">
                <div
                  className="upload-dataset-toggle"
                  role="radiogroup"
                  aria-label="Destino de carga"
                >
                  {MANUAL_UPLOAD_DATASET_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      role="radio"
                      aria-checked={uploadDatasetType === option.value}
                      className={
                        uploadDatasetType === option.value
                          ? "upload-dataset-toggle__option upload-dataset-toggle__option--selected"
                          : "upload-dataset-toggle__option"
                      }
                      onClick={() => {
                        setUploadDatasetType(option.value);
                        appendUploadConsoleEntries([{ level: "info", text: `Destino de carga: ${option.label}.` }]);
                        resetUploadProgress();
                      }}
                      disabled={
                        uploadPreflightState.status === "loading" ||
                        uploadJobIsActive
                      }
                    >
                      <span>{option.label}</span>
                      <small>{option.helper}</small>
                    </button>
                  ))}
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
                    if (uploadJobIsActive) {
                      return;
                    }
                    setIsUploadDragActive(false);
                    handleUploadFileSelected(event.dataTransfer.files[0] ?? null);
                  }}
                  >
                    <input
                      className="sr-only"
                      type="file"
                      accept=".csv,text/csv"
                      disabled={uploadJobIsActive}
                      onChange={(event) => handleUploadFileSelected(event.target.files?.[0] ?? null)}
                    />
                  <FileSpreadsheet size={24} aria-hidden="true" />
                  <strong>{uploadFile ? uploadFile.name : "Arrastra CSV o haz clic para elegir"}</strong>
                  <span>
                    CSV delimitado por <code>;</code>. El backend revisa columnas requeridas, hash y límite
                    configurado.
                  </span>
                  {uploadFile ? (
                    <small>{`${formatFileSize(uploadFile.size)} · último cambio ${new Date(uploadFile.lastModified).toLocaleDateString("es-CL")}`}</small>
                  ) : (
                    <small>También puedes hacer clic para buscar el archivo.</small>
                  )}
                </label>

                <div className="upload-sheet__info" role="note">
                  <CircleAlert size={15} aria-hidden="true" />
                  <span>1 CSV por corrida, validación previa y procesamiento acotado al archivo cargado.</span>
                </div>

                <section className={`upload-workflow upload-workflow--${uploadFlowStage}`} aria-label="Progreso del flujo">
                  <div className="upload-workflow__header">
                    <div>
                      <span className="workspace-mode__label">Centro de Ingesta</span>
                      <strong>{uploadFlowHeadline}</strong>
                      <p>
                        Cierra el panel si quieres, el flujo sigue visible en el estado del botón y
                        vuelve al reabrir.
                      </p>
                    </div>
                    <Badge className={`upload-console__status upload-console__status--${uploadFlowTone}`}>
                      {uploadFlowBusy ? "En curso" : uploadFlowStage === "success" ? "Listo" : uploadFlowStage === "error" ? "Error" : "Preparado"}
                    </Badge>
                  </div>
                  <ol className="upload-workflow__steps">
                    {uploadWorkflowSteps.map((step) => (
                      <li
                        key={step.key}
                        className={`upload-workflow__step upload-workflow__step--${step.state}`}
                      >
                        <span className="upload-workflow__step-marker" aria-hidden="true" />
                        <div className="upload-workflow__step-body">
                          <div className="upload-workflow__step-copy">
                            <strong>{step.label}</strong>
                            <span>{step.summary}</span>
                          </div>
                          <div className="upload-workflow__meter" aria-hidden="true">
                            <span />
                          </div>
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>

                <section className="upload-console" aria-label="Consola de procesamiento" aria-live="polite" aria-atomic="false">
                  <div className="upload-console__header">
                    <span className="upload-console__title">
                      <Terminal size={15} aria-hidden="true" />
                      Consola de ingesta
                      <span
                        className={`upload-live-pips${
                          uploadFlowBusy ? " upload-live-pips--active" : " upload-live-pips--idle"
                        }`}
                        aria-hidden="true"
                      >
                        <span />
                        <span />
                        <span />
                      </span>
                    </span>
                    <Badge className={`upload-console__status upload-console__status--${uploadConsoleStatus.tone}`}>
                      {uploadConsoleStatus.label}
                    </Badge>
                  </div>
                  <ol className="upload-console__lines">
                    {uploadConsoleEntries.map((line, index) => (
                      <li key={`${index}-${line.level}-${line.text.slice(0, 32)}`} className={`upload-console__line upload-console__line--${line.level}`}>
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        <code>{line.text}</code>
                      </li>
                    ))}
                  </ol>
                </section>

                {uploadPreflightState.status === "loading" ? (
                  <div className="upload-progress" role="status">
                    <RefreshCw size={16} aria-hidden="true" className="upload-progress__spinner" />
                    <div>
                      <strong>Validación previa en curso</strong>
                      <span>Revisando delimitador, columnas requeridas, hash y resumen previo.</span>
                    </div>
                  </div>
                ) : null}

                {uploadPreflightState.status === "error" ? (
                  <NoDataState
                    title="Validación previa rechazada"
                    description={uploadPreflightState.message}
                    isError
                    statusCode={uploadPreflightState.statusCode}
                    action={
                      <Button
                        leadingIcon={<RefreshCw size={15} aria-hidden="true" />}
                        onClick={handleStartPreflight}
                        disabled={!uploadCanValidate}
                      >
                        Reintentar validación
                      </Button>
                    }
                  />
                ) : null}

                {uploadPreflightState.status === "success" ? (
                  <section className="upload-preview" aria-label="Resumen de validación previa">
                    <div className="upload-preview__header">
                      <div>
                        <span className="workspace-mode__label">Validación previa lista</span>
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
                          <strong>Hash ya visto en el flujo</strong>
                          <span>
                            Archivo origen previo: {uploadPreflightState.data.duplicate_source_file.file_name}. Si confirmas, la UI debe leer conteos canónicos y duplicados por separado.
                          </span>
                        </div>
                      </div>
                    ) : null}

                    <dl className="upload-preview__facts">
                      <div>
                        <dt>Nombre canónico</dt>
                        <dd>{uploadPreflightState.data.canonical_filename}</dd>
                      </div>
                      <div>
                        <dt>Hash SHA-256</dt>
                        <dd>{uploadPreflightState.data.file_hash_sha256.slice(0, 16)}…</dd>
                      </div>
                      <div>
                        <dt>Tamaño</dt>
                        <dd>{formatFileSize(uploadPreflightState.data.file_size_bytes)}</dd>
                      </div>
                      <div>
                        <dt>Preparación</dt>
                        <dd>{uploadPreflightState.data.status === "staged" ? "Listo para procesar" : "Ya consumido"}</dd>
                      </div>
                    </dl>
                  </section>
                ) : null}

                {uploadJobState.status === "loading" ? (
                  <div className="upload-progress upload-progress--processing" role="status">
                    <RefreshCw size={16} aria-hidden="true" className="upload-progress__spinner" />
                    <div>
                      <strong>Cargando los datos</strong>
                      <span>Backend registra Raw y construye deltas Normalized y Silver para el conjunto elegido.</span>
                    </div>
                    <Button variant="ghost" onClick={abortActiveUpload}>
                      Cancelar espera
                    </Button>
                  </div>
                ) : null}

                {uploadJobState.status === "running" && uploadJobProgress ? (
                  <div className="upload-progress upload-progress--processing" role="status" aria-busy="true">
                    <RefreshCw size={16} aria-hidden="true" className="upload-progress__spinner" />
                    <div className="upload-progress__body">
                      <div className="upload-progress__meta">
                        <div>
                          <strong>{uploadJobProgress.label}</strong>
                          <span>{uploadJobProgress.detail}</span>
                        </div>
                        <Badge>{`${uploadJobProgress.percent}%`}</Badge>
                      </div>
                      <div className="upload-progress__bar" aria-hidden="true">
                        <span
                          style={{
                            transform: `scaleX(${uploadJobProgress.percent / 100})`,
                          }}
                        />
                      </div>
                    </div>
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
                  <section className="upload-result" aria-label="Resultado de ingesta manual">
                    <div className="upload-result__header">
                      <div>
                        <span className="workspace-mode__label">Resultado final</span>
                        <strong>Flujo acotado completado</strong>
                        <p>{uploadJobState.data.original_filename}</p>
                      </div>
                      <Badge>Proceso {uploadJobState.data.job_id.slice(0, 8)}</Badge>
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
                        <span>Aceptadas en Raw</span>
                        <strong>{formatCount(uploadJobState.data.telemetry.accepted_rows)}</strong>
                      </article>
                      <article>
                        <span>Delta canónico</span>
                        <strong>{formatCount(uploadJobState.data.telemetry.inserted_delta_rows)}</strong>
                      </article>
                      <article>
                        <span>Duplicadas o existentes</span>
                        <strong>{formatCount(uploadJobState.data.telemetry.duplicate_existing_rows)}</strong>
                      </article>
                      <article>
                        <span>Normalizadas</span>
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
                  {uploadJobState.status === "loading" || uploadJobState.status === "running" ? (
                    <>
                      <div className="upload-sheet__actions-status" role="status" aria-busy="true">
                        <RefreshCw size={15} aria-hidden="true" className="upload-progress__spinner" />
                        <div>
                          <strong>
                            {uploadJobState.status === "running" && uploadJobProgress
                              ? uploadJobProgress.label
                              : "Procesando en backend"}
                          </strong>
                          <span>
                            {uploadJobState.status === "running" && uploadJobProgress
                              ? `${uploadJobProgress.percent}% · ${uploadJobProgress.detail}`
                              : "Las capas Raw, Normalized y Silver siguen en ejecución aunque cierres este panel."}
                          </span>
                        </div>
                      </div>
                      {uploadJobState.status === "loading" ? (
                        <Button variant="ghost" onClick={abortActiveUpload}>
                          Cancelar espera
                        </Button>
                      ) : null}
                      <Button variant="ghost" onClick={closeUploadSheet}>
                        Cerrar
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        variant="ghost"
                        leadingIcon={<FilterX size={14} aria-hidden="true" />}
                      onClick={() => {
                        abortActiveUpload();
                        setUploadDatasetType("");
                        setUploadFile(null);
                        setIsUploadDragActive(false);
                        resetUploadProgress();
                        resetUploadConsole();
                      }}
                    >
                      Limpiar
                    </Button>
                    <Button variant="ghost" onClick={closeUploadSheet}>
                      Cerrar
                    </Button>
                    <Button
                      leadingIcon={<ShieldCheck size={15} aria-hidden="true" />}
                      onClick={handleStartPreflight}
                      disabled={
                        !uploadCanValidate ||
                        uploadPreflightState.status === "loading"
                      }
                      loading={uploadPreflightState.status === "loading"}
                    >
                      Validar archivo
                    </Button>
                    <Button
                      variant="primary"
                      leadingIcon={<Upload size={15} aria-hidden="true" />}
                      onClick={handleStartProcessing}
                      disabled={!uploadCanProcess}
                    >
                      Cargar archivo
                    </Button>
                  </>
                )}
              </footer>
            </section>
          </div>
        ) : null}

        <WorkspaceDetailPane
          selectedNoticeId={queryState.selectedNoticeId}
          tab={queryState.tab}
          detailState={detailState}
          onClose={handleCloseDetail}
          onRetry={() => {
            setDetailState({ status: "loading" });
            setDetailRefreshNonce((current) => current + 1);
            replaceQuery({ selectedNoticeId: queryState.selectedNoticeId });
          }}
          onCopyNoticeCode={handleCopyNoticeCode}
        />
      </div>
    </main>
  );
}
