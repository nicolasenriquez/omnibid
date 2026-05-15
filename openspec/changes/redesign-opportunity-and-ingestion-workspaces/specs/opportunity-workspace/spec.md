## ADDED Requirements

### Requirement: The Opportunity Workspace MUST stay read-only and Spanish-first
The workspace SHALL render procurement labels in Spanish with proper accents, and it SHALL not imply write access, automation authority, or hidden persistence.

#### Scenario: User opens any workspace view
- **WHEN** the workspace renders tabs, badges, buttons, or labels
- **THEN** it uses Spanish procurement vocabulary
- **AND** it does not show raw backend field names as visible labels
- **AND** any action that is not persisted must be clearly framed as local-session behavior.

### Requirement: The Opportunity Workspace MUST preserve review context across views
The workspace SHALL support `Lista`, `Tabla`, `Priorización`, and `Seguimiento` as view modes over the same review context.

#### Scenario: User switches views
- **WHEN** the user moves from `Lista` to `Tabla`, `Priorización`, or `Seguimiento`
- **THEN** active filters and search state remain recoverable
- **AND** the selected opportunity remains recoverable without losing the current review context.

### Requirement: The Opportunity Workspace MUST default to scan-first review
The workspace SHALL default to `Lista` and present the fields needed to scan opportunities quickly.

#### Scenario: User lands on `/licitaciones`
- **WHEN** the workspace loads
- **THEN** the first view is `Lista`
- **AND** the list shows the source-backed opportunity fields that exist in the current read contract
- **AND** missing values render as explicit unavailable states instead of implied facts.

### Requirement: The Opportunity Workspace MUST expose explicit availability states
The workspace SHALL distinguish supported, partial, and unavailable data so incomplete evidence is never rendered as complete certainty.

#### Scenario: A field is not backed by the current contracts
- **WHEN** the UI needs to render a field such as documents, bases, anexos, or any missing decision signal
- **THEN** the UI shows `Sin dato`, `Cobertura parcial`, or another explicit unavailable state
- **AND** it does not display a factual-looking placeholder.

### Requirement: The Opportunity Workspace MUST use deterministic prioritization
The workspace SHALL support prioritization buckets derived from explicit rules over source-backed facts, and it SHALL not present a predictive score as business truth.

#### Scenario: User opens Priorización
- **WHEN** the board renders
- **THEN** opportunities are grouped into explainable buckets derived from dates, amount, status, and watchlist state
- **AND** no predictive score is shown as a Silver fact
- **AND** any missing input is exposed as a partial or unavailable state.

### Requirement: The Opportunity Workspace MUST keep follow-up local until a persisted slice exists
The workspace SHALL keep watchlist/follow-up behavior local-session only unless a separate persistence change is introduced.

#### Scenario: User adds an opportunity to Seguimiento
- **WHEN** the user marks an opportunity for follow-up
- **THEN** the state is preserved in the current local workspace context
- **AND** the UI makes it clear that the behavior is local until a persistence contract exists.

### Requirement: The Opportunity Workspace detail view MUST remain evidence-first
The detail experience SHALL package opportunity facts, evidence counts, timeline, and source-linked evidence without inventing docs or summaries.

#### Scenario: User opens an opportunity detail drawer
- **WHEN** the detail view renders
- **THEN** it shows official data, timeline, line evidence, offer evidence, and purchase-order evidence where available
- **AND** if documents, bases, or anexos are not source-backed, the UI shows an explicit unavailable state
- **AND** it does not fabricate a decision brief as if it were a source fact.

### Requirement: The Opportunity Workspace MUST remain compatible with current routes
The workspace SHALL preserve compatibility with the current `/licitaciones` and `/opportunities` navigation and read contract shape.

#### Scenario: Existing deep links are used
- **WHEN** a user navigates through the existing entry points
- **THEN** the opportunity workspace remains reachable
- **AND** the current read-only opportunity contracts still function for list and detail navigation.

