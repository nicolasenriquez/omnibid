## ADDED Requirements

### Requirement: Workspace MUST prioritize supplier-side decision context
The `/licitaciones` workspace SHALL prioritize a first-view that helps supplier-side users decide what to review now and why.

#### Scenario: User opens `/licitaciones`
- **WHEN** the workspace loads
- **THEN** the top section shows urgency/prioritization context (for example: abiertas, cierran pronto, monto relevante, en radar, sin revisar)
- **AND** metrics are API-backed or explicitly unavailable
- **AND** the UI SHALL NOT render fabricated values.

### Requirement: Default view MUST be a scan-first opportunity list
The workspace SHALL default to `Lista` and present a minimum scan contract per opportunity.

#### Scenario: User triages opportunities
- **WHEN** `Lista` is active
- **THEN** each item shows title, code, official status, procurement type, buyer, region, publication date, close date, days remaining, estimated amount, and product/category context where available
- **AND** missing values use explicit unavailable states (`Sin dato`) instead of inferred placeholders.

### Requirement: Workspace labels MUST use Spanish procurement vocabulary
The workspace SHALL render user-visible labels with Spanish business terms and proper accents, and it SHALL keep raw backend field names out of visible labels.

#### Scenario: User sees navigation and filters
- **WHEN** the workspace renders tabs, filters, actions, and metadata labels
- **THEN** it uses terms such as `Licitaciones`, `Lista`, `Tabla`, `Radar`, `Pública`, `Región`, `Publicación`, `Código`, `Compra Ágil`, and `Centro de Ingesta`
- **AND** it does not show raw field names such as `noticeId`, `externalNoticeCode`, or `derivedStage` as visible text.

### Requirement: Multi-view context MUST remain stable
The workspace SHALL support `Lista`, `Tabla`, and `Radar` without losing active review context.

#### Scenario: User switches views
- **WHEN** the user moves between `Lista`, `Tabla`, and `Radar`
- **THEN** active filters and query state remain preserved where practical
- **AND** selected opportunity context remains recoverable without route replacement.

### Requirement: Opportunity actions MUST keep MVP read-only semantics explicit
Per-opportunity actions SHALL be business-intent labeled while avoiding false persistence expectations.

#### Scenario: User interacts with opportunity actions
- **WHEN** actions are rendered
- **THEN** primary action is `Analizar oportunidad`
- **AND** secondary actions include `Agregar al radar`, `Ver fuente`, `Descartar`
- **AND** `Descartar` behavior is local-session in MVP unless persistent write APIs are explicitly implemented in a separate change.

### Requirement: Detail drawer MUST package evidence and preserve human-review guardrails
The shared detail drawer SHALL package evidence for review and state decision boundaries.

#### Scenario: User opens detail from any primary view
- **WHEN** detail opens from `Lista`, `Tabla`, or `Radar`
- **THEN** the drawer shows summary, key dates, buyer context, amount, product/line evidence, offer evidence, purchase-order evidence, and relationship certainty where available
- **AND** it includes explicit copy that legal/commercial bid decisions require human review.

### Requirement: Supplier profile compatibility signals MUST be deterministic and explainable
The system SHALL allow opportunity review against a supplier profile using non-predictive, traceable rules.

#### Scenario: Supplier profile exists
- **GIVEN** a profile with categories/regions/products/amount preferences
- **WHEN** an opportunity is rendered
- **THEN** the UI shows compatibility signals derived from explicit source fields/rules
- **AND** each signal exposes the rule provenance
- **AND** no predictive score field is persisted in Silver.

#### Scenario: Supplier profile is missing
- **GIVEN** no profile exists
- **WHEN** the user opens the workspace
- **THEN** neutral opportunity evidence is shown
- **AND** the UI invites profile setup
- **AND** no synthetic fit/risk recommendation is shown.

### Requirement: Data operations MUST be visually separated from decision flow
Technical ingestion tooling SHALL not dominate the commercial review surface.

#### Scenario: User focuses on opportunity triage
- **WHEN** the user is in `/licitaciones`
- **THEN** only concise data trust/freshness signals are shown inline
- **AND** upload consoles/log-heavy interactions are accessed via dedicated `Centro de Ingesta` navigation.

### Requirement: Compra Ágil MUST be represented as a distinct source lane when available
The workspace SHALL provide a dedicated Compra Ágil lane when agile-flagged records exist.

#### Scenario: Compra Ágil data is available
- **GIVEN** agile indicators are present in source-backed datasets
- **WHEN** the user opens the Compra Ágil lane
- **THEN** the UI applies source-specific filters and urgency cues
- **AND** it does not conflate Compra Ágil semantics with large tender list defaults.

### Requirement: Buyer intelligence snapshot MUST be deterministic and data-bounded
The system SHALL provide buyer historical context only when corroborated by available data.

#### Scenario: Sufficient buyer history exists
- **WHEN** detail or list asks for buyer intelligence
- **THEN** the UI may show deterministic aggregates (for example volume, amount bands, competition, materialization indicators)
- **AND** values reference known source-derived facts.

#### Scenario: Insufficient buyer history exists
- **WHEN** data density is not enough
- **THEN** the UI shows a clear insufficient-history state
- **AND** does not fabricate buyer intelligence summaries.

### Requirement: Benchmark inspiration MUST remain functional, not visual-copy
The redesign SHALL use external listing benchmarks for information clarity only.

#### Scenario: Implementation applies benchmark references
- **WHEN** scanability patterns are adopted
- **THEN** Omnibid preserves distinct product identity and supplier-side decision framing
- **AND** external UI style is not copied one-to-one.

### Requirement: Decision signals MUST expose coverage state explicitly
The workspace SHALL distinguish supported, partial, and unavailable data states so sparse data is never rendered as complete certainty.

#### Scenario: A field is present with good coverage
- **WHEN** a decision signal is backed by current evidence
- **THEN** the UI may render the value normally

#### Scenario: A field exists but is sparse or partially covered
- **WHEN** a signal has partial coverage or limited support
- **THEN** the UI SHALL render an explicit partial or unavailable state such as `Cobertura parcial` or `Sin dato`
- **AND** it SHALL NOT present the signal as complete truth.

#### Scenario: A field has zero usable coverage
- **WHEN** a signal is not backed by current evidence
- **THEN** the UI SHALL render `Sin dato` or equivalent unavailable copy
- **AND** it SHALL NOT elevate the signal into a primary badge, filter, or recommendation.

#### Scenario: Site visit is not yet backed by usable data
- **WHEN** the workspace evaluates `has_site_visit_flag`
- **THEN** it SHALL render `Sin dato`
- **AND** it SHALL NOT expose site visit as a core badge or filter until non-zero coverage exists in the corpus.

#### Scenario: Semantic annotations are only partially covered
- **WHEN** a triage signal depends on annotation layers with incomplete coverage
- **THEN** the UI SHALL render `Cobertura parcial`
- **AND** it SHALL keep the signal explanatory rather than definitive.

### Requirement: Adjacent product opportunities MUST remain explicitly deferred
The change SHALL keep the current decision-first upgrade separate from broader follow-on capabilities that are valuable but out of scope here.

#### Scenario: The proposal references future follow-ups
- **WHEN** the proposal, design, or tasks mention watchlists, alerts, public SEO, evidence export, trust dashboards, semantic facets, additional procurement-mode lanes, or line-level investigation handoff
- **THEN** those items are treated as future slices and not as commitments in this change
- **AND** the current implementation remains centered on `/licitaciones`, read-only decision support, and the already-specified sprint scope.
