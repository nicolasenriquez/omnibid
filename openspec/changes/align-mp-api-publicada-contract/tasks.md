## 0. Investigation and baseline

- [x] 0.1 Inspect the current API parser, Silver refresh, canonicalization bridge, and opportunities contract to confirm the exact fields and outputs that are already present.
  Notes: Use the current source shape in `backend/pipeline/extract/mp_api_schemas.py`, `backend/pipeline/transform/mp_api_notice_refresh.py`, `backend/pipeline/transform/mp_api_read_model_bridge.py`, and `backend/api/routers/opportunities.py` as the baseline.
  Notes: Baseline drift confirmed: parser aliases still use `FundingSource` and `VisibilityAmount` (not official `FuenteFinanciamiento` / `VisibilidadMonto`), Silver snapshot refresh still hardcodes many available fields to `None`/`False`, and `/opportunities` still lacks `source_view` routing.
- [x] 0.2 Add or update baseline tests that fail before the contract fix.
  Notes: Lock the current behavior around official `Publicada` parsing, lifecycle-aware availability, and `/opportunities` exposure before changing implementation.
  Notes: Added expected-red baseline tests in `tests/unit/test_mercado_publico_schemas.py`, `tests/unit/test_mp_api_notice_refresh.py`, and `tests/unit/test_opportunities_query.py`.
- [x] 0.3 Confirm the field coverage boundary between licitación surface, raw-only preservation, and CSV-only historical data.
  Notes: Close the scope on what is must-propagate for current opportunities, what remains raw-only for drift detection, and what stays in the CSV monthly path.
  Notes: Boundary confirmed from current models/transforms: licitación surface fields belong in parser/snapshot/normalized-silver-opportunities path; unknown/new payload fields remain preserved in `api_source_payload.payload_json`; post-award historical entities remain CSV-path (`normalized_ordenes_compra*` and downstream purchase-order Silver entities), not invented from `Publicada` API notices.

## 1. Official Mercado Público field contract

- [x] 1.1 Update `backend/pipeline/extract/mp_api_schemas.py` so the parsed contract uses the official Mercado Público keys and states.
  Notes: Keep the public contract in the same terminology Mercado Público uses in the API and docs, including `CodigoEstado`, `Estado`, `CodigoTipo`, `Tipo`, `TipoConvocatoria`, `Informada`, `VisibilidadMonto`, and `FuenteFinanciamiento`.
  Notes: Parser aliases updated to official keys: `FuenteFinanciamiento`, `VisibilidadMonto`, and explicit `Informada` field in `LicitacionNotice`.
- [x] 1.2 Retire legacy public-contract wording from tests and docs where it describes official fields using non-official terminology.
  Notes: The public contract should speak only in Mercado Público terms.
  Notes: Legacy wording retired in parser fixture/docs surface (`tests/fixtures/detail_by_codigo_payload.json`, `docs/architecture/mp_api_pipeline_hardening_audit.md`).
- [x] 1.3 Add or update parsing tests so the official fields are preserved from the payload and exposed through the parsed model.
  Notes: Keep regression coverage for the discovery/detail payloads already used by the pipeline.
  Notes: Added/updated parsing assertions for official fields and fixture-driven coverage in `tests/unit/test_mercado_publico_schemas.py`.

## 2. Silver refresh source-awareness

- [x] 2.1 Update `backend/pipeline/transform/mp_api_notice_refresh.py` to populate `notice_description_raw` from the snapshot when available.
  Notes: The Silver builder should stop hardcoding values that already exist in the snapshot-enriched contract.
  Notes: `notice_description_raw` and normalized `notice_description_clean` now flow from snapshot `description`.
- [x] 2.2 Populate the other available public fields from the snapshot instead of forcing `None` or `False`.
  Notes: Cover the fields the API already publishes, especially description, dates, counts, and tender-type metadata.
  Notes: Snapshot refresh now propagates `created_date`, `award_date`, `estimated_award_date`, `claim_count`, `tipo`, `codigo_tipo`, and visibility semantics (`hidden_budget_flag`) instead of forced defaults.
- [x] 2.3 Derive official state metadata in Silver: `mp_estado_codigo`, `mp_estado_nombre`, `mp_estado_canonical`.
  Notes: Map the official lifecycle values `Publicada`, `Cerrada`, `Desierta`, `Adjudicada`, `Revocada`, and `Suspendida`.
  Notes: Added canonical state derivation in refresh (`5/6/7/8/18/19`) with fallback normalization by official state name.
- [x] 2.4 Derive `data_source_kind` and `availability_context` from the source mode and official state.
  Notes: `Publicada` should resolve to a current opportunity context, not a historical full-cycle context.
  Notes: Added source-aware derivation: `api_publicada`/`api_detail`/`api_historical` + `current_publicada_discovery`/`current_publicada_detail`/`historical_full_cycle`.
- [x] 2.5 Add tests for source-aware Silver refresh and official state derivation.
  Notes: Added refresh tests for propagation + official-state/source-context derivation in `tests/unit/test_mp_api_notice_refresh.py`.

## 3. Canonicalization bridge

- [x] 3.1 Update `backend/pipeline/transform/mp_api_read_model_bridge.py` so normalized and Silver payloads carry the official Mercado Público fields through the read path.
  Notes: Use the raw API payload and the snapshot together, but do not let the snapshot become the only source for the public contract.
  Notes: Bridge now merges payload rows with latest snapshot values only when payload value is missing/blank, preserving payload-first contract while carrying official fields through to normalized/silver builders.
- [x] 3.2 Ensure API-only `Publicada` notices can still produce enough normalized and Silver rows for `/opportunities`.
  Notes: Canonicalization now injects `SourceMode` + official fields into Silver notice payload path and keeps API-only `Publicada` rows producing `silver_notice` and `normalized_licitaciones` entries even when discovery payload is sparse.
- [x] 3.3 Add tests for official state propagation and item/category propagation from API payloads.
  Notes: Added bridge tests for snapshot-enriched official state propagation and nested `Items/Listado` flattening into normalized item + silver line/category rows (`tests/unit/test_mp_api_read_model_bridge.py`).

## 4. Opportunities API contract

- [x] 4.1 Update `backend/api/routers/opportunities.py` to expose official state metadata in list, detail, and summary responses.
  Notes: Include the official state code/name/canonical form and the source/availability context.
  Notes: List/detail now expose `mpEstado*`, `dataSourceKind`, and `availabilityContext`; summary includes Publicada/source-context metrics.
- [x] 4.2 Add `source_view=publicadas` as a discovery filter.
  Notes: Keep backward compatibility with the current `derivedStage` behavior and historical CSV filters.
  Notes: Added shared SQL predicate: `mp_estado_canonical='publicada'` OR `data_source_kind in ('api_publicada','api_detail')`.
- [x] 4.3 Ensure the API can surface `CodigoTipo`, `Tipo`, `TipoConvocatoria`, `Informada`, `VisibilidadMonto`, and `FuenteFinanciamiento` where available.
  Notes: List/detail now coalesce these fields from Silver, normalized, snapshot, and payload (`Informada`).
- [x] 4.4 Ensure buyer region and commune can come from the API `Comprador` section.
  Notes: List/detail now coalesce buyer region/commune from normalized and latest snapshot buyer-unit fields.
- [x] 4.5 Add tests for `source_view=publicadas` and for official field exposure in `/opportunities`.
  Notes: Updated unit coverage in opportunities query/router/contract model tests.

## 5. Lifecycle-aware availability semantics

- [x] 5.1 Add derived availability logic for `Publicada` licitaciones.
  Notes: Participants, offers, adjudication, and purchase orders should be marked as lifecycle-pending when the official state is `Publicada`.
  Notes: `/opportunities/{notice_id}` now derives `participantsAvailability`, `offersAvailability`, `awardAvailability`, `purchaseOrderAvailability`, and `descriptionAvailability` from official state/source context.
- [x] 5.2 Keep `not_reported_by_source` and `pipeline_missing` distinct from `not_yet_public`.
  Notes: Added explicit derivation rules for API-source gaps (`not_reported_by_source`) vs non-API missing data (`pipeline_missing`) and kept `Publicada` lifecycle gaps as `not_yet_public`.
- [x] 5.3 Add tests proving that `Publicada` does not render lifecycle-pending data as a pipeline failure.
  Notes: Added unit coverage for Publicada no-postclose-data and Informada no-offers scenarios in opportunities API tests.

## 6. Documentation and changelog

- [x] 6.1 Add or update the Mercado Público contract docs under `docs/contracts/mercado-publico/`.
  Notes: Document the official state set, the discovery semantics, the field contract, and the availability semantics in the same terminology Mercado Público uses.
  Notes: Added `docs/contracts/mercado-publico/publicadas-opportunities-contract.md` with official state mapping, `source_view=publicadas`, field contract, and availability rules.
- [x] 6.2 Update `CHANGELOG.md` if the behavior change will be shipped as part of a user-visible release.
  Notes: This is a contract and behavior change, so it should be recorded when the release process requires changelog coverage.
  Notes: Added `[Unreleased]` changelog entry for Publicada opportunities contract alignment and lifecycle-aware availability semantics.

## 7. Client labels and discovery surface

- [x] 7.1 Add a `Publicadas / Activas` filter or tab in `client/`.
  Notes: Keep the user-facing terminology aligned with Mercado Público.
  Notes: Added a filter-area `Vista` control with `Publicadas / Activas` mapped to `source_view=publicadas` through URL/query/api filter plumbing.
- [x] 7.2 Replace generic `No disponible` labels with lifecycle-aware labels.
  Notes: Use `Pendiente de publicación`, `No aplica`, `No informado por fuente`, and `No cargado` where appropriate.
  Notes: Detail-pane empty offers/purchase-orders/timeline states now use lifecycle availability labels derived from backend availability fields.
- [x] 7.3 Add a test or local verification for the discovery filter behavior if the client already has UI tests in scope.
  Notes: No client UI test suite is currently scoped for this workspace filter flow; completed local verification with `npm run typecheck` and `npm run lint` in `client/` after wiring `source_view` query serialization.
- [x] 7.4 Add filtering UI state split for search: `querySearch` (draft, app-local) vs applied API filters.
  Notes: Keep `querySearch` out of URL params; only applied filters should drive API requests.
  Notes: Implemented app-local draft/applied search state in the workspace; URL/query-state no longer persists `q`.
- [x] 7.5 Update filter interaction model so search no longer triggers backend list/summary fetch on every keypress.
  Notes: Commit search only on explicit apply action and/or controlled debounce/Enter behavior.
  Notes: Search input now updates local draft state on keypress and only commits to API filters on Enter or `Aplicar`.
- [x] 7.6 Keep filtering polish confined to the filter panel only.
  Notes: Do not change explorer/radar tables, cards, or detail drawer behavior beyond receiving updated filter payload.
  Notes: Filtering behavior changes are confined to filter/query plumbing and filter-panel controls.
- [x] 7.7 Add `Publicadas / Activas` as a first-class discovery control in the filter area and map it to `source_view=publicadas`.
  Notes: Preserve backward-compatible `derivedStage` behavior and keep the control naming aligned with Mercado Público terminology.
  Notes: Added `Vista` control in primary filter row and wired `source_view=publicadas` through URL-state and API query serialization.
- [x] 7.8 Add/upgrade region filtering in the filter area using user-facing region labels backed by API-ready query values.
  Notes: Prioritize high-frequency regions and keep the interaction efficient for large region/commune cardinality.
  Notes: Added curated high-frequency region options and `Región` filter select in the main filter row, wired to `buyer_region` query serialization.
- [x] 7.9 Align official state filter options with Mercado Público official lifecycle states.
  Notes: Include `Publicada`, `Cerrada`, `Desierta`, `Adjudicada`, `Revocada`, and `Suspendida` in the filtering surface where applicable.
  Notes: Centralized lifecycle status filter options in shared view-model constants and rendered them from the filter select to avoid contract drift.
- [x] 7.10 Add focused frontend tests for filtering-only behavior.
  Notes: Cover draft vs applied search state, no per-keystroke network trigger, `source_view=publicadas` emission, and region/state filter serialization.
  Notes: Added Vitest test suite and focused tests for URL/query serialization, API query mapping, source-view chip/status labels; executed `npm run test`, `npm run typecheck`, and `npm run lint` in `client/`.

## 8. Final validation

- [x] 8.1 Run the relevant unit tests for parsing, refresh, and opportunity contract changes.
  Notes: Ran `rtk uv run pytest -q tests/unit/test_mercado_publico_schemas.py tests/unit/test_mp_api_notice_refresh.py tests/unit/test_mp_api_read_model_bridge.py tests/unit/test_opportunities_query.py tests/unit/test_opportunities_contract_models.py tests/unit/test_opportunity_workspace_api.py` -> `42 passed`.
- [x] 8.2 Run the relevant quality gates for the touched backend and client slices.
  Notes: Backend gates passed: `ruff check` on touched backend/tests and `mypy` on touched backend modules. Client gates passed: `npm run test`, `npm run typecheck`, `npm run lint`.
- [x] 8.3 Verify the change does not alter historical CSV behavior.
  Notes: Historical CSV-path guard tests passed via `rtk uv run pytest -q tests/unit/test_normalized_transform.py tests/unit/test_normalized_loader_helpers.py` -> `43 passed`; opportunities normalized fallback assertions remain covered in opportunities API tests.
