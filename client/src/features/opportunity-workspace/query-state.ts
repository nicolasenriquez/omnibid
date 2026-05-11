import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  WORKSPACE_DEFAULTS,
  parseWorkspaceQueryState,
  patchWorkspaceQuery,
  toFilters,
} from "@/src/lib/url-state/workspace";
import type { OpportunityWorkspaceQueryState } from "@/src/types/opportunities";

function hasActiveWorkspaceFilters(state: OpportunityWorkspaceQueryState): boolean {
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

function buildExplorerScopeKey(state: OpportunityWorkspaceQueryState): string {
  return [
    state.tab,
    state.q.trim(),
    state.officialStatus,
    state.stage,
    state.buyerRegion,
    state.primaryCategory,
    state.publicationFrom,
    state.publicationTo,
    state.closeFrom,
    state.closeTo,
    state.minAmount,
    state.maxAmount,
    state.procurementType,
    state.lessThan100Utm ? "1" : "0",
    String(state.pageSize),
    state.sortBy,
    state.sortOrder,
  ].join("|");
}

export function useOpportunityWorkspaceQueryState(): {
  queryState: OpportunityWorkspaceQueryState;
  filters: ReturnType<typeof toFilters>;
  activeFilters: boolean;
  explorerScopeKey: string;
  replaceQuery: (patch: Partial<OpportunityWorkspaceQueryState>) => void;
} {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const queryState = useMemo(
    () => parseWorkspaceQueryState(searchParams),
    [searchParams],
  );
  const filters = useMemo(() => toFilters(queryState), [queryState]);
  const activeFilters = useMemo(
    () => hasActiveWorkspaceFilters(queryState),
    [queryState],
  );
  const explorerScopeKey = useMemo(
    () => buildExplorerScopeKey(queryState),
    [queryState],
  );
  const replaceQuery = useCallback(
    (patch: Partial<OpportunityWorkspaceQueryState>) => {
      router.replace(patchWorkspaceQuery(pathname, searchParams, patch), { scroll: false });
    },
    [pathname, router, searchParams],
  );

  return {
    queryState,
    filters,
    activeFilters,
    explorerScopeKey,
    replaceQuery,
  };
}
