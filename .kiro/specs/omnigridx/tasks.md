# Implementation Plan: OmniGridX Fast Judge MVP

## Overview

Finish the shortest credible Python judge path using only bundled non-customer samples. Reuse the completed domain, provenance, ingestion, Massachusetts metadata, demo-local gate, and Simulation_Engine work. Add independent checking; existing, rule-based, and optimized schedules; a disclosed sample-only Screening_Estimate cost calculation; deterministic outage, emissions, and clean-energy metrics; one comparison/report page; minimal JSON/HTML delivery; deterministic local end-to-end coverage; and a fail-closed Render `demo-public` deployment with local fallback.

Every required implementation leaf includes focused tests. Broad properties and all historical-tariff, policy, multi-state, customer/private/production, tenant, commercial-validation, live-adapter, and forecasting work are optional and appear only after required waves. The judge MVP contains no ML, weather, or demand forecasting and must not be described as AI forecasting; constrained optimization may be described as grid intelligence.

## Tasks

- [x] 1. Establish the Python project and dependency boundary
  - [x] 1.1 Create the modular-monolith package skeleton and pinned dependency files
    - Create one Python application with domain, application, infrastructure, and web modules; add test directories without introducing microservices or a message broker.
    - Pin the Python version and exact runtime/test dependency versions, including SciPy for MILP, Hypothesis for properties, the selected thin HTTP/template stack, and the test runner; keep forecasting dependencies out of the MVP environment.
    - Add deterministic test, type-check, and package commands suitable for local single-run execution.
    - _Requirements: 2.10, 7.11, 11.1, 11.2, 13.1, 14.2, 14.4_
  - [x] 1.2 Implement supported Kiro task hooks and minimal steering guidance
    - Inspect the Kiro hook format installed in the development environment, then add tracked pre-task and post-task hooks using that supported format rather than assuming a schema.
    - Make pre-task validation check `tasks.md` format, one exact incomplete leaf-task identity, prior-wave dependency completion, and the required spec files; make post-task validation run the task-targeted test plus established strict type and package checks and block completion on any failure.
    - Keep validation deterministic, non-interactive, local-only, bounded, and free of secrets or network calls; add concise steering guidance and a small self-check covering ready, unknown, malformed/ambiguous, dependency-blocked, and post-check-failure cases.
    - _Requirements: 14.3, 14.7, 14.11_

- [x] 2. Define domain values, records, and reproducible manifests
  - [x] 2.1 Implement domain quantities, units, identifiers, intervals, and validation errors
    - Represent energy, power, duration, money, emissions, timestamps, and finite numeric inputs with explicit units and boundary validation.
    - Preserve UTC instants plus America/New_York local time, offset, time-zone name, and fold so repeated daylight-saving wall times remain distinct.
    - Define stable diagnostic and capability-status values without coupling domain code to HTTP or persistence.
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.2, 3.4, 8.3_
  - [x] 2.2 Implement immutable source, dataset, scenario, schedule, result, and Run_Manifest models
    - Define append-only record shapes from the design, including exactly three alternative types and complete interval-result fields.
    - Serialize canonical manifests with ordered interval IDs, decimal strings, explicit units, hashes, versions, solver settings, tolerances, deployment mode, and capability mode; derive the SHA-256 run fingerprint.
    - Keep repository, snapshot, solver, tariff, source-adapter, and state-pack ports narrow and in-process.
    - _Requirements: 1.3, 2.1, 2.2, 4.1, 4.2, 9.2, 9.3, 10.6_
  - [x] 2.3 Write the property test for deterministic run reproducibility
    - **Property 9: Deterministic run reproducibility**
    - Generate immutable manifests and assert stable normalized inputs, alternative set, labels, fingerprint, exact non-solver outputs, and tolerance-bounded optimized outputs.
    - **Validates: Requirements 1.3, 4.1, 4.2, 9.2, 9.3, 10.6**

- [x] 3. Store immutable snapshots, provenance, and the Massachusetts reference pack
  - [x] 3.1 Implement content-addressed snapshots and append-only provenance persistence
    - Store bytes by computed SHA-256 using temporary-write then atomic-rename semantics, verify bytes on read, and reject content/hash mismatch.
    - Persist complete Source_Record metadata, DatasetVersion records, normalized-record provenance edges, and prior versions without mutation.
    - Use SQLite on local disk and a local immutable object directory behind the designed repository ports.
    - _Requirements: 1.3, 1.6, 1.7, 1.12, 1.13, 10.6_
  - [x] 3.2 Create the versioned Massachusetts_Data_Pack from approved snapshot metadata
    - Supply the reference schema, America/New_York time zone, billing calendar, approved source declarations, geography mappings, emissions factor references, and explicit supported/unsupported capabilities.
    - Treat the Hackachusetts catalog only as discovery metadata and retain canonical publisher URLs; do not encode Massachusetts constants in calculation modules.
    - Use versioned local snapshots and mark live adapters as a production milestone.
    - _Requirements: 1.13, 10.1, 10.2, 10.3, 10.9_
  - [x] 3.3 Write the property test for complete authoritative source provenance
    - **Property 10: Source provenance is complete and authoritative**
    - Generate accepted records and assert each traces to unchanged bytes and complete source metadata, with publisher authority distinct from discovery URLs.
    - **Validates: Requirements 1.3, 1.7, 1.13**
  - [x] 3.4 Write snapshot and Massachusetts pack smoke tests
    - Verify append-only behavior, hash checks, local-disk SQLite configuration, bundled snapshot hashes, required source metadata, and pack version identity.
    - _Requirements: 1.3, 1.7, 10.1, 10.2, 10.9_

- [x] 4. Implement ingestion quality controls and the sample-only demo gate
  - [x] 4.1 Implement local-snapshot parsing, normalization, validation, and freshness decisions
    - Validate required fields, finite values, declared units, timestamps, cadence, duplicates, geography, coverage, plausible ranges, and source metadata.
    - Partition record-scope failures while rejecting dataset-scope failures or zero-valid-record datasets; preserve prior dataset versions and report all diagnostics.
    - Record count and processing duration separately from download duration, and block or qualify stale data according to declared use.
    - _Requirements: 1.1–1.12_
  - [x] 4.2 Implement the deployment and data-admission gate for demo-local mode
    - Permit unauthenticated startup only on loopback with bundled sample dataset IDs; disable uploads, remote adapters, real customer data, and public binding.
    - Require Authorized_Customer_Data for site-load and tariff conclusions and keep public/zonal sources contextual only.
    - Emit explicit Demo/Future labels for capabilities outside the first-release boundary.
    - _Requirements: 1.14, 1.15, 7.9, 11.1–11.5, 13.1, 13.11_
  - [x] 4.3 Write the property test for validation partitioning without corruption
    - **Property 11: Record validation partitions without corruption**
    - Generate mixed-validity datasets and assert exact accepted/rejected partitions, complete diagnostics, and preservation of earlier versions after dataset failure.
    - **Validates: Requirements 1.2, 1.4, 1.5, 1.6**
  - [x] 4.4 Write ingestion boundary and one-million-record benchmark tests
    - Cover DST folds, tolerance boundaries, missing metadata, stale-data decisions, zero-valid datasets, separate durations, and a generated local snapshot of 1,000,000 records without imposing an unsupported runtime target.
    - _Requirements: 1.1, 1.7–1.12_

- [x] 5. Complete independent interval validation
  - [x] 5.1 Implement the Simulation_Engine energy model
    - Produce exactly one complete record per interval using kWh, duration-adjusted kW bounds, generation/load decomposition, gross grid flows, battery flows, explicit losses, served load, and critical/noncritical unserved load.
    - Enforce declared grid and asset availability, permissions, bounds, reserve behavior, and simultaneous-flow rules; reject missing inputs or impossible schedules without partial results.
    - _Requirements: 2.1–2.9, 3.3–3.7_
  - [x] 5.2 Implement the independent ConstraintChecker with focused tests
    - Recompute conservation, decompositions, grid/asset/storage/reserve/service bounds, SOC transitions, direction rules, and terminal treatment without using optimizer constraint-building code.
    - Reject candidates with interval-level residual diagnostics outside versioned tolerances.
    - Add deterministic tests for one valid multi-interval schedule and one violation of each checked constraint class.
    - _Requirements: 2.3–2.10, 3.3–3.7_
  - [ ]* 5.3 Write the property test for complete, conserved, independently valid schedules
    - **Property 1: Complete, conserved, independently valid schedules**
    - **Validates: Requirements 2.1–2.5, 2.9, 2.10, 3.1, 3.3**
  - [ ]* 5.4 Write the property test for storage state transitions and bounds
    - **Property 2: Storage state transition and bounds**
    - **Validates: Requirements 3.4–3.7**
  - [ ]* 5.5 Write the property test for unsupported simultaneous flows
    - **Property 3: Unsupported simultaneous flows never occur**
    - **Validates: Requirements 2.6, 2.7**

- [x] 6. Build exactly three dispatch alternatives
  - [x] 6.1 Implement existing-operation and documented rule-based schedules with focused tests
    - Produce the common Schedule schema from the frozen bundled scenario and require independent-checker success.
    - Keep rule behavior explicit and versioned; add fixed-sample tests for both alternatives and no extra strategies.
    - _Requirements: 2.10, 4.1, 4.2, 4.8, 11.1_
  - [x] 6.2 Implement the SciPy SolverPort adapter and bounded MILP with a known-optimum test
    - Build the cost-minimizing model with hard bounds, required service/storage constraints, and direction binaries only when needed; use physical bounds rather than arbitrary big-M values.
    - Publish a candidate only after independent checking and test one tiny enumerated optimum.
    - _Requirements: 3.1–3.8, 4.1_
  - [x] 6.3 Map solver outcomes with table-driven focused tests
    - Map optimal, feasible-at-timeout, timeout-without-solution, proven-infeasible, numerical-failure, and constraint-check-failed outcomes with required schedule/objective presence rules.
    - Reject optimization without completed simulation and test every status using deterministic stubs.
    - _Requirements: 3.8–3.13_
  - [ ]* 6.4 Write the property test for optimization objective reconciliation
    - **Property 4: Optimization objective reconciles to disclosed components**
    - **Validates: Requirements 3.1, 3.2, 3.6, 3.8**
  - [ ]* 6.5 Add broad solver adapter edge-case tests
    - Extend beyond the required known optimum and status table only if time permits.
    - _Requirements: 3.8–3.13_

- [x] 7. Calculate transparent sample Screening_Estimate cost
  - [x] 7.1 Implement the SampleCostCalculator with focused arithmetic and disclosure tests
    - Apply one dated, versioned Sample_Screening_Rate_Configuration to gross imports and exports for the bundled scenario using existing decimal/unit types.
    - Label every cost and savings value `Screening_Estimate`; disclose currency, units, effective period, source or assumption label, and exclusions.
    - State that the configuration is not a verified tariff, historical reconciliation, account-applicability decision, or future-savings validation; add a direct Decimal-oracle test.
    - _Requirements: 5.1–5.3_
  - [ ]* 7.2 Implement post-MVP held-out tariff reconciliation
    - Add verified tariff/account evidence and line-item reconciliation only after the judge MVP.
    - _Requirements: 5.4–5.14_
  - [ ]* 7.3 Write the property test for line-item-strict reconciliation
    - **Property 5: Historical tariff reconciliation is line-item strict**
    - **Validates: Requirements 5.6–5.10**
  - [ ]* 7.4 Write the property test for verified tariff effective dates and future labels
    - **Property 6: Verified tariff effective dates and future labels are preserved**
    - **Validates: Requirements 5.11–5.14**

- [ ] 8. Add required sample metrics
  - [x] 8.1 Implement deterministic outage-service metrics with focused tests
    - Validate the declared sample outage inputs, force grid bounds to zero while unavailable, and calculate critical unserved kWh and interruption hours.
    - Label results deterministic `Outage_Service_Screening`, not probabilistic reliability; test declared, missing-input, and not-evaluated cases.
    - _Requirements: 6.1–6.6_
  - [x] 8.2 Implement emissions and clean-energy metrics with focused tests
    - Calculate purchased-electricity emissions from gross nonnegative imports, report exports separately, and attribute grid charging at import time.
    - Calculate origin-aware clean-energy share and zero-denominator N/A behavior; test with direct arithmetic oracles and complete factor metadata.
    - _Requirements: 4.3–4.5, 8.1–8.7_
  - [ ]* 8.3 Write the property test for gross-import emissions
    - **Property 7: Purchased-electricity emissions use gross imports only**
    - **Validates: Requirements 8.1, 8.2, 8.7**
  - [ ]* 8.4 Add broad outage and metric edge-case tests
    - Extend generated and disclosure coverage beyond the required focused cases only if time permits.
    - _Requirements: 4.4, 4.5, 6.1–6.6, 8.3–8.6_

- [x] 9. Orchestrate and present the sample comparison
  - [x] 9.1 Implement all-or-nothing exactly-three orchestration with focused tests
    - Run existing, rule-based, and optimized alternatives against one bundled manifest and publish only when all three pass independent checks.
    - Attach sample cost, outage, emissions, clean-energy, peak import, solver, and checker results; test exact membership, shared inputs, and all-or-nothing failure.
    - _Requirements: 4.1–4.8, 11.1, 11.2_
  - [x] 9.2 Implement report models and exact Fast_Judge_MVP disclosures with snapshot tests
    - Produce one stable comparison model containing manifest/sample identity, exactly three alternatives, required metrics, assumptions, exclusions, and report fingerprint.
    - State sample-only Screening_Estimate, deterministic outage screening, no verified tariff, no customer data, no local-grid feasibility, and no AI/weather/demand forecasting; describe optimization only as constrained grid intelligence.
    - Add focused schema/snapshot tests and forbidden-claim assertions.
    - _Requirements: 2.11, 4.3–4.9, 5.2, 5.3, 6.4, 8.3–8.6, 11.1–11.4_
  - [ ]* 9.3 Write the property test for transparent three-alternative decisions
    - **Property 12: Three-alternative sample decisions are transparent**
    - **Validates: Requirements 4.1–4.8, 5.1–5.3, 11.1, 11.2**
  - [ ]* 9.4 Write the property test for fail-closed judge capabilities
    - **Property 13: Judge capabilities fail closed**
    - **Validates: Requirements 1.14, 1.15, 7.11, 11.1–11.4, 13.1, 13.12, 13.13**

- [ ] 10. Defer policy intelligence
  - [ ]* 10.1 Implement reviewed policy snapshots only after the judge MVP
    - Keep policy administration and calculation use absent from public routes until implemented and reviewed.
    - _Requirements: 9.1–9.9_
  - [ ]* 10.2 Add deferred policy snapshot tests
    - Test immutable pinning, applicability, missing evidence, and review gates when Task 10.1 is selected.
    - _Requirements: 9.1–9.9_

- [ ] 11. Defer multi-state activation and isolation
  - [ ]* 11.1 Implement state-pack activation and no-fallback isolation after the judge MVP
    - Reuse existing Massachusetts reference metadata; add activation, resolution, and cross-state contracts only when expansion is selected.
    - _Requirements: 10.3–10.11_
  - [ ]* 11.2 Write the deferred state-pack isolation property test
    - **Property 8: State-pack isolation and canonical invariants**
    - **Validates: Requirements 10.3–10.11**

- [ ] 12. Defer real-data, private, production, and tenant security modules
  - [ ]* 12.1 Implement post-MVP SecurityReadiness and authorization
    - Do not expose customer/private/production paths before every applicable control passes.
    - _Requirements: 13.2–13.11_
  - [ ]* 12.2 Implement post-MVP tenant repositories and audit lifecycle
    - Add tenant isolation, audit, retention, deletion, and backup propagation only before real customer operations.
    - _Requirements: 13.6–13.9_
  - [ ]* 12.3 Write the deferred production-security property test
    - **Property 14: Production security gates real data**
    - **Validates: Requirements 13.2–13.11**
  - [ ]* 12.4 Add deferred customer-security integration tests
    - Exercise role, tenant, audit, retention, backup, and incident controls only with synthetic data.
    - _Requirements: 13.2–13.11_

- [ ] 13. Defer commercial-validation evidence operations
  - [ ]* 13.1 Implement append-only commercial evidence records after the judge MVP
    - Keep the module absent from public routes and independent from calculations.
    - _Requirements: 12.1, 12.3, 12.5, 12.7, 12.9_
  - [ ]* 13.2 Implement evidence-derived paid-validation gates
    - Derive claims only from qualifying evidence and preserve the unvalidated statement otherwise.
    - _Requirements: 12.2–12.8_
  - [ ]* 13.3 Write the deferred evidence-only claims property test
    - **Property 15: Commercial claims derive only from evidence**
    - **Validates: Requirements 12.2–12.8**

- [x] 14. Deliver the local and Render sample-only application
  - [x] 14.1 Implement the minimal HTML/JSON sample endpoints with focused route tests
    - Expose `/`, `/api/sample-report`, optional bodyless `/api/sample-run`, and `/healthz`; render existing application results without duplicating calculations.
    - Accept no uploads or caller-supplied scenario data and test the minimal success/error contracts.
    - _Requirements: 11.1–11.4, 13.1, 13.12, 14.5, 14.16_
  - [x] 14.2 Implement deterministic human and JSON report export with compatibility tests
    - Render one comparison page and stable JSON from the immutable report model, preserving sample identity, fingerprints, three alternatives, metrics, assumptions, exclusions, statuses, and disclosures.
    - Add schema compatibility and exact forbidden-claim tests.
    - _Requirements: 2.11, 4.3–4.9, 5.1–5.3, 6.3–6.5, 8.2–8.6, 11.1–11.4, 14.16_
  - [x] 14.3 Add the deterministic local end-to-end test before deployment
    - In one in-process test, initialize bundled bytes in temporary state, execute all three alternatives, independently check each schedule, calculate every metric, and request the HTML and JSON report.
    - Assert a stable report fingerprint, exact labels, and representative denied routes; make this test pass before Task 14.4.
    - _Requirements: 2.1–2.11, 3.1–3.13, 4.1–4.9, 5.1–5.3, 6.1–6.6, 8.1–8.7, 11.1–11.4, 13.1, 13.12, 13.13, 14.5, 14.16_
  - [x] 14.4 Implement fail-closed Render `demo-public` startup with focused configuration tests
    - Add minimal Render free Python-service configuration and pinned start command using the existing runtime, Git deployment, platform bind host and `$PORT`; add no Docker, database service, authentication, worker, paid resource, or persistent disk.
    - Initialize fresh ephemeral state from bundled non-customer samples on every boot and expose only health, sample report/flow, and required static assets.
    - Fail startup if uploads, arbitrary source registration, remote adapters, customer/commercial/policy/state/tariff/forecast operations, non-sample sources, response-visible secrets, workers, persistence claims, or deferred runtime imports are enabled.
    - Add local startup configuration tests for safe and unsafe matrices.
    - _Requirements: 7.11, 11.1–11.4, 13.12, 13.13, 14.5, 14.6, 14.15–14.17_
  - [x] 14.5 Add local `demo-public` route, readiness, secret, and restart tests
    - Boot twice with fresh temporary state and platform-like host/`$PORT`; require `/healthz` readiness only after sample initialization and compare deterministic report fingerprints.
    - Assert every non-allowlisted and deferred route is denied, no secret appears in responses, and `demo-local` remains loopback-only.
    - _Requirements: 13.1, 13.11–13.13, 14.5, 14.15, 14.16_
  - [x] 14.6 Implement the bounded hosted smoke validator with mocked focused tests
    - Accept only a configured HTTPS base URL; bound retries and timeouts for cold starts; check `/healthz`, sample report fingerprint, and representative denied routes without sending code, secrets, customer data, or arbitrary payloads.
    - Add mocked tests for success, cold-start retry, fingerprint mismatch, non-HTTPS URL, timeout, and unexpectedly open routes.
    - _Requirements: 13.12, 13.13, 14.5, 14.6, 14.10, 14.15, 14.16_
  - [x] 14.7 Wire hosted and local judge paths into submission metadata and validators
    - Require the Render HTTPS URL, `/healthz`, deterministic report fingerprint, and `make demo` fallback in Submission_Metadata and local submission validation.
    - Document cold-start, ephemeral/no-persistence, free-tier volatility, and local fallback without adding credentials or account-provisioning tasks.
    - Add pass/fail fixture tests for these fields and disclosures.
    - _Requirements: 14.2, 14.4–14.6, 14.11, 14.15–14.17_

- [x] 15. Checkpoint - Run all Fast Judge MVP checks
  - Run the deterministic local end-to-end test, full test suite, strict type check, package build, task-hook self-check, and submission validator; fix failures before packaging.
  - _Requirements: 14.3–14.5, 14.15, 14.16_

- [x] 16. Create and validate the judge-ready repository package
  - [x] 16.1 Finalize submission artifacts and automated repository validation
    - Complete `README.md`, evidence-based submission write-up, `THIRD_PARTY_NOTICES.md`, versioned Submission_Metadata, and licensed bundled assets with exact setup, `make demo`, and `make check` instructions.
    - Describe implemented optimization as grid intelligence, explicitly state that the judge MVP contains no AI/weather/demand forecasting, and claim only Kiro/tools evidenced in the repository.
    - Validate required tracked files and `.kiro` content, ignore rules, public URL placeholder/value, notices, cold-start/ephemeral/free-tier disclosures, secret/customer-data exclusions, and Final_Submission_Commit consistency with automated pass/fail fixtures.
    - _Requirements: 14.1–14.17_

- [ ] 17. Keep future capabilities outside the judge dependency path
  - [ ]* 17.1 Add live source adapters after source and licensing validation
    - Reuse the immutable bytes-to-dataset contract and keep remote adapters unavailable in the public demo.
    - _Requirements: 1.8, 1.12, 7.9, 10.9_
  - [ ]* 17.2 Add operational forecasting only after separate commercial validation
    - Use issue-time-safe inputs and time-ordered evaluation; do not modify judge routes or claims.
    - _Requirements: 7.1–7.11_
  - [ ]* 17.3 Write the deferred leakage-safe forecasting property test
    - **Property 16: Forecast evaluation prevents future leakage when enabled**
    - **Validates: Requirements 7.1–7.5**
  - [ ]* 17.4 Add other separately validated future modules
    - Add broad policy, extra states, data-center modeling, or extra strategies only behind separate evidence and tests.
    - _Requirements: 4.8, 4.9, 7.8, 9.9, 10.3–10.11, 11.6–11.9_

- [ ] 18. Establish public-business contracts, fixtures, and mode boundary
  - [-] 18.1 Add public-business domain records, configuration, and official-source fixtures with focused tests
    - Define the approved adapter, refresh, Dataset display, policy, Aggregate_Scope, forecast, business storage, maintenance, section-status, and API-envelope records using existing identifiers, quantities, timestamps, immutable records, and validation errors.
    - Add small versioned JSON/CSV fixtures for the configured official policy, historical demand, official forecast, and Supply_Context source schemas; include canonical Source_Record metadata and content hashes without customer or telemetry data.
    - Add focused validation/serialization tests for complete records, finite/unit-bearing values, field omissions, stable fingerprints, and fixture provenance; tests must read fixtures locally and perform no network access.
    - _Requirements: 15.5, 15.7–15.9, 16.2, 17.1, 17.4, 17.5, 17.8, 18.2, 19.1, 19.4, 20.2–20.4_
  - [~] 18.2 Extend the capability gate for a separate Public_Business_Mode with focused isolation tests
    - Add public-business startup settings and decisions without changing `demo-local` or `demo-public` decisions, route contracts, sample IDs, or fingerprints.
    - Require complete allowlisted adapter bounds, schemas, freshness thresholds, refresh schedules, and repositories; reject uploads, arbitrary URLs/sources, customer/private/tenant/tariff-verification, commercial mutation, and predictive-maintenance capabilities.
    - Add table-driven tests for one safe matrix, every missing/unsafe setting, configured-ID admission, and unchanged judge-mode decisions.
    - _Requirements: 15.5, 15.6, 20.1, 20.2, 20.8–20.12_

- [ ] 19. Implement approved public-source refresh and atomic publication
  - [~] 19.1 Implement bounded official-source adapters and fixture parsers with focused transport tests
    - Add explicit Massachusetts-pack adapter definitions and source-specific parsers only for the fixtures required by the five pages; do not create a generic arbitrary-URL adapter.
    - Use a standard-library HTTPS fetcher with exact host/path allowlists, redirect rejection, content-type and response-size checks, separate bounded timeouts, bounded retries, and sanitized source-specific failures.
    - Inject fixture transport in tests and cover valid responses, schema drift, malformed bytes, wrong content type, oversize response, redirect, host/path mismatch, timeout, and exhausted retries without live network calls.
    - _Requirements: 15.5, 16.1, 17.13, 20.1–20.3, 20.6, 20.12_
  - [~] 19.2 Implement RefreshCoordinator transactional publication with focused failure tests
    - Reuse content-addressed snapshots, Source_Record provenance, normalized records, and SQLite transactions to record every Refresh_Run and move a current-version pointer only after all validations pass.
    - Preserve prior versions and pointers on retrieval, parsing, provenance, schema, unit, geography, interval, coverage, freshness, or publication failure; never expose partial candidate records.
    - Use fixed clocks and fake adapters to test successful publication, unchanged-byte deduplication, every required audit field, rollback at each stage, and concurrent/current-pointer conflict behavior.
    - _Requirements: 15.7, 15.8, 17.13, 20.3–20.7_
  - [~] 19.3 Implement the public Dataset catalog, freshness states, and bounded in-process scheduler with focused tests
    - Resolve immutable current versions into complete display metadata and `current`, `stale`, `unavailable`, or `unsupported` states; stale current-use data must fail closed while retaining last-valid metadata and refresh outcome.
    - Start one scheduled refresh loop only in the business app lifecycle, prevent overlapping runs for the same adapter, and make cancellation leave repositories consistent; expose no public refresh mutation operation.
    - Test threshold boundaries with a fixed clock, missing/failed versions, scheduler due/not-due/overlap/cancellation behavior, and absence of scheduler construction in both judge modes.
    - _Requirements: 15.7, 15.8, 16.4, 17.13, 20.4–20.9, 20.11_
  - [ ]* 19.4 Write the property test for atomic traceable refresh publication
    - Add a dedicated property-test file with at least 100 examples.
    - **Property 24: Public-data refresh publication is atomic and traceable**
    - **Validates: Requirements 15.7, 15.8, 17.13, 20.2–20.7**

- [ ] 20. Implement reviewed policy snapshots and applicability
  - [~] 20.1 Implement PolicyService and policy view models with focused tests
    - Accept records only from configured official federal or Massachusetts canonical sources; validate required metadata, named review, effective dates, freshness, supersession, and informational/calculation use.
    - Create immutable pinned Policy_Snapshots, preserve historical pins, identify newer reviewed snapshots, and compute exactly one applicability status from approved public evidence with missing-evidence diagnostics.
    - Return only reviewed record values and exact canonical links with informational/not-legal-advice labels; test unofficial/missing/unreviewed records, threshold boundaries, successor links, all statuses, and historical reopen behavior from fixtures.
    - _Requirements: 16.1–16.11_
  - [ ]* 20.2 Write the property test for official reviewed policy publication
    - Add a dedicated property-test file with at least 100 examples.
    - **Property 19: Policy publication is official, reviewed, pinned, and unambiguous**
    - **Validates: Requirements 16.1–16.4, 16.6–16.9, 16.11**

- [ ] 21. Implement aggregate demand, supply, and forecast services
  - [~] 21.1 Implement historical series and Aggregate_Scope matching with focused tests
    - Normalize pinned historical demand and Supply_Context into graph/table-neutral series with complete source, units, cadence, coverage, retrieval, freshness, basis, and limitation metadata.
    - Compare series only when geography, interval, time period, and measurement basis all match; otherwise omit numeric comparison and list every mismatched dimension.
    - Test a matching fixture, each independent and combined mismatch, failed/stale Dataset versions, distinct series statuses, and identical graph/table source values.
    - _Requirements: 15.4, 15.7, 15.8, 17.1, 17.8–17.13_
  - [~] 21.2 Implement official-first forecast selection and validated baseline fallback with focused tests
    - Prefer a current matching Official_Published_Demand_Forecast and preserve all supplied or unavailable publisher quality metadata.
    - When no current official forecast exists, compute the declared time-of-week arithmetic-mean baseline, evaluate against last-value persistence on rolling time-ordered holdouts using only inputs available by simulated issue time, and validate only horizons meeting configured observation/error rules.
    - Return unavailable when fallback validation fails; label over-horizon output Long_Range_Scenario_Projection only with declared growth, weather, and supply assumptions; report prediction intervals as not produced.
    - Test hand-calculable fixtures for official preference, leakage exclusion, means, comparator/error by horizon, insufficient history, stale official data, failed validation, and the exact horizon boundary.
    - _Requirements: 17.2–17.7, 17.11, 17.13_
  - [~] 21.3 Assemble demand-and-supply business responses with focused schema tests
    - Combine historical demand, forecast/projection status, Supply_Context, scope comparison, source envelopes, section states, fingerprints, and aggregate-data limitations without recomputing service values.
    - Fail only affected sections where possible and reject unknown scope IDs, repeated parameters, malformed horizons, and unsupported requests without fallback.
    - Add deterministic schema snapshots for current, partial-unavailable, stale, mismatched, projection, and fully unavailable responses.
    - _Requirements: 15.7–15.9, 17.1–17.13_
  - [ ]* 21.4 Write the property test for official-first leakage-safe forecast selection
    - Add a dedicated property-test file with at least 100 examples.
    - **Property 20: Forecast selection is official-first and leakage-safe**
    - **Validates: Requirements 17.2–17.7, 17.11**
  - [ ]* 21.5 Write the property test for scope-safe aggregate comparison
    - Add a dedicated property-test file with at least 100 examples.
    - **Property 21: Aggregate comparison is scope-safe**
    - **Validates: Requirements 17.8–17.10, 17.13**

- [ ] 22. Present checked storage and dispatch results
  - [~] 22.1 Implement BusinessStorageService with focused no-recomputation tests
    - Build a public-data reference Scenario through existing services, then map its independently checked exactly-three report into usable capacity, power limits, reserve treatment, initial/terminal State_of_Charge, energy flows, losses, peaks, active/violated constraints, and source version.
    - Preserve each core metric, label, assumption, exclusion, solver status, and checker status; calculate only direct peak differences from existing operation and withhold all metrics for a rejected schedule.
    - Use existing report fixtures and calculator spies to test exact value fidelity, each alternative once, peak arithmetic, constraint details, sanitized rejection diagnostics, and zero presentation-layer calculation calls.
    - _Requirements: 15.5, 18.1–18.7_
  - [ ]* 22.2 Write the property test for checked storage presentation fidelity
    - Add a dedicated property-test file with at least 100 examples.
    - **Property 22: Storage presentation preserves checked results**
    - **Validates: Requirements 18.1–18.7**

- [ ] 23. Implement optimization-based maintenance windows
  - [~] 23.1 Implement MaintenancePlanner with bounded candidate optimization and focused tests
    - Validate and pin the configured asset, horizon, starts, duration, availability, constraints, demand forecast, Supply_Context, objective components, and checker tolerance before evaluating any candidate.
    - For every allowed contiguous window, mark the declared asset unavailable, reuse the existing Simulation_Engine and Optimizer, reject failed hard constraints or independent checks, and select the lowest declared objective with earliest-start tie-breaking.
    - Add hand-enumerated tests for a known best window, tie, invalid/noncontiguous input, pinned versions despite current-version changes, candidate checker failure, all-infeasible result, and complete conflict diagnostics.
    - _Requirements: 19.1–19.6_
  - [~] 23.2 Implement maintenance result presentation and unsupported predictive states with focused tests
    - Report selected start/end, duration, asset, objective/components, peak and unserved-load impacts, binding constraints, input versions, solver/checker statuses, or no-plan diagnostics.
    - Label every result a planning estimate and not predictive maintenance; expose explicit unsupported text and no telemetry, health score, remaining-useful-life, or failure-prediction fields or operations.
    - Add stable schema snapshots for successful, infeasible, missing, invalid, stale, and unsupported-predictive cases.
    - _Requirements: 15.8, 15.9, 19.4–19.9_
  - [ ]* 23.3 Write the property test for pinned feasible maintenance optimization
    - Add a dedicated property-test file with at least 100 examples.
    - **Property 23: Maintenance plans are pinned, feasible, and optimal among candidates**
    - **Validates: Requirements 19.1–19.6**

- [ ] 24. Deliver the isolated five-page business application
  - [~] 24.1 Implement the separate Starlette business app and strict API routes with focused tests
    - Add a distinct ASGI entry point that composes only public-business services and serves the five page fallbacks, six read-only APIs, business assets, and readiness after gate/repository/fixture/view initialization.
    - Validate exact configured query IDs and bounded horizons; reject request bodies, non-GET methods, judge routes, unknown routes, uploads, arbitrary URL/source, customer/tariff/tenant/commercial, predictive, and non-allowlisted adapter operations before fetch or storage.
    - Add route/schema tests for success, initialization, partial unavailable states, malformed queries, sanitized errors, no-side-effect denials, and a route/service-set comparison with both judge apps.
    - _Requirements: 15.1, 15.5–15.9, 20.8–20.12_
  - [~] 24.2 Build the React five-page shell, navigation, and accessibility primitives with focused no-dependency tests
    - Reuse React/Vite and existing visual styles; add ordinary links for Overview, Demand & Supply, Storage & Dispatch, Policy & Regulation, and Maintenance Planning, with pathname-derived current state and no router dependency.
    - Add a skip link, landmarks, one page heading, `aria-current`, accessible control names, visible `:focus-visible`, text-independent status, reduced-motion behavior, loading/error announcements, and responsive layouts.
    - Extract route/status/quantity formatting into plain JavaScript helpers and test all routes, current-link uniqueness, state labels, and edge formatting with Node's built-in test runner; keep Vite build as the JSX/CSS compilation check.
    - _Requirements: 15.1–15.3, 15.8, 15.9_
  - [~] 24.3 Implement the five page views and graph-table equivalence with focused frontend/build tests
    - Render Overview status/provenance, demand/forecast/supply, checked storage/dispatch, reviewed policy, and maintenance planning from the read-only API schemas, including current/stale/unavailable/unsupported sections and required limitations.
    - Render lightweight accessible SVG trends without a chart dependency and pair every graph, status, and comparison with a table/text representation sourced from the same view model.
    - Add pure view-model tests for graph/table equality, source links, exactly-three alternatives, policy and maintenance labels, unavailable states, and forbidden claims; build the production bundle and serve it only from the business app.
    - _Requirements: 15.1–15.9, 16.10, 17.1, 17.11, 17.12, 18.1–18.7, 19.7–19.9_
  - [ ]* 24.4 Write the property test for complete dashboard navigation
    - Add a dedicated property-test file with at least 100 examples.
    - **Property 17: Dashboard route navigation is complete**
    - **Validates: Requirements 15.1, 15.2**
  - [ ]* 24.5 Write the property test for graphical and textual value equivalence
    - Add a dedicated property-test file with at least 100 examples.
    - **Property 18: Graphical and textual values are equivalent**
    - **Validates: Requirements 15.4, 17.1**
  - [ ]* 24.6 Write the property test for fail-closed public-business isolation
    - Add a dedicated property-test file with at least 100 examples.
    - **Property 25: Public-business admission and mode isolation fail closed**
    - **Validates: Requirements 15.5, 15.6, 15.9, 20.1, 20.8–20.12**

- [ ] 25. Prove deterministic business behavior and judge compatibility
  - [~] 25.1 Add the fixture-only public-business end-to-end test
    - Initialize immutable source fixtures and provenance in temporary repositories, publish valid current versions, assemble all five pages, execute checked storage and maintenance calculations, and request every HTML/API route in one local test.
    - Assert stable fingerprints with generated time excluded, complete metadata/disclosures, graph-table equality, unavailable/stale behavior, and zero network calls; repeat from fresh state and compare outputs.
    - _Requirements: 15.1–15.9, 16.1–16.11, 17.1–17.13, 18.1–18.7, 19.1–19.9, 20.3–20.7_
  - [~] 25.2 Add judge-mode regression and cross-mode security tests
    - Boot `demo-local`, `demo-public`, and `public-business` separately and assert disjoint route/service sets, disabled adapters/scheduler/business imports in judge processes, and no fetch/storage effect from prohibited business requests.
    - Re-run existing judge HTML/JSON snapshots, bundled inputs, report fingerprints, labels, denied routes, and startup matrices unchanged; test that business failures cannot mutate judge state.
    - _Requirements: 11.1–11.4, 13.1, 13.12, 13.13, 20.9–20.12_

- [ ] 26. Complete the public-business coding checkpoint
  - [~] 26.1 Wire local checks and package data, then run the bounded release suite
    - Add the fixture files, business frontend bundle, and separate business entry point to existing package/build configuration; add narrow non-watch frontend tests and public-business integration commands without changing `make demo` judge behavior.
    - Run required fixture tests, full Python tests, strict type check, frontend tests/build, package build, task-hook self-check, submission validator, and unchanged judge regression suite; fix code or fixture failures before completion.
    - _Requirements: 14.4, 15.1–15.9, 20.9–20.12_

## Notes

- **Remaining required leaves:** 18 — 18.1–18.2; 19.1–19.3; 20.1; 21.1–21.3; 22.1; 23.1–23.2; 24.1–24.3; 25.1–25.2; and 26.1.
- **Remaining required execution waves:** 10 waves (graph waves 19–28). Up to five independent required leaves run in parallel; optional leaves remain after required public-business completion.
- Graph waves 0–18 and all existing checkbox states preserve the completed Fast Judge MVP execution history. The new app must keep its routes, fingerprints, labels, and tests unchanged.
- Every new nontrivial required leaf includes a narrow focused test. Adapter, refresh, policy, demand, supply, forecast, storage, maintenance, API, and end-to-end tests use checked-in source fixtures or injected fakes and perform no live network calls.
- Optional Properties 17–25 broaden combinations after required deterministic checks. Existing optional historical tariff, broad policy, multi-state, real customer/private/production/tenant, commercial-validation, operational-ML, data-center, and extra-strategy work remains deferred.
- Public_Business_Mode enables only the approved bounded official-source adapters, reviewed public policy, official forecast selection, and transparent validated baseline described by Requirements 15–20. Arbitrary/credentialed adapters and Operational_ML_Forecast remain deferred.
- Real customer data, verified customer tariffs, authentication/tenancy, customer-specific conclusions, feeder/service/interconnection feasibility, asset telemetry, health scoring, remaining useful life, and predictive maintenance remain unavailable.
- No new runtime or frontend dependency is planned. The separate business ASGI entry point reuses the modular monolith, SQLite/snapshots, calculation core, Starlette, and React/Vite.

### Manual Submission Checklist

- [~] Register no more than four team members and confirm the named representative is authorized to submit.
- [~] Review originality, ownership, licenses, privacy, notices, and absence of unlicensed media or marks.
- [~] Record a functioning demonstration under three minutes, upload it to an approved public host, and verify the public link.
- [~] Create or link the Render service, verify its HTTPS URL with the bounded smoke validator, and record the URL in Submission_Metadata.
- [~] Enter required track, project, repository, judge-path, Kiro, team, representative, and video data in the official form.
- [~] Record the Final_Submission_Commit and freeze submitted materials after the deadline unless organizers permit changes.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1"] },
    { "id": 3, "tasks": ["2.2"] },
    { "id": 4, "tasks": ["2.3", "3.1", "3.2"] },
    { "id": 5, "tasks": ["3.3", "3.4", "4.1", "4.2"] },
    { "id": 6, "tasks": ["4.3", "4.4", "5.1"] },
    { "id": 7, "tasks": ["5.2"] },
    { "id": 8, "tasks": ["6.1", "6.2"] },
    { "id": 9, "tasks": ["6.3", "7.1", "8.1", "8.2"] },
    { "id": 10, "tasks": ["9.1"] },
    { "id": 11, "tasks": ["9.2"] },
    { "id": 12, "tasks": ["14.1", "14.2"] },
    { "id": 13, "tasks": ["14.3"] },
    { "id": 14, "tasks": ["14.4"] },
    { "id": 15, "tasks": ["14.5", "14.6"] },
    { "id": 16, "tasks": ["14.7"] },
    { "id": 17, "tasks": ["15"] },
    { "id": 18, "tasks": ["16.1"] },
    { "id": 19, "tasks": ["18.1"] },
    { "id": 20, "tasks": ["18.2"] },
    { "id": 21, "tasks": ["19.1", "20.1", "21.1", "22.1", "24.2"] },
    { "id": 22, "tasks": ["19.2", "21.2"] },
    { "id": 23, "tasks": ["19.3", "21.3", "23.1"] },
    { "id": 24, "tasks": ["23.2"] },
    { "id": 25, "tasks": ["24.1"] },
    { "id": 26, "tasks": ["24.3"] },
    { "id": 27, "tasks": ["25.1", "25.2"] },
    { "id": 28, "tasks": ["26.1"] },
    { "id": 29, "tasks": ["19.4", "20.2", "21.4", "21.5", "22.2", "23.3", "24.4", "24.5", "24.6"] },
    { "id": 30, "tasks": ["5.3", "5.4", "5.5", "6.4", "6.5"] },
    { "id": 31, "tasks": ["7.2", "7.3", "7.4", "8.3", "8.4"] },
    { "id": 32, "tasks": ["9.3", "9.4", "10.1", "11.1", "12.1"] },
    { "id": 33, "tasks": ["10.2", "11.2", "12.2", "13.1", "17.1"] },
    { "id": 34, "tasks": ["12.3", "12.4", "13.2", "17.2", "17.4"] },
    { "id": 35, "tasks": ["13.3", "17.3"] }
  ]
}
```
