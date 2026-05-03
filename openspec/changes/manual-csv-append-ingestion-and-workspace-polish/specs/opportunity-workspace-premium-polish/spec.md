## ADDED Requirements

### Requirement: Workspace header MUST present premium operational hierarchy
The `/licitaciones` workspace SHALL present a refined operational header with clear title, read-only/API state, primary actions, and snapshot KPIs.

#### Scenario: User views the workspace header
- **WHEN** the workspace loads
- **THEN** the header shows the workspace purpose, current view context, API/filter/date states, and snapshot KPIs
- **AND** the visual hierarchy is compact, readable, and aligned with a premium SaaS operations product

#### Scenario: Manual upload action is available
- **WHEN** the operator views the workspace header
- **THEN** a green primary `Cargar CSV` action is available
- **AND** the action opens the manual upload flow rather than mutating Explorer or Radar rows directly

### Requirement: KPI visualization MUST preserve relevant metrics and improve scan quality
The workspace SHALL keep relevant KPI metrics while improving their grouping, labels, and status affordances.

#### Scenario: Summary metrics are available
- **WHEN** API-backed summary metrics are available
- **THEN** the UI renders total opportunities, active filters, open, closing soon, awarded, total amount, and other supported pulse metrics with clear labels
- **AND** no KPI is fabricated from stale or unrelated data

#### Scenario: Metrics are loading or unavailable
- **WHEN** metrics are loading or unavailable
- **THEN** the UI shows stable loading or unavailable states
- **AND** layout does not collapse or mislead the user with fake values

### Requirement: Expanded evidence panel MUST use document-like visual hierarchy
The Explorer expanded evidence section SHALL present key licitación evidence with clearer hierarchy while preserving all relevant fields.

#### Scenario: User expands a licitación row
- **WHEN** a user expands a row in Explorer
- **THEN** the panel shows category/title context, publication/close dates, amount, buyer, lines/items, offers, purchase-order evidence, and certainty where available
- **AND** the layout makes primary facts easier to scan than secondary metadata

#### Scenario: Evidence relationship is uncertain
- **WHEN** purchase-order or line evidence is approximate
- **THEN** the panel shows relationship certainty
- **AND** approximate evidence is not styled or worded as confirmed truth

### Requirement: Upload UI MUST be accessible and resilient
The manual upload UI SHALL support keyboard, screen reader, and error recovery needs.

#### Scenario: User opens upload flow
- **WHEN** the upload modal or sheet opens
- **THEN** focus moves into the flow
- **AND** the dataset selector, drop zone, file picker, confirm button, and cancel button have accessible labels

#### Scenario: Preflight or processing fails
- **WHEN** upload preflight or processing fails
- **THEN** the UI shows a clear error near the relevant step
- **AND** the user can retry, replace the file, or cancel without refreshing the page
