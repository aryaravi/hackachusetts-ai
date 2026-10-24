# OmniGridX: MVP Assumptions and Production Gaps

This companion is subordinate to requirements.md and design.md. If it conflicts, those documents win. Requirement references use R1-R13.

## Commercial status

- Unvalidated: no paid pilot, signed order, repeat purchase, customer-data commitment, or measured workflow improvement has been supplied.
- Buyer hypothesis: a principal or practice leader at an independent energy consultancy.
- Repeated job: authorized Massachusetts commercial-site interval data and bills into an auditable solar-and-storage screening report.
- Value hypothesis: reduce analyst and reviewer time per accepted report without material analytical errors.
- Strongest payment evidence: none. Data availability, technical feasibility, competitors, and demo interest do not establish willingness to pay.

## Release boundary

### Hackathon demo
- Loopback-only, bundled sample snapshots, no real-data upload, no public binding, no remote adapters.
- Broad features are labeled Hackathon_Demo or Future_Capability and are not commercial evidence.

### First commercial-validation release
- One Massachusetts commercial-site workflow and at most one independently verified account/tariff configuration.
- Exactly three alternatives: existing operation, documented rule-based dispatch, and optimized dispatch.
- Advisory economic, energy-balance, and deterministic outage-service screening only.
- No autonomous control, power-flow/interconnection approval, probabilistic reliability, investment-grade projections, or validated future-savings claims.

### Future capabilities
- Live data adapters, operational ML forecasts, long-range projections, utility capacity planning, bespoke data-center thermal modeling, broad policy intelligence, multiple state tariff coverage, composite rankings, and LLM explanations.

## Data and provenance (R1)
- MVP: Hackachusetts is discovery metadata; underlying publisher URLs are authoritative. Public sources are context only. Customer conclusions require authorized interval data, bills, account/rate, supply terms, assets, and limits.
- MVP: Every input has Source_Record metadata, immutable raw bytes, quality status, version/as-of date, and provenance.
- Production gaps: live adapters, licensing review, freshness monitoring, customer data agreements, real-file quality tests, and measured processing targets separate from download latency.

## Energy model and optimizer (R2-R3)
- MVP: complete interval accounting for generation, curtailment, gross import/export, battery flows, served load, and critical/noncritical unserved load.
- MVP: explicit grid/asset availability, battery limits, reserve, initial/terminal state of charge, financial/degradation/shortage objective terms, and independent schedule checking.
- Production gaps: domain review, real equipment calibration, representative performance tests, validated tolerances/diagnostics, and separate qualified power-flow/protection studies.

## Decision workflow (R4)
- MVP: absolute cost, peak demand, critical unserved energy, interruption duration, clean share, and purchased-electricity emissions for the three alternatives.
- MVP: recommend only when the buyer supplies mandatory constraints and a deterministic rule; otherwise compare without recommendation.
- Production gaps: buyer-tested decision rules, comparison with existing workflow, sensitivity analysis, and independent reviewer acceptance.

## Tariffs (R5)
- MVP: no tariff, including National Grid G-3, is verified until account applicability and controlling documents are independently reviewed.
- MVP: held-out reconciliation must pass every supported line item and total at pilot-agreed tolerances. Future results remain Screening_Estimate.
- MVP: Historically_Reconciled_Tariff_Calculation applies only to tested account, periods, tariff versions, line items, and exclusions. Billing_Grade is retired.
- Production gaps: verified rate/supply/riders/taxes/calendar/effective dates, multiple held-out periods, tariff regression fixtures, and separate verification for every added utility or municipal light plant.

## Outage, emissions, policy (R6, R8-R9)
- MVP outage: deterministic inputs and outputs; no outage plus unlimited import is not evaluated, never perfect reliability.
- MVP emissions: gross nonnegative imports times a declared inventory factor; exports and avoided emissions are separate; battery charging is attributed at import.
- MVP policy: immutable reviewed records pinned to results; applicability may be applicable, inapplicable, unknown, or not-evaluated; no LLM policy values.
- Production gaps: customer-approved critical loads, tested outage cases, reviewed emissions scope/factors, policy ownership/change tracking, and qualified applicability review.

## Forecasting and data centers (R7)
- MVP: utility forecasting and bespoke data-center thermal modeling are demo/future capabilities, not first-release claims.
- MVP: territory thresholds are aggregate comparisons, not feeder or connection feasibility; declared large loads must be de-duplicated from baseline growth.
- Production gaps: open-source gradient-boosted model with issuance-time features, time holdouts, baseline comparison and calibrated intervals; live monitoring; utility network partner; measured data-center calibration.

## State replication (R10)
- MVP: Massachusetts is the reference State_Data_Pack; core calculations have no state constants; missing capabilities fail closed and never fall back to Massachusetts.
- MVP: versioned snapshots are allowed and canonical cross-state tests enforce unit and conservation invariants.
- Production gaps: named state reviewers, official state sources, source monitoring, tariff fixtures, regulatory review, and live adapters added state by state.

## Capability and security gates (R11, R13)
- MVP: unauthenticated mode is sample-only, loopback-only, and technically unable to accept real data.
- Before real data: authorization terms, authentication/authorization, tenant isolation, encryption, secret management, audit logs, backups, retention/deletion, and incident ownership.

## Commercial validation gates (R12)
These are proposed gates, not evidence already achieved:
1. Record buyer, budget source, current workflow, annual project frequency, labor, spend, urgency, and accepted deliverable.
2. Obtain two independent paid pilots or paid orders with buyer identity, amount, scope, and payment status.
3. Obtain one repeat paid project from each pilot buyer before claiming repeat demand.
4. Measure delivery time, defects/rework, reviewer acceptance, founder labor, third-party cost, and gross margin per report.
5. Stop or narrow for no payment, data, acceptance, repeat use, or when bespoke labor exceeds supported price.

## Authority and maintenance
- Exact source URLs live in requirements.md. Calculation architecture lives in design.md.
- When evidence replaces an assumption, remove it here and record it in the applicable requirement, fixture, run manifest, or commercial record.
