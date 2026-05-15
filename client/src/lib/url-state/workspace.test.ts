import { describe, expect, it } from "vitest";

import {
  WORKSPACE_DEFAULTS,
  parseWorkspaceQueryState,
  patchWorkspaceQuery,
  toFilters,
} from "@/src/lib/url-state/workspace";

describe("workspace url state", () => {
  it("keeps search as app-local state and still parses source_view", () => {
    const params = new URLSearchParams(
      "q=licitacion&source_view=publicadas&region=Regi%C3%B3n%20Metropolitana%20de%20Santiago&page=2",
    );

    const state = parseWorkspaceQueryState(params);

    expect(state.q).toBe("");
    expect(state.mode).toBe("abiertas");
    expect(state.sourceView).toBe("publicadas");
    expect(state.buyerRegion).toBe("Región Metropolitana de Santiago");
    expect(state.page).toBe(2);
  });

  it("serializes source_view and excludes q from URL query", () => {
    const params = new URLSearchParams("q=foo");
    const next = patchWorkspaceQuery("/licitaciones", params, {
      sourceView: "publicadas",
      page: 1,
      buyerRegion: "Región del Biobío",
    });

    const parsed = new URL(next, "https://example.test");
    expect(parsed.searchParams.get("source_view")).toBe("publicadas");
    expect(parsed.searchParams.get("region")).toBe("Región del Biobío");
    expect(parsed.searchParams.get("q")).toBeNull();
  });

  it("emits API filters with sourceView and without local search", () => {
    const state = {
      ...WORKSPACE_DEFAULTS,
      q: "debe-quedar-local",
      sourceView: "publicadas" as const,
      buyerRegion: "Región de Valparaíso",
      officialStatus: "publicada",
    };

    const filters = toFilters(state);
    expect(filters.q).toBeUndefined();
    expect(filters.sourceView).toBe("publicadas");
    expect(filters.buyerRegion).toBe("Región de Valparaíso");
    expect(filters.officialStatus).toBe("publicada");
  });

  it("serializes and parses historical mode from URL query", () => {
    const next = patchWorkspaceQuery("/licitaciones", new URLSearchParams(), {
      mode: "historicas",
      page: 1,
    });

    const parsed = new URL(next, "https://example.test");
    expect(parsed.searchParams.get("mode")).toBe("historicas");

    const state = parseWorkspaceQueryState(parsed.searchParams);
    expect(state.mode).toBe("historicas");
  });

  it("defaults both modes to descending order", () => {
    const state = parseWorkspaceQueryState(new URLSearchParams());
    expect(WORKSPACE_DEFAULTS.sortOrder).toBe("desc");
    expect(state.sortOrder).toBe("desc");
  });

  it("preserves sourceView explicitly and does not infer it from mode", () => {
    const abiertasFilters = toFilters({
      ...WORKSPACE_DEFAULTS,
      mode: "abiertas",
      sourceView: "",
    });
    expect(abiertasFilters.sourceView).toBeUndefined();

    const abiertasExplicitFilters = toFilters({
      ...WORKSPACE_DEFAULTS,
      mode: "abiertas",
      sourceView: "publicadas",
    });
    expect(abiertasExplicitFilters.sourceView).toBe("publicadas");

    const historicasFilters = toFilters({
      ...WORKSPACE_DEFAULTS,
      mode: "historicas",
      sourceView: "publicadas",
    });
    expect(historicasFilters.sourceView).toBe("publicadas");
  });
});
