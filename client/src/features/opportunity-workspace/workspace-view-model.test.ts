import { describe, expect, it } from "vitest";

import {
  getActiveFilterChips,
  OFFICIAL_STATUS_FILTER_OPTIONS,
  REGION_FILTER_OPTIONS,
} from "@/src/features/opportunity-workspace/workspace-view-model";
import { WORKSPACE_DEFAULTS } from "@/src/lib/url-state/workspace";

describe("workspace filter view model", () => {
  it("exposes official Mercado Público lifecycle states", () => {
    expect(OFFICIAL_STATUS_FILTER_OPTIONS.map((option) => option.value)).toEqual([
      "publicada",
      "cerrada",
      "desierta",
      "adjudicada",
      "revocada",
      "suspendida",
    ]);
  });

  it("includes top region options for efficient selection", () => {
    expect(REGION_FILTER_OPTIONS.length).toBeGreaterThanOrEqual(10);
    expect(REGION_FILTER_OPTIONS[0]).toBe("Región Metropolitana de Santiago");
  });

  it("renders source view and official status chips with aligned labels", () => {
    const chips = getActiveFilterChips({
      ...WORKSPACE_DEFAULTS,
      sourceView: "publicadas",
      officialStatus: "publicada",
    });
    const labels = chips.map((chip) => chip.label);

    expect(labels).toContain("Vista: Publicadas / Activas");
    expect(labels).toContain("Estado oficial: Publicada");
  });
});
