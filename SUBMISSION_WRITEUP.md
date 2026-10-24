# OmniGridX Submission Write-up

## What OmniGridX does

Electrification and new clean generation are changing when New England needs power. OmniGridX presents recent official Massachusetts and ISO New England context, eight clean or flexible resource options, and one independently checked synthetic commercial-site screening.

The calculation path runs exactly three dispatch alternatives: documented existing operation, a deterministic clean-generation-first rule, and a bounded cost-minimizing MILP. This implemented optimization is constrained grid intelligence. A separate constraint checker recomputes each candidate’s balances and physical bounds before publication.

The React interface presents operating cost, maximum site import, deterministic critical-load service and interruption, purchased-electricity emissions, and origin-aware clean-energy share. A separate `Simulated_AI_Draft` combines cited context with unchanged checked report values. It is template-generated; no model or external AI service is called. Four fictional people demonstrate ordered analyst, energy-provider, government-data, and manager review. These acknowledgements are unauthenticated, ephemeral, and incapable of spending or control.

The Fast Judge MVP contains no AI, weather, or demand forecasting. Values remain advisory screening outputs. The public flow accepts no uploads, arbitrary scenarios or URLs, customer data, remote retrieval, authenticated/private operations, real approvals, procurement, or equipment commands.

## Potential value and adoption

Energy analysts often assemble public context, calculations, assumptions, citations, and reviewer evidence across disconnected tools. OmniGridX demonstrates how one immutable run manifest, one checked comparison, one pinned fact snapshot, and an explicit review sequence could make an early screening deliverable easier to inspect.

This demo does not establish commercial demand, analyst-time savings, tariff accuracy, local-grid feasibility, government or utility endorsement, production readiness, or legal authorization. Those require evidence and controls outside this repository.

## Intentional and accessible product design

- Six explicit routes cover overview, grid data, clean options, AI draft, approvals, and sources.
- Solar, wind, hydro, nuclear, geothermal, storage, demand flexibility, and efficiency are distinguished rather than treated as interchangeable generation.
- Queue, pipeline, forecast, target, historical, and site metrics retain separate labels and limitations.
- The existing exactly-three report schema and fingerprint remain unchanged.
- Cost is always `Screening_Estimate`; outage output is deterministic `Outage_Service_Screening`.
- The AI and approval experience is visibly simulated and has no real-world authority.
- The interface uses landmarks, headings, description lists, native controls, `aria-current`, keyboard focus, live errors, responsive layouts, and reduced motion.

## Public facts and provenance

The manually curated snapshot records limited public facts from ISO New England, the Commonwealth of Massachusetts, and the U.S. Energy Information Administration, with canonical URLs, periods, units, evidence types, and limitations. It was retrieved on October 24, 2026 and is not a live feed or publisher-byte archive. Every record remains pending human validation.

The Fast Judge calculation input remains only `src/omnigridx/infrastructure/data/sample/judge-scenario-v1.json`, an original fictional sample. Public facts provide context and never alter its optimization, metrics, or report fingerprint.

## Kiro use and evidence

Development used Kiro’s spec workflow through `.kiro/specs/omnigridx/requirements.md`, `.kiro/specs/omnigridx/design.md`, `.kiro/specs/omnigridx/tasks.md`, repository steering, and `.kiro/hooks/task_validation.py` with `.kiro/hooks/task-checks.json`. No quantitative workflow-effect measurement was collected. The repository makes no claim for unrecorded Kiro features, real AI model execution, or measured workflow effects.

## Tools and deployment

The backend uses Starlette/Uvicorn, Jinja2, SciPy MILP, and immutable domain records. React and Vite compile the frontend into the same Python package. Render runs one ephemeral process because the simulated approval sequence is process-local. Pytest, Hypothesis, mypy, setuptools, and build support local verification. Ownership, licenses, sources, and attribution are listed in `THIRD_PARTY_NOTICES.md`.
