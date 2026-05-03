# Intermediary Business Model

## Purpose
Describe the business that `omnibid` supports: a supplier-side team that wants to find public opportunities, understand them quickly, and decide whether to bid.

## Audience
- founders and product people
- analysts and operators
- agents that need a business framing before implementation

## Problem
Teams waste time scanning many public opportunities, reading long bases, checking dates, understanding requirements, and deciding whether a process is worth pursuing.

## Customer and user
- Customer: a supplier-side company or team that wants to sell to the State.
- Internal user: commercial ops, bid managers, analysts, and subject matter reviewers.
- External counterpart: the public buyer, which is not the app user.

## Operating flow
1. Monitor active sources.
2. Detect a relevant notice.
3. Read bases and attached documents.
4. Check deadlines, eligibility, and required evidence.
5. Compare the opportunity with supplier capabilities.
6. Decide whether to participate.
7. Prepare the offer and supporting documents.
8. Track adjudication and purchase order follow-up.
9. Verify execution and receipt.

## Value proposition
- reduce search time
- keep source lineage explicit
- surface deadlines and milestones early
- help teams prioritize review work
- package evidence for human decision making

## What the app can automate
- notice detection and refresh
- source normalization and deduplication
- deadline extraction and alerts
- comparison across history and active opportunities
- evidence packaging for review

## What the app must not automate
- reading the legal meaning of the bases
- deciding compliance on its own
- choosing whether to bid without human review
- selecting the final commercial strategy
- treating AI narrative as canonical truth

## Risks
- missing or late source updates
- schema drift in downloads
- legacy labels that no longer match current rules
- false confidence from approximate matches
- operational mistakes if a human skips review

## Human review requirement
The app should support people, not replace them.
It must keep a human in the loop for legal, commercial, and compliance decisions, especially before submitting an offer.

## AI support, not AI authority
AI can help summarize, classify, extract dates, compare records, and draft review notes.
AI must not decide alone:
- bid / no-bid
- legal sufficiency
- supplier eligibility
- final submission readiness
- compliance attestation

## Core sentence
The app helps find, understand, and prioritize opportunities.
It does not replace reading bases, administrative compliance, or the final legal/commercial decision.

## Validation checklist
- Keep the supplier-side framing explicit.
- Separate buyer-side platform facts from our internal customer.
- Avoid product claims that imply legal certainty.
