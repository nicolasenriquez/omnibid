# Procurement Lifecycle

## Purpose
Document the procurement flow that `omnibid` needs to observe when a team evaluates whether to participate in a public opportunity.

## Audience
- analysts who review opportunities
- agents that need a deterministic lifecycle map

## Lifecycle diagram
```text
opportunity/publication
-> review bases
-> question forum
-> answers publication
-> offer preparation
-> close
-> technical opening
-> economic opening
-> evaluation
-> adjudication
-> purchase order
-> acceptance / reception / execution
```

## Critical dates and observable fields

| Step | Critical dates | Helpful fields | Human check |
|---|---|---|---|
| Publication | publication date | `FechaPublicacion`, `Fechas/FechaPublicacion` | Is the opportunity actually open? |
| Bases review | base availability, annex dates | attached documents, description, `Descripcion` | Are mandatory documents present? |
| Forum | forum start and end | `Fechas/FechaInicio`, `Fechas/FechaFinal` | Can questions still be asked? |
| Answers publication | response publication date | `Fechas/FechaPubRespuestas` | Did answers change the scope? |
| Offer preparation | deadline-sensitive planning | bases, answers, attachments | Can the team comply in time? |
| Close | close date | `FechaCierre`, `Fechas/FechaCierre` | Is the tender already closed? |
| Technical opening | technical opening date | `Fechas/FechaActoAperturaTecnica` | Are technical documents complete? |
| Economic opening | economic opening date | `Fechas/FechaActoAperturaEconomica` | Are prices and conditions exposed? |
| Evaluation | evaluation date | `Fechas/FechaTiempoEvaluacion`, `CantidadReclamos` | Is there evidence of contestation or risk? |
| Adjudication | award date | `FechaAdjudicacion`, `Adjudicacion/Fecha` | Was the offer selected? |
| Purchase order | order send date | `FechaEnvio`, `CodigoLicitacion`, `CodigoEstado` | Does the OC link back to the notice? |
| Acceptance/execution | acceptance, receipt, cancellation | `FechaAceptacion`, `FechaCancelacion`, `Estado`, `EstadoProveedor` | Did the commercial execution actually start? |

## Events useful for alerts
- new publication in a target category
- answers published close to deadline
- forum closes soon
- offer deadline approaching
- adjudication published
- purchase order created or accepted
- order cancelled, suspended, or received partially

## Risks
- Attachments may contain the real business rules while the structured fields look incomplete.
- Dates can move, especially during extensions or amendments.
- Evaluation and award can be delayed beyond the first expected timetable.
- Some procedures are not classic public tenders, so the same lifecycle does not always apply.

## Missing data that still needs human review
- full bases and annexes
- clarification documents
- award resolution or contract text
- rejection reasons and forum context
- manual compliance checks for mandatory requirements

## Validation checklist
- Keep lifecycle steps separate from model tables.
- Treat attached documents as first-class evidence.
- Do not infer adjudication from publication alone.
