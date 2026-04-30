## ADDED Requirements

### Requirement: Render Premium Read-Only Opportunity Workspace
The frontend SHALL render `/licitaciones` as a Spanish read-only operational SaaS workspace for public procurement opportunities.

#### Scenario: Workspace avoids raw technical labels
- **WHEN** a user views the workspace
- **THEN** visible labels are Spanish domain labels
- **AND** raw field names such as `derivedStage`, `externalNoticeCode`, or `noticeId` are not displayed as UI labels

#### Scenario: Workspace stays read-only
- **WHEN** a user interacts with the MVP workspace
- **THEN** the UI does not expose assignment, notes, discard, workflow mutation, AI analysis, recommendation, score, or persistent drag-and-drop actions

### Requirement: Provide Explorer and Radar Views
The frontend SHALL provide `Explorador` and `Radar` as the primary workspace views.

#### Scenario: User switches between primary views
- **WHEN** a user switches between `Explorador` and `Radar`
- **THEN** the workspace updates the main view without replacing the route with an unrelated page
- **AND** supported filter and selection context is preserved where practical

#### Scenario: Radar cards use notice-level grain
- **WHEN** the Radar board renders opportunity cards
- **THEN** each card represents one licitación/notice
- **AND** cards are grouped by derived stage using Spanish stage labels

### Requirement: Maintain Notice-Level Explorer Grain
The Explorer table SHALL render one parent row per licitación/notice and keep child evidence inside expansion or detail views.

#### Scenario: Parent rows are not duplicated by child evidence
- **WHEN** a licitación has multiple lines, offers, suppliers, awards, or purchase-order evidence
- **THEN** the Explorer renders one parent row for the licitación
- **AND** child evidence is shown in expansion or detail sections instead of duplicating the parent row

#### Scenario: Expanded evidence distinguishes certainty
- **WHEN** expanded evidence includes approximate or indirect purchase-order relationships
- **THEN** the UI shows relationship certainty such as Alta, Media, Baja, or Sin evidencia
- **AND** approximate relationships are not presented as confirmed facts

### Requirement: Preserve Context With Shared Detail Drawer
The frontend SHALL use a shared detail drawer for selected Explorer rows and Radar cards.

#### Scenario: Selecting an opportunity opens detail without losing context
- **WHEN** a user selects a row or card
- **THEN** a `Detalle de licitación` drawer opens
- **AND** the underlying Explorer or Radar context remains visible or recoverable

#### Scenario: Detail drawer renders evidence sections conditionally
- **WHEN** detail data is available
- **THEN** the drawer shows relevant sections for summary, key dates, buyer, products/services, amounts, offers, awards, purchase orders, relationship certainty, and metadata
- **AND** unavailable evidence is omitted or represented with a clear empty state rather than fabricated

### Requirement: Harden Workspace States and Accessibility
The frontend SHALL handle operational states and accessible interaction details consistently.

#### Scenario: Data is loading
- **WHEN** workspace data is loading
- **THEN** the UI shows stable loading placeholders or skeletons
- **AND** layout does not jump unnecessarily

#### Scenario: Data is unavailable or empty
- **WHEN** the API returns an error or no matching opportunities
- **THEN** the UI shows an actionable error or useful empty state
- **AND** the UI does not show fake opportunities or stale misleading counts

#### Scenario: User navigates interactively
- **WHEN** a user hovers, selects, tabs through, or focuses interactive controls
- **THEN** visible hover, selected, and focus states are present with sufficient contrast
