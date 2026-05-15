## ADDED Requirements

### Requirement: The UI System MUST provide reusable decision-surface components
The UI System SHALL provide reusable components for KPI cards, status badges, filter chips, tabs, side panels, tables, empty states, timeline rows, and progress rows.

#### Scenario: A product surface renders shared primitives
- **WHEN** the Opportunity Workspace or Ingestion Center needs a scan-density component
- **THEN** it can reuse the shared UI system instead of building a one-off component
- **AND** the component follows the same visual and accessibility contract.

### Requirement: The UI System MUST encode explicit availability states
The UI System SHALL render `Sin dato`, `Cobertura parcial`, and source-backed certainty states consistently across the app.

#### Scenario: A value is missing or partial
- **WHEN** a component receives a missing or partial value
- **THEN** it renders the explicit availability state
- **AND** it does not substitute a vague placeholder that looks factual.

### Requirement: The UI System MUST support Spanish procurement labels
The UI System SHALL preserve Spanish procurement vocabulary and proper accents in visible labels, helper text, and empty states.

#### Scenario: A shared component receives a label
- **WHEN** the component renders text for a procurement surface
- **THEN** it uses Spanish business language
- **AND** it does not surface raw schema field names as labels.

### Requirement: The UI System MUST support compact and evidence-dense layouts
The UI System SHALL support scan-first layouts and evidence-dense detail layouts without forcing a separate component family for each surface.

#### Scenario: A table and a drawer render side by side
- **WHEN** the workspace uses the same shared primitives in `Lista` and the detail pane
- **THEN** the spacing, typography, and badge states remain consistent
- **AND** the surface can stay readable at high data density.

### Requirement: The UI System MUST preserve read-only affordances
The UI System SHALL not make unavailable or local-only actions look like persisted workflow actions.

#### Scenario: A button represents local follow-up or a read-only action
- **WHEN** the component renders `Agregar al radar`, `Ver fuente`, or an unavailable action
- **THEN** the label and state communicate the real behavior
- **AND** the UI does not imply write access that does not exist.

### Requirement: The UI System MUST keep accessibility and keyboard flow intact
The UI System SHALL preserve keyboard navigation, visible focus, and accessible status messaging across cards, tabs, drawers, and tables.

#### Scenario: A user navigates by keyboard
- **WHEN** focus moves through the shared components
- **THEN** the active state remains visible
- **AND** the component tree keeps the interaction flow predictable.

