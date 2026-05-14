import { describe, expect, it } from "vitest";

import { filtersToQuery } from "@/src/lib/api/opportunities";
import type { OpportunityFilters } from "@/src/types/opportunities";

describe("opportunities API filter serialization", () => {
  it("includes source_view and core filters in query payload", () => {
    const filters: OpportunityFilters = {
      q: "servicio",
      officialStatus: "publicada",
      buyerRegion: "Región Metropolitana de Santiago",
      sourceView: "publicadas",
      page: 1,
      pageSize: 20,
      sortBy: "close_date",
      sortOrder: "asc",
    };

    const query = filtersToQuery(filters);

    expect(query.q).toBe("servicio");
    expect(query.official_status).toBe("publicada");
    expect(query.buyer_region).toBe("Región Metropolitana de Santiago");
    expect(query.source_view).toBe("publicadas");
  });
});
