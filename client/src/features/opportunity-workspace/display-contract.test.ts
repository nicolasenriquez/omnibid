import { describe, expect, it } from "vitest";

import {
  AVAILABILITY_CAUSE_LABELS,
  getOpportunityFieldScope,
  WORKSPACE_MODE_LABELS,
} from "@/src/features/opportunity-workspace/display-contract";

describe("opportunity display contract", () => {
  it("classifies notice-level and cycle-level fields", () => {
    expect(getOpportunityFieldScope("buyerRegion")).toBe("notice");
    expect(getOpportunityFieldScope("complaintCount")).toBe("notice");
    expect(getOpportunityFieldScope("offers")).toBe("cycle");
    expect(getOpportunityFieldScope("purchaseOrders")).toBe("cycle");
  });

  it("uses explicit availability labels by cause", () => {
    expect(AVAILABILITY_CAUSE_LABELS.not_yet_public).toBe("Aún no aplica");
    expect(AVAILABILITY_CAUSE_LABELS.pending_detail).toBe("Pendiente de detalle");
    expect(AVAILABILITY_CAUSE_LABELS.pipeline_missing).toBe("Histórico no cargado");
  });

  it("exposes workspace mode labels", () => {
    expect(WORKSPACE_MODE_LABELS.abiertas).toBe("Abiertas");
    expect(WORKSPACE_MODE_LABELS.historicas).toBe("Históricas");
  });
});
