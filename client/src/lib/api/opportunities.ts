import type {
  OpportunityDetail,
  OpportunityFilters,
  OpportunityListResponse,
  OpportunitySummaryResponse,
} from "@/src/types/opportunities";

import { requestJson } from "@/src/lib/api/http";

function filtersToQuery(filters: OpportunityFilters): Record<string, string | number | boolean> {
  return {
    q: filters.q ?? "",
    official_status: filters.officialStatus ?? "",
    stage: filters.stage ?? "",
    buyer_region: filters.buyerRegion ?? "",
    primary_category: filters.primaryCategory ?? "",
    publication_from: filters.publicationFrom ?? "",
    publication_to: filters.publicationTo ?? "",
    close_from: filters.closeFrom ?? "",
    close_to: filters.closeTo ?? "",
    min_amount: filters.minAmount ?? "",
    max_amount: filters.maxAmount ?? "",
    procurement_type: filters.procurementType ?? "",
    less_than_100_utm: filters.lessThan100Utm ?? "",
    page: filters.page,
    page_size: filters.pageSize,
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
  };
}

export async function fetchOpportunities(
  filters: OpportunityFilters,
  signal?: AbortSignal,
): Promise<OpportunityListResponse> {
  return requestJson<OpportunityListResponse>("/opportunities", {
    query: filtersToQuery(filters),
    signal,
  });
}

export async function fetchOpportunitySummary(
  filters: OpportunityFilters,
  signal?: AbortSignal,
): Promise<OpportunitySummaryResponse> {
  return requestJson<OpportunitySummaryResponse>("/opportunities/summary", {
    query: filtersToQuery(filters),
    signal,
  });
}

export async function fetchOpportunityDetail(
  noticeId: string,
  signal?: AbortSignal,
): Promise<OpportunityDetail> {
  return requestJson<OpportunityDetail>(`/opportunities/${encodeURIComponent(noticeId)}`, {
    signal,
  });
}
