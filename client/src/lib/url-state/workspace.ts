import type {
  OpportunityFilters,
  ProcurementTypeFilter,
  SourceViewFilter,
  OpportunitySortDirection,
  OpportunitySortField,
  OpportunityStage,
  OpportunityWorkspaceQueryState,
  WorkspaceTab,
} from "@/src/types/opportunities";
import { OPPORTUNITY_STAGES } from "@/src/types/opportunities";

type ReadOnlyParams = Pick<URLSearchParams, "get" | "toString">;

const VALID_TABS: WorkspaceTab[] = ["radar", "explorer"];
const VALID_SORT_FIELDS: OpportunitySortField[] = [
  "close_date",
  "publication_date",
  "estimated_amount",
  "days_remaining",
];
const VALID_SORT_DIRECTIONS: OpportunitySortDirection[] = ["asc", "desc"];
const VALID_PROCUREMENT_TYPES: ProcurementTypeFilter[] = ["public", "private", "service"];
const VALID_SOURCE_VIEWS: SourceViewFilter[] = ["publicadas"];

const DEFAULT_QUERY_STATE: OpportunityWorkspaceQueryState = {
  tab: "explorer",
  selectedNoticeId: null,
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
  sourceView: "",
  lessThan100Utm: false,
  page: 1,
  pageSize: 20,
  sortBy: "close_date",
  sortOrder: "asc",
};

function parsePositiveInteger(value: string | null, fallback: number): number {
  if (!value) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback;
  }
  return parsed;
}

function parseStage(value: string | null): OpportunityStage | "" {
  if (!value) {
    return "";
  }
  const stage = value as OpportunityStage;
  return OPPORTUNITY_STAGES.includes(stage) ? stage : "";
}

function parseSortField(value: string | null): OpportunitySortField {
  if (!value) {
    return DEFAULT_QUERY_STATE.sortBy;
  }
  const sortBy = value as OpportunitySortField;
  return VALID_SORT_FIELDS.includes(sortBy) ? sortBy : DEFAULT_QUERY_STATE.sortBy;
}

function parseSortOrder(value: string | null): OpportunitySortDirection {
  if (!value) {
    return DEFAULT_QUERY_STATE.sortOrder;
  }
  const sortOrder = value as OpportunitySortDirection;
  return VALID_SORT_DIRECTIONS.includes(sortOrder)
    ? sortOrder
    : DEFAULT_QUERY_STATE.sortOrder;
}

function parseTab(value: string | null): WorkspaceTab {
  if (!value) {
    return DEFAULT_QUERY_STATE.tab;
  }
  const tab = value as WorkspaceTab;
  return VALID_TABS.includes(tab) ? tab : DEFAULT_QUERY_STATE.tab;
}

function parseProcurementType(value: string | null): ProcurementTypeFilter | "" {
  if (!value) {
    return "";
  }
  const procurementType = value as ProcurementTypeFilter;
  return VALID_PROCUREMENT_TYPES.includes(procurementType) ? procurementType : "";
}

function parseSourceView(value: string | null): SourceViewFilter | "" {
  if (!value) {
    return "";
  }
  const sourceView = value as SourceViewFilter;
  return VALID_SOURCE_VIEWS.includes(sourceView) ? sourceView : "";
}

function parseBoolean(value: string | null): boolean {
  return value === "true";
}

function parseAmount(value: string): number | undefined {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined;
}

export function parseWorkspaceQueryState(
  searchParams: URLSearchParams | ReadOnlyParams,
): OpportunityWorkspaceQueryState {
  return {
    tab: parseTab(searchParams.get("tab")),
    selectedNoticeId: searchParams.get("selected"),
    q: DEFAULT_QUERY_STATE.q,
    officialStatus: searchParams.get("status") ?? DEFAULT_QUERY_STATE.officialStatus,
    stage: parseStage(searchParams.get("stage")),
    buyerRegion: searchParams.get("region") ?? DEFAULT_QUERY_STATE.buyerRegion,
    primaryCategory: searchParams.get("category") ?? DEFAULT_QUERY_STATE.primaryCategory,
    publicationFrom:
      searchParams.get("publication_from") ?? DEFAULT_QUERY_STATE.publicationFrom,
    publicationTo: searchParams.get("publication_to") ?? DEFAULT_QUERY_STATE.publicationTo,
    closeFrom: searchParams.get("close_from") ?? DEFAULT_QUERY_STATE.closeFrom,
    closeTo: searchParams.get("close_to") ?? DEFAULT_QUERY_STATE.closeTo,
    minAmount: searchParams.get("min_amount") ?? DEFAULT_QUERY_STATE.minAmount,
    maxAmount: searchParams.get("max_amount") ?? DEFAULT_QUERY_STATE.maxAmount,
    procurementType: parseProcurementType(searchParams.get("procurement_type")),
    sourceView: parseSourceView(searchParams.get("source_view")),
    lessThan100Utm: parseBoolean(searchParams.get("less_than_100_utm")),
    page: parsePositiveInteger(searchParams.get("page"), DEFAULT_QUERY_STATE.page),
    pageSize: parsePositiveInteger(
      searchParams.get("page_size"),
      DEFAULT_QUERY_STATE.pageSize,
    ),
    sortBy: parseSortField(searchParams.get("sort_by")),
    sortOrder: parseSortOrder(searchParams.get("sort_order")),
  };
}

export function toFilters(queryState: OpportunityWorkspaceQueryState): OpportunityFilters {
  return {
    officialStatus: queryState.officialStatus || undefined,
    stage: queryState.stage || undefined,
    buyerRegion: queryState.buyerRegion || undefined,
    primaryCategory: queryState.primaryCategory || undefined,
    publicationFrom: queryState.publicationFrom || undefined,
    publicationTo: queryState.publicationTo || undefined,
    closeFrom: queryState.closeFrom || undefined,
    closeTo: queryState.closeTo || undefined,
    minAmount: parseAmount(queryState.minAmount),
    maxAmount: parseAmount(queryState.maxAmount),
    procurementType: queryState.procurementType || undefined,
    sourceView: queryState.sourceView || undefined,
    lessThan100Utm: queryState.lessThan100Utm || undefined,
    page: queryState.page,
    pageSize: queryState.pageSize,
    sortBy: queryState.sortBy,
    sortOrder: queryState.sortOrder,
  };
}

export function patchWorkspaceQuery(
  pathname: string,
  current: URLSearchParams | ReadOnlyParams,
  patch: Partial<OpportunityWorkspaceQueryState>,
): string {
  const params = new URLSearchParams(current.toString());
  const merged = {
    ...parseWorkspaceQueryState(current),
    ...patch,
  };

  const setOrDelete = (key: string, value: string | null | undefined): void => {
    if (!value) {
      params.delete(key);
      return;
    }
    params.set(key, value);
  };

  setOrDelete("tab", merged.tab !== DEFAULT_QUERY_STATE.tab ? merged.tab : null);
  setOrDelete("selected", merged.selectedNoticeId);
  params.delete("q");
  setOrDelete("status", merged.officialStatus.trim() ? merged.officialStatus.trim() : null);
  setOrDelete("stage", merged.stage || null);
  setOrDelete("region", merged.buyerRegion.trim() ? merged.buyerRegion.trim() : null);
  setOrDelete("category", merged.primaryCategory.trim() ? merged.primaryCategory.trim() : null);
  setOrDelete(
    "publication_from",
    merged.publicationFrom.trim() ? merged.publicationFrom.trim() : null,
  );
  setOrDelete(
    "publication_to",
    merged.publicationTo.trim() ? merged.publicationTo.trim() : null,
  );
  setOrDelete("close_from", merged.closeFrom.trim() ? merged.closeFrom.trim() : null);
  setOrDelete("close_to", merged.closeTo.trim() ? merged.closeTo.trim() : null);
  setOrDelete("min_amount", merged.minAmount.trim() ? merged.minAmount.trim() : null);
  setOrDelete("max_amount", merged.maxAmount.trim() ? merged.maxAmount.trim() : null);
  setOrDelete("procurement_type", merged.procurementType || null);
  setOrDelete("source_view", merged.sourceView || null);
  setOrDelete("less_than_100_utm", merged.lessThan100Utm ? "true" : null);
  setOrDelete("page", merged.page === DEFAULT_QUERY_STATE.page ? null : String(merged.page));
  setOrDelete(
    "page_size",
    merged.pageSize === DEFAULT_QUERY_STATE.pageSize ? null : String(merged.pageSize),
  );
  setOrDelete(
    "sort_by",
    merged.sortBy === DEFAULT_QUERY_STATE.sortBy ? null : merged.sortBy,
  );
  setOrDelete(
    "sort_order",
    merged.sortOrder === DEFAULT_QUERY_STATE.sortOrder ? null : merged.sortOrder,
  );

  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

export const WORKSPACE_DEFAULTS = DEFAULT_QUERY_STATE;
