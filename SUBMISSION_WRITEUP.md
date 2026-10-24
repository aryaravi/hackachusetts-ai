# OmniGridX Submission Write-up

## What OmniGridX does

OmniGridX is a sample-only Massachusetts commercial-site energy screening application. It runs one frozen synthetic site through exactly three dispatch alternatives: documented existing operation, a deterministic solar-first rule, and a bounded cost-minimizing MILP. This implemented optimization is constrained grid intelligence. A separate constraint checker recomputes each candidate’s balances and physical bounds before the application publishes an all-or-nothing comparison.

The React judge interface presents operating cost, peak import, deterministic critical-load service, purchased-electricity emissions, and origin-aware clean-energy share. Values are advisory screening outputs. The public flow accepts no uploads, arbitrary scenarios, customer data, remote sources, or authenticated/private operations. The judge MVP contains no AI, weather, or demand forecasting.

## Potential value and adoption

Energy consultants often assemble data, dispatch calculations, assumptions, and reviewer evidence across disconnected tools. OmniGridX demonstrates how one immutable run manifest and one independently checked comparison could make an early screening deliverable easier to reproduce and review. The adoption path is intentionally narrow: validate this sample workflow, then separately add authorized customer inputs, verified account tariffs, qualified engineering review, and production security before making customer-specific conclusions.

This MVP does not establish commercial demand, measured analyst-time savings, tariff accuracy, local-grid feasibility, or production readiness. Those require evidence outside this repository.

## Intentional and accessible product design

- Exactly three alternatives prevent strategy proliferation in the judge path.
- Content hashes, explicit units, source identities, versions, and report fingerprints make outputs traceable.
- Cost is always labeled `Screening_Estimate`; outage output is deterministic `Outage_Service_Screening`.
- Public and local demos fail closed to one bundled synthetic sample and expose only health and sample-report routes.
- The interface uses semantic headings, articles, lists, description lists, native buttons, keyboard-operable controls, live status/error regions, responsive layouts, and reduced-motion styling.
- Massachusetts public-source entries are attribution and discovery metadata only; source values are not bundled or represented as customer data.

The original project contribution is the integration of immutable sample provenance, complete interval accounting, independent physical checks, three transparent dispatch paths, deterministic metrics, and fail-closed delivery into one reviewable judge flow. Third-party libraries provide the declared framework, solver, build, and test capabilities; they are inventoried in `THIRD_PARTY_NOTICES.md`.

## Kiro use and evidence

Development used Kiro’s spec workflow through `.kiro/specs/omnigridx/requirements.md`, `.kiro/specs/omnigridx/design.md`, `.kiro/specs/omnigridx/tasks.md`, repository steering, and `.kiro/hooks/task_validation.py` with `.kiro/hooks/task-checks.json`. The hooks validate exact task identity and dependency waves, then map completed tasks to bounded local checks. Property-based tests in `tests/property/` map reproducibility, provenance, and validation-partition properties to named requirements.

Kiro MCP servers and Kiro Powers were not used for product runtime behavior, and no claim is made that they were. No quantitative workflow-effect measurement was collected; the evidence is the tracked spec, hooks, steering, task history, and resulting code. The repository makes no claim for unrecorded Kiro features or tools.

## Public data and bundled assets

The Massachusetts reference pack records canonical publisher metadata for City of Boston, Commonwealth of Massachusetts, Massachusetts DEP, HIFLD, ISO New England, National Weather Service, NREL, EPA, and EIA sources. These entries support provenance and explain future source qualification; the Fast Judge MVP does not retrieve or redistribute publisher data. Its only calculation input is `src/omnigridx/infrastructure/data/sample/judge-scenario-v1.json`, an original fictional sample covered by the repository `LICENSE`.

## Tools and integrations

The Python backend uses Starlette/Uvicorn, Jinja2, SciPy MILP, and immutable domain records. The frontend uses React and Vite and is compiled to static assets served by the same Python process. Render configuration describes one free Python web service with ephemeral state. Pytest, Hypothesis, mypy, setuptools, and build support local verification and packaging. Full ownership, license, asset, and attribution details are in `THIRD_PARTY_NOTICES.md`.
