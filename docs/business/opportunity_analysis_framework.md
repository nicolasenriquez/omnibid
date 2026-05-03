# Opportunity Analysis Framework

## Purpose
Define a deterministic analysis frame for public opportunities without turning it into a score or recommendation engine.

## Audience
- analysts and commercial reviewers
- agents that need to structure opportunity review

## Analysis rules
- Record facts first.
- Separate deterministic signals from commercial heuristics.
- Keep prediction, ranking, and recommendation out of Silver.
- Do not treat approximate matches as certainty.

## Fact layer
Official facts are the source of truth:
- notice state
- publication date
- close date
- forum dates
- answer publication date
- technical opening date
- economic opening date
- adjudication date
- awarded supplier
- award quantity
- award amount
- item count
- estimated amount
- acquisition type
- currency
- buying unit
- category or ONU code
- number of bidders
- number of complaints
- linked purchase order
- purchase order amount and state

## Deterministic signals
| Signal | Why it matters | Source shape |
|---|---|---|
| days until close | deadline pressure | dates in API or CSV |
| forum opened / closed | remaining question window | notice dates |
| answers published | scope may have shifted | notice dates |
| technical opening reached | evaluation stage started | notice dates |
| economic opening reached | commercial comparison starts | notice dates |
| adjudication published | opportunity outcome changed | notice or award records |
| purchase order linked | downstream execution exists | OC fields and links |
| OC accepted / received | execution is active | OC states |
| number of bidders | competitiveness proxy | offers or awards |
| number of complaints | process risk proxy | API field if available |

## Commercial heuristics
These are not truth, only review aids:
- short time to close may require immediate action
- many items may increase offer complexity
- high estimated value may justify more review
- repeated buyer or category history may indicate fit
- an existing OC may signal recurring demand

## Future features for Gold / ML
- bid / no-bid ranking
- fit or priority score
- probability estimates
- forecast of award or conversion
- anomaly detection
- supplier recommendation

## Suggested human actions
- read bases and annexes
- verify supplier eligibility
- confirm deadline and forum timing
- compare against historic activity
- prepare the commercial and legal review
- decide whether to bid

## Validation checklist
- Never present a heuristic as a fact.
- Never present a score as a business truth.
- Keep this framework separate from canonical persisted tables.
